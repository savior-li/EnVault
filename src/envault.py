#!/usr/bin/env python3
"""
EnVault - DevEnv Backup Tool
开发环境备份、快照、上传网盘一体化工具
Supports: encryption, multi-directory, exclusion rules, multiple formats, multiple cloud storage
"""

import os
import sys
import json
import argparse
import subprocess
import tarfile
import shutil
import requests
import hashlib
import logging
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from functools import wraps
import yaml


VERSION = "1.1.0"

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "envault"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_BACKUP_DIR = Path.home() / ".envault"
DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw"
DEFAULT_RESTIC_REPO = DEFAULT_BACKUP_DIR / "restic"
DEFAULT_LOG_DIR = DEFAULT_BACKUP_DIR / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "envault.log"

SUPPORTED_FORMATS = ["tar.gz", "tar.bz2", "tar.xz", "tar", "zip", "tar.xz"]

CATBOX_URL = "https://catbox.moe/user/api.php"
TMPFILES_URL = "https://tmpfiles.org/api/v1/upload"
GOFILE_URL = "https://store3.gofile.io/contents/uploadFile"
UGUU_URL = "https://uguu.se/api/upload"


class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'


class I18n:
    messages = {
        "en": {
            "start_backup": "Starting backup process...",
            "backup_complete": "Backup complete",
            "backup_created": "Backup created: {}",
            "restore_complete": "Restore complete",
            "upload_success": "Upload successful: {}",
            "upload_failed": "Upload failed: {}",
            "encryption_enabled": "Encryption enabled",
            "decryption_failed": "Decryption failed",
            "config_loaded": "Config loaded: {} directories",
            "excluded_files": "Excluded {} files matching rules",
            "compression_format": "Using compression format: {}",
            "unknown_command": "Unknown command",
            "backup_verified": "Backup verified: {}",
            "verification_failed": "Verification failed: {}",
            "incremental_backup": "Incremental backup: {} changes",
            "cleanup_complete": "Cleanup complete: removed {} files",
            "rotate_log": "Log rotated: {} bytes archived",
        },
        "zh": {
            "start_backup": "开始备份流程...",
            "backup_complete": "备份完成",
            "backup_created": "备份已创建: {}",
            "restore_complete": "恢复完成",
            "upload_success": "上传成功: {}",
            "upload_failed": "上传失败: {}",
            "encryption_enabled": "加密已启用",
            "decryption_failed": "解密失败",
            "config_loaded": "配置已加载: {} 个目录",
            "excluded_files": "已排除 {} 个匹配规则的文件",
            "compression_format": "使用压缩格式: {}",
            "unknown_command": "未知命令",
            "backup_verified": "备份已校验: {}",
            "verification_failed": "校验失败: {}",
            "incremental_backup": "增量备份: {} 个变化",
            "cleanup_complete": "清理完成: 删除 {} 个文件",
            "rotate_log": "日志轮转: {} 字节已归档",
        },
        "es": {
            "start_backup": "Iniciando proceso de respaldo...",
            "backup_complete": "Respaldo completo",
            "backup_created": "Respaldo creado: {}",
            "restore_complete": "Restauración completa",
            "upload_success": "Subida exitosa: {}",
            "upload_failed": "Subida fallida: {}",
            "encryption_enabled": "Cifrado habilitado",
            "decryption_failed": "Descifrado fallido",
            "config_loaded": "Configuración cargada: {} directorios",
            "excluded_files": "Excluidos {} archivos que coinciden con las reglas",
            "compression_format": "Usando formato de compresión: {}",
            "unknown_command": "Comando desconocido",
            "backup_verified": "Respaldo verificado: {}",
            "verification_failed": "Verificación fallida: {}",
            "incremental_backup": "Respaldo incremental: {} cambios",
            "cleanup_complete": "Limpieza completa: {} archivos eliminados",
            "rotate_log": "Log rotado: {} bytes archivados",
        }
    }

    def __init__(self, lang: str = "en"):
        self.lang = lang if lang in self.messages else "en"

    def __call__(self, key: str, *args) -> str:
        msg = self.messages[self.lang].get(key, key)
        if args:
            return msg.format(*args)
        return msg


