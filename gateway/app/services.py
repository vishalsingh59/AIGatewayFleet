import base64
import base64
import json
import os
from pathlib import Path
import random
import shutil
import threading
import time
from typing import Dict, List, Optional

import requests

from shared.security import (
    parse_version,
    sha256_file,
    validate_attestation_payload,
    verify_signature_bytes,
)

GATEWAY_ID = os.getenv("GATEWAY_ID", "gateway-1")

GATEWAY_DATA_DIR = Path(os.getenv("GATEWAY_DATA_DIR", "gateway/data"))
CACHE_DIR = GATEWAY_DATA_DIR / "cache"
MANIFESTS_DIR = CACHE_DIR / "manifests"
PACKAGES_DIR = CACHE_DIR / "packages"
SBOM_DIR = CACHE_DIR / "sbom"
ATTESTATIONS_DIR = CACHE_DIR / "attestations"
SIGNATURES_DIR = CACHE_DIR / "signatures"
METRICS_DIR = GATEWAY_DATA_DIR / "metrics"
METRICS_FILE = METRICS_DIR / "buffer.jsonl"

CI_DIR = Path("ci")
CI_ARTIFACTS_DIR = CI_DIR / "artifacts"
CI_MANIFESTS_DIR = CI_DIR / "manifests"
CI_SBOM_DIR = CI_DIR / "sbom"
CI_ATTESTATIONS_DIR = CI_DIR / "attestations"
CI_SIGNATURES_DIR = CI_DIR / "signatures"

GATEWAY_PUBLIC_KEY_PATH = Path(
    os.getenv("GATEWAY_PUBLIC_KEY_PATH", "gateway/keys/update-public.pem")
)

DASHBOARD_METRICS_URL = os.getenv("DASHBOARD_METRICS_URL", "http://127.0.0.1:9000/metrics")
FORWARD_TIMEOUT_SECONDS = int(os.getenv("GATEWAY_FORWARD_TIMEOUT", "5"))
FORWARD_RETRIES = int(os.getenv("GATEWAY_FORWARD_RETRIES", "2"))
FORWARD_RETRY_BACKOFF_SECONDS = float(os.getenv("GATEWAY_FORWARD_RETRY_BACKOFF_SECONDS", "0.5"))

REQUIRED_MANIFEST_FIELDS = {
    "version",
    "artifact_name",
    "artifact_url",
    "sbom_name",
    "attestation_name",
    "signature_name",
    "sbom_signature_name",
    "attestation_signature_name",
    "manifest_signature_name",
    "artifact_sha256",
    "sbom_sha256",
    "attestation_sha256",
}

BUFFER_LOCK = threading.Lock()


