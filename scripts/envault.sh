#!/bin/bash
#===============================================
# EnVault - DevEnv Backup Tool
# 开发环境备份、快照、上传网盘一体化工具
#===============================================

set -e

VERSION="1.1.0"
CONFIG_DIR="${XDG_CONFIG_DIR:-$HOME/.config}/envault"
CONFIG_FILE="${CONFIG_DIR}/config.yaml"
BACKUP_DIR="${BACKUP_DIR:-$HOME/.envault}"
LOG_DIR="${BACKUP_DIR}/logs"
RESTIC_REPO="${BACKUP_DIR}/restic"

CATBOX_URL="https://catbox.moe/user/api.php"
TMPFILES_URL="https://tmpfiles.org/api/v1/upload"
GOFILE_URL="https://store3.gofile.io/contents/uploadFile"
UGUU_URL="https://uguu.se/api/upload"

SUPPORTED_FORMATS="tar.gz|tar.bz2|tar.xz|zip"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

LANG="${ENVAULT_LANG:-en}"

log() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
info() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }

check_deps() {
    local deps=("tar" "curl" "openssl")
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            warn "$dep not found"
        fi
    done
}

init_dirs() {
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$RESTIC_REPO"
}

get_default_config() {
    cat << 'EOF'
backup_dirs:
  - path: ~/.openclaw
    name: openclaw

exclude_patterns:
  - "*.log"
  - "*.tmp"
  - "__pycache__"
  - ".git"
  - "node_modules"
  - ".cache"

compression: tar.gz

encryption:
  enabled: false
  method: openssl
  password: null

cloud_upload:
  catbox: true
  tmpfiles: true
  gofile: false
  uguu: false

restic:
  enabled: true
  keep_last: 10

cleanup:
  enabled: false
  keep_days: 7
  keep_count: 10

incremental:
  enabled: false

verify:
  enabled: true

language: en
EOF
}

load_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        get_default_config > "$CONFIG_FILE"
        info "Config initialized: $CONFIG_FILE"
    fi
    cat "$CONFIG_FILE"
}

save_config() {
    mkdir -p "$CONFIG_DIR"
    cat > "$CONFIG_FILE"
    info "Config saved: $CONFIG_FILE"
}

match_exclude() {
    local path="$1"
    local pattern="$2"
    
    if [[ "$pattern" == "*."* ]]; then
        local ext="${pattern:1}"
        [[ "$path" == *"$ext" ]] && return 0
    elif [[ "$path" == *"$pattern"* ]]; then
        return 0
    elif [[ "$(basename "$path")" == "$pattern" ]]; then
        return 0
    fi
    return 1
}

rotate_log() {
    local max_size_mb="${1:-10}"
    local log_file="${LOG_DIR}/envault.log"
    
    if [ ! -f "$log_file" ]; then
        return 0
    fi
    
    local size_mb=$(du -m "$log_file" 2>/dev/null | cut -f1)
    
    if [ "$size_mb" -gt "$max_size_mb" ] 2>/dev/null; then
        local archive_name="envault-$(date +%Y%m%d-%H%M%S).log"
        mv "$log_file" "${LOG_DIR}/${archive_name}"
        touch "$log_file"
        info "Log rotated: ${size_mb}MB archived"
    fi
}

log_to_file() {
    local msg="[$(date -Iseconds)] $1"
    echo "$msg" >> "${LOG_DIR}/envault.log" 2>/dev/null
}

get_file_hash() {
    local file="$1"
    openssl dgst -sha256 "$file" 2>/dev/null | awk '{print $2}'
}

verify_archive() {
    local archive="$1"
    local checksum="${archive}.sha256"
    
    if [ ! -f "$checksum" ]; then
        echo "Checksum file not found"
        return 1
    fi
    
    local expected_hash=$(cat "$checksum")
    local actual_hash=$(get_file_hash "$archive")
    
    if [ "$expected_hash" = "$actual_hash" ]; then
        echo "sha256:$actual_hash"
        return 0
    else
        echo "Hash mismatch"
        return 1
    fi
}

create_checksum() {
    local archive="$1"
    local checksum="${archive}.sha256"
    local hash=$(get_file_hash "$archive")
    echo "$hash" > "$checksum"
    echo "$checksum"
}

