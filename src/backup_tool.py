#!/usr/bin/env python3
"""
DevEnv Backup Tool
开发环境备份、快照、上传网盘一体化工具 - Python 版本
"""

import os
import sys
import json
import argparse
import subprocess
import tarfile
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List


VERSION = "1.0.0"

# 默认配置
DEFAULT_BACKUP_DIR = Path.home() / ".backup-tool"
DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw"
DEFAULT_RESTIC_REPO = DEFAULT_BACKUP_DIR / "restic"

# API 端点
CATBOX_URL = "https://catbox.moe/user/api.php"
TMPFILES_URL = "https://tmpfiles.org/api/v1/upload"
GOFILE_URL = "https://store3.gofile.io/contents/uploadFile"


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'


def log(msg: str, color: str = Colors.GREEN):
    print(f"{color}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]{Colors.NC} {msg}")


def warn(msg: str):
    log(msg, Colors.YELLOW)


def error(msg: str):
    log(msg, Colors.RED)


def check_deps() -> bool:
    """检查依赖"""
    deps = ["tar", "curl"]
    for dep in deps:
        if not subprocess.run(["which", dep], capture_output=True).returncode == 0:
            error(f"{dep} 未安装")
            return False
    return True


def init_dirs():
    """初始化目录"""
    DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    (DEFAULT_BACKUP_DIR / "logs").mkdir(parents=True, exist_ok=True)
    (DEFAULT_RESTIC_REPO).mkdir(parents=True, exist_ok=True)


def create_backup(source_dir: Path, backup_name: Optional[str] = None) -> Optional[Path]:
    """创建压缩备份"""
    if not source_dir.exists():
        error(f"源目录不存在: {source_dir}")
        return None
    
    backup_name = backup_name or f"{source_dir.name}-backup"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = DEFAULT_BACKUP_DIR / f"{backup_name}-{timestamp}.tar.gz"
    
    log(f"开始备份: {source_dir}")
    
    try:
        with tarfile.open(backup_file, "w:gz") as tar:
            tar.add(source_dir, arcname=source_dir.name)
        log(f"备份完成: {backup_file}")
        return backup_file
    except Exception as e:
        error(f"备份失败: {e}")
        return None


def create_restic_snapshot(source_dir: Path, description: str = "manual backup") -> bool:
    """创建 Restic 快照"""
    password = os.environ.get("RESTIC_PASSWORD")
    if not password:
        warn("RESTIC_PASSWORD 未设置，跳过快照")
        return True
    
    log(f"创建 Restic 快照: {source_dir}")
    
    env = os.environ.copy()
    env["RESTIC_PASSWORD"] = password
    
    try:
        result = subprocess.run(
            ["restic", "backup", str(source_dir), 
             "--repo", str(DEFAULT_RESTIC_REPO),
             "--tag", "backup",
             "--description", description,
             "--quiet"],
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            log("Restic 快照创建成功")
            return True
        else:
            error(f"Restic 快照创建失败: {result.stderr}")
            return False
    except FileNotFoundError:
        error("restic 未安装")
        return False


def upload_catbox(file_path: Path) -> Optional[str]:
    """上传到 Catbox"""
    log(f"上传到 Catbox: {file_path}")
    
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                CATBOX_URL,
                files={"reqtype": (None, "fileupload"), "fileToUpload": f}
            )
        if response.status_code == 200:
            url = response.text.strip()
            log(f"Catbox 上传成功: {url}")
            return url
        else:
            error(f"Catbox 上传失败: {response.status_code}")
            return None
    except Exception as e:
        error(f"Catbox 上传异常: {e}")
        return None


def upload_tmpfiles(file_path: Path) -> Optional[str]:
    """上传到 Tmpfiles"""
    log(f"上传到 Tmpfiles: {file_path}")
    
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                TMPFILES_URL,
                files={"file": f}
            )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                url = data.get("data", {}).get("url", "")
                log(f"Tmpfiles 上传成功: {url}")
                return url
        error(f"Tmpfiles 上传失败: {response.text}")
        return None
    except Exception as e:
        error(f"Tmpfiles 上传异常: {e}")
        return None


def upload_gofile(file_path: Path) -> Optional[str]:
    """上传到 Gofile"""
    account_id = os.environ.get("GOFILE_ACCOUNT_ID")
    token = os.environ.get("GOFILE_TOKEN")
    
    if not account_id or not token:
        warn("Gofile 凭证未设置，跳过")
        return None
    
    log(f"上传到 Gofile: {file_path}")
    
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                GOFILE_URL,
                files={"file": f},
                data={"accountId": account_id, "token": token}
            )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                url = data.get("data", {}).get("downloadPage", "")
                log(f"Gofile 上传成功: {url}")
                return url
        error(f"Gofile 上传失败: {response.text}")
        return None
    except Exception as e:
        error(f"Gofile 上传异常: {e}")
        return None


