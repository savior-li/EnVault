# EnVault

**DevEnv Backup Tool - Snapshots and Cloud Upload**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Bash-4.0+-green.svg)](https://www.gnu.org/software/bash/)

Solve data loss after dev environment/sandbox restart.

## Features

- **Multi-directory backup** - YAML config for multiple directories
- **Smart exclusion** - Skip `*.log`, `node_modules`, etc.
- **Backup encryption** - GPG symmetric/asymmetric
- **Multiple formats** - tar.gz, tar.bz2, tar.xz, zip
- **Restic snapshots** - Space-efficient versioning
- **Multi-cloud upload** - Catbox, Tmpfiles, Gofile, Uguu
- **Multi-language** - English, 中文, Español

## Quick Start

```bash
# 1. Install
curl -fsSL https://raw.githubusercontent.com/savior-li/backup-tool/main/src/envault.py -o ~/bin/envault
chmod +x ~/bin/envault

# 2. Initialize config
envault init

# 3. Edit config
nano ~/.config/envault/config.yaml

# 4. Run backup
envault backup
```

## Supported Platforms

| Platform | Support |
|----------|---------|
| Linux | ✅ |
| macOS | ✅ |
| Windows (WSL) | ✅ |

## Documentation

- [Quick Start](#quick-start)
- [Full Manual](MANUAL_en.md) - Complete guide
- [中文手册](MANUAL_zh.md)
- [Manual en Español](MANUAL_es.md)

## Commands

| Command | Description |
|---------|-------------|
| `envault backup` | Full backup (uses config) |
| `envault backup /path` | Backup specific directory |
| `envault backup --encrypt` | Enable encryption |
| `envault backup --format zip` | Specify compression |
| `envault restore <file>` | Restore backup |
| `envault list` | List Restic snapshots |
| `envault prune [n]` | Keep last n snapshots |
| `envault init` | Initialize config |
| `envault config` | Show config |

## Config Example

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

language: en
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RESTIC_PASSWORD` | For snapshots | Restic repo password |
| `GPG_PASSWORD` | For decrypt | GPG decrypt password |
| `GOFILE_ACCOUNT_ID` | For Gofile | Gofile account ID |
| `GOFILE_TOKEN` | For Gofile | Gofile API token |
| `ENVAULT_LANG` | No | Language (en/zh/es) |

## Dependencies

| Dependency | Required | Description |
|------------|----------|-------------|
| tar | Yes | Compression |
| curl | Yes | HTTP client |
| gpg | For encryption | GPG |
| restic | For snapshots | Incremental backup |
| python3 | Recommended | Run Python version |
| requests | Python | HTTP library |
| pyyaml | Python | YAML parsing |

## Install Dependencies

```bash
# Ubuntu/Debian
apt install tar curl gpg restic

# macOS
brew install curl gpg restic

# Python deps
pip install requests pyyaml
```

## Multi-language

```bash
export ENVAULT_LANG=zh  # 中文
export ENVAULT_LANG=es  # Español
export ENVAULT_LANG=en  # English
```

## FAQ

<details>
<summary>Q: How to set up scheduled backup?</summary>

Use cron:

```bash
crontab -e
# Add: 0 * * * * /path/to/envault backup
```

Or Systemd Timer (see MANUAL.md)

</details>

<details>
<summary>Q: Forgot password for encrypted backup?</summary>

Cannot recover. Keep passwords safe. Use asymmetric encryption for team use.

</details>

<details>
<summary>Q: Backup file too large?</summary>

1. Add exclusion rules to skip `node_modules`, `*.log`, etc.
2. Use higher compression: `compression: tar.xz`

</details>

## File Structure

```
~/.envault/
├── restic/              # Restic snapshots
├── logs/                # Logs
├── links-*.json        # Upload links
└── *.tar.gz            # Local backups

~/.config/envault/
└── config.yaml         # Config file
```

## License

MIT License

Copyright (c) 2026 EnVault