import base64
import json
import subprocess
from pathlib import Path

from client.app.core import check_for_update, verify_release
from shared.security import canonical_json_bytes, sha256_bytes


def _generate_keypair(tmp_path: Path):
    private_key = tmp_path / "update-private.pem"
    public_key = tmp_path / "update-public.pem"
    subprocess.run(
        [
            "openssl",
            "genpkey",
            "-algorithm",
            "RSA",
            "-out",
            str(private_key),
            "-pkeyopt",
            "rsa_keygen_bits:2048",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "openssl",
            "rsa",
            "-in",
            str(private_key),
            "-pubout",
            "-out",
            str(public_key),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return private_key, public_key


def _sign_bytes(data: bytes, private_key: Path) -> bytes:
    payload_path = private_key.parent / "payload.bin"
    signature_path = private_key.parent / "payload.sig"
    payload_path.write_bytes(data)
    subprocess.run(
        [
            "openssl",
            "dgst",
            "-sha256",
            "-sign",
            str(private_key),
            "-out",
            str(signature_path),
            str(payload_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return signature_path.read_bytes()


def test_verify_release_accepts_valid_signed_manifest(monkeypatch, tmp_path):
    _, public_key = _generate_keypair(tmp_path)
    private_key = tmp_path / "update-private.pem"

    sbom_bytes = b'{"artifact":"robot-app-1.4.0.bin","version":"1.4.0"}'
    attestation_payload = {
        "subject": {
            "name": "robot-app-1.4.0.bin",
            "version": "1.4.0",
            "sha256": "unused-in-this-test",
        },
        "materials": [
            {
                "name": "sbom-1.4.0.json",
                "sha256": sha256_bytes(sbom_bytes),
            }
        ],
    }
    attestation_bytes = canonical_json_bytes(attestation_payload)

    manifest = {
        "version": "1.4.0",
        "artifact_name": "robot-app-1.4.0.bin",
        "artifact_url": "/updates/package/1.4.0",
        "sbom_name": "sbom-1.4.0.json",
        "attestation_name": "attestation-1.4.0.json",
        "signature_name": "robot-app-1.4.0.sig",
        "sbom_signature_name": "sbom-1.4.0.sig",
        "attestation_signature_name": "attestation-1.4.0.sig",
        "manifest_signature_name": "manifest-1.4.0.sig",
        "artifact_sha256": "unused-in-this-test",
        "sbom_sha256": sha256_bytes(sbom_bytes),
        "attestation_sha256": sha256_bytes(attestation_bytes),
    }
    manifest_bytes = canonical_json_bytes(manifest)

    class DummyResponse:
        def __init__(self, payload=None, content=b""):
            self._payload = payload or {}
            self.content = content
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, timeout=5):
        if url.endswith("/updates/signatures/1.4.0"):
            return DummyResponse(
                payload={
                    "signature": base64.b64encode(b"unused").decode("utf-8"),
                    "sbom_signature": base64.b64encode(_sign_bytes(sbom_bytes, private_key)).decode("utf-8"),
                    "attestation_signature": base64.b64encode(
                        _sign_bytes(attestation_bytes, private_key)
                    ).decode("utf-8"),
                    "manifest_signature": base64.b64encode(
                        _sign_bytes(manifest_bytes, private_key)
                    ).decode("utf-8"),
                }
            )
        if url.endswith("/updates/sbom/1.4.0"):
            return DummyResponse(content=sbom_bytes)
        if url.endswith("/updates/attestation/1.4.0"):
            return DummyResponse(content=attestation_bytes)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("client.app.core.CLIENT_PUBLIC_KEY_PATH", public_key)

    assert verify_release(
        manifest,
        "http://127.0.0.1:8081",
        manifest_bytes=manifest_bytes,
    ) is True


def test_verify_release_rejects_incomplete_manifest():
    manifest = {
        "version": "1.4.0",
        "artifact_name": "robot-app-1.4.0.bin",
    }

    try:
        verify_release(manifest, "http://127.0.0.1:8081")
        assert False, "Expected ValueError for incomplete manifest"
    except ValueError as exc:
        assert "Manifest missing required fields" in str(exc)


def test_verify_release_rejects_attestation_mismatch(monkeypatch, tmp_path):
    _, public_key = _generate_keypair(tmp_path)
    private_key = tmp_path / "update-private.pem"

    sbom_bytes = b'{"artifact":"robot-app-1.4.0.bin","version":"1.4.0"}'
    bad_attestation_payload = {
        "subject": {
            "name": "robot-app-9.9.9.bin",
            "version": "1.4.0",
            "sha256": "unused-in-this-test",
        },
        "materials": [
            {
                "name": "sbom-1.4.0.json",
                "sha256": sha256_bytes(sbom_bytes),
            }
        ],
    }
    bad_attestation_bytes = canonical_json_bytes(bad_attestation_payload)

    manifest = {
        "version": "1.4.0",
        "artifact_name": "robot-app-1.4.0.bin",
        "artifact_url": "/updates/package/1.4.0",
        "sbom_name": "sbom-1.4.0.json",
        "attestation_name": "attestation-1.4.0.json",
        "signature_name": "robot-app-1.4.0.sig",
        "sbom_signature_name": "sbom-1.4.0.sig",
        "attestation_signature_name": "attestation-1.4.0.sig",
        "manifest_signature_name": "manifest-1.4.0.sig",
        "artifact_sha256": "unused-in-this-test",
        "sbom_sha256": sha256_bytes(sbom_bytes),
        "attestation_sha256": sha256_bytes(bad_attestation_bytes),
    }
    manifest_bytes = canonical_json_bytes(manifest)

    class DummyResponse:
        def __init__(self, payload=None, content=b""):
            self._payload = payload or {}
            self.content = content
            self.status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, timeout=5):
        if url.endswith("/updates/signatures/1.4.0"):
            return DummyResponse(
                payload={
                    "signature": base64.b64encode(b"unused").decode("utf-8"),
                    "sbom_signature": base64.b64encode(_sign_bytes(sbom_bytes, private_key)).decode("utf-8"),
                    "attestation_signature": base64.b64encode(
                        _sign_bytes(bad_attestation_bytes, private_key)
                    ).decode("utf-8"),
                    "manifest_signature": base64.b64encode(
                        _sign_bytes(manifest_bytes, private_key)
                    ).decode("utf-8"),
                }
            )
        if url.endswith("/updates/sbom/1.4.0"):
            return DummyResponse(content=sbom_bytes)
        if url.endswith("/updates/attestation/1.4.0"):
            return DummyResponse(content=bad_attestation_bytes)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("client.app.core.CLIENT_PUBLIC_KEY_PATH", public_key)

    try:
        verify_release(
            manifest,
            "http://127.0.0.1:8081",
            manifest_bytes=manifest_bytes,
        )
        assert False, "Expected ValueError for attestation mismatch"
    except ValueError as exc:
        assert "Attestation subject artifact mismatch" in str(exc)


def test_check_for_update_rejects_downgrade_manifest(monkeypatch, tmp_path):
    state_file = tmp_path / "version_state.json"
    state_file.write_text(
        json.dumps(
            {
                "current_version": "1.9.1",
                "previous_version": "1.0.0",
                "highest_version": "1.9.1",
            }
        ),
        encoding="utf-8",
    )

    class DummyResponse:
        status_code = 200
        content = canonical_json_bytes({"version": "1.8.0", "artifact_url": "/updates/package/1.8.0"})

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "version": "1.8.0",
                "artifact_url": "/updates/package/1.8.0",
            }

    monkeypatch.setattr("client.app.core.VERSION_STATE_FILE", state_file)
    monkeypatch.setattr("client.app.core.requests.get", lambda *args, **kwargs: DummyResponse())

    update_info = check_for_update()

    assert update_info["update_available"] is False
    assert update_info["latest_version"] == "1.8.0"
    assert "downgrade detected" in update_info["reason"]
