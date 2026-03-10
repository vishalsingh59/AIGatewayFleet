import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def canonical_json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_version(version: str):
    return tuple(int(part) for part in version.split("."))


def verify_signature_bytes(data: bytes, signature: bytes, public_key_path: Path):
    if not public_key_path.exists():
        raise FileNotFoundError(f"Public key not found: {public_key_path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        payload_tmp = Path(tmp_dir) / "payload.bin"
        sig_tmp = Path(tmp_dir) / "signature.sig"
        payload_tmp.write_bytes(data)
        sig_tmp.write_bytes(signature)

        try:
            subprocess.run(
                [
                    "openssl",
                    "dgst",
                    "-sha256",
                    "-verify",
                    str(public_key_path),
                    "-signature",
                    str(sig_tmp),
                    str(payload_tmp),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise ValueError("Signature verification failed") from exc


def validate_attestation_payload(attestation: dict, manifest: dict):
    subject = attestation.get("subject")
    if not isinstance(subject, dict):
        raise ValueError("Attestation missing subject block")

    materials = attestation.get("materials")
    if not isinstance(materials, list) or not materials:
        raise ValueError("Attestation missing materials list")

    subject_name = subject.get("name")
    subject_version = subject.get("version")
    subject_sha = subject.get("sha256")

    if subject_name != manifest["artifact_name"]:
        raise ValueError("Attestation subject artifact mismatch")
    if subject_version != manifest["version"]:
        raise ValueError("Attestation subject version mismatch")
    if subject_sha != manifest["artifact_sha256"]:
        raise ValueError("Attestation subject checksum mismatch")

    sbom_name = manifest["sbom_name"]
    sbom_sha = manifest["sbom_sha256"]
    sbom_material = next((item for item in materials if item.get("name") == sbom_name), None)
    if sbom_material is None:
        raise ValueError("Attestation missing SBOM material")
    if sbom_material.get("sha256") != sbom_sha:
        raise ValueError("Attestation SBOM checksum mismatch")
