from collections import Counter, defaultdict
import json
import threading
import time
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field

from dashboard.app.config import DASHBOARD_METRICS_FILE, DASHBOARD_PERSIST_METRICS
from shared.security import parse_version

UNKNOWN_GATEWAY = "unknown-gateway"
UNKNOWN_ROBOT = "unknown-robot"
UNKNOWN_VERSION = "unknown"


class MetricPayload(BaseModel):
    robot_id: str = Field(..., min_length=1)
    gateway_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    status: Literal["healthy", "rolled_back", "unhealthy", "failed"]
    cpu: Optional[int] = Field(default=None, ge=0, le=100)
    memory: Optional[int] = Field(default=None, ge=0, le=100)
    timestamp: Optional[int] = Field(default=None, ge=0)

    def to_payload(self) -> dict:
        model_dump = getattr(self, "model_dump", None)
        if callable(model_dump):
            return model_dump()
        return self.dict()


class MetricStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._metrics: List[dict] = []
        self._metrics.extend(self._load_persisted())

    def add(self, metric: dict):
        with self._lock:
            self._metrics.append(metric)
            self._persist(metric)

    def snapshot(self) -> List[dict]:
        with self._lock:
            return list(self._metrics)

    def clear(self):
        with self._lock:
            self._metrics.clear()
            if DASHBOARD_PERSIST_METRICS and DASHBOARD_METRICS_FILE.exists():
                DASHBOARD_METRICS_FILE.unlink()

    def _persist(self, metric: dict):
        if not DASHBOARD_PERSIST_METRICS:
            return

        DASHBOARD_METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DASHBOARD_METRICS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(metric) + "\n")

    def _load_persisted(self) -> List[dict]:
        if not DASHBOARD_PERSIST_METRICS:
            return []

        if not DASHBOARD_METRICS_FILE.exists():
            return []

        loaded = []
        with open(DASHBOARD_METRICS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    loaded.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return loaded


metric_store = MetricStore()


def _normalize_metric(metric: dict) -> dict:
    normalized = dict(metric)
    timestamp = normalized.get("timestamp")
    if not isinstance(timestamp, int) or timestamp < 0:
        normalized["timestamp"] = int(time.time())
    return normalized


def add_metric(metric: dict):
    metric_store.add(_normalize_metric(metric))


def clear_metrics():
    metric_store.clear()


def _latest_metrics_by_robot(metrics: List[dict]) -> List[dict]:
    latest_by_robot: Dict[Tuple[str, str], Tuple[dict, int]] = {}
    for idx, metric in enumerate(metrics):
        key = (
            metric.get("gateway_id", UNKNOWN_GATEWAY),
            metric.get("robot_id", UNKNOWN_ROBOT),
        )
        metric_timestamp = metric.get("timestamp", 0)
        existing = latest_by_robot.get(key)
        if existing is None:
            latest_by_robot[key] = (metric, idx)
            continue

        existing_metric, existing_idx = existing
        existing_timestamp = existing_metric.get("timestamp", 0)
        if (metric_timestamp, idx) >= (existing_timestamp, existing_idx):
            latest_by_robot[key] = (metric, idx)

    return [entry[0] for entry in latest_by_robot.values()]


def _group_by_gateway(metrics: List[dict]) -> dict:
    grouped = defaultdict(list)
    for metric in metrics:
        grouped[metric.get("gateway_id", UNKNOWN_GATEWAY)].append(metric)
    return dict(grouped)


def _version_counts(metrics: List[dict]) -> dict:
    return dict(Counter(metric.get("version", UNKNOWN_VERSION) for metric in metrics))


def _latest_version(version_counts: dict):
    valid_versions = [version for version in version_counts if version != UNKNOWN_VERSION]
    if not valid_versions:
        return None
    return max(valid_versions, key=parse_version)


def get_fleet_status():
    snapshot = metric_store.snapshot()
    latest_metrics = _latest_metrics_by_robot(snapshot)
    failing = [metric for metric in latest_metrics if metric.get("status") != "healthy"]
    gateways = _group_by_gateway(latest_metrics)
    version_counts = _version_counts(latest_metrics)
    status_counts = dict(Counter(metric.get("status", "unknown") for metric in latest_metrics))
    latest_version = _latest_version(version_counts)

    outdated_robots = []
    gateway_version_summary = {}

    for gateway_id, robots in gateways.items():
        gateway_versions = Counter(robot.get("version", UNKNOWN_VERSION) for robot in robots)
        gateway_version_summary[gateway_id] = dict(gateway_versions)

        if latest_version:
            for robot in robots:
                version = robot.get("version", UNKNOWN_VERSION)
                if version != latest_version:
                    outdated_robots.append(
                        {
                            "robot_id": robot.get("robot_id"),
                            "gateway_id": gateway_id,
                            "current_version": version,
                            "expected_version": latest_version,
                            "status": robot.get("status"),
                        }
                    )

    return {
        "total_robots": len(latest_metrics),
        "total_reports": len(snapshot),
        "total_gateways": len(gateways),
        "latest_version": latest_version,
        "versions": version_counts,
        "status_counts": status_counts,
        "version_mismatch": len(version_counts) > 1,
        "outdated_robots": outdated_robots,
        "gateway_version_summary": gateway_version_summary,
        "gateways": gateways,
        "failing": failing,
    }


def get_fleet_summary():
    fleet = get_fleet_status()
    status_counts = fleet.get("status_counts", {})
    return {
        "total_robots": fleet["total_robots"],
        "total_gateways": fleet["total_gateways"],
        "total_reports": fleet["total_reports"],
        "latest_version": fleet["latest_version"],
        "healthy_robots": status_counts.get("healthy", 0),
        "failing_robots": len(fleet["failing"]),
        "outdated_robots": len(fleet["outdated_robots"]),
        "version_mismatch": fleet["version_mismatch"],
    }
