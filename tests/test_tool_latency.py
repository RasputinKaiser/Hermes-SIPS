"""Tests for the tool-latency lens (tool_latency.py + /tool-latency endpoint)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DASHBOARD = _REPO_ROOT / "dashboard"
for _path in (str(_DASHBOARD), str(_REPO_ROOT / "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    import plugin_api  # noqa: E402
    import tool_latency  # noqa: E402
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise


def _write_stream(path: Path, events: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")


@pytest.fixture()
def stream(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    hook_path = tmp_path / "hook_events.jsonl"
    monkeypatch.setattr("sips_paths.hook_events_path", lambda: hook_path, raising=False)
    return hook_path


def _post(tool: str, duration_ms: int, *, age_s: float = 0.0) -> dict:
    ts = time.time() - age_s
    from datetime import datetime, timezone

    return {
        "schema": "hermes.sips.event.v1",
        "id": f"e-{tool}-{duration_ms}-{age_s}",
        "ts": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
        "event": "post_tool_call",
        "tool_name": tool,
        "status": "ok",
        "duration_ms": duration_ms,
    }


def test_latency_stats_median_p90_max(stream: Path) -> None:
    _write_stream(stream, [
        _post("terminal", 100),
        _post("terminal", 300),
        _post("terminal", 200),
        _post("terminal", 1000),
        _post("read_file", 10),
    ])
    payload = tool_latency.tool_latency_payload(window_hours=24)
    assert payload["available"] is True
    rows = {row["tool"]: row for row in payload["tools"]}
    terminal = rows["terminal"]
    assert terminal["calls"] == 4
    assert terminal["median_ms"] == 250  # interpolated: (200+300)/2
    assert terminal["max_ms"] == 1000
    assert 300 <= terminal["p90_ms"] <= 1000
    assert terminal["total_s"] == 1.6
    assert rows["read_file"]["median_ms"] == 10
    # ordered by total time descending
    assert payload["tools"][0]["tool"] == "terminal"


def test_latency_skips_events_without_duration(stream: Path) -> None:
    _write_stream(stream, [
        {"schema": "hermes.sips.event.v1", "event": "post_tool_call", "tool_name": "old_tool", "ts": "2026-08-29T00:00:00Z"},
        _post("timed_tool", 500),
    ])
    payload = tool_latency.tool_latency_payload()
    tools = {row["tool"] for row in payload["tools"]}
    assert "timed_tool" in tools and "old_tool" not in tools


def test_latency_other_events_ignored(stream: Path) -> None:
    _write_stream(stream, [
        {"schema": "hermes.sips.event.v1", "event": "pre_tool_call", "tool_name": "terminal", "ts": "2026-08-29T00:00:00Z", "duration_ms": 99999},
        _post("terminal", 250),
    ])
    payload = tool_latency.tool_latency_payload()
    assert payload["tools"][0]["calls"] == 1
    assert payload["tools"][0]["median_ms"] == 250


def test_latency_missing_stream_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("sips_paths.hook_events_path", lambda: tmp_path / "nope.jsonl", raising=False)
    payload = tool_latency.tool_latency_payload()
    assert payload["available"] is False
    assert "not found" in payload["reason"]


def test_latency_corrupt_lines_skipped(stream: Path) -> None:
    stream.write_text("{corrupt\n" + json.dumps(_post("terminal", 100)) + "\n", encoding="utf-8")
    payload = tool_latency.tool_latency_payload()
    assert payload["tools"][0]["calls"] == 1


def test_latency_endpoint_serves(stream: Path) -> None:
    _write_stream(stream, [_post("terminal", 100)])
    data = plugin_api.get_tool_latency()
    assert data["schema"] == "sips.tool-latency.v1"
    assert data["available"] is True
    assert data["tools"][0]["tool"] == "terminal"
