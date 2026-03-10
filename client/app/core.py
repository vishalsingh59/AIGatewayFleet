import base64
import json
import random
import shutil
import time
from pathlib import Path
from typing import Optional, Set

import requests

from client.app.config import (
    BACKUP_DIR,
    CLIENT_PUBLIC_KEY_PATH,
    DOWNLOAD_DIR,
    GATEWAY_URL,
    HTTP_RETRIES,
    HTTP_RETRY_BACKOFF_SECONDS,
    HTTP_TIMEOUT_DOWNLOAD,
    HTTP_TIMEOUT_SHORT,
    INITIAL_VERSION,
    INSTALLED_DIR,
    STATE_DIR,
    ROBOT_ID,
    VERSION_STATE_FILE,
)
from shared.security import (
    canonical_json_bytes,
    parse_version,
    sha256_bytes,
    sha256_file,
    validate_attestation_payload,
    verify_signature_bytes,
)

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


def _load_version_state() -> dict:
    if not VERSION_STATE_FILE.exists():
        return {
            "current_version": INITIAL_VERSION,
            "previous_version": INITIAL_VERSION,
            "highest_version": INITIAL_VERSION,
        }
    with open(VERSION_STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_version_state(state: dict):
    VERSION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(VERSION_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def init_robot_state():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    state = _load_version_state()
    current_version = state["current_version"]

    installed_artifact = INSTALLED_DIR / f"robot-app-{current_version}.bin"
    if not installed_artifact.exists():
        installed_artifact.write_text(
            f"dummy robot software v{current_version}\nstatus=healthy\n",
            encoding="utf-8",
        )


def _is_retryable(exc: requests.RequestException) -> bool:
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True

    response = getattr(exc, "response", None)
    if response is None:
        return False

    return response.status_code == 429 or response.status_code >= 500


def _request_with_retry(
    request_fn,
    url: str,
    timeout: int,
    acceptable_statuses: Optional[Set[int]] = None,
    **kwargs,
):
    attempts = max(1, HTTP_RETRIES + 1)
    acceptable_statuses = acceptable_statuses or set()

    for attempt in range(1, attempts + 1):
        try:
            response = request_fn(url, timeout=timeout, **kwargs)
            status_code = getattr(response, "status_code", 200)
            if status_code in acceptable_statuses:
                return response
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            if attempt >= attempts or not _is_retryable(exc):
                raise

            backoff = HTTP_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            jitter = random.uniform(0, backoff * 0.1)
            time.sleep(backoff + jitter)

    raise RuntimeError("Unreachable retry state")


def get_current_version() -> str:
    state = _load_version_state()
    return state["current_version"]


def get_highest_version() -> str:
    state = _load_version_state()
    return state["highest_version"]


def check_for_update():
    current_version = get_current_version()
    response = _request_with_retry(
        requests.get,
        f"{GATEWAY_URL}/updates/manifest",
        timeout=HTTP_TIMEOUT_SHORT,
        acceptable_statuses={404},
    )

    if response.status_code == 404:
        return {
            "current_version": current_version,
            "latest_version": current_version,
            "update_available": False,
            "artifact_url": None,
            "manifest": None,
            "reason": "No valid manifest available on gateway",
        }

    response.raise_for_status()

    manifest = response.json()
    manifest_bytes = response.content
    latest_version = manifest["version"]
    current_parsed = parse_version(current_version)
    latest_parsed = parse_version(latest_version)
    highest_version = get_highest_version()
    highest_parsed = parse_version(highest_version)
    
    reason = None
    if latest_parsed < highest_parsed:
        reason = (
            f"Rejected manifest version {latest_version}: "
            f"downgrade detected (highest seen: {highest_version})"
        )
        update_available = False
    elif latest_parsed < current_parsed:
        reason = (
            f"Rejected manifest version {latest_version}: "
            f"older than current version {current_version}"
        )
        update_available = False
    elif latest_parsed == current_parsed:
        reason = "Gateway already serving current version"
        update_available = False
    else:
        update_available = True

    return {
        "current_version": current_version,
        "latest_version": latest_version,
        "update_available": update_available,
        "artifact_url": f"{GATEWAY_URL}{manifest['artifact_url']}",
        "manifest": manifest,
        "manifest_bytes": manifest_bytes,
        "reason": reason,
    }


def verify_release(manifest: dict, gateway_url: str, manifest_bytes: Optional[bytes] = None):
    missing = REQUIRED_MANIFEST_FIELDS - manifest.keys()
    if missing:
        raise ValueError(f"Manifest missing required fields: {sorted(missing)}")

    version = manifest["version"]

    signatures_response = _request_with_retry(
        requests.get,
        f"{gateway_url}/updates/signatures/{version}",
        timeout=HTTP_TIMEOUT_SHORT,
    )
    signatures = signatures_response.json()

    if not signatures.get("manifest_signature"):
        raise ValueError(f"Manifest signature for version {version} not found")
    manifest_bytes = manifest_bytes or canonical_json_bytes(manifest)
    verify_signature_bytes(
        manifest_bytes,
        base64.b64decode(signatures["manifest_signature"]),
        CLIENT_PUBLIC_KEY_PATH,
    )

    sbom_response = _request_with_retry(
        requests.get,
        f"{gateway_url}/updates/sbom/{version}",
        timeout=HTTP_TIMEOUT_SHORT,
    )
    if sha256_bytes(sbom_response.content) != manifest["sbom_sha256"]:
        raise ValueError("SBOM checksum mismatch")

    if not signatures.get("sbom_signature"):
        raise ValueError(f"SBOM signature for version {version} not found")
    verify_signature_bytes(
        sbom_response.content,
        base64.b64decode(signatures["sbom_signature"]),
        CLIENT_PUBLIC_KEY_PATH,
    )

    attestation_response = _request_with_retry(
        requests.get,
        f"{gateway_url}/updates/attestation/{version}",
        timeout=HTTP_TIMEOUT_SHORT,
    )
    if sha256_bytes(attestation_response.content) != manifest["attestation_sha256"]:
        raise ValueError("Attestation checksum mismatch")

    if not signatures.get("attestation_signature"):
        raise ValueError(f"Attestation signature for version {version} not found")
    verify_signature_bytes(
        attestation_response.content,
        base64.b64decode(signatures["attestation_signature"]),
        CLIENT_PUBLIC_KEY_PATH,
    )

    attestation_payload = json.loads(attestation_response.content.decode("utf-8"))
    validate_attestation_payload(attestation_payload, manifest)

    return True


def download_package(package_url: str, version: str) -> str:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    package_path = DOWNLOAD_DIR / f"robot-app-{version}.bin"
    temp_path = package_path.with_suffix(".part")

    resume_offset = temp_path.stat().st_size if temp_path.exists() else 0
    headers = {}
    mode = "wb"
    if resume_offset > 0:
        headers["Range"] = f"bytes={resume_offset}-"
        mode = "ab"

    response = _request_with_retry(
        requests.get,
        package_url,
        timeout=HTTP_TIMEOUT_DOWNLOAD,
        stream=True,
        headers=headers,
        acceptable_statuses={206},
    )

    # If server ignores range requests and returns full body, restart cleanly.
    if resume_offset > 0 and response.status_code == 200:
        mode = "wb"

    with open(temp_path, mode) as f:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if chunk:
                f.write(chunk)

    temp_path.replace(package_path)
    return str(package_path)


def verify_package(package_path: str, manifest: dict, gateway_url: str) -> bool:
    file_path = Path(package_path)

    if not file_path.exists():
        raise ValueError("Package file does not exist")

    if file_path.stat().st_size == 0:
        raise ValueError("Package file is empty")

    file_hash = sha256_file(file_path)
    if file_hash != manifest["artifact_sha256"]:
        raise ValueError("Artifact checksum mismatch")

    version = manifest["version"]
    signatures_response = _request_with_retry(
        requests.get,
        f"{gateway_url}/updates/signatures/{version}",
        timeout=HTTP_TIMEOUT_SHORT,
    )
    signatures = signatures_response.json()
    if not signatures.get("signature"):
        raise ValueError(f"Signature for version {version} not found")
    verify_signature_bytes(
        file_path.read_bytes(),
        base64.b64decode(signatures["signature"]),
        CLIENT_PUBLIC_KEY_PATH,
    )

    return True


def install_package(package_path: str, new_version: str):
    INSTALLED_DIR.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    state = _load_version_state()
    current_version = state["current_version"]

    current_installed_package = INSTALLED_DIR / f"robot-app-{current_version}.bin"
    if not current_installed_package.exists():
        current_installed_package.write_text(
            f"dummy robot software v{current_version}",
            encoding="utf-8",
        )

    backup_package = BACKUP_DIR / f"robot-app-{current_version}.bin"
    shutil.copy2(current_installed_package, backup_package)

    target_path = INSTALLED_DIR / f"robot-app-{new_version}.bin"
    shutil.copy2(package_path, target_path)

    state["previous_version"] = state["current_version"]
    state["current_version"] = new_version
    
    highest_parsed = parse_version(state["highest_version"])
    new_parsed = parse_version(new_version)
    if new_parsed > highest_parsed:
        state["highest_version"] = new_version
    
    _save_version_state(state)


def run_healthcheck() -> bool:
    current_version = get_current_version()
    installed_artifact = INSTALLED_DIR / f"robot-app-{current_version}.bin"

    if not installed_artifact.exists():
        return False

    content = installed_artifact.read_text(encoding="utf-8")

    if "status=broken" in content:
        return False

    return "status=healthy" in content


def rollback():
    state = _load_version_state()
    previous_version = state["previous_version"]

    backup_package = BACKUP_DIR / f"robot-app-{previous_version}.bin"
    restored_package = INSTALLED_DIR / f"robot-app-{previous_version}.bin"

    if not backup_package.exists():
        raise FileNotFoundError(
            f"Backup package not found for previous version: {previous_version}"
        )

    shutil.copy2(backup_package, restored_package)

    state["current_version"] = previous_version
    _save_version_state(state)

    return previous_version


def send_metrics(status: str = "healthy"):
    current_version = get_current_version()

    payload = {
        "robot_id": ROBOT_ID,
        "version": current_version,
        "status": status,
        "cpu": 32,
        "memory": 48,
    }

    response = _request_with_retry(
        requests.post,
        f"{GATEWAY_URL}/metrics",
        timeout=HTTP_TIMEOUT_SHORT,
        json=payload,
    )
    return response.json()