def is_gateway_online() -> bool:
    value = os.getenv("GATEWAY_ONLINE", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_latest_manifest_path():
    if not MANIFESTS_DIR.exists():
        return None

    manifest_files = list(MANIFESTS_DIR.glob("*.json"))
    if not manifest_files:
        return None

    latest_manifest = None
    latest_version = None

    for manifest_file in manifest_files:
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            version = manifest_data.get("version")
            if not version:
                continue

            try:
                parsed = parse_version(version)
            except Exception:
                continue

            if latest_version is None or parsed > parse_version(latest_version):
                latest_version = version
                latest_manifest = manifest_file
        except Exception:
            continue

    return str(latest_manifest) if latest_manifest else None


def _manifest_sort_key(manifest_path: Path):
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        version = data.get("version")
        if not version:
            return parse_version("0.0.0")
        return parse_version(version)
    except Exception:
        return parse_version("0.0.0")


def _iter_manifests_sorted() -> List[Path]:
    manifests = list(CI_MANIFESTS_DIR.glob("*.json"))
    manifests.sort(key=_manifest_sort_key)
    return manifests


def get_package_path(version: str):
    package_file = PACKAGES_DIR / f"robot-app-{version}.bin"
    return str(package_file) if package_file.exists() else None


def get_sbom_path(version: str):
    sbom_file = SBOM_DIR / f"sbom-{version}.json"
    return str(sbom_file) if sbom_file.exists() else None


def get_signature_path(version: str):
    signature_file = SIGNATURES_DIR / f"robot-app-{version}.sig"
    return str(signature_file) if signature_file.exists() else None


def get_attestation_path(version: str):
    attestation_file = ATTESTATIONS_DIR / f"attestation-{version}.json"
    return str(attestation_file) if attestation_file.exists() else None


def get_sbom_signature_path(version: str):
    signature_file = SIGNATURES_DIR / f"sbom-{version}.sig"
    return str(signature_file) if signature_file.exists() else None


def get_attestation_signature_path(version: str):
    signature_file = SIGNATURES_DIR / f"attestation-{version}.sig"
    return str(signature_file) if signature_file.exists() else None


def get_manifest_signature_path(version: str):
    signature_file = SIGNATURES_DIR / f"manifest-{version}.sig"
    return str(signature_file) if signature_file.exists() else None


def get_all_signatures(version: str) -> Dict[str, Optional[str]]:
    def _read_signature(path_func):
        path = path_func(version)
        if path:
            return base64.b64encode(Path(path).read_bytes()).decode("utf-8")
        return None

    return {
        "signature": _read_signature(get_signature_path),
        "sbom_signature": _read_signature(get_sbom_signature_path),
        "attestation_signature": _read_signature(get_attestation_signature_path),
        "manifest_signature": _read_signature(get_manifest_signature_path),
    }


def verify_manifest_file(manifest_path: Path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    missing = REQUIRED_MANIFEST_FIELDS - manifest.keys()
    if missing:
        raise ValueError(f"Manifest missing required fields: {sorted(missing)}")

    artifact_path = CI_ARTIFACTS_DIR / manifest["artifact_name"]
    sbom_path = CI_SBOM_DIR / manifest["sbom_name"]
    attestation_path = CI_ATTESTATIONS_DIR / manifest["attestation_name"]
    artifact_signature_path = CI_SIGNATURES_DIR / manifest["signature_name"]
    sbom_signature_path = CI_SIGNATURES_DIR / manifest["sbom_signature_name"]
    attestation_signature_path = CI_SIGNATURES_DIR / manifest["attestation_signature_name"]
    manifest_signature_path = CI_SIGNATURES_DIR / manifest["manifest_signature_name"]

    if not artifact_path.exists():
        raise FileNotFoundError(f"Artifact not found: {artifact_path}")

    if not sbom_path.exists():
        raise FileNotFoundError(f"SBOM not found: {sbom_path}")

    if not attestation_path.exists():
        raise FileNotFoundError(f"Attestation not found: {attestation_path}")

    if not artifact_signature_path.exists():
        raise FileNotFoundError(f"Artifact signature not found: {artifact_signature_path}")

    if not sbom_signature_path.exists():
        raise FileNotFoundError(f"SBOM signature not found: {sbom_signature_path}")

    if not attestation_signature_path.exists():
        raise FileNotFoundError(f"Attestation signature not found: {attestation_signature_path}")

    if not manifest_signature_path.exists():
        raise FileNotFoundError(f"Manifest signature not found: {manifest_signature_path}")

    if sha256_file(artifact_path) != manifest["artifact_sha256"]:
        raise ValueError(f"Artifact checksum mismatch for {artifact_path.name}")

    if sha256_file(sbom_path) != manifest["sbom_sha256"]:
        raise ValueError(f"SBOM checksum mismatch for {sbom_path.name}")

    if sha256_file(attestation_path) != manifest["attestation_sha256"]:
        raise ValueError(f"Attestation checksum mismatch for {attestation_path.name}")

    verify_signature_bytes(artifact_path.read_bytes(), artifact_signature_path.read_bytes(), GATEWAY_PUBLIC_KEY_PATH)
    verify_signature_bytes(sbom_path.read_bytes(), sbom_signature_path.read_bytes(), GATEWAY_PUBLIC_KEY_PATH)
    verify_signature_bytes(
        attestation_path.read_bytes(),
        attestation_signature_path.read_bytes(),
        GATEWAY_PUBLIC_KEY_PATH,
    )
    verify_signature_bytes(manifest_path.read_bytes(), manifest_signature_path.read_bytes(), GATEWAY_PUBLIC_KEY_PATH)

    with open(attestation_path, "r", encoding="utf-8") as f:
        attestation = json.load(f)
    validate_attestation_payload(attestation, manifest)

    return {
        "artifact_path": artifact_path,
        "sbom_path": sbom_path,
        "attestation_path": attestation_path,
        "artifact_signature_path": artifact_signature_path,
        "sbom_signature_path": sbom_signature_path,
        "attestation_signature_path": attestation_signature_path,
        "manifest_signature_path": manifest_signature_path,
    }


def sync_from_ci():
    synced_files = []
    rejected_manifests = []

    cache_artifacts_dir = CACHE_DIR / "packages"
    cache_manifests_dir = CACHE_DIR / "manifests"
    cache_sbom_dir = CACHE_DIR / "sbom"
    cache_signatures_dir = CACHE_DIR / "signatures"

    cache_artifacts_dir.mkdir(parents=True, exist_ok=True)
    cache_manifests_dir.mkdir(parents=True, exist_ok=True)
    cache_sbom_dir.mkdir(parents=True, exist_ok=True)
    cache_attestations_dir = CACHE_DIR / "attestations"
    cache_attestations_dir.mkdir(parents=True, exist_ok=True)
    cache_signatures_dir.mkdir(parents=True, exist_ok=True)

    if not CI_MANIFESTS_DIR.exists():
        return {
            "status": "sync completed",
            "synced_files": [],
            "rejected_manifests": [],
            "message": "No manifests found",
        }

    for manifest_path in _iter_manifests_sorted():
        try:
            verified = verify_manifest_file(manifest_path)

            targets = [
                (manifest_path, cache_manifests_dir / manifest_path.name),
                (verified["artifact_path"], cache_artifacts_dir / verified["artifact_path"].name),
                (verified["sbom_path"], cache_sbom_dir / verified["sbom_path"].name),
                (
                    verified["attestation_path"],
                    cache_attestations_dir / verified["attestation_path"].name,
                ),
                (
                    verified["artifact_signature_path"],
                    cache_signatures_dir / verified["artifact_signature_path"].name,
                ),
                (
                    verified["sbom_signature_path"],
                    cache_signatures_dir / verified["sbom_signature_path"].name,
                ),
                (
                    verified["attestation_signature_path"],
                    cache_signatures_dir / verified["attestation_signature_path"].name,
                ),
                (
                    verified["manifest_signature_path"],
                    cache_signatures_dir / verified["manifest_signature_path"].name,
                ),
            ]

            for src, dst in targets:
                shutil.copy2(src, dst)
                synced_files.append(str(dst))

        except Exception as exc:
            rejected_manifests.append({
                "manifest": str(manifest_path),
                "reason": str(exc),
            })

    return {
        "status": "sync completed",
        "synced_files": synced_files,
        "rejected_manifests": rejected_manifests,
    }


def store_metric(metric: dict):
    payload = dict(metric)
    timestamp = payload.get("timestamp")
    if not isinstance(timestamp, int) or timestamp < 0:
        payload["timestamp"] = int(time.time())

    with BUFFER_LOCK:
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")


def read_buffered_lines() -> List[str]:
    with BUFFER_LOCK:
        if not METRICS_FILE.exists():
            return []
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            return f.readlines()


def replace_buffered_lines(lines: List[str]):
    with BUFFER_LOCK:
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        with open(METRICS_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)


def _is_retryable_forward_status(status_code: int) -> bool:
    return status_code == 429 or status_code >= 500


def _forward_metric_with_retry(metric: dict) -> bool:
    attempts = max(1, FORWARD_RETRIES + 1)

    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(
                DASHBOARD_METRICS_URL,
                json=metric,
                timeout=FORWARD_TIMEOUT_SECONDS,
            )
            if response.status_code == 200:
                return True
            if attempt >= attempts or not _is_retryable_forward_status(response.status_code):
                return False
        except requests.RequestException:
            if attempt >= attempts:
                return False

        backoff = FORWARD_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
        jitter = random.uniform(0, backoff * 0.1)
        time.sleep(backoff + jitter)

    return False


def forward_buffered_metrics():
    lines = read_buffered_lines()

    if not lines:
        return {
            "forwarded": 0,
            "remaining": 0,
            "message": "No buffered metrics found",
        }

    remaining_lines = []
    forwarded_count = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            metric = json.loads(line)
            if _forward_metric_with_retry(metric):
                forwarded_count += 1
            else:
                remaining_lines.append(line + "\n")

        except Exception:
            remaining_lines.append(line + "\n")

    replace_buffered_lines(remaining_lines)

    return {
        "forwarded": forwarded_count,
        "remaining": len(remaining_lines),
        "message": "Forwarding attempt completed",
    }