i18n = I18n(os.environ.get("ENVAULT_LANG", "en"))


def log(msg: str, color: str = Colors.GREEN):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{color}[{timestamp}]{Colors.NC} {msg}")
    log_to_file(msg)


def log_to_file(msg: str):
    try:
        if DEFAULT_LOG_FILE.parent.exists():
            with open(DEFAULT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def warn(msg: str):
    log(msg, Colors.YELLOW)


def error(msg: str):
    log(msg, Colors.RED)


def info(msg: str):
    log(msg, Colors.BLUE)


def check_deps() -> bool:
    deps = {"tar": "tar", "curl": "curl", "openssl": "openssl"}
    missing = []
    for cmd, name in deps.items():
        if not shutil.which(cmd):
            missing.append(name)
    if missing:
        warn(f"Missing dependencies: {', '.join(missing)}")
    return True


def init_dirs():
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    (DEFAULT_RESTIC_REPO).mkdir(parents=True, exist_ok=True)


def rotate_log_if_needed(max_size_mb: int = 10):
    try:
        if not DEFAULT_LOG_FILE.exists():
            return
        size_mb = DEFAULT_LOG_FILE.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            archive_name = f"envault-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
            archive_path = DEFAULT_LOG_DIR / archive_name
            shutil.move(str(DEFAULT_LOG_FILE), str(archive_path))
            info(i18n("rotate_log", int(size_mb * 1024 * 1024)))
            with open(DEFAULT_LOG_FILE, "w", encoding="utf-8") as f:
                pass
    except Exception as e:
        warn(f"Log rotation failed: {e}")


def load_config(config_file: Path = DEFAULT_CONFIG_FILE) -> Dict[str, Any]:
    if not config_file.exists():
        return get_default_config()

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        info(i18n("config_loaded", len(config.get("backup_dirs", []))))
        return config
    except Exception as e:
        warn(f"Failed to load config: {e}, using defaults")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    return {
        "backup_dirs": [
            {"path": str(DEFAULT_OPENCLAW_DIR), "name": "openclaw"}
        ],
        "exclude_patterns": [
            "*.log",
            "*.tmp",
            "__pycache__",
            ".git",
            "node_modules",
            ".cache"
        ],
        "compression": "tar.gz",
        "encryption": {
            "enabled": False,
            "method": "openssl",
            "password": None
        },
        "cloud_upload": {
            "catbox": True,
            "tmpfiles": True,
            "gofile": False,
            "uguu": False
        },
        "restic": {
            "enabled": True,
            "keep_last": 10
        },
        "cleanup": {
            "enabled": False,
            "keep_days": 7,
            "keep_count": 10
        },
        "incremental": {
            "enabled": False,
            "manifest_file": ".envault-manifest.json"
        },
        "verify": {
            "enabled": True,
            "algorithm": "sha256"
        },
        "log": {
            "max_size_mb": 10,
            "rotate": True
        },
        "language": "en"
    }


def save_config(config: Dict[str, Any], config_file: Path = DEFAULT_CONFIG_FILE):
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def match_exclude(path: Path, patterns: List[str]) -> bool:
    path_str = str(path)
    name = path.name
    for pattern in patterns:
        if pattern.startswith("*."):
            ext = pattern[1:]
            if name.endswith(ext):
                return True
        elif pattern in path_str:
            return True
        elif path.name == pattern:
            return True
    return False


def get_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    hash_func = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()


def verify_archive(archive_path: Path, algorithm: str = "sha256") -> Tuple[bool, str]:
    manifest_path = archive_path.with_suffix(f"{archive_path.suffix}.{algorithm}")
    if not manifest_path.exists():
        return False, "Manifest not found"

    try:
        expected_hash = manifest_path.read_text().strip()
        actual_hash = get_file_hash(archive_path, algorithm)
        if expected_hash == actual_hash:
            return True, f"{algorithm}:{actual_hash}"
        return False, f"Hash mismatch: expected {expected_hash}, got {actual_hash}"
    except Exception as e:
        return False, str(e)


def create_checksum(archive_path: Path, algorithm: str = "sha256") -> Path:
    hash_value = get_file_hash(archive_path, algorithm)
    manifest_path = archive_path.with_suffix(f"{archive_path.suffix}.{algorithm}")
    manifest_path.write_text(hash_value)
    return manifest_path


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    if not manifest_path.exists():
        return {}
    try:
        return json.loads(manifest_path.read_text())
    except Exception:
        return {}


def save_manifest(manifest_path: Path, data: Dict[str, Any]):
    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_file_mtime_size(path: Path) -> Tuple[float, int]:
    try:
        stat = path.stat()
        return stat.st_mtime, stat.st_size
    except Exception:
        return 0, 0


def find_changed_files(
    source_dir: Path,
    manifest: Dict[str, Any],
    exclude_patterns: List[str]
) -> List[Path]:
    changed = []
    source_key = str(source_dir)

    if source_key not in manifest:
        manifest[source_key] = {}

    manifest_dir = manifest[source_key]

    for item in source_dir.rglob("*"):
        if match_exclude(item, exclude_patterns):
            continue

        rel_path = str(item.relative_to(source_dir))
        mtime, size = get_file_mtime_size(item)

        if item.is_dir():
            continue

        if rel_path not in manifest_dir:
            changed.append(item)
        else:
            old_mtime, old_size = manifest_dir[rel_path]
            if mtime > old_mtime or size != old_size:
                changed.append(item)

    for rel_path in list(manifest_dir.keys()):
        full_path = source_dir / rel_path
        if not full_path.exists():
            del manifest_dir[rel_path]

    return changed


def create_backup_with_excludes(
    source_dirs: List[Dict[str, str]],
    exclude_patterns: List[str],
    compression: str = "tar.gz",
    output_name: str = "backup",
    incremental: bool = False,
    verify: bool = True
) -> Optional[Path]:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = DEFAULT_BACKUP_DIR / f"{output_name}-{timestamp}.{compression}"

    log(i18n("compression_format", compression))

    excluded_count = 0
    temp_dir = DEFAULT_BACKUP_DIR / f"temp_{timestamp}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    changed_count = 0
    manifest_path = DEFAULT_BACKUP_DIR / ".file-manifest.json"
    manifest = load_manifest(manifest_path)

    try:
        for source in source_dirs:
            source_path = Path(source["path"])
            if not source_path.exists():
                warn(f"Source not found: {source_path}")
                continue

            if incremental:
                changed_files = find_changed_files(source_path, manifest, exclude_patterns)
                changed_count += len(changed_files)

                if not changed_files:
                    info("No changes detected, skipping backup")
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    return None

                dest_dir = temp_dir / source.get("name", source_path.name)
                dest_dir.mkdir(parents=True, exist_ok=True)

                for item in changed_files:
                    rel_path = item.relative_to(source_path)
                    dest_path = dest_dir / rel_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)

                    mtime, size = get_file_mtime_size(item)
                    manifest[str(source_path)][str(rel_path)] = (mtime, size)
            else:
                dest_dir = temp_dir / source.get("name", source_path.name)
                dest_dir.mkdir(parents=True, exist_ok=True)

                for item in source_path.rglob("*"):
                    if match_exclude(item, exclude_patterns):
                        excluded_count += 1
                        continue

                    rel_path = item.relative_to(source_path)
                    dest_path = dest_dir / rel_path

                    if item.is_dir():
                        dest_path.mkdir(parents=True, exist_ok=True)
                    else:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest_path)

                        if incremental:
                            mtime, size = get_file_mtime_size(item)
                            manifest.setdefault(str(source_path), {})[str(rel_path)] = (mtime, size)

        if excluded_count > 0:
            info(i18n("excluded_files", excluded_count))

        if incremental and changed_count > 0:
            info(i18n("incremental_backup", changed_count))

        if incremental:
            save_manifest(manifest_path, manifest)

        if compression == "zip":
            shutil.make_archive(
                str(backup_file.with_suffix("")),
                "zip",
                temp_dir
            )
        else:
            ext = compression.split('.')[-1] if '.' in compression else "gz"
            mode = f"w:{ext}"
            with tarfile.open(backup_file, mode) as tar:
                tar.add(temp_dir, arcname=".")

        log(i18n("backup_created", backup_file))

        if verify:
            checksum_file = create_checksum(backup_file, "sha256")
            info(i18n("backup_verified", checksum_file.name))

        return backup_file

    except Exception as e:
        error(f"Backup failed: {e}")
        return None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def encrypt_file_openssl(input_file: Path, password: str = None) -> Optional[Path]:
    if not password:
        password = os.environ.get("ENVAULT_PASSWORD", "")

    output_file = input_file.with_suffix(input_file.suffix + ".enc")

    cmd = [
        "openssl", "enc", "-aes-256-cbc",
        "-salt",
        "-pbkdf2",
        "-iter", "100000",
        "-out", str(output_file),
        "-in", str(input_file)
    ]

    if password:
        cmd.extend(["-pass", f"pass:{password}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            info(i18n("encryption_enabled"))
            input_file.unlink()
            return output_file
        else:
            error(f"Encryption failed: {result.stderr}")
            return None
    except Exception as e:
        error(f"Encryption error: {e}")
        return None
    except Exception as e:
        error(f"Encryption error: {e}")
        return None


def decrypt_file_openssl(input_file: Path, password: str = None, output_dir: Path = None) -> Optional[Path]:
    if not password:
        password = os.environ.get("ENVAULT_PASSWORD", "")

    if output_dir is None:
        output_dir = Path.home()

    output_dir.mkdir(parents=True, exist_ok=True)

    output_stem = input_file.stem.replace(".enc", "")
    output_file = output_dir / output_stem

    cmd = [
        "openssl", "enc", "-aes-256-cbc", "-d",
        "-pbkdf2",
        "-iter", "100000",
        "-out", str(output_file),
        "-in", str(input_file)
    ]

    if password:
        cmd.extend(["-pass", f"pass:{password}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return output_file
        else:
            error(f"Decryption failed: {result.stderr}")
            return None
    except Exception as e:
        error(f"Decryption error: {e}")
        return None


def encrypt_file(input_file: Path, method: str = "openssl", recipient: str = None) -> Optional[Path]:
    password = os.environ.get("ENVAULT_PASSWORD")

    if method == "openssl" or method == "aes":
        return encrypt_file_openssl(input_file, password)
    else:
        return encrypt_file_openssl(input_file, password)


def decrypt_file(input_file: Path, method: str = "openssl", password: str = None, output_dir: Path = None) -> Optional[Path]:
    if not password:
        password = os.environ.get("ENVAULT_PASSWORD")

    if method == "openssl" or method == "aes":
        return decrypt_file_openssl(input_file, password, output_dir)
    else:
        return decrypt_file_openssl(input_file, password, output_dir)


def upload_catbox(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                CATBOX_URL,
                files={"reqtype": (None, "fileupload"), "fileToUpload": f}
            )
        if response.status_code == 200:
            url = response.text.strip()
            return url
    except Exception as e:
        warn(f"Catbox upload failed: {e}")
    return None


def upload_tmpfiles(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                TMPFILES_URL,
                files={"file": f}
            )
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                return data.get("data", {}).get("url", "")
    except Exception as e:
        warn(f"Tmpfiles upload failed: {e}")
    return None


def upload_gofile(file_path: Path) -> Optional[str]:
    account_id = os.environ.get("GOFILE_ACCOUNT_ID")
    token = os.environ.get("GOFILE_TOKEN")

    if not account_id or not token:
        warn("Gofile upload skipped: GOFILE_ACCOUNT_ID or GOFILE_TOKEN not set")
        return None

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
                return data.get("data", {}).get("downloadPage", "")
    except Exception as e:
        warn(f"Gofile upload failed: {e}")
    return None


def upload_uguu(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                UGUU_URL,
                files={"file": f}
            )
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("url", "")
    except Exception as e:
        warn(f"Uguu upload failed: {e}")
    return None


def cleanup_old_backups(keep_days: int = 7, keep_count: int = 10) -> int:
    removed = 0
    now = datetime.now()
    backup_files = sorted(
        list(DEFAULT_BACKUP_DIR.glob("*.tar.gz")) +
        list(DEFAULT_BACKUP_DIR.glob("*.tar.bz2")) +
        list(DEFAULT_BACKUP_DIR.glob("*.tar.xz")) +
        list(DEFAULT_BACKUP_DIR.glob("*.zip")) +
        list(DEFAULT_BACKUP_DIR.glob("*.enc")),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    for i, backup in enumerate(backup_files):
        should_remove = False

        if i >= keep_count:
            should_remove = True

        try:
            age_days = (now - datetime.fromtimestamp(backup.stat().st_mtime)).days
            if age_days > keep_days:
                should_remove = True
        except Exception:
            pass

        if should_remove:
            backup.unlink()
            checksum = backup.with_suffix(f"{backup.suffix}.sha256")
            if checksum.exists():
                checksum.unlink()
            removed += 1

    if removed > 0:
        info(i18n("cleanup_complete", removed))

    return removed


def full_backup(config: Dict[str, Any]) -> bool:
    log(i18n("start_backup"))

    rotate_log_if_needed(config.get("log", {}).get("max_size_mb", 10))

    incremental_config = config.get("incremental", {})
    incremental_enabled = incremental_config.get("enabled", False)

    verify_config = config.get("verify", {})
    verify_enabled = verify_config.get("enabled", True)

    backup_file = create_backup_with_excludes(
        source_dirs=config.get("backup_dirs", []),
        exclude_patterns=config.get("exclude_patterns", []),
        compression=config.get("compression", "tar.gz"),
        incremental=incremental_enabled,
        verify=verify_enabled
    )

    if not backup_file:
        info("No backup created (no changes or error)")
        return True

    enc_config = config.get("encryption", {})
    if enc_config.get("enabled", False):
        method = enc_config.get("method", "openssl")
        backup_file = encrypt_file(backup_file, method) or backup_file

    restic_config = config.get("restic", {})
    if restic_config.get("enabled", True):
        password = os.environ.get("RESTIC_PASSWORD")
        if password:
            for source in config.get("backup_dirs", []):
                source_path = Path(source["path"])
                if source_path.exists():
                    create_restic_snapshot(source_path, f"backup {datetime.now().isoformat()}")

    cleanup_config = config.get("cleanup", {})
    if cleanup_config.get("enabled", False):
        cleanup_old_backups(
            cleanup_config.get("keep_days", 7),
            cleanup_config.get("keep_count", 10)
        )

    links = {
        "timestamp": datetime.now().isoformat(),
        "compression": config.get("compression", "tar.gz"),
        "encrypted": enc_config.get("enabled", False),
        "incremental": incremental_enabled,
        "files": {"local": str(backup_file)}
    }

    cloud_config = config.get("cloud_upload", {})

    if backup_file.exists() and backup_file.stat().st_size < 200 * 1024 * 1024:
        ext = ".gz" if ".gz" in backup_file.suffixes else ".tar.xz" if ".xz" in backup_file.suffixes else backup_file.suffix

        if cloud_config.get("catbox", True):
            if url := upload_catbox(backup_file):
                links["files"]["catbox"] = url

        if cloud_config.get("tmpfiles", True):
            temp_file = backup_file.with_suffix(str(ext) + ".tgz")
            shutil.copy2(backup_file, temp_file)
            if url := upload_tmpfiles(temp_file):
                links["files"]["tmpfiles"] = url
            temp_file.unlink()

        if cloud_config.get("gofile", False):
            if url := upload_gofile(backup_file):
                links["files"]["gofile"] = url

        if cloud_config.get("uguu", False):
            if url := upload_uguu(backup_file):
                links["files"]["uguu"] = url

    links_file = DEFAULT_BACKUP_DIR / f"links-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    links_file.write_text(json.dumps(links, ensure_ascii=False, indent=2))

    log(i18n("backup_complete"))
    return True


def restore_backup(backup_file: Path, target_dir: Path = None, password: str = None) -> bool:
    if not backup_file.exists():
        error(f"Backup file not found: {backup_file}")
        return False

    target_dir = target_dir or Path.home()
    working_file = backup_file

    if backup_file.suffix == ".enc":
        if not password:
            password = os.environ.get("ENVAULT_PASSWORD")
        if password:
            decrypted = decrypt_file(backup_file, "openssl", password, target_dir)
            if decrypted:
                working_file = decrypted
            else:
                return False
        else:
            error("Encrypted file requires ENVAULT_PASSWORD env var")
            return False

    verify_config = {"enabled": True, "algorithm": "sha256"}
    if verify_config.get("enabled", True):
        valid, msg = verify_archive(working_file, verify_config.get("algorithm", "sha256"))
        if not valid:
            error(i18n("verification_failed", msg))
            return False
        info(i18n("backup_verified", msg))

    try:
        if working_file.suffix == ".zip":
            shutil.unpack_archive(working_file, target_dir)
        else:
            with tarfile.open(working_file, "r:*") as tar:
                tar.extractall(target_dir)

        log(i18n("restore_complete"))
        return True
    except Exception as e:
        error(f"Restore failed: {e}")
        return False


def create_restic_snapshot(source_dir: Path, description: str = "backup") -> bool:
    password = os.environ.get("RESTIC_PASSWORD")
    if not password:
        return True

    env = os.environ.copy()
    env["RESTIC_PASSWORD"] = password

    try:
        subprocess.run(
            ["restic", "backup", str(source_dir),
             "--repo", str(DEFAULT_RESTIC_REPO),
             "--tag", "envault",
             "--quiet"],
            env=env,
            capture_output=True
        )
        return True
    except Exception as e:
        warn(f"Restic snapshot failed: {e}")
        return False


def list_snapshots() -> bool:
    password = os.environ.get("RESTIC_PASSWORD")
    if not password:
        warn("RESTIC_PASSWORD not set")
        return False

    env = os.environ.copy()
    env["RESTIC_PASSWORD"] = password

    try:
        result = subprocess.run(
            ["restic", "snapshots", "--repo", str(DEFAULT_RESTIC_REPO)],
            env=env, capture_output=True, text=True
        )
        print(result.stdout)
        return result.returncode == 0
    except Exception as e:
        error(f"Restic error: {e}")
        return False


def prune_snapshots(keep_last: int = 10) -> bool:
    password = os.environ.get("RESTIC_PASSWORD")
    if not password:
        return False

    env = os.environ.copy()
    env["RESTIC_PASSWORD"] = password

    try:
        result = subprocess.run(
            ["restic", "forget", "--repo", str(DEFAULT_RESTIC_REPO),
             f"--keep-last={keep_last}", "--prune"],
            env=env, capture_output=True, text=True
        )
        if result.returncode == 0:
            info(f"Pruned snapshots, keeping last {keep_last}")
        return result.returncode == 0
    except Exception as e:
        error(f"Prune failed: {e}")
        return False


def init_config():
    config = get_default_config()
    save_config(config)
    info(f"Config initialized: {DEFAULT_CONFIG_FILE}")
    print(f"\nEdit {DEFAULT_CONFIG_FILE} to customize your backup settings.")


def show_help():
    print(f"""EnVault v{VERSION} - DevEnv Backup Tool

Usage: envault <command> [options]

Commands:
    backup              Run full backup (uses config file)
    backup <dir>        Backup single directory
    restore <file>      Restore from backup file
    list                List Restic snapshots
    prune [n]           Keep last n snapshots (default: 10)
    cleanup             Clean old local backups
    init                Initialize config file
    config              Show current config
    verify <file>       Verify backup file integrity
    help                Show this help

Options:
    --config <file>     Use custom config file
    --format <fmt>      Compression format: tar.gz, tar.bz2, tar.xz, zip
    --encrypt           Enable encryption
    --openssl          Use OpenSSL encryption (default)
    --exclude <pattern> Add exclusion pattern
    --incremental       Enable incremental backup
    --lang <lang>       Language: en, zh, es

Examples:
    envault backup
    envault backup /path/to/dir --encrypt --format zip
    envault backup --incremental
    envault restore backup.tar.gz
    envault verify backup.tar.gz.sha256
    envault cleanup
    envault init

Config File: {DEFAULT_CONFIG_FILE}

""")
    print("Environment Variables:")
    print("  RESTIC_PASSWORD     Restic repository password")
    print("  ENVAULT_PASSWORD   Encryption/decryption password")
    print("  GOFILE_ACCOUNT_ID Gofile account ID")
    print("  GOFILE_TOKEN     Gofile token")
    print("  ENVAULT_LANG      Language (en/zh/es)")


def show_config(config: Dict[str, Any]):
    print(yaml.dump(config, default_flow_style=False, allow_unicode=True))


def main():
    check_deps()
    init_dirs()

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("command", nargs="?")
    parser.add_argument("arg1", nargs="?")
    parser.add_argument("arg2", nargs="?")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--format", "--compression", dest="format")
    parser.add_argument("--encrypt", action="store_true")
    parser.add_argument("--openssl", action="store_true")
    parser.add_argument("--exclude", action="append", dest="excludes")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--lang", dest="lang")
    parser.add_argument("--name", dest="name")
    args, unknown = parser.parse_known_args()

    global i18n
    if args.lang:
        i18n = I18n(args.lang)

    config_file = args.config or DEFAULT_CONFIG_FILE
    config = load_config(config_file)

    if args.format:
        config["compression"] = args.format
    if args.excludes:
        config["exclude_patterns"].extend(args.excludes)
    if args.encrypt or args.openssl:
        config["encryption"]["enabled"] = True
        config["encryption"]["method"] = "openssl"
    if args.incremental:
        config["incremental"]["enabled"] = True

    command = args.command or "help"

    if command == "backup":
        if args.arg1:
            source = Path(args.arg1)
            if source.exists():
                backup_name = args.name or source.name
                file = create_backup_with_excludes(
                    [{"path": str(source), "name": backup_name}],
                    config.get("exclude_patterns", []),
                    config.get("compression", "tar.gz"),
                    backup_name,
                    incremental=config.get("incremental", {}).get("enabled", False),
                    verify=config.get("verify", {}).get("enabled", True)
                )
                if file:
                    if config.get("encryption", {}).get("enabled"):
                        encrypt_file(file, config.get("encryption", {}).get("method", "openssl"))
                    restic_config = config.get("restic", {})
                    if restic_config.get("enabled", True) and os.environ.get("RESTIC_PASSWORD"):
                        create_restic_snapshot(source, f"backup {datetime.now().isoformat()}")
        else:
            full_backup(config)

    elif command == "restore":
        if not args.arg1:
            error("Specify backup file")
            sys.exit(1)
        target = Path(args.arg2) if args.arg2 else None
        restore_backup(Path(args.arg1), target)

    elif command == "list":
        list_snapshots()

    elif command == "prune":
        keep = int(args.arg1) if args.arg1 else 10
        prune_snapshots(keep)

    elif command == "cleanup":
        cleanup_config = config.get("cleanup", {})
        cleanup_old_backups(
            cleanup_config.get("keep_days", 7),
            cleanup_config.get("keep_count", 10)
        )

    elif command == "verify":
        if args.arg1:
            file_path = Path(args.arg1)
            valid, msg = verify_archive(file_path, "sha256")
            if valid:
                info(i18n("backup_verified", msg))
            else:
                error(i18n("verification_failed", msg))
        else:
            error("Specify file to verify")

    elif command == "init":
        init_config()

    elif command == "config":
        show_config(config)

    else:
        show_help()


if __name__ == "__main__":
    main()