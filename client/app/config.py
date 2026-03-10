import os
from pathlib import Path

ROBOT_ID = os.getenv("ROBOT_ID", "robot-1")
STATE_DIR = Path(os.getenv("CLIENT_STATE_DIR", f"client/state/{ROBOT_ID}"))
DOWNLOAD_DIR = STATE_DIR / "downloads"
INSTALLED_DIR = STATE_DIR / "installed"
BACKUP_DIR = STATE_DIR / "backup"
VERSION_STATE_FILE = STATE_DIR / "version_state.json"

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://127.0.0.1:8080")
CLIENT_PUBLIC_KEY_PATH = Path(os.getenv("CLIENT_PUBLIC_KEY_PATH", "client/keys/update-public.pem"))

INITIAL_VERSION = os.getenv("INITIAL_VERSION", "1.0.0")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "30"))
HTTP_TIMEOUT_SHORT = int(os.getenv("CLIENT_HTTP_TIMEOUT_SHORT", "5"))
HTTP_TIMEOUT_DOWNLOAD = int(os.getenv("CLIENT_HTTP_TIMEOUT_DOWNLOAD", "20"))
HTTP_RETRIES = int(os.getenv("CLIENT_HTTP_RETRIES", "2"))
HTTP_RETRY_BACKOFF_SECONDS = float(os.getenv("CLIENT_HTTP_RETRY_BACKOFF_SECONDS", "0.5"))
