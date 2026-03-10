import os
from pathlib import Path

DASHBOARD_DATA_DIR = Path(os.getenv("DASHBOARD_DATA_DIR", "dashboard/data"))
DASHBOARD_METRICS_FILE = DASHBOARD_DATA_DIR / "metrics.jsonl"
DASHBOARD_PERSIST_METRICS = os.getenv("DASHBOARD_PERSIST_METRICS", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