def full_backup(source_dir: Path = DEFAULT_OPENCLAW_DIR) -> bool:
    """完整备份流程"""
    log("=== 开始完整备份流程 ===")
    
    backup_file = create_backup(source_dir)
    if not backup_file:
        error("备份失败，终止流程")
        return False
    
    create_restic_snapshot(source_dir, f"auto-backup {datetime.now().isoformat()}")
    
    links = {
        "timestamp": datetime.now().isoformat(),
        "files": {"local": str(backup_file)}
    }
    
    if backup_file.exists():
        if url := upload_catbox(backup_file):
            links["files"]["catbox"] = url
        
        tgz_file = backup_file.with_suffix(".tgz")
        tgz_file.write_bytes(backup_file.read_bytes())
        if url := upload_tmpfiles(tgz_file):
            links["files"]["tmpfiles"] = url
        tgz_file.unlink()
        
        if url := upload_gofile(backup_file):
            links["files"]["gofile"] = url
    
    links_file = DEFAULT_BACKUP_DIR / f"links-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    links_file.write_text(json.dumps(links, ensure_ascii=False, indent=2))
    log(f"链接已记录: {links_file}")
    
    log("=== 备份流程完成 ===")
    return True


def restore_backup(backup_file: Path, target_dir: Optional[Path] = None) -> bool:
    """恢复备份"""
    if not backup_file.exists():
        error(f"备份文件不存在: {backup_file}")
        return False
    
    target_dir = target_dir or DEFAULT_OPENCLAW_DIR
    
    log(f"恢复备份到: {target_dir}")
    
    if target_dir.exists():
        backup_old = Path(str(target_dir) + f".bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
        target_dir.rename(backup_old)
        warn(f"旧数据已备份到: {backup_old}")
    
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with tarfile.open(backup_file, "r:gz") as tar:
            tar.extractall(target_dir.parent)
        log("恢复完成")
        return True
    except Exception as e:
        error(f"恢复失败: {e}")
        return False


def list_snapshots() -> bool:
    """列出 Restic 快照"""
    password = os.environ.get("RESTIC_PASSWORD")
    if not password:
        warn("RESTIC_PASSWORD 未设置")
        return False
    
    env = os.environ.copy()
    env["RESTIC_PASSWORD"] = password
    
    try:
        result = subprocess.run(
            ["restic", "snapshots", "--repo", str(DEFAULT_RESTIC_REPO)],
            env=env,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return result.returncode == 0
    except FileNotFoundError:
        error("restic 未安装")
        return False


def prune_snapshots(keep_last: int = 10) -> bool:
    """清理旧快照"""
    password = os.environ.get("RESTIC_PASSWORD")
    if not password:
        warn("RESTIC_PASSWORD 未设置")
        return False
    
    log(f"清理旧快照，保留最近 {keep_last} 个")
    
    env = os.environ.copy()
    env["RESTIC_PASSWORD"] = password
    
    try:
        result = subprocess.run(
            ["restic", "forget", "--repo", str(DEFAULT_RESTIC_REPO),
             f"--keep-last={keep_last}", "--prune"],
            env=env,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            log("清理完成")
            print(result.stdout)
        else:
            error(f"清理失败: {result.stderr}")
        return result.returncode == 0
    except FileNotFoundError:
        error("restic 未安装")
        return False


def show_help():
    print(f"""DevEnv Backup Tool v{VERSION}

用法: backup-tool.py <命令> [选项]

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
    python backup-tool.py backup
    python backup-tool.py restore backup-file.tar.gz
    python backup-tool.py list
    python backup-tool.py prune 5

""")


def main():
    if not check_deps():
        sys.exit(1)
    
    init_dirs()
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("arg1", nargs="?")
    parser.add_argument("arg2", nargs="?")
    args = parser.parse_args()
    
    command = args.command or "help"
    
    if command == "backup":
        source = Path(args.arg1) if args.arg1 else DEFAULT_OPENCLAW_DIR
        full_backup(source)
    
    elif command == "restore":
        if not args.arg1:
            error("请指定备份文件")
            sys.exit(1)
        target = Path(args.arg2) if args.arg2 else None
        restore_backup(Path(args.arg1), target)
    
    elif command == "list":
        list_snapshots()
    
    elif command == "prune":
        keep = int(args.arg1) if args.arg1 else 10
        prune_snapshots(keep)
    
    else:
        show_help()


if __name__ == "__main__":
    main()