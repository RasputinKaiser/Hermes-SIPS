"""Routine lifecycle observations are telemetry, not verified task outcomes."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import sips_session_bridge as bridge


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "trust_test_adapter", Path(__file__).resolve().parents[1] / "hermes_adapter.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "configure_environment", lambda: tmp_path)
    monkeypatch.setattr(module, "_sips_home", lambda: tmp_path)
    monkeypatch.setattr(module, "_run_command", Mock(return_value={"ok": True}))
    monkeypatch.setattr(bridge, "finish_session", Mock())
    return module


@pytest.mark.parametrize("flags", [
    {"completed": True},
    {"completed": False, "failed": True},
    {"completed": True, "interrupted": True},
    {},
])
def test_turn_end_keeps_telemetry_without_memory_or_verified_result(adapter, flags):
    adapter._update_session("session-one", turns=2, tool_calls=3, edits=1, failures=1)
    adapter._on_session_end(session_id="session-one", **flags)
    adapter._run_command.assert_not_called()
    bridge.finish_session.assert_not_called()
    events = [json.loads(line) for line in adapter._event_path().read_text().splitlines()]
    event = next(row for row in events if row["event"] == "on_session_end")
    assert event["metrics"] == {"turns": 2, "tool_calls": 3, "edits": 1, "failures": 1}
    assert event["outcome"] == "unverified"
    assert event["completed"] is flags.get("completed", False)
    assert event["interrupted"] is flags.get("interrupted", False)
    assert event["failed"] is flags.get("failed", False)


def test_repeated_turn_ends_do_not_close_runtime_or_promote_memory(adapter):
    for _ in range(2):
        adapter._update_session("same-session", turns=1, tool_calls=1)
        adapter._on_session_end(session_id="same-session", completed=True)
    adapter._run_command.assert_not_called()
    bridge.finish_session.assert_not_called()
    assert adapter._load_state()["sessions"]["same-session"]["turns"] == 2


@pytest.mark.parametrize("hook", ["_on_session_finalize", "_on_session_reset"])
def test_teardown_closes_unverified_runtime_without_promoting_memory(adapter, monkeypatch, hook):
    close = Mock()
    monkeypatch.setattr(bridge, "close_session", close, raising=False)
    getattr(adapter, hook)(session_id="session-one")
    close.assert_called_once_with("session-one", exit_reason=hook.removeprefix("_on_"))
    adapter._run_command.assert_not_called()
    bridge.finish_session.assert_not_called()


def test_bridge_close_cancels_unverified_session_without_success_receipt(tmp_path, monkeypatch):
    monkeypatch.setenv("SIPS_HOME", str(tmp_path))
    monkeypatch.setattr(bridge, "_CONTROLLER", None)
    monkeypatch.setattr(bridge, "_ACTIVE", {})
    monkeypatch.setattr(bridge, "_EVIDENCE_PATHS", {})
    bridge.start_session("unverified", str(tmp_path), evidence_path=str(tmp_path / "events.jsonl"))
    assert "unverified" in bridge._ACTIVE
    assert callable(getattr(bridge, "close_session", None)), "bridge needs neutral teardown"
    bridge.close_session("unverified", exit_reason="session_finalize")
    state = bridge._controller().read_status("h-unverified")
    assert state["status"] == "canceled"
    result = state["tasks"]["session"]["result"]
    assert result["status"] == "canceled"
    assert result["claims"] == []
    assert result["evidence"] == []
    assert result["artifacts"] == []
    assert result["blockers"] == ["run_canceled"]
    assert "unverified" not in bridge._ACTIVE
    assert "unverified" not in bridge._EVIDENCE_PATHS
    bridge.close_session("unverified", exit_reason="session_finalize")  # idempotent
