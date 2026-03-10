import base64

from client.app.core import verify_release
from shared.security import sha256_bytes


def test_verify_release_accepts_valid_manifest(monkeypatch):
    attestation_bytes = (
        b'{"subject":{"name":"robot-app-1.4.0.bin","version":"1.4.0","sha256":"unused-in-this-test"},'
        b'"materials":[{"name":"sbom-1.4.0.json","sha256":"c78af98e01b34457ae0e0ba861b3ddd36605c4b8a416e231c4805d6aded3ecf0"}]}'
    )

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
        "sbom_sha256": "c78af98e01b34457ae0e0ba861b3ddd36605c4b8a416e231c4805d6aded3ecf0",
        "attestation_sha256": sha256_bytes(attestation_bytes),
    }

    class DummyResponse:
        def __init__(self, payload=None, content=b""):
            self._payload = payload or {}
            self.content = content

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, timeout=5):
        if url.endswith("/updates/signatures/1.4.0"):
            return DummyResponse(
                payload={
                    "signature": base64.b64encode(b"signature").decode("utf-8"),
                    "sbom_signature": base64.b64encode(b"sbom-signature").decode("utf-8"),
                    "attestation_signature": base64.b64encode(b"attestation-signature").decode("utf-8"),
                    "manifest_signature": base64.b64encode(b"manifest-signature").decode("utf-8"),
                }
            )
        if url.endswith("/updates/sbom/1.4.0"):
            return DummyResponse(content=b"{\"sbom\":\"content\"}")
        if url.endswith("/updates/attestation/1.4.0"):
            return DummyResponse(content=attestation_bytes)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("client.app.core.verify_signature_bytes", lambda *args, **kwargs: True)

    assert verify_release(manifest, "http://127.0.0.1:8081") is True


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


def test_verify_release_rejects_attestation_mismatch(monkeypatch):
    bad_attestation = (
        b'{"subject":{"name":"robot-app-9.9.9.bin","version":"1.4.0","sha256":"unused-in-this-test"},'
        b'"materials":[{"name":"sbom-1.4.0.json","sha256":"c78af98e01b34457ae0e0ba861b3ddd36605c4b8a416e231c4805d6aded3ecf0"}]}'
    )
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
        "sbom_sha256": "c78af98e01b34457ae0e0ba861b3ddd36605c4b8a416e231c4805d6aded3ecf0",
        "attestation_sha256": sha256_bytes(bad_attestation),
    }

    class DummyResponse:
        def __init__(self, payload=None, content=b""):
            self._payload = payload or {}
            self.content = content

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, timeout=5):
        if url.endswith("/updates/signatures/1.4.0"):
            return DummyResponse(
                payload={
                    "signature": base64.b64encode(b"signature").decode("utf-8"),
                    "sbom_signature": base64.b64encode(b"sbom-signature").decode("utf-8"),
                    "attestation_signature": base64.b64encode(b"attestation-signature").decode("utf-8"),
                    "manifest_signature": base64.b64encode(b"manifest-signature").decode("utf-8"),
                }
            )
        if url.endswith("/updates/sbom/1.4.0"):
            return DummyResponse(content=b"{\"sbom\":\"content\"}")
        if url.endswith("/updates/attestation/1.4.0"):
            return DummyResponse(content=bad_attestation)
        raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr("requests.get", fake_get)
    monkeypatch.setattr("client.app.core.verify_signature_bytes", lambda *args, **kwargs: True)

    try:
        verify_release(manifest, "http://127.0.0.1:8081")
        assert False, "Expected ValueError for attestation mismatch"
    except ValueError as exc:
        assert "Attestation subject artifact mismatch" in str(exc)
