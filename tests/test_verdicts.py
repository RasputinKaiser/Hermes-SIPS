"""Tests for the verdicts lens (verdicts_payload + /verdicts endpoint)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_REPO_ROOT / "dashboard"), str(_REPO_ROOT / "scripts")):
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
    lines = [json.dumps(e) for e in events]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _post(tool: str, duration_ms: int, status: str = "ok", offset_s: float = 0.0) -> dict:
    ts = time.time() - offset_s
    return {
        "event": "post_tool_call",
        "tool_name": tool,
        "duration_ms": duration_ms,
        "status": status,
        "timestamp": ts,
    }


@pytest.fixture()
def stream(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "hook_events.jsonl"

    def _fake_hook_events_path():
        return path

    import sips_paths

    monkeypatch.setattr(sips_paths, "hook_events_path", _fake_hook_events_path, raising=False)
    return path


def test_verdicts_ok_and_slow(stream: Path) -> None:
    # terminal: 6 calls, p95 ~ 9-10s -> slow (>= 5s). read_file: fast -> ok.
    events = [_post("terminal", 9000 + i * 100) for i in range(6)]
    events += [_post("read_file", 120 + i) for i in range(6)]
    _write_stream(stream, events)
    payload = tool_latency.verdicts_payload(window_hours=24)
    assert payload["available"] is True
    assert payload["schema"] == "sips.verdicts.v1"
    verdicts = {v["tool"]: v for v in payload["verdicts"]}
    assert verdicts["terminal"]["verdict"] == "slow"
    assert verdicts["read_file"]["verdict"] == "ok"
    assert verdicts["terminal"]["calls"] == 6
    assert verdicts["terminal"]["p95_ms"] > verdicts["read_file"]["p95_ms"]


def test_verdicts_denied(stream: Path) -> None:
    events = [_post("Write", 50), _post("Write", 60, status="denied")]
    _write_stream(stream, events)
    payload = tool_latency.verdicts_payload(window_hours=24)
    verdicts = {v["tool"]: v for v in payload["verdicts"]}
    assert verdicts["Write"]["verdict"] == "denied"
    assert verdicts["Write"]["denials"] == 1


def test_verdicts_ok_when_under_five_calls(stream: Path) -> None:
    # Only 4 calls at 40s each: no self-relative p95 basis, but 40s is above
    # the static 30s slow line, so slow; anything under is ok, not stalled.
    events = [_post("Bash", 40_000) for _ in range(4)]
    _write_stream(stream, events)
    payload = tool_latency.verdicts_payload(window_hours=24)
    verdicts = {v["tool"]: v for v in payload["verdicts"]}
    assert verdicts["Bash"]["verdict"] == "slow"


def test_verdicts_empty_stream(stream: Path) -> None:
    stream.parent.mkdir(parents=True, exist_ok=True)
    stream.write_text("", encoding="utf-8")
    payload = tool_latency.verdicts_payload(window_hours=24)
    assert payload["available"] is False
    assert payload["verdicts"] == []


def test_verdicts_missing_stream(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import sips_paths

    monkeypatch.setattr(
        sips_paths,
        "hook_events_path",
        lambda: tmp_path / "nope.jsonl",
        raising=False,
    )
    payload = tool_latency.verdicts_payload(window_hours=24)
    assert payload["available"] is False
    assert payload["verdicts"] == []


def test_verdicts_endpoint_clamps_window(stream: Path) -> None:
    events = [_post("terminal", 900)]
    _write_stream(stream, events)
    payload = plugin_api.get_verdicts(window_hours=99999)
    assert payload["window_hours"] == 168
    assert payload["claim_boundary"]
