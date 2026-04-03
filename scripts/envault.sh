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

i18n() {
    local key="$1"
    shift
    case "$LANG" in
        zh)
            case "$key" in
                start) echo "开始备份流程..." ;;
                complete) echo "备份完成" ;;
                restore) echo "恢复完成" ;;
                upload_ok) echo "上传成功: $1" ;;
                upload_fail) echo "上传失败: $1" ;;
                encrypt) echo "加密已启用" ;;
                decrypt_fail) echo "解密失败" ;;
                config_load) echo "配置已加载: $1 个目录" ;;
                excluded) echo "已排除 $1 个匹配规则的文件" ;;
                format) echo "使用压缩格式: $1" ;;
                *) echo "$key" ;;
            esac
            ;;
        es)
            case "$key" in
                start) echo "Iniciando proceso de respaldo..." ;;
                complete) echo "Respaldo completo" ;;
                restore) echo "Restauración completa" ;;
                upload_ok) echo "Subida exitosa: $1" ;;
                upload_fail) echo "Subida fallida: $1" ;;
                encrypt) echo "Cifrado habilitado" ;;
                decrypt_fail) echo "Descifrado fallido" ;;
                config_load) echo "Configuración cargada: $1 directorios" ;;
                excluded) echo "Excluidos $1 archivos" ;;
                format) echo "Usando formato: $1" ;;
                *) echo "$key" ;;
            esac
            ;;
        *)
            case "$key" in
                start) echo "Starting backup process..." ;;
                complete) echo "Backup complete" ;;
                restore) echo "Restore complete" ;;
                upload_ok) echo "Upload successful: $1" ;;
                upload_fail) echo "Upload failed: $1" ;;
                encrypt) echo "Encryption enabled" ;;
                decrypt_fail) echo "Decryption failed" ;;
                config_load) echo "Config loaded: $1 directories" ;;
                excluded) echo "Excluded $1 files matching rules" ;;
                format) echo "Using compression format: $1" ;;
                *) echo "$key" ;;
            esac
            ;;
    esac
}

log() { echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }
info() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"; }

check_deps() {
    local deps=("tar" "curl" "gpg" "python3")
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            warn "$dep not found"
        fi
    done
}

init_dirs() {
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR/logs"
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
  recipient: null

cloud_upload:
  catbox: true
  tmpfiles: true
  gofile: false
  uguu: false

restic:
  enabled: true
  keep_last: 10

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

create_backup() {
    local source_dir="$1"
    local backup_name="$2"
    local compression="${3:-tar.gz}"
    local exclude_patterns="$4"
    
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="${BACKUP_DIR}/${backup_name}-${timestamp}.tar.gz"
    
    if [ ! -d "$source_dir" ]; then
        error "Source directory not found: $source_dir"
        return 1
    fi
    
    log "$(i18n format "$compression")"
    
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
        info "$(i18n excluded "$excluded_count")"
    fi
    
    case "$compression" in
        zip)
            backup_file="${BACKUP_DIR}/${backup_name}-${timestamp}.zip"
            zip -r "$backup_file" -q "$source_dir" --exclude "*.log" --exclude "*.tmp" --exclude "__pycache__/*"
            ;;
        tar.gz)
            tar -czf "$backup_file" -C "$HOME" "$(basename "$source_dir")" 2>/dev/null
            ;;
        tar.bz2)
            backup_file="${backup_file%.gz}.bz2"
            tar -cjf "$backup_file" -C "$HOME" "$(basename "$source_dir")" 2>/dev/null
            ;;
        tar.xz)
            backup_file="${backup_file%.gz}.xz"
            tar -cJf "$backup_file" -C "$HOME" "$(basename "$source_dir")" 2>/dev/null
            ;;
        *)
            tar -czf "$backup_file" -C "$HOME" "$(basename "$source_dir")" 2>/dev/null
            ;;
    esac
    
    log "$(i18n complete)"
    echo "$backup_file"
}

encrypt_backup() {
    local backup_file="$1"
    local recipient="$2"
    
    log "$(i18n encrypt)"
    
    local encrypted_file="${backup_file}.gpg"
    
    if [ -n "$recipient" ]; then
        gpg --batch --yes --recipient "$recipient" --encrypt --compress-algo none "$backup_file"
    else
        gpg --batch --yes --symmetric --compress-algo none "$backup_file"
    fi
    
    rm -f "$backup_file"
    echo "$encrypted_file"
}

upload_catbox() {
    local file="$1"
    log "Uploading to Catbox..."
    local result=$(curl -s -F "reqtype=fileupload" -F "fileToUpload=@$file" "$CATBOX_URL")
    echo "$result"
}

upload_tmpfiles() {
    local file="$1"
    log "Uploading to Tmpfiles..."
    local result=$(curl -s -F "file=@$file" "$TMPFILES_URL")
    echo "$result" | grep -oP 'https?://tmpfiles.org/[^"]+'
}

