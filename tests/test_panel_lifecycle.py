"""Tests for the lifecycle lens: /lifecycle endpoint and homebase_status section.

Each test bootstraps an isolated SIPS_HOME via monkeypatch so no live state
under ~/.hermes/sips is ever touched. Handlers are called in-process, the same
verification the Hermes desktop skill prescribes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DASHBOARD = _REPO_ROOT / "dashboard"
for _path in (str(_DASHBOARD), str(_REPO_ROOT / "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    import plugin_api  # noqa: E402
    import harness_homebase_mcp as hb  # noqa: E402
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise

if not hasattr(plugin_api, "router"):  # pragma: no cover - defensive
    pytest.skip("fastapi not installed in this environment", allow_module_level=True)


def _hook_event(**overrides: object) -> dict:
    base = {
        "schema": "hermes.sips.event.v1",
        "id": "test-event",
        "ts": "2026-08-28T21:00:00+00:00",
        "event": "post_tool_call",
        "session_id": "s-1",
        "tool_name": "terminal",
        "status": "ok",
    }
    base.update(overrides)
    return base


@pytest.fixture()
def sips_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("SIPS_HOME", str(tmp_path))
    monkeypatch.setattr(plugin_api, "hook_events_path", lambda: tmp_path / "hook_events.jsonl", raising=False)
    return tmp_path


def _write_hook_events(events: list[dict], sips_home: Path) -> Path:
    path = sips_home / "hook_events.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def test_lifecycle_endpoint_aggregates_tools_and_sessions(sips_home: Path) -> None:
    _write_hook_events(
        [
            _hook_event(event="pre_tool_call", status="allowed"),
            _hook_event(event="post_tool_call", status="ok"),
            _hook_event(event="post_tool_call", tool_name="patch", status="error"),
            _hook_event(event="on_session_start"),
        ],
        sips_home,
    )

    view = plugin_api.get_lifecycle()
    assert view["schema"] == "sips.lifecycle.v1"
    assert view["available"] is True
    assert view["window_events"] == 4
    tools = {row["tool"]: row for row in view["tools"]}
    assert tools["terminal"]["ok"] == 1
    assert tools["terminal"]["allowed"] == 1
    assert tools["patch"]["error"] == 1
    assert view["tools"][0]["tool"] == "terminal"  # highest total first
    sessions = {row["session_id"]: row for row in view["sessions"]}
    assert sessions["s-1"]["events"] == 4
    assert sessions["s-1"]["tool_count"] == 2


def test_lifecycle_flags_denied_events(sips_home: Path) -> None:
    _write_hook_events(
        [_hook_event(event="pre_tool_call", tool_name="terminal", status="denied")],
        sips_home,
    )

    view = plugin_api.get_lifecycle()
    tools = {row["tool"]: row for row in view["tools"]}
    assert tools["terminal"]["denied"] == 1
    assert len(view["denials"]) == 1
    assert view["denials"][0]["tool"] == "terminal"


def test_lifecycle_histogram_buckets_by_hour(sips_home: Path) -> None:
    _write_hook_events(
        [
            _hook_event(ts="2026-08-28T20:00:00+00:00"),
            _hook_event(ts="2026-08-28T20:30:00+00:00"),
            _hook_event(ts="2026-08-28T21:15:00+00:00"),
        ],
        sips_home,
    )

    view = plugin_api.get_lifecycle()
    assert {"hour": "2026-08-28T20", "events": 2} in view["histogram"]
    assert {"hour": "2026-08-28T21", "events": 1} in view["histogram"]


def test_lifecycle_unavailable_without_stream(sips_home: Path) -> None:
    view = plugin_api.get_lifecycle()
    assert view["available"] is False
    assert view["tools"] == []
    assert "claim_boundary" in view


def test_dashboard_payload_embeds_lifecycle(sips_home: Path) -> None:
    _write_hook_events([_hook_event()], sips_home)

    payload = plugin_api._dashboard_payload()
    assert payload["lifecycle"]["available"] is True
    assert payload["lifecycle"]["window_events"] == 1


def test_homebase_status_renders_lifecycle_section(sips_home: Path) -> None:
    _write_hook_events(
        [
            _hook_event(event="post_tool_call", tool_name="terminal", status="ok"),
            _hook_event(event="post_tool_call", tool_name="terminal", status="error"),
        ],
        sips_home,
    )

    payload = hb.status_payload(sips_home)
    payload["lifecycle"] = hb.lifecycle_summary(sips_home)
    markdown = hb.render(payload, "Harness Homebase Status")
    assert "## Lifecycle Lens" in markdown
    assert "**terminal** `2 calls (1 issues)`" in markdown
    assert "**session** `s-1` events=`2`" in markdown


def test_lifecycle_summary_handles_corrupt_lines(sips_home: Path) -> None:
    path = sips_home / "hook_events.jsonl"
    path.write_text('{"event":"post_tool_call","tool_name":"terminal"}\nnot json\n\n', encoding="utf-8")

    summary = hb.lifecycle_summary(sips_home)
    assert summary["available"] is True
    assert summary["window_events"] == 1
