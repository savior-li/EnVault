#!/bin/bash
#===============================================
# DevEnv Backup Tool
# 开发环境备份、快照、上传网盘一体化工具
#===============================================

set -e

VERSION="1.0.0"
BACKUP_DIR="${BACKUP_DIR:-$HOME/.backup-tool}"
OPENCLAW_DIR="${OPENCLAW_DIR:-$HOME/.openclaw}"
RESTIC_REPO="${BACKUP_DIR}/restic"
LOG_FILE="${BACKUP_DIR}/backup.log"

# 云存储配置
CATBOX_URL="https://catbox.moe/user/api.php"
TMPFILES_URL="https://tmpfiles.org/api/v1/upload"
GOFILE_URL="https://store3.gofile.io/contents/uploadFile"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# 检查依赖
check_deps() {
    local deps=("tar" "curl" "restic")
    for dep in "${deps[@]}"; do
        if ! command -v $dep &> /dev/null; then
            error "$dep 未安装"
            exit 1
        fi
    done
}

# 初始化目录
init_dirs() {
    mkdir -p "$BACKUP_DIR"
    mkdir -p "$BACKUP_DIR/logs"
    mkdir -p "$RESTIC_REPO"
}

# 创建备份
create_backup() {
    local source_dir="$1"
    local backup_name="$2"
    local timestamp=$(date +%Y%m%d-%H%M%S)
    local backup_file="${BACKUP_DIR}/${backup_name}-${timestamp}.tar.gz"
    
    if [ ! -d "$source_dir" ]; then
        error "源目录不存在: $source_dir"
        return 1
    fi
    
    log "开始备份: $source_dir"
    tar -czf "$backup_file" -C "$HOME" "$(basename "$source_dir")" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        log "备份完成: $backup_file"
        echo "$backup_file"
    else
        error "备份失败"
        return 1
    fi
}

# 创建 Restic 快照
create_restic_snapshot() {
    local source_dir="$1"
    local description="${2:-manual backup}"
    
    if [ -z "$RESTIC_PASSWORD" ]; then
        warn "RESTIC_PASSWORD 未设置，跳过快照"
        return 0
    fi
    
    export RESTIC_PASSWORD
    
    log "创建 Restic 快照: $source_dir"
    restic backup "$source_dir" --repo "$RESTIC_REPO" --tag "backup" --description "$description" --quiet
    
    if [ $? -eq 0 ]; then
        log "Restic 快照创建成功"
    else
        error "Restic 快照创建失败"
        return 1
    fi
}

# 上传到 Catbox
upload_catbox() {
    local file="$1"
    
    log "上传到 Catbox: $file"
    local result=$(curl -s -F "reqtype=fileupload" -F "fileToUpload=@$file" "$CATBOX_URL")
    
    echo "$result"
}

# 上传到 Tmpfiles
upload_tmpfiles() {
    local file="$1"
    
    log "上传到 Tmpfiles: $file"
    local result=$(curl -s -F "file=@$file" "$TMPFILES_URL")
    
    echo "$result"
}

# 上传到 Gofile
upload_gofile() {
    local file="$1"
    
    if [ -z "$GOFILE_ACCOUNT_ID" ] || [ -z "$GOFILE_TOKEN" ]; then
        warn "Gofile 凭证未设置，跳过"
        return 0
    fi
    
    log "上传到 Gofile: $file"
    local result=$(curl -s \
        -F "file=@$file" \
        -F "accountId=$GOFILE_ACCOUNT_ID" \
        -F "token=$GOFILE_TOKEN" \
        "$GOFILE_URL")
    
    echo "$result"
}

# 解析 JSON 响应
parse_json_url() {
    local json="$1"
    local field="$2"
    
    echo "$json" | grep -o "\"$field\":[^,}]*" | sed 's/.*"'"$field"'": *"\([^"]*\)".*/\1/' | head -1
}