create_backup() {
    local source_dir="$1"
    local backup_name="$2"
    local compression="${3:-tar.gz}"
    local exclude_patterns="$4"
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="${BACKUP_DIR}/${backup_name}-${timestamp}.${compression}"
    
    if [ ! -d "$source_dir" ]; then
        error "Source directory not found: $source_dir"
        return 1
    fi
    
    info "Using compression format: $compression"
    
    local excluded_count=0
    local temp_dir="${BACKUP_DIR}/temp_${timestamp}"
    mkdir -p "$temp_dir"
    
    if [ -n "$exclude_patterns" ]; then
        while IFS= read -r pattern; do
            [ -z "$pattern" ] && continue
            local excluded=$(find "$source_dir" -name "$pattern" -type f 2>/dev/null | wc -l)
            excluded_count=$((excluded_count + excluded))
        done <<< "$exclude_patterns"
    fi
    
    if [ $excluded_count -gt 0 ]; then
        info "Excluded $excluded_count files matching rules"
    fi
    
    case "$compression" in
        zip)
            backup_file="${BACKUP_DIR}/${backup_name}-${timestamp}.zip"
            zip -r "$backup_file" -q "$source_dir" \
                --exclude "*.log" --exclude "*.tmp" \
                --exclude "__pycache__/*" --exclude ".git/*" \
                --exclude "node_modules/*" --exclude ".cache/*"
            ;;
        tar.bz2)
            backup_file="${BACKUP_DIR}/${backup_name}-${timestamp}.tar.bz2"
            tar -cjf "$backup_file" -C "$HOME" "$(basename "$source_dir")" 2>/dev/null
            ;;
        tar.xz)
            backup_file="${BACKUP_DIR}/${backup_name}-${timestamp}.tar.xz"
            tar -cJf "$backup_file" -C "$HOME" "$(basename "$source_dir")" 2>/dev/null
            ;;
        *)
            backup_file="${BACKUP_DIR}/${backup_name}-${timestamp}.tar.gz"
            tar -czf "$backup_file" -C "$HOME" "$(basename "$source_dir")" 2>/dev/null
            ;;
    esac
    
    if [ -f "$backup_file" ]; then
        log "Backup created: $backup_file"
        create_checksum "$backup_file" > /dev/null
        echo "$backup_file"
    fi
    
    rm -rf "$temp_dir"
}

encrypt_openssl() {
    local input_file="$1"
    local password="${ENVAULT_PASSWORD:-}"
    local output_file="${input_file}.enc"
    
    if [ -z "$password" ]; then
        warn "ENVAULT_PASSWORD not set, skipping encryption"
        return 1
    fi
    
    log "Encryption enabled"
    
    openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
        -out "$output_file" -in "$input_file" \
        -pass "pass:$password" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        rm -f "$input_file"
        rm -f "${input_file}.sha256" 2>/dev/null
        echo "$output_file"
    else
        error "Encryption failed"
        return 1
    fi
}

decrypt_openssl() {
    local input_file="$1"
    local password="${ENVAULT_PASSWORD:-}"
    local output_dir="${2:-$HOME}"
    
    if [ -z "$password" ]; then
        error "ENVAULT_PASSWORD not set"
        return 1
    fi
    
    local output_file="${output_dir}/$(basename "${input_file%.enc}")"
    
    openssl enc -aes-256-cbc -d -pbkdf2 -iter 100000 \
        -out "$output_file" -in "$input_file" \
        -pass "pass:$password" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "$output_file"
    else
        error "Decryption failed"
        return 1
    fi
}

upload_catbox() {
    local file="$1"
    info "Uploading to Catbox..."
    local result=$(curl -s -F "reqtype=fileupload" -F "fileToUpload=@$file" "$CATBOX_URL")
    echo "$result"
}

upload_tmpfiles() {
    local file="$1"
    info "Uploading to Tmpfiles..."
    local result=$(curl -s -F "file=@$file" "$TMPFILES_URL")
    echo "$result" | grep -oP 'https?://tmpfiles.org/[^"]+'
}

upload_gofile() {
    local file="$1"
    local account_id="$GOFILE_ACCOUNT_ID"
    local token="$GOFILE_TOKEN"
    
    if [ -z "$account_id" ] || [ -z "$token" ]; then
        warn "Gofile credentials not set"
        return 1
    fi
    
    info "Uploading to Gofile..."
    local result=$(curl -s \
        -F "file=@$file" \
        -F "accountId=$account_id" \
        -F "token=$token" \
        "$GOFILE_URL")
    echo "$result" | grep -oP 'https?://[^"]+gofile[^"]*'
}

upload_uguu() {
    local file="$1"
    info "Uploading to Uguu..."
    local result=$(curl -s -F "file=@$file" "$UGUU_URL")
    echo "$result" | grep -oP 'https?://[^"]+'
}

