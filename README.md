# DevEnv Backup Tool

开发环境数据备份、快照、上传网盘一体化工具。

## 功能特性

- 本地压缩备份 (tar.gz)
- Restic 增量快照管理
- 多网盘上传 (Catbox, Tmpfiles, Gofile)
- 备份记录管理
- 定时备份支持

## 支持平台

- Linux
- macOS
- Windows (WSL)

## 安装

### 方式一：直接下载

```bash
# 下载脚本
curl -fsSL https://raw.githubusercontent.com/savior-li/backup-tool/main/scripts/backup-tool.sh -o ~/bin/backup-tool
chmod +x ~/bin/backup-tool

# 或下载 Python 版本
curl -fsSL https://raw.githubusercontent.com/savior-li/backup-tool/main/src/backup_tool.py -o ~/bin/backup-tool.py
chmod +x ~/bin/backup-tool.py
```

### 方式二：克隆仓库

```bash
git clone https://github.com/savior-li/backup-tool.git
cd backup-tool
```

## 依赖

- `tar` - 压缩工具 (系统自带)
- `curl` - HTTP 客户端 (系统自带)
- `restic` - 增量备份工具
- `requests` - Python 版依赖 (可选)

### 安装 restic

```bash
# macOS
brew install restic

# Linux
apt install restic
# 或
yum install restic

# 或下载二进制
curl -LO https://github.com/restic/restic/releases/latest/download/restic_linux_amd64.bz2
bunzip2 restic_linux_amd64.bz2
mv restic_linux_amd64 /usr/local/bin/restic
chmod +x /usr/local/bin/restic
```

### 安装 Python 依赖 (Python 版本)

```bash
pip install requests
```

## 配置

### 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `RESTIC_PASSWORD` | 是 | Restic 仓库密码 |
| `GOFILE_ACCOUNT_ID` | 否 | Gofile 账户 ID |
| `GOFILE_TOKEN` | 否 | Gofile 令牌 |
| `BACKUP_DIR` | 否 | 备份存储目录 (默认: ~/.backup-tool) |
| `OPENCLAW_DIR` | 否 | 要备份的目录 (默认: ~/.openclaw) |

### 设置密码

```bash
export RESTIC_PASSWORD="your-strong-password"
```

建议将配置添加到 `~/.bashrc` 或 `~/.zshrc`:

```bash
echo 'export RESTIC_PASSWORD="your-strong-password"' >> ~/.bashrc
source ~/.bashrc
```

## 使用

### 完整备份

```bash
# 备份 OpenClaw 数据
backup-tool backup

# 备份指定目录
backup-tool backup /path/to/your/data
```

### 恢复备份

```bash
# 恢复到默认目录
backup-tool restore backup-file.tar.gz

# 恢复到指定目录
backup-tool restore backup-file.tar.gz /target/path
```

### 快照管理

```bash
# 查看快照列表
backup-tool list

# 清理旧快照，保留最近 5 个
backup-tool prune 5

# 保留最近 10 个 (默认)
backup-tool prune
```

### Python 版本

```bash
# 完整备份
python backup-tool.py backup

# 恢复
python backup-tool.py restore backup-file.tar.gz

# 列出快照
python backup-tool.py list
```

## 定时备份

### Cron 示例

每 10 分钟执行一次备份:

```bash
crontab -e

# 添加以下行
*/10 * * * * /path/to/backup-tool backup >> ~/.backup-tool/logs/backup-cron.log 2>&1
```

每 6 小时执行一次:

```bash
0 */6 * * * /path/to/backup-tool backup >> ~/.backup-tool/logs/backup-cron.log 2>&1
```

### Systemd 定时器 (Linux)

创建服务文件 `~/.config/systemd/user/backup-tool.service`:

```ini
[Unit]
Description=DevEnv Backup Tool

[Service]
Type=oneshot
Environment=BACKUP_DIR=%h/.backup-tool
Environment=RESTIC_PASSWORD=your-password
ExecStart=/path/to/backup-tool backup
```

创建定时器文件 `~/.config/systemd/user/backup-tool.timer`:

```ini
[Unit]
Description=Run backup-tool every 6 hours

[Timer]
OnCalendar=*-*-* *:00/6
Persistent=true

[Install]
WantedBy=timers.target
```

启用定时器:

```bash
systemctl --user daemon-reload
systemctl --user enable --now backup-tool.timer
```

## 备份存储

### 目录结构

```
~/.backup-tool/
├── restic/              # Restic 快照存储
├── logs/                # 日志文件
├── openclaw-backup-*.tar.gz  # 压缩备份
├── links-*.json         # 上传链接记录
└── config               # 配置文件 (可选)
```

### 上传链接

备份完成后，链接会保存到 `links-*.json` 文件:

```json
{
  "timestamp": "2026-04-03T12:00:00+00:00",
  "files": {
    "local": "/root/.backup-tool/openclaw-backup-20260403-120000.tar.gz",
    "catbox": "https://catbox.moe/xxx.gz",
    "tmpfiles": "https://tmpfiles.org/xxx.tgz",
    "gofile": "https://gofile.io/d/xxx"
  }
}
```

## 常见问题

### Q: RESTIC_PASSWORD 未设置
A: 必须设置此变量才能使用快照功能。设置方法见上文"配置"部分。

### Q: restic 仓库损坏
A: 可以使用 `restic check --repo ~/.backup-tool/restic` 检查仓库完整性。

### Q: 上传失败
A: 检查网络连接。Catbox 和 Tmpfiles 无需认证，Gofile 需要设置 `GOFILE_ACCOUNT_ID` 和 `GOFILE_TOKEN`。

## License

MIT