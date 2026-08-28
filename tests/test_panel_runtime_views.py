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


def test_run_detail_projects_tasks_events_budgets(sips_home: Path) -> None:
    """Detail must mirror the runtime read API shapes (probed 2026-08-28)."""
    import subprocess

    env = dict(os.environ, SIPS_HOME=str(sips_home))
    cli = str(_REPO_ROOT / "scripts" / "sips_runtime.py")

    def _cli(op: str, payload: dict) -> None:
        subprocess.run(
            ["python3", cli, "write", "--op", op, "--json", json.dumps(payload)],
            check=True, env=env, capture_output=True, text=True,
        )

    _cli("create", {
        "run_id": "h-detail",
        "objective": "detail test run",
        "idempotency_key": "h-detail:create",
        "expected_revision": 0,
        "tasks": [{
            "id": "task-a", "objective": "task a objective",
            "estimated_tokens": 50000, "retry_limit": 3,
            "resource_estimates": {"tool_calls": 16, "retrieval_tokens": 512},
        }],
        "soft_budget": 200000, "hard_budget": 400000,
    })
    _cli("submit", {"run_id": "h-detail", "idempotency_key": "h-detail:submit", "expected_revision": 1})

    view = plugin_api.get_run_detail("h-detail")
    assert view["available"] is True
    assert view["run_id"] == "h-detail"
    assert view["status"] in {"created", "running", "leased"}  # submit may auto-lease
    assert view["objective"] == "detail test run"
    assert view["budgets"]["hard_limit"] == 400000
    task_ids = [t["id"] for t in view["tasks"]]
    assert "task-a" in task_ids
    task = next(t for t in view["tasks"] if t["id"] == "task-a")
    assert task["objective"] == "task a objective"
    assert view["events"], "events projected"
    assert view["events"][0]["type"] == "run.created"
    assert "timestamp" not in view["events"][0]  # renamed to at


def test_run_detail_unknown_run(sips_home: Path) -> None:
    view = plugin_api.get_run_detail("h-does-not-exist")
    assert view["available"] is False
    assert "unknown run" in view["reason"]


