import json

from gateway.app.services import forward_buffered_metrics


def test_forwarder_keeps_failed_metrics(monkeypatch):
    buffered = [
        json.dumps({"robot_id": "robot-1", "status": "healthy"}) + "\n",
        json.dumps({"robot_id": "robot-2", "status": "failed"}) + "\n",
    ]
    replaced = {}

    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    call_count = {"count": 0}

    def fake_post(url, json=None, timeout=5):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return DummyResponse(200)
        return DummyResponse(500)

    monkeypatch.setattr(
        "gateway.app.services.read_buffered_lines",
        lambda: list(buffered),
    )
    monkeypatch.setattr(
        "gateway.app.services.replace_buffered_lines",
        lambda lines: replaced.update({"lines": lines}),
    )
    monkeypatch.setattr("requests.post", fake_post)

    result = forward_buffered_metrics()

    assert result["forwarded"] == 1
    assert result["remaining"] == 1
    assert len(replaced["lines"]) == 1
    assert "robot-2" in replaced["lines"][0]


def test_forwarder_recovers_and_clears_buffer_on_later_success(monkeypatch):
    state = {
        "lines": [json.dumps({"robot_id": "robot-1", "status": "healthy"}) + "\n"],
        "attempt": 0,
    }

    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    def fake_read():
        return list(state["lines"])

    def fake_replace(lines):
        state["lines"] = list(lines)

    def fake_post(url, json=None, timeout=5):
        state["attempt"] += 1
        if state["attempt"] == 1:
            return DummyResponse(503)
        return DummyResponse(200)

    monkeypatch.setattr("gateway.app.services.read_buffered_lines", fake_read)
    monkeypatch.setattr("gateway.app.services.replace_buffered_lines", fake_replace)
    monkeypatch.setattr("gateway.app.services.requests.post", fake_post)
    monkeypatch.setattr("gateway.app.services.FORWARD_RETRIES", 0)

    first_result = forward_buffered_metrics()
    second_result = forward_buffered_metrics()

    assert first_result["forwarded"] == 0
    assert first_result["remaining"] == 1
    assert second_result["forwarded"] == 1
    assert second_result["remaining"] == 0
    assert state["lines"] == []
