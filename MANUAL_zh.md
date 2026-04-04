# EnVault 使用手册

## 目录

1. [介绍](#介绍)
2. [安装](#安装)
3. [快速开始](#快速开始)
4. [配置详解](#配置详解)
5. [命令参考](#命令参考)
6. [高级功能](#高级功能)
7. [定时备份](#定时备份)
8. [故障排除](#故障排除)

---

## 介绍

### 什么是 EnVault？

EnVault 是一款开发环境备份工具，专门解决以下痛点：

- 云开发环境（如 GitHub Codespaces、Replit）重启后数据丢失
- 沙盒环境重置导致配置和数据消失
- 需要在不同设备间同步开发环境

### 核心特性

| 特性 | 说明 |
|------|------|
| 多目录备份 | 一键备份多个指定目录 |
| 智能排除 | 自动忽略临时文件、日志等 |
| 备份加密 | GPG 加密保护敏感数据 |
| 多格式支持 | tar.gz, tar.bz2, tar.xz, zip |
| 增量快照 | Restic 实现节省空间的版本管理 |
| 多网盘上传 | 免费云存储：Catbox, Tmpfiles, Uguu, Gofile |
| 多语言界面 | English, 中文, Español |

### 工作原理

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  源目录     │ ──▶ │  EnVault     │ ──▶ │  本地备份       │
│ ~/.openclaw │     │  (打包+加密) │     │  ~/.envault/    │
└─────────────┘     └──────────────┘     └─────────────────┘
                                                 │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
             ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
             │   Catbox    │            │   Tmpfiles  │            │    Uguu     │
             │ catbox.moe  │            │ tmpfiles.org│            │   uguu.se   │
             └─────────────┘            └─────────────┘            └─────────────┘
```

---

## 安装

### 系统要求

- Linux / macOS / Windows (WSL)
- Python 3.8+ 或 Bash 4.0+
- 依赖: tar, curl, gpg (加密用), restic (快照用)

### 安装步骤

#### 方式一：下载脚本（推荐）

```bash
# 创建 bin 目录
mkdir -p ~/bin

# 下载 Python 版本
curl -fsSL https://raw.githubusercontent.com/savior-li/EnVault/main/src/envault.py \
  -o ~/bin/envault
chmod +x ~/bin/envault

# 添加到 PATH（可选，添加到 ~/.bashrc）
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 方式二：克隆仓库

```bash
git clone https://github.com/savior-li/EnVault.git ~/envault
cd ~/envault
```

#### 方式三：Python pip 安装

```bash
pip install envault
```

### 安装依赖

```bash
# Ubuntu/Debian
apt update && apt install -y tar curl gpg restic

# macOS
brew install curl gpg restic

# Python 依赖（使用 Python 版本时）
pip install requests pyyaml
```

---

## 快速开始

### 1. 初始化配置

```bash
envault init
```

这会在 `~/.config/envault/config.yaml` 创建默认配置。

### 2. 编辑配置

```bash
nano ~/.config/envault/config.yaml
```

基础配置示例：

```yaml
backup_dirs:
  - path: ~/.openclaw
    name: openclaw
  - path: ~/projects
    name: my-projects

exclude_patterns:
  - "*.log"
  - "__pycache__"
  - "node_modules"
  - ".git"

compression: tar.gz

encryption:
  enabled: false

cloud_upload:
  catbox: true
  tmpfiles: true
  gofile: false
  uguu: false
```

### 3. 执行备份

```bash
envault backup
```

输出示例：

```
[2026-04-03 12:00:00] Starting backup process...
[2026-04-03 12:00:01] Using compression format: tar.gz
[2026-04-03 12:00:01] Excluded 42 files matching rules
[2026-04-03 12:00:02] Backup complete: /root/.envault/envault-20260403-120002.tar.gz
[2026-04-03 12:00:03] Upload successful: https://catbox.moe/xxx.gz
[2026-04-03 12:00:04] Links saved: /root/.envault/links-20260403-120004.json
```

### 4. 查看备份链接

```bash
cat ~/.envault/links-*.json | tail -1
```

### 5. 恢复备份

```bash
envault restore ~/.envault/envault-20260403-120002.tar.gz
```

---

## 配置详解

### 完整配置项

```yaml
# ============ 备份目录 ============
backup_dirs:
  - path: ~/.openclaw              # 目录路径
    name: openclaw                 # 备份名称（用于生成文件名）
  - path: ~/projects/myapp
    name: myapp

# ============ 排除规则 ============
exclude_patterns:
  # 文件类型
  - "*.log"                        # 日志文件
  - "*.tmp"                        # 临时文件
  - "*.bak"                        # 备份文件
  - "*.swp"                        # Vim 临时文件
  
  # 目录
  - "__pycache__"                  # Python 缓存
  - ".git"                         # Git 仓库
  - "node_modules"                 # npm 依赖
  - ".cache"                       # 缓存目录
  
  # 系统文件
  - ".DS_Store"                    # macOS
  - "Thumbs.db"                    # Windows

# ============ 压缩格式 ============
# 可选: tar.gz (默认), tar.bz2, tar.xz, zip
compression: tar.gz

# ============ 加密设置 ============
encryption:
  enabled: false
  
  # 对称加密（简单密码保护）
  # recipient 留空即可
  
  # 非对称加密（需要 GPG 公钥）
  # recipient: your@email.com

# ============ 云存储 ============
cloud_upload:
  catbox: true      # https://catbox.moe (无需认证，最大 200MB)
  tmpfiles: true     # https://tmpfiles.org (无需认证，临时文件)
  gofile: false     # https://gofile.io (需要 API token)
  uguu: false       # https://uguu.se (无需认证，临时文件)

# ============ Restic 快照 ============
restic:
  enabled: true
  keep_last: 10      # 保留最近 10 个快照

# ============ 语言设置 ============
# 可选: en (English), zh (中文), es (Español)
language: en
```

### 配置优先级

命令行参数 > 环境变量 > 配置文件 > 默认值

---

## 命令参考

### envault backup

完整备份（使用配置文件）：

```bash
envault backup
```

备份指定目录：

```bash
envault backup /path/to/directory
envault backup /path/to/directory --name custom-name
```

指定压缩格式：

```bash
envault backup --format zip
envault backup --format tar.xz
```

启用加密：

```bash
envault backup --encrypt
```

添加临时排除规则：

```bash
envault backup --exclude "*.log" --exclude "__pycache__"
```

### envault restore

恢复备份：

```bash
envault restore backup-file.tar.gz
```

恢复到指定目录：

```bash
envault restore backup-file.tar.gz /target/path
```

恢复加密备份：

```bash
export GPG_PASSWORD="your-password"
envault restore backup-file.tar.gz.gpg
```

### envault list

查看 Restic 快照：

```bash
envault list
```

需要设置 `RESTIC_PASSWORD` 环境变量。

### envault prune

清理旧快照：

```bash
envault prune           # 保留最近 10 个
envault prune 5         # 保留最近 5 个
envault prune 0         # 删除所有快照
```

### envault config

查看当前配置：

```bash
envault config
```

### envault init

初始化默认配置文件：

```bash
envault init
```

---

## 高级功能

### GPG 加密

#### 对称加密（简单）

```bash
envault backup --encrypt
```

加密后生成 `.tar.gz.gpg` 文件，解密时需要密码。

#### 非对称加密（推荐用于团队）

1. 生成密钥对：

```bash
gpg --full-generate-key
```

2. 备份时指定接收者：

```yaml
encryption:
  enabled: true
  recipient: your@email.com
```

3. 或命令行：

```bash
envault backup --encrypt --recipient your@email.com
```

#### 解密恢复

```bash
export GPG_PASSWORD="your-password"
envault restore backup.tar.gz.gpg
```

### 多网盘策略

| 网盘 | 适用场景 | 限制 | 认证 |
|------|----------|------|------|
| Catbox | 长期存储 | 200MB/文件 | 无 |
| Tmpfiles | 临时分享 | 200MB/文件 | 无 |
| Uguu | 临时分享 | 无明确限制 | 无 |
| Gofile | 长期存储 | 无限制 | 需要 API token |

推荐策略：

```yaml
cloud_upload:
  catbox: true      # 主要备份
  tmpfiles: true    # 快速分享
  gofile: true      # 大文件备份
  uguu: false       # 按需启用
```

### Restic 增量快照

Restic 特点：

- 只存储变化的部分
- 支持加密
- 可挂载恢复单个文件
- 支持备份到 S3 等远程存储

初始化仓库：

```bash
export RESTIC_PASSWORD="your-repo-password"
restic init --repo ~/.envault/restic
```

查看快照：

```bash
export RESTIC_PASSWORD="your-repo-password"
restic snapshots --repo ~/.envault/restic
```

恢复特定快照：

```bash
export RESTIC_PASSWORD="your-repo-password"
restic restore latest --repo ~/.envault/restic --target /restore/path
```

---

## 定时备份

### Cron

1. 编辑 crontab：

```bash
crontab -e
```

2. 添加定时任务：

```bash
# 每小时备份
0 * * * * /path/to/envault backup >> ~/.envault/logs/cron.log 2>&1

# 每 10 分钟备份（活跃开发时）
*/10 * * * * /path/to/envault backup

# 每天凌晨 3 点备份
0 3 * * * /path/to/envault backup

# 每周日凌晨 4 点备份
0 4 * * 0 /path/to/envault backup
```

### Systemd Timer（Linux）

1. 创建服务文件：

```bash
mkdir -p ~/.config/systemd/user
nano ~/.config/systemd/user/envault.service
```

内容：

```ini
[Unit]
Description=EnVault Backup Service

[Service]
Type=oneshot
Environment=BACKUP_DIR=%h/.envault
Environment=RESTIC_PASSWORD=your-password
Environment=ENVAULT_LANG=zh
ExecStart=/path/to/envault backup
StandardOutput=append:%h/.envault/logs/systemd.log
StandardError=append:%h/.envault/logs/systemd.log
```

2. 创建定时器：

```bash
nano ~/.config/systemd/user/envault.timer
```

内容：

```ini
[Unit]
Description=EnVault Backup Timer

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

3. 启用定时器：

```bash
systemctl --user daemon-reload
systemctl --user enable --now envault.timer

# 查看状态
systemctl --user list-timers
```

### macOS LaunchAgent

1. 创建 plist：

```bash
mkdir -p ~/Library/LaunchAgents
nano ~/Library/LaunchAgents/com.envault.backup.plist
```

内容：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.envault.backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/envault</string>
        <string>backup</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>EnvironmentVariables</key>
    <dict>
        <key>RESTIC_PASSWORD</key>
        <string>your-password</string>
    </dict>
</dict>
</plist>
```

2. 启用：

```bash
launchctl load ~/Library/LaunchAgents/com.envault.backup.plist
```

---

## 故障排除

### 常见问题

#### Q: 提示 "command not found"

```bash
# 检查是否添加到 PATH
echo $PATH | grep -q "$HOME/bin" && echo "OK" || echo "Add to PATH"

# 手动指定路径运行
~/bin/envault backup
```

#### Q: 备份文件太大

1. 检查排除规则是否生效：

```bash
envault config  # 查看当前排除规则
```

2. 添加更多排除：

```bash
envault backup --exclude "*.mp4" --exclude "*.zip" --exclude "node_modules"
```

3. 使用更高压缩率：

```yaml
compression: tar.xz  # 比 tar.gz 压缩率更高
```

#### Q: 云上传失败

1. 检查网络：

```bash
curl -I https://catbox.moe
```

2. Catbox/Tmpfiles/Uguu 无需认证，检查文件大小限制。

3. Gofile 需要正确设置环境变量：

```bash
export GOFILE_ACCOUNT_ID="your-account-id"
export GOFILE_TOKEN="your-token"
envault backup
```

#### Q: 解密失败

1. 确认密码正确：

```bash
export GPG_PASSWORD="your-password"
gpg --batch --decrypt backup.tar.gz.gpg 2>&1 | head
```

2. 检查是否设置正确：

```bash
echo $GPG_PASSWORD
```

#### Q: Restic 快照损坏

1. 检查仓库完整性：

```bash
export RESTIC_PASSWORD="your-password"
restic check --repo ~/.envault/restic
```

2. 修复仓库：

```bash
restic rebuild-index --repo ~/.envault/restic
```

#### Q: 权限错误

```bash
# 检查目录权限
ls -la ~/.envault/
ls -la ~/.config/envault/

# 修复权限
chmod 700 ~/.envault
chmod 700 ~/.config/envault
chmod 600 ~/.config/envault/config.yaml
```

### 调试模式

查看详细输出：

```bash
# Bash 版本
bash -x envault backup

# Python 版本
python -v envault.py backup
```

### 获取帮助

```bash
envault help
```

---

## 环境变量参考

| 变量 | 必填 | 说明 |
|------|------|------|
| `RESTIC_PASSWORD` | 快照用 | Restic 仓库密码 |
| `GPG_PASSWORD` | 解密用 | GPG 解密密码 |
| `GOFILE_ACCOUNT_ID` | Gofile 用 | Gofile 账户 ID |
| `GOFILE_TOKEN` | Gofile 用 | Gofile API Token |
| `ENVAULT_LANG` | 否 | 语言 (en/zh/es) |
| `BACKUP_DIR` | 否 | 备份存储目录 |
| `CONFIG_FILE` | 否 | 配置文件路径 |

---

## 文件结构

```
~/.envault/
├── restic/                    # Restic 快照存储
│   ├── config
│   ├── data/
│   ├── index/
│   ├── keys/
│   ├── locks/
│   ├── snapshots/
│   └── tmp/
├── logs/                     # 日志文件
│   ├── backup.log
│   └── systemd.log
├── links-20260403-120000.json   # 上传链接记录
├── envault-20260403-120000.tar.gz  # 备份文件
└── envault-20260403-120000.tar.gz.gpg  # 加密备份

~/.config/envault/
└── config.yaml              # 配置文件
```

---

## 许可证

MIT License

Copyright (c) 2026 EnVault