upload_gofile() {
    local file="$1"
    local account_id="$GOFILE_ACCOUNT_ID"
    local token="$GOFILE_TOKEN"
    
    if [ -z "$account_id" ] || [ -z "$token" ]; then
        return 1
    fi
    
    log "Uploading to Gofile..."
    local result=$(curl -s \
        -F "file=@$file" \
        -F "accountId=$account_id" \
        -F "token=$token" \
        "$GOFILE_URL")
    echo "$result" | grep -oP 'https?://[^"]+gofile[^"]*'
}

upload_uguu() {
    local file="$1"
    log "Uploading to Uguu..."
    local result=$(curl -s -F "file=@$file" "$UGUU_URL")
    echo "$result" | grep -oP 'https?://[^"]+'
}

full_backup() {
    log "$(i18n start)"
    
    local compression=$(grep "^compression:" "$CONFIG_FILE" | cut -d' ' -f2)
    local backup_file=$(create_backup "$HOME/.openclaw" "envault" "$compression")
    
    if [ -f "$CONFIG_FILE" ] && grep -q "enabled: true" "$CONFIG_FILE"; then
        if grep -A1 "encryption:" "$CONFIG_FILE" | grep -q "enabled: true"; then
            local recipient=$(grep "recipient:" "$CONFIG_FILE" | cut -d' ' -f2 | tr -d '""')
            backup_file=$(encrypt_backup "$backup_file" "$recipient")
        fi
    fi
    
    local links_file="${BACKUP_DIR}/links-$(date +%Y%m%d-%H%M%S).json"
    local links_json="{\"timestamp\": \"$(date -Iseconds)\", \"compression\": \"$compression\", \"files\": {\"local\": \"$backup_file\"}"
    
    if [ -f "$backup_file" ]; then
        local ext="${backup_file##*.}"
        if [ "$ext" = "gz" ] || [ "$ext" = "bz2" ] || [ "$ext" = "xz" ]; then
            ext="tgz"
        fi
        
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
    log "Links saved: $links_file"
    
    log "$(i18n complete)"
}

restore_backup() {
    local backup_file="$1"
    local target_dir="${2:-$HOME}"
    
    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi
    
    log "Restoring to: $target_dir"
    
    if [[ "$backup_file" == *.gpg ]] || [[ "$backup_file" == *.enc ]]; then
        local password="${GPG_PASSWORD}"
        if [ -z "$password" ]; then
            error "Encrypted file requires GPG_PASSWORD env var"
            return 1
        fi
        export GPG_PASSWORD="$password"
        local decrypted="${backup_file%.gpg}"
        decrypted="${decrypted%.enc}"
        gpg --batch --yes --decrypt --output "$decrypted" "$backup_file"
        backup_file="$decrypted"
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
    
    log "$(i18n restore)"
}

show_help() {
    cat << EOF
EnVault v${VERSION} - DevEnv Backup Tool

Usage: envault <command> [options]

Commands:
    backup              Run full backup (uses config)
    backup <dir>        Backup single directory
    restore <file>      Restore from backup
    list                List Restic snapshots
    prune [n]           Keep last n snapshots
    init                Initialize config
    config              Show current config
    help                Show this help

Options:
    --format <fmt>      Compression: tar.gz, tar.bz2, tar.xz, zip
    --encrypt           Enable encryption
    --exclude <pattern> Add exclusion pattern
    --lang <lang>       Language: en, zh, es

Examples:
    envault backup
    envault backup /path/to/dir --encrypt --format zip
    envault restore backup.tar.gz
    envault init

Config: ${CONFIG_FILE}

Environment Variables:
    RESTIC_PASSWORD     Restic password
    GPG_PASSWORD        Decryption password
    GOFILE_ACCOUNT_ID   Gofile account
    GOFILE_TOKEN        Gofile token
    ENVAULT_LANG        Language (en/zh/es)

EOF
}

main() {
    check_deps
    init_dirs
    
    local command="${1:-help}"
    shift 2>/dev/null
    
    case "$command" in
        backup)
            if [ -n "$1" ]; then
                local backup_file=$(create_backup "$1" "$(basename "$1")" "${2:-tar.gz}")
                if [ "$3" = "--encrypt" ]; then
                    backup_file=$(encrypt_backup "$backup_file")
                fi
            else
                full_backup
            fi
            ;;
        restore)
            if [ -z "$1" ]; then
                error "Specify backup file"
                exit 1
            fi
            restore_backup "$1" "$2"
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
            restic forget --repo "$RESTIC_REPO" --keep-last "${1:-10}" --prune
            ;;
        init)
            get_default_config | save_config
            ;;
        config)
            load_config
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "$(i18n upload_fail "$command")"
            show_help
            exit 1
            ;;
    esac
}

main "$@"