def test_runtime_read_tool_status_and_events(sips_home: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """homebase_runtime_read: auto-discovery, events limit, invalid op rejection."""
    import subprocess

    import harness_homebase_mcp as h

    env = dict(os.environ, SIPS_HOME=str(sips_home))
    cli = str(_REPO_ROOT / "scripts" / "sips_runtime.py")

    def _cli(op: str, payload: dict) -> None:
        subprocess.run(
            ["python3", cli, "write", "--op", op, "--json", json.dumps(payload)],
            check=True, env=env, capture_output=True, text=True,
        )

    _cli("create", {
        "run_id": "h-tool", "objective": "tool probe", "idempotency_key": "h-tool:create",
        "expected_revision": 0,
        "tasks": [{
            "id": "t1", "objective": "t", "estimated_tokens": 50000, "retry_limit": 3,
            "resource_estimates": {"tool_calls": 16, "retrieval_tokens": 512},
        }],
        "soft_budget": 200000, "hard_budget": 400000,
    })
    _cli("submit", {"run_id": "h-tool", "idempotency_key": "h-tool:submit", "expected_revision": 1})

    # no run_id -> auto-discover the run just created
    payload = h.runtime_read_payload(tmp_path, "status", "")
    assert payload["ok"] is True
    assert payload["run_id"] == "h-tool"
    assert payload["data"]["objective"] == "tool probe"
    assert payload["data"]["budgets"]["hard_limit"] == 400000

    # events with limit
    payload_ev = h.runtime_read_payload(tmp_path, "events", "h-tool", 2)
    assert payload_ev["ok"] is True
    assert payload_ev["count"] == 2
    assert all(set(e) == {"event_type", "timestamp", "revision", "actor"} for e in payload_ev["data"])

    # unknown run degrades to ok:false, not an exception
    payload_bad = h.runtime_read_payload(tmp_path, "status", "h-nope")
    assert payload_bad["ok"] is False
    assert "unknown run" in payload_bad["error"]

    # empty runs root -> explicit error (SIPS_HOME must point at the empty dir;
    # _latest_runtime_run_id reads the env-resolved root, not its argument)
    monkeypatch.setenv("SIPS_HOME", str(tmp_path / "empty-home"))
    payload_none = h.runtime_read_payload(tmp_path.parent, "status", "")
    assert payload_none["ok"] is False
    assert payload_none["error"] == "no runtime runs exist"


def test_fleet_create_and_attach_writes(sips_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Write endpoints create spines and attach children via the real registry."""
    import harness_homebase_mcp as h

    monkeypatch.setattr(plugin_api, "PLUGIN_ROOT", tmp_path)

    created = plugin_api.post_fleet_create({"objective": "write test campaign", "campaign_id": "write-test-1", "tags": ["test"]})
    assert created["available"] is True
    assert created["campaign_id"] == "write-test-1"
    assert created["status"] == "active"
    assert created["revision"] == 1

    attached = plugin_api.post_fleet_attach({"campaign_id": "write-test-1", "title": "child one", "role": "Scout", "objective": "scout"})
    assert attached["available"] is True
    assert attached["child_count"] == 1
    assert attached["revision"] == 2

    # the list endpoint now sees the campaign
    fleet = plugin_api.get_fleet()
    assert any(c["campaign_id"] == "write-test-1" for c in fleet["campaigns"])


def test_fleet_write_validation_rejects_bad_input(sips_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from fastapi import HTTPException

    monkeypatch.setattr(plugin_api, "PLUGIN_ROOT", tmp_path)

    with pytest.raises(HTTPException) as e1:
        plugin_api.post_fleet_create({"objective": ""})
    assert e1.value.status_code == 422
    with pytest.raises(HTTPException) as e2:
        plugin_api.post_fleet_create({"objective": "x", "campaign_id": "bad/id"})
    assert e2.value.status_code == 422
    with pytest.raises(HTTPException) as e3:
        plugin_api.post_fleet_attach({"campaign_id": "c1", "title": ""})
    assert e3.value.status_code == 422
    with pytest.raises(HTTPException) as e4:
        plugin_api.post_fleet_attach({"campaign_id": "c1", "title": "t", "role": "Emperor"})
    assert e4.value.status_code == 422


def test_fleet_attach_unknown_campaign_degrades(sips_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(plugin_api, "PLUGIN_ROOT", tmp_path)
    result = plugin_api.post_fleet_attach({"campaign_id": "no-such", "title": "x"})
    assert result["available"] is False
    assert result["reason"] == "campaign_not_found"


def test_memory_browse_filters_and_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """/memory: newest-first, tier/status/query filters, limit clamp."""
    monkeypatch.setattr(plugin_api, "load_records", lambda: [
        {"id": "mem_a", "title": "Alpha lesson", "tier": "learning", "status": "active", "confidence": "high", "tags": ["t1"], "scope": "/tmp", "created_at": "2026-08-28T01:00:00+00:00", "body": "alpha body"},
        {"id": "mem_b", "title": "Beta work", "tier": "work", "status": "candidate", "confidence": "medium", "tags": [], "scope": "/tmp", "created_at": "2026-08-28T02:00:00+00:00", "body": "beta body"},
        {"id": "mem_c", "title": "Gamma archived", "tier": "learning", "status": "archived", "confidence": "low", "tags": [], "scope": "/tmp", "created_at": "2026-08-27T00:00:00+00:00", "body": "gamma"},
    ])

    view = plugin_api.get_memory()
    assert view["available"] is True
    assert view["total_matched"] == 3
    assert [r["id"] for r in view["records"]] == ["mem_b", "mem_a", "mem_c"]  # newest first
    assert plugin_api.get_memory(tier="learning")["total_matched"] == 2
    assert plugin_api.get_memory(status="archived")["records"][0]["id"] == "mem_c"
    assert [r["id"] for r in plugin_api.get_memory(query="beta")["records"]] == ["mem_b"]
    assert len(plugin_api.get_memory(limit=1)["records"]) == 1


def test_memory_browse_rejects_bad_filters() -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as e1:
        plugin_api.get_memory(tier="bogus")
    assert e1.value.status_code == 422
    with pytest.raises(HTTPException) as e2:
        plugin_api.get_memory(status="nope")
    assert e2.value.status_code == 422


def test_fleet_child_status_write_and_validation(sips_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(plugin_api, "PLUGIN_ROOT", tmp_path)

    plugin_api.post_fleet_create({"objective": "r5 test", "campaign_id": "child-status-1"})
    plugin_api.post_fleet_attach({"campaign_id": "child-status-1", "title": "kid", "role": "Worker"})
    child_id = plugin_api.get_fleet_campaign("child-status-1")["children"][0]["child_id"]

    result = plugin_api.post_fleet_child_status({"campaign_id": "child-status-1", "child_id": child_id, "status": "blocked", "reason": "probe"})
    assert result["available"] is True
    assert result["status"] == "blocked"
    assert result["revision"] == 3

    # detail now reflects the new status
    detail = plugin_api.get_fleet_campaign("child-status-1")
    assert detail["children"][0]["status"] == "blocked"


def test_run_annotate_roundtrip(sips_home: Path, tmp_path: Path) -> None:
    """Annotations persist beside the event store and surface in list+detail."""
    import subprocess

    env = dict(os.environ, SIPS_HOME=str(sips_home))
    cli = str(_REPO_ROOT / "scripts" / "sips_runtime.py")
    subprocess.run(
        ["python3", cli, "write", "--op", "create", "--json", json.dumps({
            "run_id": "h-ann", "objective": "annotate me", "idempotency_key": "k1", "expected_revision": 0,
            "tasks": [{"id": "t1", "objective": "t", "estimated_tokens": 50000, "retry_limit": 3,
                       "resource_estimates": {"tool_calls": 16, "retrieval_tokens": 512}}],
            "soft_budget": 200000, "hard_budget": 400000,
        })],
        check=True, env=env, capture_output=True, text=True,
    )

    first = plugin_api.post_run_annotate("h-ann", {"label": "First pass"})
    assert first["available"] is True
    assert first["label"] == "First pass"
    second = plugin_api.post_run_annotate("h-ann", {"label": "Second pass"})
    assert second["available"] is True
    assert len(second["labels"]) == 2

    detail = plugin_api.get_run_detail("h-ann")
    assert [l["label"] for l in detail["labels"]] == ["First pass", "Second pass"]
    row = next(r for r in plugin_api.get_runs()["runs"] if r["run_id"] == "h-ann")
    assert row["label"] == "Second pass"  # newest label wins in the list

    missing = plugin_api.post_run_annotate("h-nope", {"label": "x"})
    assert missing["available"] is False
    assert missing["reason"] == "run_not_found"

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        plugin_api.post_run_annotate("h-ann", {"label": ""})
    assert excinfo.value.status_code == 422


def test_campaign_status_write_and_open_children_guard(sips_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(plugin_api, "PLUGIN_ROOT", tmp_path)

    plugin_api.post_fleet_create({"objective": "campaign status test", "campaign_id": "camp-status-1"})
    result = plugin_api.post_fleet_campaign_status({"campaign_id": "camp-status-1", "status": "abandoned", "reason": "test"})
    assert result["available"] is True
    assert result["status"] == "abandoned"

    # reopen
    reopen = plugin_api.post_fleet_campaign_status({"campaign_id": "camp-status-1", "status": "active"})
    assert reopen["available"] is True
    assert reopen["status"] == "active"

    # completing with open children is rejected by the registry
    plugin_api.post_fleet_attach({"campaign_id": "camp-status-1", "title": "open kid", "role": "Worker"})
    blocked = plugin_api.post_fleet_campaign_status({"campaign_id": "camp-status-1", "status": "completed"})
    assert blocked["available"] is False
    assert blocked["reason"] == "campaign_has_open_children"

    missing = plugin_api.post_fleet_campaign_status({"campaign_id": "no-such", "status": "archived"})
    assert missing["available"] is False
    assert missing["reason"] == "campaign_not_found"

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as excinfo:
        plugin_api.post_fleet_campaign_status({"campaign_id": "camp-status-1", "status": "quantum"})
    assert excinfo.value.status_code == 422


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


def test_run_detail_projects_gates_and_lesson(sips_home: Path) -> None:
    """Gate evidence {name: {ok}} and lesson_candidate project to bounded chips."""
    import subprocess

    env = dict(os.environ, SIPS_HOME=str(sips_home))
    cli = str(_REPO_ROOT / "scripts" / "sips_runtime.py")

    def _cli(op: str, payload: dict) -> dict:
        proc = subprocess.run(
            ["python3", cli, "write", "--op", op, "--json", json.dumps(payload)],
            check=True, env=env, capture_output=True, text=True,
        )
        return json.loads(proc.stdout)

    _cli("create", {
        "run_id": "h-gates",
        "objective": "gate projection run",
        "idempotency_key": "h-gates:create",
        "expected_revision": 0,
        "tasks": [{"id": "task-g", "objective": "gated task",
                   "estimated_tokens": 8000, "retry_limit": 1}],
    })
    _cli("submit", {"run_id": "h-gates", "idempotency_key": "h-gates:submit", "expected_revision": 1})
    _cli("lease", {"run_id": "h-gates", "owner": "tester", "task_id": "task-g",
                   "idempotency_key": "h-gates:lease", "expected_revision": 2})
    # The CLI's write response is a flat summary; the fencing token lives on
    # the task.leased event, which advance must present back.
    fencing = None
    events_path = sips_home / "runtime" / "v1" / "runs" / "h-gates" / "events.jsonl"
    for line in events_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("event_type") == "task.leased" and str((event.get("payload") or {}).get("task_id")) == "task-g":
            fencing = ((event.get("payload") or {}).get("lease") or {}).get("fencing_token")
    assert fencing is not None, "task.leased event must carry a fencing_token"
    _cli("advance", {
        "run_id": "h-gates", "task_id": "task-g", "owner": "tester",
        "idempotency_key": "h-gates:advance", "expected_revision": 3,
        "fencing_token": fencing,
        "status": "succeeded",
        "summary": "did the gated thing",
        # The runtime validates evidence (status + anchor + count) and requires
        # every gate in GATE_ORDER to pass on advance, so a real receipt is
        # all-passing with all five gates present.
        "gates": {name: {"ok": True, "evidence": [
            {"status": "passed", "evidence_path": str(sips_home / f"{name}.jsonl"), "count": 1}]}
            for name in ("integrity", "correctness", "regression", "resource", "benefit")},
        "lesson_candidate": {"title": "learned a thing"},
    })

    view = plugin_api.get_run_detail("h-gates")
    assert view["available"] is True
    task = next(t for t in view["tasks"] if t["id"] == "task-g")
    assert task["gates"] == {name: "ok" for name in ("integrity", "correctness", "regression", "resource", "benefit")}
    assert task["has_lesson"] is True
    assert task["answer"] == "did the gated thing"


def test_run_events_endpoint_projects_task_summaries(sips_home: Path) -> None:
    """GET /runs/{id}/events: bounded trail with task_id + per-event summary."""
    import subprocess

    env = dict(os.environ, SIPS_HOME=str(sips_home))
    cli = str(_REPO_ROOT / "scripts" / "sips_runtime.py")

    def _cli(op: str, payload: dict) -> dict:
        proc = subprocess.run(
            ["python3", cli, "write", "--op", op, "--json", json.dumps(payload)],
            check=True, env=env, capture_output=True, text=True,
        )
        return json.loads(proc.stdout)

    _cli("create", {
        "run_id": "h-events",
        "objective": "event trail run",
        "idempotency_key": "h-events:create",
        "expected_revision": 0,
        "tasks": [{"id": "task-e", "objective": "eventful task",
                   "estimated_tokens": 8000, "retry_limit": 1}],
    })
    _cli("submit", {"run_id": "h-events", "idempotency_key": "h-events:submit", "expected_revision": 1})
    _cli("lease", {"run_id": "h-events", "owner": "tester", "task_id": "task-e",
                   "idempotency_key": "h-events:lease", "expected_revision": 2})
    fencing = None
    events_path = sips_home / "runtime" / "v1" / "runs" / "h-events" / "events.jsonl"
    for line in events_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("event_type") == "task.leased":
            fencing = ((event.get("payload") or {}).get("lease") or {}).get("fencing_token")
    assert fencing is not None
    _cli("advance", {
        "run_id": "h-events", "task_id": "task-e", "owner": "tester",
        "idempotency_key": "h-events:advance", "expected_revision": 3,
        "fencing_token": fencing, "status": "succeeded", "summary": "the eventful outcome",
        "gates": {name: {"ok": True, "evidence": [
            {"status": "passed", "evidence_path": str(sips_home / f"{name}.jsonl"), "count": 1}]}
            for name in ("integrity", "correctness", "regression", "resource", "benefit")},
    })

    view = plugin_api.get_run_events("h-events")
    assert view["available"] is True
    assert view["total"] == 4  # create + submit + lease + advance
    advanced = next(e for e in view["events"] if e["type"] == "task.advanced")
    assert advanced["task_id"] == "task-e"
    assert advanced["summary"] == "the eventful outcome"
    created = next(e for e in view["events"] if e["type"] == "run.created")
    assert created["task_id"] is None
    # unknown run degrades like the detail view
    missing = plugin_api.get_run_events("h-does-not-exist")
    assert missing["available"] is False
    # limit clamps
    assert len(plugin_api.get_run_events("h-events", limit=2)["events"]) == 2


def test_run_detail_counts_receipts(sips_home: Path) -> None:
    """receipt_count reflects the run's receipts/ dir (0 when absent)."""
    run_dir = sips_home / "runtime" / "v1" / "runs" / "h-receipts"
    (run_dir / "receipts").mkdir(parents=True)
    (run_dir / "receipts" / "000001-x.json").write_text("{}", encoding="utf-8")
    (run_dir / "receipts" / "000002-y.json").write_text("{}", encoding="utf-8")
    (run_dir / "events.jsonl").write_text(
        json.dumps({"event_type": "run.created", "payload": {"objective": "r"}}) + "\n",
        encoding="utf-8",
    )
    view = plugin_api.get_run_detail("h-receipts")
    # status read fails without full runtime state (no lease present), but the
    # receipt_count projection works independently of run validity.
    assert view.get("receipt_count") == 2
    # a run with no receipts dir reports 0 through the same path
    (sips_home / "runtime" / "v1" / "runs" / "h-empty").mkdir(parents=True)
    (sips_home / "runtime" / "v1" / "runs" / "h-empty" / "events.jsonl").write_text("", encoding="utf-8")
    assert plugin_api.get_run_detail("h-empty").get("receipt_count") == 0


def test_runs_projects_task_progress_from_events(sips_home: Path) -> None:
    """Per-run progress derives from run.created specs + task.* events."""
    _write_events(
        "h-progress",
        [
            {
                "event_type": "run.created",
                "payload": {
                    "objective": "progress run",
                    "tasks": [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}, {"id": "t4"}],
                },
            },
            {"event_type": "run.submitted", "payload": {}},
            {"event_type": "task.leased", "payload": {"task_id": "t1"}},
            {"event_type": "task.heartbeat", "payload": {"task_id": "t1"}},
            {"event_type": "task.advanced", "payload": {"task_id": "t1", "result": {"status": "succeeded"}}},
            # alias + retry semantics mirror the runtime reducer
            {"event_type": "task.advanced", "payload": {"task_id": "t2", "result": {"status": "complete"}}},
            {"event_type": "task.advanced", "payload": {"task_id": "t3", "result": {"status": "failed"}}},
            {"event_type": "task.advanced", "payload": {"task_id": "t4", "result": {"status": "retry"}}},
            {"event_type": "task.leased", "payload": {"task_id": "t4"}},
        ],
        sips_home,
    )
    view = plugin_api.get_runs()
    assert view["available"] is True
    run = next(r for r in view["runs"] if r["run_id"] == "h-progress")
    assert run["progress"] == {"total": 4, "succeeded": 2, "failed": 1, "active": 1}


def test_runs_progress_never_seen_tasks_count_active(sips_home: Path) -> None:
    """Tasks declared in the plan but never leased stay in the active bucket."""
    _write_events(
        "h-untouched",
        [
            {
                "event_type": "run.created",
                "payload": {"objective": "idle run", "tasks": [{"id": "a"}, {"id": "b"}]},
            },
        ],
        sips_home,
    )
    view = plugin_api.get_runs()
    run = next(r for r in view["runs"] if r["run_id"] == "h-untouched")
    assert run["progress"] == {"total": 2, "succeeded": 0, "failed": 0, "active": 2}


def test_runs_without_task_events_progress_is_zeroed(sips_home: Path) -> None:
    _write_events(
        "h-no-tasks",
        [
            {"event_type": "run.created", "payload": {"objective": "no task specs"}},
            {"event_type": "run.submitted", "payload": {}},
        ],
        sips_home,
    )
    view = plugin_api.get_runs()
    run = next(r for r in view["runs"] if r["run_id"] == "h-no-tasks")
    assert run["progress"] == {"total": 0, "succeeded": 0, "failed": 0, "active": 0}


def test_memory_browse_returns_filter_counts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """tier_counts/status_counts come from the full store, ignoring filters."""
    monkeypatch.setattr(plugin_api, "load_records", lambda: [
        {"id": "m1", "title": "A", "tier": "work", "status": "active", "created_at": "2026-08-28T00:00:00+00:00"},
        {"id": "m2", "title": "B", "tier": "work", "status": "candidate", "created_at": "2026-08-27T00:00:00+00:00"},
        {"id": "m3", "title": "C", "tier": "learning", "status": "archived", "created_at": "2026-08-26T00:00:00+00:00"},
    ])
    unfiltered = plugin_api.get_memory()
    assert unfiltered["tier_counts"] == {"work": 2, "learning": 1}
    assert unfiltered["status_counts"] == {"active": 1, "candidate": 1, "archived": 1}
    # Counts are unaffected by the request's own filters.
    filtered = plugin_api.get_memory(tier="work")
    assert filtered["total_matched"] == 2
    assert filtered["tier_counts"] == {"work": 2, "learning": 1}
    assert filtered["status_counts"] == {"active": 1, "candidate": 1, "archived": 1}
