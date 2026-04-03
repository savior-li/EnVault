# EnVault User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
5. [Commands](#commands)
6. [Advanced Features](#advanced-features)
7. [Scheduled Backup](#scheduled-backup)
8. [Troubleshooting](#troubleshooting)

---

## Introduction

### What is EnVault?

EnVault is a development environment backup tool that solves:

- Data loss after cloud environment restart (GitHub Codespaces, Replit)
- Configuration loss from sandbox reset
- Need to sync development environments across devices

### Features

| Feature | Description |
|---------|-------------|
| Multi-directory backup | Backup multiple directories at once |
| Smart exclusion | Skip temp files, logs, etc. |
| Backup encryption | GPG protection for sensitive data |
| Multiple formats | tar.gz, tar.bz2, tar.xz, zip |
| Incremental snapshots | Restic for space-efficient versioning |
| Multi-cloud upload | Catbox, Tmpfiles, Uguu, Gofile |
| Multi-language | English, 中文, Español |

### How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Source     │ ──▶ │   EnVault    │ ──▶ │  Local Backup   │
│ ~/.openclaw │     │  (pack+encrypt)│     │  ~/.envault/    │
└─────────────┘     └──────────────┘     └─────────────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    ▼                             ▼                             ▼
             ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
             │   Catbox    │            │   Tmpfiles  │            │    Uguu     │
             │ catbox.moe  │            │ tmpfiles.org│            │   uguu.se   │
             └─────────────┘            └─────────────┘            └─────────────┘
```

---

## Installation

### Requirements

- Linux / macOS / Windows (WSL)
- Python 3.8+ or Bash 4.0+
- Dependencies: tar, curl, gpg (for encryption), restic (for snapshots)

### Install

#### Method 1: Download Script (Recommended)

```bash
mkdir -p ~/bin
curl -fsSL https://raw.githubusercontent.com/savior-li/backup-tool/main/src/envault.py -o ~/bin/envault
chmod +x ~/bin/envault
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Method 2: Clone Repository

```bash
git clone https://github.com/savior-li/backup-tool.git ~/envault
cd ~/envault
```

#### Method 3: pip Install

```bash
pip install envault
```

### Install Dependencies

```bash
# Ubuntu/Debian
apt update && apt install -y tar curl gpg restic

# macOS
brew install curl gpg restic

# Python dependencies
pip install requests pyyaml
```

---

## Quick Start

### 1. Initialize Config

```bash
envault init
```

Creates default config at `~/.config/envault/config.yaml`.

### 2. Edit Config

```bash
nano ~/.config/envault/config.yaml
```

Basic example:

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
```

### 3. Run Backup

```bash
envault backup
```

Output:

```
[2026-04-03 12:00:00] Starting backup process...
[2026-04-03 12:00:02] Backup complete: /root/.envault/envault-20260403-120002.tar.gz
[2026-04-03 12:00:03] Upload successful: https://catbox.moe/xxx.gz
```

### 4. View Backup Links

```bash
cat ~/.envault/links-*.json | tail -1
```

### 5. Restore Backup

```bash
envault restore ~/.envault/envault-20260403-120002.tar.gz
```

---

## Configuration

### Full Configuration

```yaml
# Backup directories
backup_dirs:
  - path: ~/.openclaw
    name: openclaw
  - path: ~/projects/myapp
    name: myapp

# Exclusion patterns
exclude_patterns:
  - "*.log"
  - "*.tmp"
  - "__pycache__"
  - ".git"
  - "node_modules"
  - ".cache"

# Compression: tar.gz, tar.bz2, tar.xz, zip
compression: tar.gz

# Encryption
encryption:
  enabled: false
  # recipient: your@email.com  # For asymmetric encryption

# Cloud upload (true/false)
cloud_upload:
  catbox: true      # https://catbox.moe (no auth, 200MB max)
  tmpfiles: true    # https://tmpfiles.org (no auth)
  gofile: false     # https://gofile.io (needs API token)
  uguu: false       # https://uguu.se (no auth)

# Restic snapshots
restic:
  enabled: true
  keep_last: 10

# Language: en, zh, es
language: en
```

### Configuration Priority

Command line > Environment variables > Config file > Defaults

---

## Commands

### backup

```bash
envault backup                  # Full backup (uses config)
envault backup /path           # Backup specific directory
envault backup --encrypt       # Enable encryption
envault backup --format zip    # Specify compression format
envault backup --exclude "*.log"  # Add exclusion pattern
```

### restore

```bash
envault restore backup.tar.gz              # Restore to default
envault restore backup.tar.gz /target    # Restore to specific path
export GPG_PASSWORD="password"
envault restore backup.tar.gz.gpg        # Restore encrypted backup
```

### list

```bash
envault list  # Requires RESTIC_PASSWORD
```

### prune

```bash
envault prune       # Keep last 10 (default)
envault prune 5     # Keep last 5
```

### Other Commands

```bash
envault init     # Initialize config file
envault config   # Show current config
envault help     # Show help
```

---

## Advanced Features

### GPG Encryption

#### Symmetric (Simple)

```bash
envault backup --encrypt
```

#### Asymmetric (Recommended for Teams)

```bash
# Generate key pair
gpg --full-generate-key

# Configure in yaml
encryption:
  enabled: true
  recipient: your@email.com

# Or command line
envault backup --encrypt --recipient your@email.com
```

#### Decrypt Restore

```bash
export GPG_PASSWORD="password"
envault restore backup.tar.gz.gpg
```

### Multi-Cloud Strategy

| Cloud | Use Case | Limit | Auth |
|-------|----------|-------|------|
| Catbox | Long-term storage | 200MB/file | None |
| Tmpfiles | Temporary sharing | 200MB/file | None |
| Uguu | Temporary sharing | No clear limit | None |
| Gofile | Long-term storage | No limit | API token |

### Restic Snapshots

```bash
# Initialize repo
export RESTIC_PASSWORD="password"
restic init --repo ~/.envault/restic

# View snapshots
restic snapshots --repo ~/.envault/restic

# Restore specific snapshot
restic restore latest --repo ~/.envault/restic --target /restore/path

# Check integrity
restic check --repo ~/.envault/restic
```

---

## Scheduled Backup

### Cron

```bash
crontab -e

# Every hour
0 * * * * /path/to/envault backup >> ~/.envault/logs/cron.log 2>&1

# Every 10 minutes
*/10 * * * * /path/to/envault backup

# Daily at 3am
0 3 * * * /path/to/envault backup
```

### Systemd Timer (Linux)

```ini
# ~/.config/systemd/user/envault.service
[Unit]
Description=EnVault Backup

[Service]
Type=oneshot
Environment=BACKUP_DIR=%h/.envault
Environment=RESTIC_PASSWORD=your-password
ExecStart=/path/to/envault backup
```

```ini
# ~/.config/systemd/user/envault.timer
[Unit]
Description=EnVault Backup Timer

[Timer]
OnCalendar=daily
OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now envault.timer
systemctl --user list-timers
```

---

## Troubleshooting

### Common Issues

#### Q: "command not found"

```bash
# Check PATH
echo $PATH | grep -q "$HOME/bin" && echo "OK" || echo "Add to PATH"

# Run directly
~/bin/envault backup
```

#### Q: Backup file too large

1. Check exclusion rules:
```bash
envault config
```

2. Add more exclusions:
```bash
envault backup --exclude "*.mp4" --exclude "node_modules"
```

3. Use higher compression:
```yaml
compression: tar.xz
```

#### Q: Cloud upload failed

1. Check network:
```bash
curl -I https://catbox.moe
```

2. For Gofile, set environment variables:
```bash
export GOFILE_ACCOUNT_ID="your-account-id"
export GOFILE_TOKEN="your-token"
envault backup
```

#### Q: Decrypt failed

```bash
export GPG_PASSWORD="password"
gpg --batch --decrypt backup.tar.gz.gpg 2>&1 | head
```

#### Q: Restic repo corrupted

```bash
export RESTIC_PASSWORD="password"
restic check --repo ~/.envault/restic
restic rebuild-index --repo ~/.envault/restic
```

### Debug Mode

```bash
# Bash version
bash -x envault backup

# Python version
python -v envault.py backup
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RESTIC_PASSWORD` | For snapshots | Restic repo password |
| `GPG_PASSWORD` | For decrypt | GPG decrypt password |
| `GOFILE_ACCOUNT_ID` | For Gofile | Gofile account ID |
| `GOFILE_TOKEN` | For Gofile | Gofile API token |
| `ENVAULT_LANG` | No | Language (en/zh/es) |
| `BACKUP_DIR` | No | Backup storage dir |

---

## File Structure

```
~/.envault/
├── restic/                    # Restic snapshots
│   ├── config
│   ├── data/
│   ├── index/
│   ├── snapshots/
│   └── ...
├── logs/                     # Log files
├── links-*.json             # Upload links
└── *.tar.gz                # Local backups

~/.config/envault/
└── config.yaml             # Config file
```

---

## License

MIT License

Copyright (c) 2026 EnVault