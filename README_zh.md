# EnVault

**开发环境备份、快照、上传网盘一体化工具**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Bash-4.0+-green.svg)](https://www.gnu.org/software/bash/)

解决开发环境/沙盒重启后数据丢失的痛点。

## 核心功能

- **多目录备份** - YAML 配置定义要备份的多个目录
- **智能排除** - 自动忽略 `*.log`、`node_modules` 等
- **备份加密** - GPG 对称/非对称加密
- **多格式压缩** - tar.gz, tar.bz2, tar.xz, zip
- **Restic 增量快照** - 节省存储空间
- **多网盘上传** - Catbox, Tmpfiles, Gofile, Uguu
- **多语言界面** - English, 中文, Español

## 快速开始

```bash
# 1. 安装
curl -fsSL https://raw.githubusercontent.com/savior-li/backup-tool/main/src/envault.py -o ~/bin/envault
chmod +x ~/bin/envault

# 2. 初始化配置
envault init

# 3. 编辑配置
nano ~/.config/envault/config.yaml

# 4. 执行备份
envault backup
```

## 支持平台

| 平台 | 支持 |
|------|------|
| Linux | ✅ |
| macOS | ✅ |
| Windows (WSL) | ✅ |

## 文档

- [快速开始](#快速开始)
- [完整手册](MANUAL.md) - 包含配置详解、命令参考、高级功能、定时备份、故障排除

## 命令一览

| 命令 | 说明 |
|------|------|
| `envault backup` | 完整备份（使用配置） |
| `envault backup /path` | 备份指定目录 |
| `envault backup --encrypt` | 加密备份 |
| `envault backup --format zip` | 指定压缩格式 |
| `envault restore <file>` | 恢复备份 |
| `envault list` | 查看 Restic 快照 |
| `envault prune [n]` | 清理旧快照 |
| `envault init` | 初始化配置 |
| `envault config` | 查看配置 |

## 配置示例

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
  enabled: true
  recipient: your@email.com

cloud_upload:
  catbox: true
  tmpfiles: true
  gofile: false
  uguu: false

restic:
  enabled: true
  keep_last: 10

language: zh
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `RESTIC_PASSWORD` | 快照用 | Restic 仓库密码 |
| `GPG_PASSWORD` | 解密用 | GPG 解密密码 |
| `GOFILE_ACCOUNT_ID` | Gofile 用 | Gofile 账户 ID |
| `GOFILE_TOKEN` | Gofile 用 | Gofile API Token |
| `ENVAULT_LANG` | 否 | 语言 (en/zh/es) |

## 依赖

| 依赖 | 必填 | 说明 |
|------|------|------|
| tar | 是 | 压缩工具 |
| curl | 是 | HTTP 客户端 |
| gpg | 加密用 | GPG 加密 |
| restic | 快照用 | 增量备份 |
| python3 | 推荐 | 运行 Python 版本 |
| requests | Python版 | HTTP 库 |
| pyyaml | Python版 | YAML 解析 |

## 安装依赖

```bash
# Ubuntu/Debian
apt install tar curl gpg restic

# macOS
brew install curl gpg restic

# Python 依赖
pip install requests pyyaml
```

## 多语言

```bash
export ENVAULT_LANG=zh  # 中文
export ENVAULT_LANG=es  # Español
export ENVAULT_LANG=en  # English
```

## 常见问题

<details>
<summary>Q: 如何设置定时备份？</summary>

使用 cron：

```bash
crontab -e
# 添加: 0 * * * * /path/to/envault backup
```

或使用 Systemd Timer（见 MANUAL.md）

</details>

<details>
<summary>Q: 加密备份忘记密码怎么办？</summary>

无法恢复，请妥善保管密码。建议使用非对称加密管理密钥。

</details>

<details>
<summary>Q: 备份文件太大？</summary>

1. 添加排除规则忽略 `node_modules`、`*.log` 等
2. 使用更高压缩率：`compression: tar.xz`

</details>

## 存储结构

```
~/.envault/
├── restic/              # Restic 快照
├── logs/                # 日志
├── links-*.json        # 上传链接
└── *.tar.gz            # 本地备份

~/.config/envault/
└── config.yaml         # 配置文件
```

## License

MIT License

Copyright (c) 2026 EnVault