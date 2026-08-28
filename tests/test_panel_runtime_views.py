"""Tests for the desktop-panel runtime view endpoints (/runs, /fleet, /runtime).

Each test bootstraps an isolated SIPS_HOME via monkeypatch so no live state
under ~/.hermes/sips is ever touched, then calls the plugin_api handlers
in-process (the same verification the Hermes desktop skill prescribes).
"""

from __future__ import annotations

import json
import os
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
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise

if not hasattr(plugin_api, "router"):  # pragma: no cover - defensive
    pytest.skip("fastapi not installed in this environment", allow_module_level=True)


@pytest.fixture()
def sips_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("SIPS_HOME", str(tmp_path))
    monkeypatch.setattr(plugin_api, "harness_home", lambda: tmp_path, raising=False)
    (tmp_path / "runtime" / "v1" / "runs").mkdir(parents=True)
    return tmp_path


def _write_events(run_id: str, events: list[dict], sips_home: Path) -> Path:
    run_dir = sips_home / "runtime" / "v1" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "events.jsonl"
    path.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return path


def test_runs_lists_history_most_recent_first(sips_home: Path) -> None:
    _write_events(
        "h-old",
        [
            {"event_type": "run.created", "payload": {"objective": "old session"}},
            {"event_type": "run.submitted", "payload": {"session_id": "old"}},
            {"event_type": "task.result", "payload": {"status": "succeeded"}},
        ],
        sips_home,
    )
    time.sleep(0.02)
    _write_events(
        "h-new",
        [
            {"event_type": "run.created", "payload": {"objective": "new session"}},
            {"event_type": "run.submitted", "payload": {"session_id": "new"}},
            {"event_type": "task.heartbeat", "payload": {}},
        ],
        sips_home,
    )

    view = plugin_api.get_runs()
    assert view["available"] is True
    assert view["total"] == 2
    assert [r["run_id"] for r in view["runs"]] == ["h-new", "h-old"]
    assert view["runs"][0]["status"] == "running"
    assert view["runs"][0]["objective"] == "new session"
    assert view["runs"][1]["status"] == "succeeded"
    assert view["runs"][1]["last_event"] == "task.result"


def test_runs_created_not_yet_submitted(sips_home: Path) -> None:
    _write_events("h-early", [{"event_type": "run.created", "payload": {"objective": "early"}}], sips_home)
    view = plugin_api.get_runs()
    assert view["runs"][0]["status"] == "created"


def test_runs_stale_after_six_hours_silent(sips_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time as _time

    path = _write_events(
        "h-dead",
        [
            {"event_type": "run.created", "payload": {"objective": "dead session"}},
            {"event_type": "run.submitted", "payload": {"session_id": "dead"}},
            {"event_type": "task.heartbeat", "payload": {}},
        ],
        sips_home,
    )
    # Backdate the last activity beyond the 6h staleness window.
    old = _time.time() - 7 * 3600
    os.utime(path, (old, old))
    view = plugin_api.get_runs()
    assert view["runs"][0]["status"] == "stale"


def test_runs_empty_root_is_available_with_zero(sips_home: Path) -> None:
    view = plugin_api.get_runs()
    assert view["available"] is True
    assert view["total"] == 0
    assert view["runs"] == []


def test_runs_caps_at_twelve(sips_home: Path) -> None:
    for i in range(15):
        _write_events(f"h-{i:02d}", [{"event_type": "run.created", "payload": {"objective": f"run {i}"}}], sips_home)
        time.sleep(0.01)
    view = plugin_api.get_runs()
    assert view["total"] == 15
    assert len(view["runs"]) == 12
    # most recent kept, oldest dropped
    assert view["runs"][0]["run_id"] == "h-14"
    assert view["runs"][-1]["run_id"] == "h-03"


def test_runs_skips_run_dirs_without_events(sips_home: Path) -> None:
    (sips_home / "runtime" / "v1" / "runs" / "h-empty").mkdir(parents=True)
    _write_events("h-real", [{"event_type": "run.created", "payload": {"objective": "real"}}], sips_home)
    view = plugin_api.get_runs()
    assert view["total"] == 1
    assert view["runs"][0]["run_id"] == "h-real"


def test_fleet_empty_is_available_not_error(sips_home: Path) -> None:
    view = plugin_api.get_fleet()
    assert view["available"] is True
    assert view["campaigns"] == []
    assert "claim_boundary" in view


def test_fleet_campaign_detail_not_found(sips_home: Path) -> None:
    view = plugin_api.get_fleet_campaign("no-such-campaign")
    assert view["available"] is False
    assert view["reason"] == "campaign_not_found"
    assert view["campaign_id"] == "no-such-campaign"


def test_fleet_campaign_detail_rejects_traversal() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        plugin_api.get_fleet_campaign("../etc/passwd")
    assert excinfo.value.status_code == 422


def test_fleet_campaign_detail_projects_children_and_activity(sips_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Detail mapping must match the real payload keys (probed 2026-08-28)."""
    import harness_homebase_mcp as h

    monkeypatch.setattr(plugin_api, "PLUGIN_ROOT", tmp_path)
    h.call_tool("homebase_campaign_fleet_write", {"home": str(tmp_path), "operation": "create", "request_json": json.dumps({"objective": "detail probe", "campaign_id": "detail-probe-2"})})
    h.call_tool("homebase_campaign_fleet_write", {"home": str(tmp_path), "operation": "attach", "request_json": json.dumps({"campaign_id": "detail-probe-2", "title": "child one", "role": "Worker", "objective": "do a thing"})})

    view = plugin_api.get_fleet_campaign("detail-probe-2")
    assert view["available"] is True
    assert view["objective"] == "detail probe"
    assert view["child_count"] == 1
    child = view["children"][0]
    assert child["title"] == "child one"
    assert child["role"] == "Worker"
    assert view["activity"], "activity entries projected"
    assert "event_type" not in view["activity"][0]  # renamed to kind
