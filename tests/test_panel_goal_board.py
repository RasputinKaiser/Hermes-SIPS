"""Tests for the /goal-board unified board endpoint."""

from __future__ import annotations

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
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise

if not hasattr(plugin_api, "router"):  # pragma: no cover - defensive
    pytest.skip("fastapi not installed in this environment", allow_module_level=True)


@pytest.fixture()
def sips_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("SIPS_HOME", str(tmp_path))
    monkeypatch.setattr(plugin_api, "goal_state_path", lambda: tmp_path / "goal_state.json", raising=False)
    monkeypatch.setattr(plugin_api, "harness_home", lambda: tmp_path, raising=False)
    return tmp_path


def _write_goal_state(sips_home: Path, objective: str = "test objective") -> None:
    import json

    (sips_home / "goal_state.json").write_text(
        json.dumps({"objective": objective, "status": "active", "mode": "legacy", "subtasks": []}),
        encoding="utf-8",
    )


def test_goal_board_reports_none_without_any_state(sips_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # No goal state and no runtime runs reachable.
    monkeypatch.setattr(plugin_api, "PLUGIN_ROOT", sips_home, raising=False)
    board = plugin_api.get_goal_board()
    assert board["authority"] == "none"
    assert board["runtime"] is None
    assert board["runtime_tasks"] == []
    assert board["goal"]["available"] is False
    assert "claim_boundary" in board


def test_goal_board_uses_legacy_goal_when_no_runtime(sips_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_goal_state(sips_home)
    monkeypatch.setattr(plugin_api, "PLUGIN_ROOT", sips_home, raising=False)
    board = plugin_api.get_goal_board()
    assert board["authority"] == "legacy-goal"
    assert board["goal"]["available"] is True
    assert board["goal"]["objective"] == "test objective"


def test_goal_board_prefers_runtime_authority(sips_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    _write_goal_state(sips_home)
    monkeypatch.setattr(plugin_api, "PLUGIN_ROOT", sips_home, raising=False)

    # Fake the runtime board payload so no live SIPS_HOME is read.
    class _FakeModule:
        @staticmethod
        def goal_board_payload(root, run_id, since_revision, max_changes):
            return {
                "ok": True,
                "data": {
                    "authority": "runtime-events",
                    "run_id": "h-test",
                    "status": "running",
                    "revision": 3,
                    "progress": {"complete": 1, "total": 2},
                    "ready_task_ids": ["t2"],
                    "tasks": [
                        {"id": "t1", "title": "first", "status": "succeeded", "phase": "verify", "attempts": 1},
                        {"id": "t2", "title": "second", "status": "queued", "phase": "execute", "attempts": 0},
                    ],
                    "recommendation": {"phase": "execute", "title": "second", "why": "ready", "proof_required": "receipt"},
                    "plan": {"phases": [{"title": "Execute", "status": "active"}, {"title": "Verify", "status": "not_applicable"}]},
                },
            }

    import types

    fake = types.ModuleType("harness_homebase_mcp")
    fake.goal_board_payload = _FakeModule.goal_board_payload
    monkeypatch.setitem(sys.modules, "harness_homebase_mcp", fake)

    board = plugin_api.get_goal_board()
    assert board["authority"] == "runtime"
    assert board["runtime"]["run_id"] == "h-test"
    assert board["runtime"]["progress"] == {"complete": 1, "total": 2}
    assert [t["id"] for t in board["runtime_tasks"]] == ["t1", "t2"]
    assert board["runtime_tasks"][1]["ready"] is True
    assert board["runtime_tasks"][0]["ready"] is False
    assert board["recommendation"]["phase"] == "execute"
    assert [p["title"] for p in board["phases"]] == ["Execute"]  # not_applicable dropped