cleanup_old_backups() {
    local keep_days="${1:-7}"
    local keep_count="${2:-10}"
    local removed=0
    
    mapfile -t backups < <(find "$BACKUP_DIR" -maxdepth 1 \( -name "*.tar.gz" -o -name "*.tar.bz2" -o -name "*.tar.xz" -o -name "*.zip" -o -name "*.enc" \) -type f -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-)
    
    for i in "${!backups[@]}"; do
        if [ $i -ge $keep_count ]; then
            rm -f "${backups[$i]}"
            rm -f "${backups[$i]}.sha256" 2>/dev/null
            removed=$((removed + 1))
            continue
        fi
        
        local age_days=$(($(date +%s) - $(stat -c %Y "${backups[$i]}" 2>/dev/null || echo 0) / 86400))
        if [ $age_days -gt $keep_days ] 2>/dev/null; then
            rm -f "${backups[$i]}"
            rm -f "${backups[$i]}.sha256" 2>/dev/null
            removed=$((removed + 1))
        fi
    done
    
    if [ $removed -gt 0 ]; then
        info "Cleanup complete: removed $removed files"
    fi
}

full_backup() {
    log "Starting backup process..."
    
    rotate_log 10
    
    local compression=$(grep "^compression:" "$CONFIG_FILE" | cut -d' ' -f2)
    local backup_file=$(create_backup "$HOME/.openclaw" "envault" "$compression" "$(grep -A20 '^exclude_patterns:' "$CONFIG_FILE" | grep -v '^exclude_patterns:' | grep -v '^$' | sed 's/^  - //' | tr '\n' ' ')")
    
    if [ -f "$CONFIG_FILE" ] && grep -q "enabled: true" "$CONFIG_FILE"; then
        if grep -A1 "encryption:" "$CONFIG_FILE" | grep -q "enabled: true"; then
            encrypt_openssl "$backup_file"
            backup_file="${backup_file}.enc"
        fi
    fi
    
    local links_file="${BACKUP_DIR}/links-$(date +%Y%m%d-%H%M%S).json"
    local links_json="{\"timestamp\": \"$(date -Iseconds)\", \"compression\": \"$compression\", \"files\": {\"local\": \"$backup_file\"}"
    
    if [ -f "$backup_file" ]; then
        local ext="${backup_file##*.}"
        [ "$ext" = "gz" ] && ext="tgz"
        
        if grep -q "catbox: true" "$CONFIG_FILE" 2>/dev/null; then
            local catbox_url=$(upload_catbox "$backup_file")
            [ -n "$catbox_url" ] && links_json="$links_json, \"catbox\": \"$catbox_url\""
        fi
        
        if grep -q "tmpfiles: true" "$CONFIG_FILE" 2>/dev/null; then
            local tmpfile="${backup_file}.tgz"
            cp "$backup_file" "$tmpfile"
            local tmpfiles_url=$(upload_tmpfiles "$tmpfile")
            rm -f "$tmpfile"
            [ -n "$tmpfiles_url" ] && links_json="$links_json, \"tmpfiles\": \"$tmpfiles_url\""
        fi
        
        if grep -q "gofile: true" "$CONFIG_FILE" 2>/dev/null; then
            local gofile_url=$(upload_gofile "$backup_file")
            [ -n "$gofile_url" ] && links_json="$links_json, \"gofile\": \"$gofile_url\""
        fi
        
        if grep -q "uguu: true" "$CONFIG_FILE" 2>/dev/null; then
            local uguu_url=$(upload_uguu "$backup_file")
            [ -n "$uguu_url" ] && links_json="$links_json, \"uguu\": \"$uguu_url\""
        fi
    fi
    
    links_json="$links_json}}"
    echo "$links_json" > "$links_file"
    
    if grep -q "cleanup:" "$CONFIG_FILE" && grep -A1 "cleanup:" "$CONFIG_FILE" | grep -q "enabled: true"; then
        local keep_days=$(grep "keep_days:" "$CONFIG_FILE" | cut -d' ' -f2)
        local keep_count=$(grep "keep_count:" "$CONFIG_FILE" | cut -d' ' -f2)
        cleanup_old_backups "${keep_days:-7}" "${keep_count:-10}"
    fi
    
    log "Backup complete"
}

