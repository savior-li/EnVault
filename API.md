# EnVault API Documentation

EnVault 提供命令行接口，可供其他程序调用。

## 命令行接口

### 基本命令

```bash
envault backup                    # 完整备份
envault backup <dir>            # 备份指定目录
envault restore <file>          # 恢复备份
envault restore <file> <target> # 恢复到目标目录
envault cleanup                  # 清理旧备份
envault verify <file>           # 校验备份完整性
envault config                   # 显示配置
```

### 选项

```bash
--format <fmt>      # 压缩格式: tar.gz, tar.bz2, tar.xz, zip
--encrypt            # 启用加密
--openssl            # 使用 OpenSSL 加密
--exclude <pattern>   # 添加排除规则
--incremental        # 启用增量备份
--name <name>        # 指定备份名称
--lang <lang>        # 语言: en, zh, es
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `RESTIC_PASSWORD` | Restic 仓库密码 |
| `ENVAULT_PASSWORD` | 加密/解密密码 |
| `GOFILE_ACCOUNT_ID` | Gofile 账户 ID |
| `GOFILE_TOKEN` | Gofile API Token |
| `ENVAULT_LANG` | 语言设置 |
| `BACKUP_DIR` | 备份存储目录 |

## 配置文件格式

```yaml
backup_dirs:
  - path: ~/.openclaw
    name: openclaw

exclude_patterns:
  - "*.log"
  - "__pycache__"

compression: tar.gz

encryption:
  enabled: true
  method: openssl

cloud_upload:
  catbox: true
  tmpfiles: true

cleanup:
  enabled: true
  keep_days: 7
  keep_count: 10

incremental:
  enabled: false

verify:
  enabled: true
```

## Python 模块接口

### 导入方式

```python
import subprocess
import json
from pathlib import Path
```

### 调用示例

#### 执行备份

```python
result = subprocess.run(
    ["envault", "backup", "--format", "tar.gz"],
    capture_output=True,
    text=True
)
print(result.stdout)
```

#### 恢复备份

```python
result = subprocess.run(
    ["envault", "restore", "/path/to/backup.tar.gz", "/target/dir"],
    capture_output=True,
    text=True
)
```

#### 获取备份列表

```python
backup_dir = Path.home() / ".envault"
backups = list(backup_dir.glob("*.tar.gz"))
for b in backups:
    print(b.name)
```

#### 检查备份校验和

```python
result = subprocess.run(
    ["envault", "verify", "/path/to/backup.tar.gz.sha256"],
    capture_output=True,
    text=True
)
if result.returncode == 0:
    print("Verification passed")
```

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 失败/错误 |

## 备份文件命名规则

```
{name}-{YYYYMMDD-HHMMSS}.{compression}
```

示例：
- `openclaw-20260403-120000.tar.gz`
- `backup-20260403-120000.tar.bz2`
- `myproject-20260403-120000.zip`

## 校验和文件

每次备份会生成对应的校验文件：

```
{backup-name}-{timestamp}.tar.gz.sha256
```

内容为 SHA256 哈希值。

## 日志文件

日志位置：`~/.envault/logs/envault.log`

当日志文件超过 10MB 时自动轮转，旧的日志归档为：
```
envault-YYYYMMDD-HHMMSS.log
```

## 增量备份清单

增量备份使用清单文件追踪文件变化：
```
~/.envault/.file-manifest.json
```

## 程序化调用示例

### Bash 脚本

```bash
#!/bin/bash

# 设置密码
export ENVAULT_PASSWORD="your-password"

# 执行备份
if envault backup --incremental; then
    echo "Backup successful"
else
    echo "Backup failed"
    exit 1
fi

# 检查最新备份
latest=$(ls -t ~/.envault/*.tar.gz | head -1)
echo "Latest backup: $latest"
```

### Python 脚本

```python
#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path

def run_backup(incremental=False):
    cmd = ["envault", "backup"]
    if incremental:
        cmd.append("--incremental")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0

def get_backup_links():
    links = sorted(Path.home().glob(".envault/links-*.json"))
    if links:
        with open(links[-1]) as f:
            return json.load(f)
    return {}

def get_latest_backup():
    backups = list(Path.home().glob(".envault/*.tar.gz"))
    return max(backups, key=lambda p: p.stat().st_mtime) if backups else None
```

### 定时任务 (Cron)

```bash
# 每小时备份
0 * * * * ENVAULT_PASSWORD="secret" /path/to/envault backup --incremental

# 每天凌晨 3 点清理
0 3 * * * /path/to/envault cleanup
```

## 返回值

### 成功时的 JSON 输出 (links 文件)

```json
{
  "timestamp": "2026-04-03T12:00:00+00:00",
  "compression": "tar.gz",
  "encrypted": false,
  "incremental": false,
  "files": {
    "local": "/root/.envault/openclaw-20260403-120000.tar.gz",
    "catbox": "https://catbox.moe/xxx.gz",
    "tmpfiles": "https://tmpfiles.org/xxx.tgz"
  }
}
```

## 错误处理

```python
try:
    result = subprocess.run(
        ["envault", "restore", "nonexist.tar.gz"],
        capture_output=True,
        text=True,
        timeout=300
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
except subprocess.TimeoutExpired:
    print("Restore timeout")
```