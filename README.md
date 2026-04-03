# EnVault

**开发环境备份、快照、上传网盘一体化工具**

解决开发环境/沙盒重启后数据丢失的痛点。

## 核心功能

- **多目录备份** - YAML 配置定义要备份的多个目录
- **排除规则** - 支持通配符忽略不需要的文件
- **备份加密** - GPG 非对称/对称加密保护敏感数据
- **多格式压缩** - tar.gz, tar.bz2, tar.xz, zip
- **Restic 增量快照** - 节省存储空间
- **多网盘上传** - Catbox, Tmpfiles, Gofile, Uguu
- **多语言** - English, 中文, Español

## 支持平台

- Linux
- macOS
- Windows (WSL)

## 快速开始

### 安装

```bash
# 下载 Python 版本 (推荐)
curl -fsSL https://raw.githubusercontent.com/savior-li/backup-tool/main/src/envault.py -o ~/bin/envault
chmod +x ~/bin/envault

# 或下载 Bash 版本
curl -fsSL https://raw.githubusercontent.com/savior-li/backup-tool/main/scripts/envault.sh -o ~/bin/envault
chmod +x ~/bin/envault
```

### 初始化配置

```bash
envault init  # 创建默认配置文件
```

配置文件位置: `~/.config/envault/config.yaml`

### 基础用法

```bash
# 完整备份 (使用配置)
envault backup

# 备份指定目录
envault backup /path/to/your/data

# 恢复备份
envault restore backup-file.tar.gz

# 查看快照
envault list

# 清理旧快照
envault prune 5
```

## 配置文件

编辑 `~/.config/envault/config.yaml`:

```yaml
# 要备份的目录
backup_dirs:
  - path: ~/.openclaw
    name: openclaw
  - path: ~/projects
    name: projects

# 排除规则
exclude_patterns:
  - "*.log"
  - "*.tmp"
  - "__pycache__"
  - ".git"
  - "node_modules"

# 压缩格式
compression: tar.gz

# 加密
encryption:
  enabled: true
  recipient: your@email.com  # GPG recipient

# 云存储
cloud_upload:
  catbox: true
  tmpfiles: true
  uguu: false

# Restic 快照
restic:
  enabled: true
  keep_last: 10

# 语言
language: en
```

## 高级功能

### 加密备份

```bash
# 对称加密 (需要输入密码)
envault backup --encrypt

# 或在配置中启用
# encryption:
#   enabled: true
#   recipient: your@email.com
```

设置解密密码:
```bash
export GPG_PASSWORD="your-password"
envault restore backup.tar.gz.gpg
```

### 压缩格式

```bash
# 指定压缩格式
envault backup /path --format zip
envault backup /path --format tar.bz2
envault backup /path --format tar.xz
```

支持的格式:
- `tar.gz` - 默认，兼容性好
- `tar.bz2` - 更好的压缩率
- `tar.xz` - 最高压缩率
- `zip` - Windows 兼容

### 排除规则

```bash
# 命令行添加排除
envault backup /path --exclude "*.log" --exclude "__pycache__"

# 或在配置中定义
# exclude_patterns:
#   - "*.log"
#   - "*.tmp"
```

### 多网盘上传

| 网盘 | 认证 | 说明 |
|------|------|------|
| Catbox | 无 | 最大 200MB |
| Tmpfiles | 无 | 临时存储 |
| Gofile | 需要 | 需要 API token |
| Uguu | 无 | 临时存储 |

Gofile API 获取: https://gofile.io/api

```bash
export GOFILE_ACCOUNT_ID="your-account-id"
export GOFILE_TOKEN="your-token"
envault backup
```

## 多语言

```bash
# 设置语言
export ENVAULT_LANG=zh  # 中文
export ENVAULT_LANG=es  # 西班牙语
export ENVAULT_LANG=en  # 英语

envault backup
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `RESTIC_PASSWORD` | 快照用 | Restic 仓库密码 |
| `GPG_PASSWORD` | 解密用 | GPG 解密密码 |
| `GOFILE_ACCOUNT_ID` | Gofile 用 | Gofile 账户 ID |
| `GOFILE_TOKEN` | Gofile 用 | Gofile API Token |
| `ENVAULT_LANG` | 否 | 语言 (en/zh/es) |
| `BACKUP_DIR` | 否 | 备份存储目录 |

## 定时备份

### Cron

```bash
crontab -e

# 每小时备份
0 * * * * /path/to/envault backup >> ~/.envault/logs/cron.log 2>&1

# 每 10 分钟
*/10 * * * * /path/to/envault backup
```

### Systemd

创建 `~/.config/systemd/user/envault.service`:

```ini
[Unit]
Description=EnVault Backup

[Service]
Type=oneshot
Environment=BACKUP_DIR=%h/.envault
Environment=RESTIC_PASSWORD=your-password
ExecStart=/path/to/envault backup
```

创建 `~/.config/systemd/user/envault.timer`:

```ini
[Unit]
Description=EnVault Backup Timer

[Timer]
OnCalendar=*-*-* *:00/6
Persistent=true

[Install]
WantedBy=timers.target
```

启用:

```bash
systemctl --user daemon-reload
systemctl --user enable --now envault.timer
```

## 依赖

| 依赖 | 必填 | 说明 |
|------|------|------|
| tar | 是 | 压缩工具 |
| curl | 是 | HTTP 上传 |
| gpg | 加密用 | GPG 加密 |
| python3 | 推荐 | 运行 Python 版本 |
| requests | Python版 | HTTP 库 |
| restic | 快照用 | 增量备份 |

安装依赖:

```bash
# Ubuntu/Debian
apt install tar curl gpg restic

# macOS
brew install curl gpg restic

# Python requests
pip install requests pyyaml
```

## 存储结构

```
~/.envault/
├── restic/              # Restic 快照
├── logs/                # 日志
├── links-*.json         # 上传链接记录
└── *.tar.gz             # 本地备份
```

## 常见问题

### Q: 备份文件太大?
A: 使用 `tar.xz` 压缩，或启用排除规则忽略 `node_modules` 等大目录。

### Q: 加密备份忘记密码?
A: 无法恢复，请妥善保管密码。

### Q: Restic 仓库损坏?
A: 使用 `restic check --repo ~/.envault/restic` 检查。

### Q: 上传到 Gofile 失败?
A: 确保 `GOFILE_ACCOUNT_ID` 和 `GOFILE_TOKEN` 都已设置。

## License

MIT