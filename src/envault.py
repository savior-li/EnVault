#!/usr/bin/env python3
"""
EnVault - DevEnv Backup Tool
开发环境备份、快照、上传网盘一体化工具
Enhanced: Web Dashboard, Resume Upload, Key File, E2E Encryption, Interactive Config, Webhook, Notifications, Templates
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
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from http.server import HTTPServer, SimpleHTTPRequestHandler
import yaml


VERSION = "1.2.0"

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "envault"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"
DEFAULT_BACKUP_DIR = Path.home() / ".envault"
DEFAULT_OPENCLAW_DIR = Path.home() / ".openclaw"
DEFAULT_RESTIC_REPO = DEFAULT_BACKUP_DIR / "restic"
DEFAULT_LOG_DIR = DEFAULT_BACKUP_DIR / "logs"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "envault.log"
DEFAULT_KEY_FILE = DEFAULT_CONFIG_DIR / "key.pem"
DEFAULT_TEMPLATE_DIR = DEFAULT_CONFIG_DIR / "templates"

SUPPORTED_FORMATS = ["tar.gz", "tar.bz2", "tar.xz", "tar", "zip"]

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
            "encryption_enabled": "Encryption enabled",
            "decryption_failed": "Decryption failed",
            "config_loaded": "Config loaded: {} directories",
            "excluded_files": "Excluded {} files matching rules",
            "compression_format": "Using compression format: {}",
            "backup_verified": "Backup verified: {}",
            "verification_failed": "Verification failed: {}",
            "incremental_backup": "Incremental backup: {} changes",
            "cleanup_complete": "Cleanup complete: removed {} files",
            "rotate_log": "Log rotated: {} bytes archived",
            "e2e_encrypted": "End-to-end encrypted (server cannot decrypt)",
            "key_generated": "Encryption key generated: {}",
            "key_loaded": "Encryption key loaded from: {}",
            "webhook_triggered": "Webhook triggered: {}",
            "notification_sent": "Notification sent: {}",
            "template_saved": "Template saved: {}",
            "template_loaded": "Template loaded: {}",
            "data_repaired": "Data repaired successfully",
            "server_started": "Dashboard server started: http://localhost:{}",
        },
        "zh": {
            "start_backup": "开始备份流程...",
            "backup_complete": "备份完成",
            "backup_created": "备份已创建: {}",
            "restore_complete": "恢复完成",
            "encryption_enabled": "加密已启用",
            "decryption_failed": "解密失败",
            "config_loaded": "配置已加载: {} 个目录",
            "excluded_files": "已排除 {} 个匹配规则的文件",
            "compression_format": "使用压缩格式: {}",
            "backup_verified": "备份已校验: {}",
            "verification_failed": "校验失败: {}",
            "incremental_backup": "增量备份: {} 个变化",
            "cleanup_complete": "清理完成: 删除 {} 个文件",
            "rotate_log": "日志轮转: {} 字节已归档",
            "e2e_encrypted": "端到端加密（服务器无法解密）",
            "key_generated": "加密密钥已生成: {}",
            "key_loaded": "加密密钥已加载: {}",
            "webhook_triggered": "Webhook 已触发: {}",
            "notification_sent": "通知已发送: {}",
            "template_saved": "模板已保存: {}",
            "template_loaded": "模板已加载: {}",
            "data_repaired": "数据修复成功",
            "server_started": "Dashboard 服务已启动: http://localhost:{}",
        },
        "es": {
            "start_backup": "Iniciando proceso de respaldo...",
            "backup_complete": "Respaldo completo",
            "backup_created": "Respaldo creado: {}",
            "restore_complete": "Restauración completa",
            "encryption_enabled": "Cifrado habilitado",
            "decryption_failed": "Descifrado fallido",
            "config_loaded": "Configuración cargada: {} directorios",
            "excluded_files": "Excluidos {} archivos",
            "compression_format": "Usando formato: {}",
            "backup_verified": "Respaldo verificado: {}",
            "verification_failed": "Verificación fallida: {}",
            "incremental_backup": "Respaldo incremental: {} cambios",
            "cleanup_complete": "Limpieza completa: {} archivos eliminados",
            "rotate_log": "Log rotado: {} bytes archivados",
            "e2e_encrypted": "Cifrado E2E (servidor no puede descifrar)",
            "key_generated": "Clave generada: {}",
            "key_loaded": "Clave cargada: {}",
            "webhook_triggered": "Webhook activado: {}",
            "notification_sent": "Notificación enviada: {}",
            "template_saved": "Plantilla guardada: {}",
            "template_loaded": "Plantilla cargada: {}",
            "data_repaired": "Datos reparados exitosamente",
            "server_started": "Servidor iniciado: http://localhost:{}",
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
    print(f"{color}[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]{Colors.NC} {msg}")
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
    for cmd in ["tar", "curl", "openssl"]:
        if not shutil.which(cmd):
            warn(f"Missing dependency: {cmd}")
    return True


def init_dirs():
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_RESTIC_REPO.mkdir(parents=True, exist_ok=True)


def rotate_log_if_needed(max_size_mb: int = 10):
    try:
        if not DEFAULT_LOG_FILE.exists():
            return
        size_mb = DEFAULT_LOG_FILE.stat().st_size / (1024 * 1024)
        if size_mb > max_size_mb:
            archive_name = f"envault-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
            shutil.move(str(DEFAULT_LOG_FILE), str(DEFAULT_LOG_DIR / archive_name))
            info(i18n("rotate_log", int(size_mb * 1024 * 1024)))
            open(DEFAULT_LOG_FILE, "w").close()
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
        "backup_dirs": [{"path": str(DEFAULT_OPENCLAW_DIR), "name": "openclaw"}],
        "exclude_patterns": ["*.log", "*.tmp", "__pycache__", ".git", "node_modules", ".cache"],
        "compression": "tar.gz",
        "encryption": {"enabled": False, "method": "openssl", "key_file": str(DEFAULT_KEY_FILE), "e2e": False},
        "cloud_upload": {"catbox": True, "tmpfiles": True, "gofile": False, "uguu": False},
        "restic": {"enabled": True, "keep_last": 10},
        "cleanup": {"enabled": False, "keep_days": 7, "keep_count": 10},
        "incremental": {"enabled": False},
        "verify": {"enabled": True, "algorithm": "sha256"},
        "log": {"max_size_mb": 10, "rotate": True},
        "webhook": {"enabled": False, "url": "", "events": ["backup_complete"]},
        "notifications": {
            "enabled": False,
            "dingtalk": {"enabled": False, "webhook": ""},
            "feishu": {"enabled": False, "webhook": ""},
            "slack": {"enabled": False, "webhook": ""}
        },
        "templates": {"default": "default"},
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
            if name.endswith(pattern[1:]):
                return True
        elif pattern in path_str or path.name == pattern:
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
        return False, "Hash mismatch"
    except Exception as e:
        return False, str(e)


def create_checksum(archive_path: Path, algorithm: str = "sha256") -> Path:
    hash_value = get_file_hash(archive_path, algorithm)
    manifest_path = archive_path.with_suffix(f"{archive_path.suffix}.{algorithm}")
    manifest_path.write_text(hash_value)
    return manifest_path


def repair_data(file_path: Path) -> bool:
    checksum_file = Path(str(file_path) + ".sha256")
    if not checksum_file.exists():
        return False
    try:
        expected_hash = checksum_file.read_text().strip()
        actual_hash = get_file_hash(file_path, "sha256")
        if expected_hash != actual_hash:
            temp_file = file_path.with_suffix(file_path.suffix + ".repaired")
            with open(file_path, "rb") as src, open(temp_file, "wb") as dst:
                shutil.copyfileobj(src, dst)
            if get_file_hash(temp_file, "sha256") == expected_hash:
                temp_file.replace(file_path)
                return True
            temp_file.unlink()
            return False
        return True
    except Exception:
        return False


def generate_key_file(key_file: Path = DEFAULT_KEY_FILE) -> Optional[Path]:
    cmd = ["openssl", "rand", "-hex", "32"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        key_file.write_text(result.stdout.strip())
        key_file.chmod(0o600)
        info(i18n("key_generated", key_file))
        return key_file
    return None


def load_key_file(key_file: Path = DEFAULT_KEY_FILE) -> Optional[str]:
    if not key_file.exists():
        return None
    try:
        info(i18n("key_loaded", key_file))
        return key_file.read_text().strip()
    except Exception:
        return None


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


def find_changed_files(source_dir: Path, manifest: Dict[str, Any], exclude_patterns: List[str]) -> List[Path]:
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
        if not (source_dir / rel_path).exists():
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

        if excluded_count > 0:
            info(i18n("excluded_files", excluded_count))

        if incremental and changed_count > 0:
            info(i18n("incremental_backup", changed_count))
            save_manifest(manifest_path, manifest)

        if compression == "zip":
            shutil.make_archive(str(backup_file.with_suffix("")), "zip", temp_dir)
        else:
            ext = compression.split('.')[-1] if '.' in compression else "gz"
            with tarfile.open(backup_file, f"w:{ext}") as tar:
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


def encrypt_file_openssl(input_file: Path, password: str = None, key_file: Path = None) -> Optional[Path]:
    if key_file and key_file.exists():
        password = key_file.read_text().strip()
    elif not password:
        password = os.environ.get("ENVAULT_PASSWORD", "")

    output_file = input_file.with_suffix(input_file.suffix + ".enc")

    cmd = ["openssl", "enc", "-aes-256-cbc", "-salt", "-pbkdf2", "-iter", "100000",
           "-out", str(output_file), "-in", str(input_file)]
    if password:
        cmd.extend(["-pass", f"pass:{password}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            info(i18n("encryption_enabled"))
            checksum = Path(str(input_file) + ".sha256")
            if checksum.exists():
                checksum.unlink()
            input_file.unlink()
            return output_file
        else:
            error(f"Encryption failed: {result.stderr}")
            return None
    except Exception as e:
        error(f"Encryption error: {e}")
        return None


def decrypt_file_openssl(input_file: Path, password: str = None, key_file: Path = None, output_dir: Path = None) -> Optional[Path]:
    if key_file and key_file.exists():
        password = key_file.read_text().strip()
    elif not password:
        password = os.environ.get("ENVAULT_PASSWORD", "")

    if output_dir is None:
        output_dir = Path.home()
    output_dir.mkdir(parents=True, exist_ok=True)

    output_stem = input_file.stem.replace(".enc", "")
    output_file = output_dir / output_stem

    cmd = ["openssl", "enc", "-aes-256-cbc", "-d", "-pbkdf2", "-iter", "100000",
           "-out", str(output_file), "-in", str(input_file)]
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


def upload_catbox(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            response = requests.post(CATBOX_URL, files={"reqtype": (None, "fileupload"), "fileToUpload": f})
        if response.status_code == 200:
            return response.text.strip()
    except Exception as e:
        warn(f"Catbox upload failed: {e}")
    return None


def upload_tmpfiles(file_path: Path) -> Optional[str]:
    try:
        with open(file_path, "rb") as f:
            response = requests.post(TMPFILES_URL, files={"file": f})
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
        return None
    try:
        with open(file_path, "rb") as f:
            response = requests.post(GOFILE_URL, files={"file": f}, data={"accountId": account_id, "token": token})
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
            response = requests.post(UGUU_URL, files={"file": f})
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
        list(DEFAULT_BACKUP_DIR.glob("*.tar.gz")) + list(DEFAULT_BACKUP_DIR.glob("*.tar.bz2")) +
        list(DEFAULT_BACKUP_DIR.glob("*.tar.xz")) + list(DEFAULT_BACKUP_DIR.glob("*.zip")) +
        list(DEFAULT_BACKUP_DIR.glob("*.enc")),
        key=lambda p: p.stat().st_mtime, reverse=True)

    for i, backup in enumerate(backup_files):
        should_remove = i >= keep_count
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


def send_webhook(url: str, event: str, data: Dict[str, Any]):
    if not url:
        return
    try:
        payload = {"event": event, "timestamp": datetime.now().isoformat(), "data": data}
        requests.post(url, json=payload, timeout=10)
        info(i18n("webhook_triggered", url))
    except Exception as e:
        warn(f"Webhook failed: {e}")


def send_notifications(config: Dict[str, Any], event: str, data: Dict[str, Any]):
    if not config.get("notifications", {}).get("enabled"):
        return
    message = f"EnVault: {event}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    if "backup" in event.lower():
        message += f"\nFile: {data.get('file', 'N/A')}"
        if data.get("url"):
            message += f"\nURL: {data.get('url')}"

    for notif_type in ["dingtalk", "feishu", "slack"]:
        cfg = config["notifications"].get(notif_type, {})
        if cfg.get("enabled") and cfg.get("webhook"):
            try:
                payload = {"msgtype": "text", "text": {"content": message}}
                requests.post(cfg["webhook"], json=payload, timeout=10)
                info(i18n("notification_sent", notif_type))
            except Exception as e:
                warn(f"{notif_type} notification failed: {e}")


def full_backup(config: Dict[str, Any]) -> bool:
    log(i18n("start_backup"))
    rotate_log_if_needed(config.get("log", {}).get("max_size_mb", 10))

    backup_file = create_backup_with_excludes(
        source_dirs=config.get("backup_dirs", []),
        exclude_patterns=config.get("exclude_patterns", []),
        compression=config.get("compression", "tar.gz"),
        incremental=config.get("incremental", {}).get("enabled", False),
        verify=config.get("verify", {}).get("enabled", True)
    )

    if not backup_file:
        info("No backup created (no changes or error)")
        return True

    enc_config = config.get("encryption", {})
    key_file = None
    if enc_config.get("key_file"):
        key_file = Path(enc_config["key_file"])
        if not key_file.exists() and enc_config.get("enabled"):
            generate_key_file(key_file)

    if enc_config.get("enabled", False):
        backup_file = encrypt_file_openssl(backup_file, key_file=key_file) or backup_file
        if enc_config.get("e2e"):
            info(i18n("e2e_encrypted"))

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
        cleanup_old_backups(cleanup_config.get("keep_days", 7), cleanup_config.get("keep_count", 10))

    links = {
        "timestamp": datetime.now().isoformat(),
        "compression": config.get("compression", "tar.gz"),
        "encrypted": enc_config.get("enabled", False),
        "e2e": enc_config.get("e2e", False),
        "incremental": config.get("incremental", {}).get("enabled", False),
        "files": {"local": str(backup_file)}
    }

    cloud_config = config.get("cloud_upload", {})
    if backup_file.exists() and backup_file.stat().st_size < 200 * 1024 * 1024:
        if cloud_config.get("catbox", True):
            if url := upload_catbox(backup_file):
                links["files"]["catbox"] = url
        if cloud_config.get("tmpfiles", True):
            temp_file = backup_file.with_suffix(str(backup_file.suffix) + ".tgz")
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

    webhook_config = config.get("webhook", {})
    if webhook_config.get("enabled") and "backup_complete" in webhook_config.get("events", []):
        send_webhook(webhook_config.get("url", ""), "backup_complete", links)

    send_notifications(config, "Backup Complete", links)
    log(i18n("backup_complete"))
    return True


def restore_backup(backup_file: Path, target_dir: Path = None, password: str = None, key_file: Path = None) -> bool:
    if not backup_file.exists():
        error(f"Backup file not found: {backup_file}")
        return False

    working_file = backup_file

    if backup_file.suffix == ".enc":
        if not password and not key_file:
            config = load_config()
            if config.get("encryption", {}).get("key_file"):
                key_file = Path(config["encryption"]["key_file"])
        if password or key_file:
            decrypted = decrypt_file_openssl(backup_file, password, key_file, target_dir)
            if decrypted:
                working_file = decrypted
            else:
                return False
        else:
            error("Encrypted file requires ENVAULT_PASSWORD or key_file")
            return False

    target_dir = target_dir or Path.home()

    verify_config = {"enabled": True, "algorithm": "sha256"}
    if verify_config.get("enabled", True):
        valid, msg = verify_archive(working_file, verify_config.get("algorithm", "sha256"))
        if not valid:
            error(i18n("verification_failed", msg))
            if not repair_data(working_file):
                return False
            else:
                info(i18n("data_repaired"))

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
        subprocess.run(["restic", "backup", str(source_dir), "--repo", str(DEFAULT_RESTIC_REPO),
                       "--tag", "envault", "--description", description, "--quiet"],
                      env=env, capture_output=True)
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
        result = subprocess.run(["restic", "snapshots", "--repo", str(DEFAULT_RESTIC_REPO)],
                              env=env, capture_output=True, text=True)
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
        result = subprocess.run(["restic", "forget", "--repo", str(DEFAULT_RESTIC_REPO),
                               f"--keep-last={keep_last}", "--prune"], env=env, capture_output=True, text=True)
        if result.returncode == 0:
            info(f"Pruned snapshots, keeping last {keep_last}")
        return result.returncode == 0
    except Exception as e:
        error(f"Prune failed: {e}")
        return False


def save_template(name: str, config: Dict[str, Any]):
    template_file = DEFAULT_TEMPLATE_DIR / f"{name}.yaml"
    save_config(config, template_file)
    info(i18n("template_saved", name))


def load_template(name: str) -> Optional[Dict[str, Any]]:
    template_file = DEFAULT_TEMPLATE_DIR / f"{name}.yaml"
    if not template_file.exists():
        warn(f"Template not found: {name}")
        return None
    info(i18n("template_loaded", name))
    return load_config(template_file)


def list_templates() -> List[str]:
    return [f.stem for f in DEFAULT_TEMPLATE_DIR.glob("*.yaml")]


def interactive_config():
    print(f"\n{'='*50}\nEnVault Interactive Configuration\n{'='*50}\n")
    config = get_default_config()

    print("1. Backup directories (empty line to finish):")
    config["backup_dirs"] = []
    while True:
        path = input("   Path: ").strip()
        if not path:
            break
        name = input(f"   Name [{Path(path).name}]: ").strip() or Path(path).name
        config["backup_dirs"].append({"path": path, "name": name})

    print(f"\n2. Compression format [{config['compression']}]:")
    comp = input(": ").strip()
    if comp:
        config["compression"] = comp

    print("\n3. Enable encryption? (y/n):")
    if input(": ").strip().lower() == "y":
        config["encryption"]["enabled"] = True
        print("   Use key file? (y/n):")
        if input(": ").strip().lower() == "y":
            config["encryption"]["key_file"] = str(DEFAULT_KEY_FILE)
            generate_key_file()
        print("   Enable E2E encryption? (y/n):")
        if input(": ").strip().lower() == "y":
            config["encryption"]["e2e"] = True

    print("\n4. Enable incremental backup? (y/n):")
    if input(": ").strip().lower() == "y":
        config["incremental"]["enabled"] = True

    print("\n5. Enable auto cleanup? (y/n):")
    if input(": ").strip().lower() == "y":
        config["cleanup"]["enabled"] = True
        config["cleanup"]["keep_days"] = int(input("   Keep days [7]: ").strip() or 7)
        config["cleanup"]["keep_count"] = int(input("   Keep count [10]: ").strip() or 10)

    print("\n6. Webhook URL (optional):")
    url = input(": ").strip()
    if url:
        config["webhook"]["enabled"] = True
        config["webhook"]["url"] = url

    print("\n7. Notification webhook (dingtalk/feishu/slack, optional):")
    notif = input(": ").strip()
    if notif:
        config["notifications"]["enabled"] = True
        config["notifications"][notif] = {"enabled": True, "webhook": input("   Webhook URL: ").strip()}

    print("\n8. Save as template? (name or Enter to skip):")
    template_name = input(": ").strip()
    if template_name:
        save_template(template_name, config)

    save_config(config)
    print(f"\n{'='*50}\nConfig saved: {DEFAULT_CONFIG_FILE}\n{'='*50}\n")
    return config


class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.generate_dashboard().encode())
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.get_status()).encode())
        elif self.path == "/api/backups":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.list_backups()).encode())
        else:
            super().do_GET()

    def generate_dashboard(self) -> str:
        backups = self.list_backups()
        total_size = sum(b["size"] for b in backups)
        rows = ""
        for b in backups[:20]:
            status = '<span class="status-ok">Encrypted</span>' if b.get("encrypted") else "No"
            rows += f"<tr><td>{b['name']}</td><td>{b['date']}</td><td>{b['size']/1024:.1f} KB</td><td>{status}</td></tr>"

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>EnVault Dashboard</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:40px;background:#f5f5f5}}
.container{{max-width:1200px;margin:0 auto}}
.card{{background:white;border-radius:8px;padding:20px;margin:20px 0;box-shadow:0 2px 4px rgba(0,0,0,0.1)}}
.stats{{display:flex;gap:20px}}
.stat{{flex:1;text-align:center}}
.stat-value{{font-size:2em;font-weight:bold;color:#007bff}}
.stat-label{{color:#666}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:12px;text-align:left;border-bottom:1px solid #eee}}
th{{background:#f8f9fa}}
.btn{{padding:8px 16px;border:none;border-radius:4px;cursor:pointer;background:#007bff;color:white}}
.status-ok{{background:#d4edda;color:#155724;padding:2px 8px;border-radius:4px}}
</style></head>
<body><div class="container">
<h1>EnVault Dashboard</h1>
<div class="card"><div class="stats">
<div class="stat"><div class="stat-value">{len(backups)}</div><div class="stat-label">Backups</div></div>
<div class="stat"><div class="stat-value">{total_size/1024/1024:.1f} MB</div><div class="stat-label">Total Size</div></div>
</div></div>
<div class="card"><h2>Recent Backups</h2>
<table><thead><tr><th>Name</th><th>Date</th><th>Size</th><th>Encrypted</th></tr></thead>
<tbody>{rows}</tbody></table>
</div>
<div class="card">
<button class="btn" onclick="location.reload()">Refresh</button>
<button class="btn" onclick="backup()">New Backup</button>
</div>
</div>
<script>
function backup(){{fetch('/api/backup',{{method:'POST'}}).then(()=>location.reload())}}
</script></body></html>"""

    def get_status(self) -> Dict[str, Any]:
        backups = self.list_backups()
        return {"total_backups": len(backups), "total_size": sum(b["size"] for b in backups),
                "dashboard_port": self.server.server_port}

    def list_backups(self) -> List[Dict[str, Any]]:
        backups = []
        for f in sorted(DEFAULT_BACKUP_DIR.glob("*.tar.gz"), key=lambda p: p.stat().st_mtime, reverse=True):
            backups.append({"name": f.name, "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                          "size": f.stat().st_size, "encrypted": False})
        for f in sorted(DEFAULT_BACKUP_DIR.glob("*.enc"), key=lambda p: p.stat().st_mtime, reverse=True):
            backups.append({"name": f.name, "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                          "size": f.stat().st_size, "encrypted": True})
        return backups

    def do_POST(self):
        if self.path == "/api/backup":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            threading.Thread(target=lambda: full_backup(load_config()), daemon=True).start()
            self.wfile.write(json.dumps({"status": "started"}).encode())
        else:
            self.send_response(404)
            self.end_headers()


def start_dashboard(port: int = 8765):
    os.chdir(DEFAULT_BACKUP_DIR)
    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    info(i18n("server_started", port))
    threading.Thread(target=lambda: webbrowser.open(f"http://localhost:{port}"), daemon=True).start()
    server.serve_forever()


def init_config():
    config = get_default_config()
    save_config(config)
    info(f"Config initialized: {DEFAULT_CONFIG_FILE}")


def show_help():
    print(f"""EnVault v{VERSION} - DevEnv Backup Tool

Usage: envault <command> [options]

Commands:
    backup              Run full backup
    backup <dir>        Backup single directory
    restore <file>     Restore backup
    list               List Restic snapshots
    prune [n]          Keep last n snapshots
    cleanup            Clean old backups
    init               Initialize config
    interactive        Interactive configuration
    config             Show config
    dashboard [port]   Start web dashboard (default: 8765)
    verify <file>      Verify backup
    repair <file>      Repair backup data
    keygen             Generate encryption key
    template save <n>  Save template
    template load <n>  Load template
    template list      List templates
    help               Show help

Options:
    --encrypt          Enable encryption
    --key-file <file>  Use key file
    --e2e              End-to-end encryption
    --incremental      Incremental backup
    --format <fmt>     Compression format
    --lang <lang>      Language (en/zh/es)
""")


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
    parser.add_argument("--encrypt", action="store_true")
    parser.add_argument("--key-file", dest="key_file")
    parser.add_argument("--e2e", action="store_true")
    parser.add_argument("--incremental", action="store_true")
    parser.add_argument("--format")
    parser.add_argument("--lang")
    parser.add_argument("--name", dest="name")
    args, _ = parser.parse_known_args()

    if args.lang:
        global i18n
        i18n = I18n(args.lang)

    config = load_config(args.config or DEFAULT_CONFIG_FILE)

    if args.format:
        config["compression"] = args.format
    if args.encrypt:
        config["encryption"]["enabled"] = True
    if args.key_file:
        config["encryption"]["key_file"] = args.key_file
    if args.e2e:
        config["encryption"]["enabled"] = True
        config["encryption"]["e2e"] = True
    if args.incremental:
        config.setdefault("incremental", {})["enabled"] = True

    command = args.command or "help"

    if command == "backup":
        if args.arg1:
            source = Path(args.arg1)
            if source.exists():
                backup_name = args.name or source.name
                key_file = Path(config["encryption"]["key_file"]) if config["encryption"].get("key_file") else None
                file = create_backup_with_excludes(
                    [{"path": str(source), "name": backup_name}],
                    config.get("exclude_patterns", []),
                    config.get("compression", "tar.gz"),
                    backup_name,
                    incremental=config.get("incremental", {}).get("enabled", False),
                    verify=config.get("verify", {}).get("enabled", True)
                )
                if file and config.get("encryption", {}).get("enabled"):
                    encrypt_file_openssl(file, key_file=key_file)
        else:
            full_backup(config)

    elif command == "restore":
        if not args.arg1:
            error("Specify backup file")
            sys.exit(1)
        key_file = Path(config["encryption"]["key_file"]) if config["encryption"].get("key_file") else None
        restore_backup(Path(args.arg1), Path(args.arg2) if args.arg2 else None, key_file=key_file)

    elif command == "list":
        list_snapshots()

    elif command == "prune":
        prune_snapshots(int(args.arg1) if args.arg1 else 10)

    elif command == "cleanup":
        cleanup_config = config.get("cleanup", {})
        cleanup_old_backups(cleanup_config.get("keep_days", 7), cleanup_config.get("keep_count", 10))

    elif command == "verify":
        if args.arg1:
            valid, msg = verify_archive(Path(args.arg1), "sha256")
            if valid:
                info(i18n("backup_verified", msg))
            else:
                error(i18n("verification_failed", msg))

    elif command == "repair":
        if args.arg1:
            if repair_data(Path(args.arg1)):
                info(i18n("data_repaired"))
            else:
                error("Repair failed")

    elif command == "keygen":
        key_file = generate_key_file()
        if key_file:
            config["encryption"]["enabled"] = True
            config["encryption"]["key_file"] = str(key_file)
            save_config(config)

    elif command == "interactive":
        interactive_config()

    elif command == "dashboard":
        start_dashboard(int(args.arg1) if args.arg1 else 8765)

    elif command == "template":
        if args.arg1 == "save" and args.arg2:
            save_template(args.arg2, config)
        elif args.arg1 == "load" and args.arg2:
            loaded = load_template(args.arg2)
            if loaded:
                config = loaded
        elif args.arg1 == "list":
            templates = list_templates()
            print("Templates:", ", ".join(templates) if templates else "None")
        else:
            show_help()

    elif command == "init":
        init_config()

    elif command == "config":
        show_config(config)

    else:
        show_help()


if __name__ == "__main__":
    main()
