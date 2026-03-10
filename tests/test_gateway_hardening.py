import json

import requests

from gateway.app import services as gateway_services


def test_forward_metric_retries_transient_failure(monkeypatch):
    calls = {"count": 0}

    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    def fake_post(url, json=None, timeout=5):
        calls["count"] += 1
        if calls["count"] == 1:
            raise requests.ConnectionError("temporary issue")
        return DummyResponse(200)

    monkeypatch.setattr("gateway.app.services.requests.post", fake_post)
    monkeypatch.setattr("gateway.app.services.time.sleep", lambda *_: None)
    monkeypatch.setattr("gateway.app.services.random.uniform", lambda *_: 0.0)

    ok = gateway_services._forward_metric_with_retry({"robot_id": "robot-1"})
    assert ok is True
    assert calls["count"] == 2


def test_sync_processes_manifests_in_version_order(tmp_path, monkeypatch):
    manifests_dir = tmp_path / "manifests"
    manifests_dir.mkdir(parents=True)
    (manifests_dir / "manifest-1.2.0.json").write_text(
        json.dumps({"version": "1.2.0"}),
        encoding="utf-8",
    )
    (manifests_dir / "manifest-1.1.0.json").write_text(
        json.dumps({"version": "1.1.0"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(gateway_services, "CI_MANIFESTS_DIR", manifests_dir)

    ordered_versions = [p.name for p in gateway_services._iter_manifests_sorted()]
    assert ordered_versions == ["manifest-1.1.0.json", "manifest-1.2.0.json"]
