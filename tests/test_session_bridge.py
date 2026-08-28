"""End-to-end tests for the Hermes session → graph-runtime bridge.

Each test uses an isolated SIPS_HOME sandbox so no run state leaks between
tests or into a developer's live state root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import sips_session_bridge as bridge  # noqa: E402


@pytest.fixture()
def bridge_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "sips-home"
    home.mkdir()
    events = home / "hook_events.jsonl"
    events.write_text('{"event": "probe"}\n')
    adapter = ModuleType("hermes_adapter")
    adapter._event_path = lambda: events  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "hermes_adapter", adapter)
    monkeypatch.setenv("SIPS_HOME", str(home))
    bridge._CONTROLLER = None  # force a fresh controller per test
    return home


def _board(home: Path, run_id: str = "") -> dict:
    import importlib.util

    spec = importlib.util.spec_from_file_location("hhm", _SCRIPTS / "harness_homebase_mcp.py")
    hhm = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(hhm)
    payload = hhm.goal_board_payload(home, run_id, None, 20)
    assert payload.get("ok") is True, payload
    return payload


def test_happy_path_renders_runtime_authority(bridge_home: Path) -> None:
    run = bridge.SessionRun("sess-ok", str(bridge_home / "hook_events.jsonl"))
    run.start(str(bridge_home), "probe happy path")
    run.finish(completed=True, tool_calls=42, failures=0, turns=7, exit_reason="session_end")

    payload = _board(bridge_home, run.run_id)
    data = payload["data"]
    assert data["authority"] == "runtime-events"
    assert data["status"] == "succeeded"
    assert data["objective"] == "probe happy path"
    assert data["progress"] == {"complete": 1, "total": 1, "ratio": 1.0}


def test_failed_outcome_renders_failed(bridge_home: Path) -> None:
    run = bridge.SessionRun("sess-bad", str(bridge_home / "hook_events.jsonl"))
    run.start(str(bridge_home), "probe failure")
    run.finish(completed=False, tool_calls=5, failures=3, turns=2, exit_reason="errors")

    data = _board(bridge_home, run.run_id)["data"]
    assert data["status"] == "failed"
    assert data["progress"]["complete"] == 0


def test_default_board_auto_discovers_latest_run(bridge_home: Path) -> None:
    first = bridge.SessionRun("sess-a", str(bridge_home / "hook_events.jsonl"))
    first.start(str(bridge_home), "first")
    first.finish(completed=True, tool_calls=1, failures=0, turns=1, exit_reason="session_end")
    second = bridge.SessionRun("sess-b", str(bridge_home / "hook_events.jsonl"))
    second.start(str(bridge_home), "second")

    # Latest (running) run is auto-selected with no run_id
    data = _board(bridge_home, "")["data"]
    assert data["objective"] == "second"
    assert data["status"] == "running"

    second.finish(completed=True, tool_calls=2, failures=0, turns=1, exit_reason="session_end")
    assert _board(bridge_home, "")["data"]["status"] == "succeeded"


def test_heartbeat_respects_throttle(bridge_home: Path) -> None:
    run = bridge.SessionRun("sess-throttle", str(bridge_home / "hook_events.jsonl"))
    run.start(str(bridge_home), "throttle probe")
    assert run.beats == 1
    run.heartbeat()  # immediately after start -> throttled
    assert run.beats == 1
    run.last_beat = 0.0
    run.heartbeat()
    assert run.beats == 2
    run.finish(completed=True, tool_calls=2, failures=0, turns=1, exit_reason="session_end")


def test_start_is_idempotent_per_session(bridge_home: Path) -> None:
    sid = "sess-idem"
    bridge.start_session(sid, str(bridge_home))
    first = bridge._ACTIVE[sid]
    bridge.start_session(sid, str(bridge_home))
    assert bridge._ACTIVE[sid] is first
    bridge.finish_session(sid, completed=True, tool_calls=1, failures=0, turns=1, exit_reason="session_end")
    assert sid not in bridge._ACTIVE