# 完整备份流程
full_backup() {
    local source_dir="${OPENCLAW_DIR}"
    local backup_name="openclaw-backup"
    
    log "=== 开始完整备份流程 ==="
    
    # 1. 创建压缩包
    local backup_file=$(create_backup "$source_dir" "$backup_name")
    if [ $? -ne 0 ]; then
        error "备份失败，终止流程"
        return 1
    fi
    
    # 2. 创建 Restic 快照
    create_restic_snapshot "$source_dir" "auto-backup $(date)"
    
    # 3. 记录链接
    local links_file="${BACKUP_DIR}/links-$(date +%Y%m%d-%H%M%S).json"
    local links_json="{\"timestamp\": \"$(date -Iseconds)\", \"files\": {\"local\": \"$backup_file\"}"
    
    # 4. 上传到各个网盘
    if [ -f "$backup_file" ]; then
        # Catbox
        local catbox_result=$(upload_catbox "$backup_file")
        local catbox_url=$(echo "$catbox_result" | grep -oE 'https?://[^[:space:]]+\.(catbox\.moe|gofile\.io|tmpfiles\.org)[^[:space:]]*' | head -1)
        if [ -n "$catbox_url" ]; then
            links_json="$links_json, \"catbox\": \"$catbox_url\""
        fi
        
        # Tmpfiles (重命名为 .tgz 以避免扩展名问题)
        local tgz_file="${backup_file%.gz}.tgz"
        cp "$backup_file" "$tgz_file"
        local tmpfiles_result=$(upload_tmpfiles "$tgz_file")
        rm "$tgz_file"
        local tmpfiles_url=$(echo "$tmpfiles_result" | grep -oE 'https?://tmpfiles\.org/[^[:space:]]+' | head -1)
        if [ -n "$tmpfiles_url" ]; then
            links_json="$links_json, \"tmpfiles\": \"$tmpfiles_url\""
        fi
        
        # Gofile
        local gofile_result=$(upload_gofile "$backup_file")
        local gofile_url=$(echo "$gofile_result" | grep -oE 'https?://[^[:space:]]+gofile[^[:space:]]*' | head -1)
        if [ -n "$gofile_url" ]; then
            links_json="$links_json, \"gofile\": \"$gofile_url\""
        fi
    fi
    
    links_json="$links_json}}"
    echo "$links_json" > "$links_file"
    log "链接已记录: $links_file"
    
    log "=== 备份流程完成 ==="
}

# 恢复备份
restore_backup() {
    local backup_file="$1"
    local target_dir="$2"
    
    if [ ! -f "$backup_file" ]; then
        error "备份文件不存在: $backup_file"
        return 1
    fi
    
    target_dir="${target_dir:-$HOME/.openclaw}"
    
    log "恢复备份到: $target_dir"
    
    # 先备份现有数据
    if [ -d "$target_dir" ]; then
        local backup_old="${target_dir}.bak.$(date +%Y%m%d%H%M%S)"
        mv "$target_dir" "$backup_old"
        warn "旧数据已备份到: $backup_old"
    fi
    
    mkdir -p "$(dirname "$target_dir")"
    tar -xzf "$backup_file" -C "$HOME"
    
    log "恢复完成"
}

# 查看快照列表
list_snapshots() {
    if [ -z "$RESTIC_PASSWORD" ]; then
        warn "RESTIC_PASSWORD 未设置"
        return 1
    fi
    
    export RESTIC_PASSWORD
    restic snapshots --repo "$RESTIC_REPO"
}

# 清理旧快照
prune_snapshots() {
    local keep_last="${1:-10}"
    
    if [ -z "$RESTIC_PASSWORD" ]; then
        warn "RESTIC_PASSWORD 未设置"
        return 1
    fi
    
    export RESTIC_PASSWORD
    log "清理旧快照，保留最近 $keep_last 个"
    restic forget --repo "$RESTIC_REPO" --keep-last "$keep_last" --prune
}

# 显示帮助
show_help() {
    cat << EOF
DevEnv Backup Tool v${VERSION}

用法: backup-tool <命令> [选项]

命令:
    backup           执行完整备份流程
    backup <目录>    备份指定目录
    restore <文件>   恢复备份
    restore <文件> <目标目录> 恢复备份到指定目录
    list             列出 Restic 快照
    prune [数量]     清理旧快照，保留最近 N 个 (默认 10)
    help             显示此帮助

环境变量:
    BACKUP_DIR           备份存储目录 (默认: ~/.backup-tool)
    OPENCLAW_DIR         要备份的目录 (默认: ~/.openclaw)
    RESTIC_PASSWORD      Restic 仓库密码 (必需)
    GOFILE_ACCOUNT_ID   Gofile 账户 ID (可选)
    GOFILE_TOKEN         Gofile 令牌 (可选)

示例:
    export RESTIC_PASSWORD="your-password"
    backup-tool backup
    backup-tool restore backup-file.tar.gz
    backup-tool list
    backup-tool prune 5

EOF
}

# 主入口
main() {
    check_deps
    init_dirs
    
    local command="${1:-help}"
    shift 2>/dev/null
    
    case "$command" in
        backup)
            if [ -n "$1" ]; then
                create_backup "$1" "$(basename "$1")-backup"
            else
                full_backup
            fi
            ;;
        restore)
            if [ -z "$1" ]; then
                error "请指定备份文件"
                exit 1
            fi
            restore_backup "$1" "$2"
            ;;
        list)
            list_snapshots
            ;;
        prune)
            prune_snapshots "${1:-10}"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

main "$@"