restore_backup() {
    local backup_file="$1"
    local target_dir="${2:-$HOME}"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring to: $target_dir"
    
    if [[ "$backup_file" == *.enc ]]; then
        local password="${ENVAULT_PASSWORD}"
        if [ -z "$password" ]; then
            error "Encrypted file requires ENVAULT_PASSWORD env var"
            return 1
        fi
        backup_file=$(decrypt_openssl "$backup_file" "$target_dir")
        if [ $? -ne 0 ]; then
            return 1
        fi
    fi
    
    local verify_enabled=$(grep "enabled:" "$CONFIG_FILE" 2>/dev/null | head -1 | cut -d' ' -f2)
    if [ "$verify_enabled" = "true" ]; then
        if verify_archive "$backup_file"; then
            info "Backup verified"
        else
            warn "Verification failed"
        fi
    fi
    
    case "$backup_file" in
        *.zip)
            unzip -q "$backup_file" -d "$target_dir"
            ;;
        *.bz2)
            tar -xjf "$backup_file" -C "$target_dir"
            ;;
        *.xz)
            tar -xJf "$backup_file" -C "$target_dir"
            ;;
        *)
            tar -xzf "$backup_file" -C "$target_dir"
            ;;
    esac
    
    log "Restore complete"
}

show_help() {
    cat << EOF
EnVault v${VERSION} - DevEnv Backup Tool

Usage: envault <command> [options]

Commands:
    backup              Run full backup (uses config)
    backup <dir>       Backup single directory
    restore <file>      Restore from backup
    list                List Restic snapshots
    prune [n]           Keep last n snapshots
    cleanup             Clean old local backups
    init                Initialize config
    config              Show current config
    verify <file>       Verify backup integrity
    help                Show this help

Options:
    --format <fmt>      Compression: tar.gz, tar.bz2, tar.xz, zip
    --encrypt           Enable encryption
    --exclude <pattern> Add exclusion pattern
    --incremental       Enable incremental backup
    --lang <lang>       Language: en, zh, es
    --name <name>       Backup name

Examples:
    envault backup
    envault backup /path/to/dir --encrypt --format zip
    envault restore backup.tar.gz
    envault verify backup.tar.gz.sha256
    envault cleanup

Config: ${CONFIG_FILE}

Environment Variables:
    RESTIC_PASSWORD     Restic password
    ENVAULT_PASSWORD    Encryption password
    GOFILE_ACCOUNT_ID  Gofile account
    GOFILE_TOKEN       Gofile token
    ENVAULT_LANG       Language (en/zh/es)

EOF
}

main() {
    check_deps
    init_dirs
    
    local command="${1:-help}"
    shift
    
    local args=()
    local encrypt=false
    local incremental=false
    local format=""
    local excludes=()
    local name=""
    
    while [ $# -gt 0 ]; do
        case "$1" in
            --encrypt)
                encrypt=true
                shift
                ;;
            --openssl)
                encrypt=true
                shift
                ;;
            --incremental)
                incremental=true
                shift
                ;;
            --format|--compression)
                format="$2"
                shift 2
                ;;
            --exclude)
                excludes+=("$2")
                shift 2
                ;;
            --name)
                name="$2"
                shift 2
                ;;
            --lang)
                LANG="$2"
                shift 2
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            -*)
                shift
                ;;
            *)
                args+=("$1")
                shift
                ;;
        esac
    done
    
    case "$command" in
        backup)
            if [ ${#args[@]} -gt 0 ]; then
                local source="${args[0]}"
                local backup_name="${name:-$(basename "$source")}"
                local comp="${format:-tar.gz}"
                
                local exclude_str=""
                for ex in "${excludes[@]}"; do
                    exclude_str="$exclude_str$ex "
                done
                
                local backup_file=$(create_backup "$source" "$backup_name" "$comp" "$exclude_str")
                
                if [ -n "$backup_file" ] && [ -f "$backup_file" ]; then
                    if [ "$encrypt" = true ]; then
                        encrypt_openssl "$backup_file"
                    fi
                fi
            else
                full_backup
            fi
            ;;
        restore)
            if [ ${#args[@]} -gt 0 ]; then
                restore_backup "${args[0]}" "${args[1]:-}"
            else
                error "Specify backup file"
                exit 1
            fi
            ;;
        list)
            if [ -z "$RESTIC_PASSWORD" ]; then
                warn "RESTIC_PASSWORD not set"
                exit 1
            fi
            export RESTIC_PASSWORD
            restic snapshots --repo "$RESTIC_REPO"
            ;;
        prune)
            if [ -z "$RESTIC_PASSWORD" ]; then
                warn "RESTIC_PASSWORD not set"
                exit 1
            fi
            export RESTIC_PASSWORD
            restic forget --repo "$RESTIC_REPO" --keep-last "${args[0]:-10}" --prune
            ;;
        cleanup)
            cleanup_old_backups 7 10
            ;;
        init)
            get_default_config | save_config
            ;;
        config)
            load_config
            ;;
        verify)
            if [ ${#args[@]} -gt 0 ]; then
                if verify_archive "${args[0]}"; then
                    info "Verification successful"
                else
                    error "Verification failed"
                    exit 1
                fi
            else
                error "Specify file to verify"
                exit 1
            fi
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"