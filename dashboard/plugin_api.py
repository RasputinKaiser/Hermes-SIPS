"""Read-only SIPS telemetry API for the Hermes Desktop addon.

The native Desktop addon calls this authenticated, profile-scoped namespace:
``/api/plugins/harness-self-improvement/status``.

This adapter deliberately exposes summaries rather than raw memory records,
hook payloads, environment values, or credentials. It is safe to render in a
local control-plane dashboard and fails closed to explicit unavailable states.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PLUGIN_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_homebase_mcp import status_payload  # noqa: E402
from sips_paths import goal_state_path, harness_home, hook_events_path  # noqa: E402

try:
    from memory_fabric_jsonl import load_records, store_path  # noqa: E402
except Exception:  # pragma: no cover - memory is optional at runtime
    load_records = None
    store_path = None

router = APIRouter()

RECENT_EVENT_LIMIT = 40  # events kept in the /status payload for drill-down


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _goal_summary() -> dict[str, Any]:
    path = goal_state_path()
    state = _read_json(path)
    if not state:
        return {
            "available": False,
            "status": "none",
            "objective": "No active goal",
            "subtasks": {"total": 0, "done": 0, "pending": 0, "failed": 0},
        }

    subtasks = [item for item in state.get("subtasks", []) if isinstance(item, dict)]
    counts = {
        "total": len(subtasks),
        "done": sum(item.get("status") == "done" for item in subtasks),
        "pending": sum(item.get("status") == "pending" for item in subtasks),
        "failed": sum(item.get("status") == "failed" for item in subtasks),
    }
    current = next((item for item in subtasks if item.get("status") == "pending"), None)
    objective = str(state.get("objective") or "Untitled goal").strip()
    return {
        "available": True,
        "status": str(state.get("status") or "unknown"),
        "mode": str(state.get("mode") or "legacy"),
        "objective": objective[:320],
        "turn_count": int(state.get("turnCount") or 0),
        "cycle_count": int(state.get("cycleCount") or 0),
        "plateau_streak": int(state.get("plateauStreak") or 0),
        "subtasks": counts,
        "current_subtask": (str(current.get("description") or "")[:220] if current else None),
        "created_at": state.get("createdAt"),
    }


def _memory_summary() -> dict[str, Any]:
    if load_records is None or store_path is None:
        return {"available": False, "reason": "memory fabric module unavailable"}
    try:
        path = store_path()
        records = load_records(path)
    except Exception as exc:  # pragma: no cover - defensive boundary
        return {"available": False, "reason": f"memory fabric unavailable: {type(exc).__name__}"}

    status_counts: dict[str, int] = {}
    verified = 0
    for record in records:
        if not isinstance(record, dict):
            continue
        status = str(record.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        if record.get("verify_before_use") is False or status in {"verified", "active"}:
            verified += 1
    return {
        "available": True,
        "store_present": path.is_file(),
        "record_count": len(records),
        "verified_or_active_count": verified,
        "status_counts": status_counts,
    }


def _event_summary() -> dict[str, Any]:
    path = hook_events_path()
    if not path.is_file():
        return {"available": False, "event_count": 0, "recent": []}

    recent: list[dict[str, Any]] = []
    capped = False
    total = 0
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                total += 1
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(item, dict):
                    continue
                recent.append(
                    {
                        "event": str(item.get("event") or item.get("hook_event") or item.get("name") or "lifecycle"),
                        "timestamp": item.get("timestamp") or item.get("created_at") or item.get("recordedAt"),
                        "tool": item.get("tool_name"),
                        "outcome": item.get("outcome") or item.get("status"),
                    }
                )
                if len(recent) > RECENT_EVENT_LIMIT:
                    recent = recent[-RECENT_EVENT_LIMIT:]
                    capped = True
    except OSError:
        return {"available": False, "event_count": 0, "recent": [], "recent_capped": False}
    return {"available": True, "event_count": total, "recent": recent, "recent_capped": capped}


def _surface_counts(payload: dict[str, Any]) -> dict[str, int]:
    surfaces = payload.get("surfaces") or {}
    return {
        "commands": len(surfaces.get("commands") or []),
        "agents": len(surfaces.get("agents") or []),
        "scripts": len(surfaces.get("scripts") or []),
        "hook_events": len(surfaces.get("hook_events") or []),
        "mcp_servers": len(surfaces.get("mcp_servers") or []),
        "mcp_tools": len(surfaces.get("mcp_tools") or []),
    }


def _dashboard_payload() -> dict[str, Any]:
    payload = status_payload(PLUGIN_ROOT)
    manifest = payload.get("manifest") or {}
    return {
        "schema": "sips.dashboard.v1",
        "generated_at": _now(),
        "status": payload.get("status", "source_not_found"),
        "version": manifest.get("version"),
        "manifest": {
            "name": manifest.get("name"),
            "description": manifest.get("description"),
            "has_hooks": bool(manifest.get("has_hooks")),
            "has_commands": bool(manifest.get("has_commands")),
            "has_mcp_servers": bool(manifest.get("has_mcp_servers")),
        },
        "surface_counts": _surface_counts(payload),
        "proof_layers": payload.get("proof_layers") or {},
        "git": {"is_git": bool((payload.get("git") or {}).get("is_git"))},
        "goal": _goal_summary(),
        "memory": _memory_summary(),
        "events": _event_summary(),
        "claim_boundary": "Read-only summaries of local SIPS state. Raw memory, hook payloads, credentials, and write operations are excluded.",
    }


ACTION_SPECS: dict[str, dict[str, Any]] = {
    "inspect_source": {
        "label": "Inspect source",
        "description": "Re-check the vendored SIPS source and worktree proof layers.",
        "tool": "homebase_status",
        "targets": ["repo_source", "worktree"],
        "kind": "inspection",
    },
    "verify_source": {
        "label": "Verify source",
        "description": "Run the bounded SIPS manifest verification without a full regression suite.",
        "tool": "homebase_verify",
        "targets": ["repo_source", "worktree"],
        "kind": "verification",
    },
    "audit_host": {
        "label": "Audit host",
        "description": "Inspect host configuration and live hook enablement/trust receipts.",
        "tool": "homebase_host_audit",
        "targets": ["host_config", "transport"],
        "kind": "inspection",
    },
    "check_mcp_freshness": {
        "label": "Check MCP freshness",
        "description": "Check source, cache, config, child-process, and task-surface freshness.",
        "tool": "homebase_mcp_freshness",
        "targets": ["installed_cache", "task_advertisement", "task_callability", "transport"],
        "kind": "probe",
    },
    "inspect_goal": {
        "label": "Inspect goal",
        "description": "Read the current SIPS goal loop without changing it.",
        "tool": "homebase_goal",
        "targets": [],
        "kind": "inspection",
    },
    "inspect_routes": {
        "label": "Inspect routes",
        "description": "List the available SIPS command, script, and MCP routes.",
        "tool": "homebase_routes",
        "targets": [],
        "kind": "inspection",
    },
}

PROOF_ACTIONS = {
    "repo_source": "inspect_source",
    "worktree": "inspect_source",
    "installed_cache": "check_mcp_freshness",
    "host_config": "audit_host",
    "task_advertisement": "check_mcp_freshness",
    "task_callability": "check_mcp_freshness",
    "transport": "check_mcp_freshness",
}


def _action_catalog(payload: dict[str, Any]) -> list[dict[str, Any]]:
    proof = payload.get("proof_layers") or {}
    ready_states = {"inspected", "active", "done", "verified", "connected", "ready", "healthy", "ok", "source_present"}
    gaps = {name for name, value in proof.items() if str(value).lower() not in ready_states}
    catalog: list[dict[str, Any]] = []
    for action_id, spec in ACTION_SPECS.items():
        targets = list(spec.get("targets") or [])
        catalog.append(
            {
                "id": action_id,
                "label": spec["label"],
                "description": spec["description"],
                "tool": spec["tool"],
                "targets": targets,
                "kind": spec["kind"],
                "recommended": bool(gaps.intersection(targets)),
            }
        )
    return catalog


def _bounded_action_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"value": str(value)[:500]}

    keep = {
        "status",
        "overall_status",
        "proof_layers",
        "claim_boundary",
        "findings",
        "manifest",
        "git",
        "routes",
        "next_checks",
        "verification_commands",
    }
    bounded: dict[str, Any] = {}
    for key in keep:
        item = value.get(key)
        if item is None:
            continue
        if isinstance(item, list):
            bounded[key] = item[:8]
        elif isinstance(item, dict) and key == "proof_layers":
            bounded[key] = {str(name): str(status) for name, status in item.items()}
        elif isinstance(item, dict):
            bounded[key] = {str(name): str(status)[:500] for name, status in list(item.items())[:12]}
        elif isinstance(item, (str, int, float, bool)):
            bounded[key] = item if not isinstance(item, str) else item[:1200]
    return bounded


def _action_result(action_id: str, started_at: str, result: dict[str, Any]) -> dict[str, Any]:
    structured = result.get("structuredContent") or {}
    summary = _bounded_action_payload(structured)
    failed = bool(result.get("isError"))
    status = summary.get("overall_status") or summary.get("status") or ("failed" if failed else "completed")
    return {
        "schema": "sips.action.result.v1",
        "action_id": action_id,
        "tool": ACTION_SPECS[action_id]["tool"],
        "ok": not failed,
        "status": str(status),
        "started_at": started_at,
        "completed_at": _now(),
        "summary": summary,
        "claim_boundary": summary.get("claim_boundary") or "This action reports only the bounded evidence returned by its SIPS Homebase tool.",
    }


ACTION_HISTORY_PATH = PLUGIN_ROOT / "dashboard" / "action_history.jsonl"


def _append_action_history(entry: dict[str, Any]) -> None:
    try:
        with ACTION_HISTORY_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # history is best-effort; never block the action result


def _read_action_history(limit: int = 30) -> list[dict[str, Any]]:
    try:
        lines = ACTION_HISTORY_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                entries.append(item)
        except ValueError:
            continue
    return entries


@router.get("/actions")
def get_actions() -> dict[str, Any]:
    payload = _dashboard_payload()
    return {
        "schema": "sips.actions.v1",
        "generated_at": payload["generated_at"],
        "actions": _action_catalog(payload),
        "proof_actions": PROOF_ACTIONS,
        "claim_boundary": "Actions are allowlisted SIPS Homebase inspections/probes; no arbitrary shell, raw memory, credentials, or write operation is exposed here.",
    }


@router.post("/actions/{action_id}")
def run_action(action_id: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    if action_id not in ACTION_SPECS:
        raise HTTPException(status_code=404, detail="unknown_sips_action")

    started_at = _now()
    args: dict[str, Any] = {"root": str(PLUGIN_ROOT)}
    if action_id == "verify_source":
        args["run_tests"] = bool((body or {}).get("run_tests"))

    try:
        from harness_homebase_mcp import call_tool

        result = call_tool(ACTION_SPECS[action_id]["tool"], args)
        action_result = _action_result(action_id, started_at, result)
        _append_action_history({
            "action_id": action_id,
            "ok": action_result["ok"],
            "status": action_result["status"],
            "proof_layers": action_result.get("summary", {}).get("proof_layers", {}),
            "completed_at": action_result["completed_at"],
        })
        return action_result
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {
            "schema": "sips.action.result.v1",
            "action_id": action_id,
            "tool": ACTION_SPECS[action_id]["tool"],
            "ok": False,
            "status": "failed",
            "started_at": started_at,
            "completed_at": _now(),
            "summary": {"error": type(exc).__name__},
            "claim_boundary": "The action failed before producing a SIPS evidence result.",
        }


@router.get("/status")
def get_status() -> dict[str, Any]:
    payload = _dashboard_payload()
    payload["actions"] = _action_catalog(payload)
    payload["proof_actions"] = PROOF_ACTIONS

    # Persisted proof trend: ready-layer counts across recorded action runs,
    # oldest -> newest, so the hero sparkline survives restarts.
    ready_states = {"inspected", "active", "done", "verified", "connected", "ready", "healthy", "ok", "source_present"}
    trend: list[int] = []
    for entry in _read_action_history(limit=24):
        proof = entry.get("proof_layers")
        if isinstance(proof, dict) and proof:
            trend.append(sum(1 for value in proof.values() if str(value).lower() in ready_states))
    current_proof = payload.get("proof_layers") or {}
    if current_proof:
        trend.append(sum(1 for value in current_proof.values() if str(value).lower() in ready_states))
    payload["proof_trend"] = trend
    return payload


@router.get("/action-history")
def get_action_history() -> dict[str, Any]:
    entries = _read_action_history()
    return {
        "schema": "sips.action.history.v1",
        "entries": entries,
        "generated_at": _now(),
        "claim_boundary": "History records bounded action outcomes only; no raw tool payloads are retained.",
    }


@router.get("/health")
def get_health() -> dict[str, Any]:
    payload = _dashboard_payload()
    return {
        "schema": "sips.dashboard.health.v1",
        "status": payload["status"],
        "generated_at": payload["generated_at"],
        "proof_layers": payload["proof_layers"],
    }


# ---------------------------------------------------------------------------
# Interactive endpoints — bounded wrappers around allowlisted Homebase tools.
# Same contract as the action endpoints: no arbitrary shell, raw memory, or
# credentials; every response carries an explicit claim boundary.
# ---------------------------------------------------------------------------

def _tool_payload(result: dict[str, Any]) -> dict[str, Any]:
    return result.get("structuredContent") or {}


@router.get("/selfloop")
def get_selfloop() -> dict[str, Any]:
    started_at = _now()
    try:
        from harness_homebase_mcp import call_tool

        payload = _tool_payload(call_tool("homebase_selfloop", {"root": str(PLUGIN_ROOT), "action": "status"}))
        state = payload.get("state") or {}
        return {
            "schema": "sips.selfloop.view.v1",
            "generated_at": _now(),
            "ok": payload.get("status") == "passed",
            "active": bool(state.get("ok")) or state.get("status") not in (None, "none"),
            "state": {k: state.get(k) for k in ("objective", "status", "focus", "cycle_count", "started_at") if k in state},
            "raw": {k: payload.get(k) for k in ("protocol",) if payload.get(k)},
            "claim_boundary": "Selfloop status is a bounded read of persisted loop state; it does not prove any improvement claim.",
        }
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {"schema": "sips.selfloop.view.v1", "generated_at": started_at, "ok": False, "active": False, "state": {}, "error": type(exc).__name__,
                "claim_boundary": "The selfloop read failed before producing state."}


@router.post("/selfloop")
def post_selfloop(body: dict[str, Any]) -> dict[str, Any]:
    started_at = _now()
    action = str((body or {}).get("action") or "")
    if action not in {"start", "pause", "resume", "complete", "clear", "record"}:
        raise HTTPException(status_code=422, detail="invalid_selfloop_action")

    args: dict[str, Any] = {"root": str(PLUGIN_ROOT), "action": action}
    focus = str((body or {}).get("focus") or "").strip()
    outcome = str((body or {}).get("outcome") or "").strip()
    summary = str((body or {}).get("summary") or "").strip()
    if action == "start" and focus:
        args["focus"] = focus[:300]
    if action == "record":
        if outcome not in {"improved", "plateau", "blocked"}:
            raise HTTPException(status_code=422, detail="invalid_record_outcome")
        args["outcome"] = outcome
        if summary:
            args["summary"] = summary[:2000]

    try:
        from harness_homebase_mcp import call_tool

        payload = _tool_payload(call_tool("homebase_selfloop", args))
        state = payload.get("state") or {}
        ok = payload.get("status") == "passed"
        return {
            "schema": "sips.selfloop.mutation.v1",
            "action": action,
            "ok": ok,
            "state": {k: state.get(k) for k in ("objective", "status", "focus", "cycle_count", "started_at") if k in state},
            "error": None if ok else str((state or {}).get("error") or "selfloop command failed"),
            "completed_at": _now(),
            "claim_boundary": "Selfloop mutations persist loop state only; the agent must still execute and verify each improvement cycle.",
        }
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {"schema": "sips.selfloop.mutation.v1", "action": action, "ok": False, "state": {}, "error": type(exc).__name__,
                "completed_at": _now(), "claim_boundary": "The selfloop mutation failed before producing state."}


@router.post("/recall")
def post_recall(body: dict[str, Any]) -> dict[str, Any]:
    query = str((body or {}).get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=422, detail="recall_query_required")
    limit = max(1, min(int((body or {}).get("limit") or 5), 10))

    try:
        from harness_homebase_mcp import call_tool

        payload = _tool_payload(call_tool("homebase_recall", {"root": str(PLUGIN_ROOT), "query": query[:300], "limit": limit}))
        records = []
        for record in (payload.get("records") or [])[:limit]:
            if not isinstance(record, dict):
                continue
            records.append({
                "title": str(record.get("title") or "Untitled")[:160],
                "tier": str(record.get("tier") or "unknown"),
                "confidence": str(record.get("confidence") or "unknown"),
                "status": str(record.get("status") or "unknown"),
                "body": str(record.get("body") or record.get("summary") or "")[:600],
                "tags": [str(tag)[:40] for tag in (record.get("tags") or [])[:6] if tag],
            })
        return {
            "schema": "sips.recall.v1",
            "query": query[:300],
            "status": payload.get("status"),
            "records": records,
            "generated_at": _now(),
            "claim_boundary": "Recall returns scoped SIPS lesson summaries; retrieval gates do not prove the selected claims.",
        }
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {"schema": "sips.recall.v1", "query": query[:300], "status": "failed", "records": [], "error": type(exc).__name__,
                "generated_at": _now(), "claim_boundary": "The recall search failed before producing records."}


@router.post("/record")
def post_record(body: dict[str, Any]) -> dict[str, Any]:
    title = str((body or {}).get("title") or "").strip()
    lesson_body = str((body or {}).get("body") or "").strip()
    if not title or not lesson_body:
        raise HTTPException(status_code=422, detail="title_and_body_required")
    tier = str((body or {}).get("tier") or "learning")
    if tier not in {"work", "knowledge", "learning"}:
        raise HTTPException(status_code=422, detail="invalid_tier")

    args: dict[str, Any] = {
        "root": str(PLUGIN_ROOT),
        "tier": tier,
        "title": title[:160],
        "body": lesson_body[:2000],
        "scope": str(PLUGIN_ROOT),
    }
    tags = str((body or {}).get("tags") or "").strip()
    if tags:
        args["tags"] = tags[:200]

    try:
        from harness_homebase_mcp import call_tool

        payload = _tool_payload(call_tool("homebase_record", args))
        ok = payload.get("status") == "passed"
        return {
            "schema": "sips.record.v1",
            "ok": ok,
            "title": title[:160],
            "error": None if ok else "record command failed",
            "generated_at": _now(),
            "claim_boundary": "Recording persists a lesson into the SIPS Memory Fabric; it does not verify the lesson.",
        }
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {"schema": "sips.record.v1", "ok": False, "title": title[:160], "error": type(exc).__name__,
                "generated_at": _now(), "claim_boundary": "The record write failed before persisting."}


@router.get("/routes")
def get_routes() -> dict[str, Any]:
    try:
        from harness_homebase_mcp import call_tool

        payload = _tool_payload(call_tool("homebase_routes", {"root": str(PLUGIN_ROOT)}))
        routes = []
        for route in (payload.get("routes") or [])[:24]:
            if isinstance(route, dict):
                routes.append({
                    "name": str(route.get("route") or route.get("name") or "")[:120],
                    "mcp_tool": str(route.get("mcp_tool") or "")[:120],
                    "fallback": str(route.get("fallback") or "")[:200],
                })
        return {
            "schema": "sips.routes.v1",
            "routes": routes,
            "generated_at": _now(),
            "claim_boundary": "Routes list declared SIPS command surfaces; listing a route does not prove it is currently callable.",
        }
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {"schema": "sips.routes.v1", "routes": [], "error": type(exc).__name__,
                "generated_at": _now(), "claim_boundary": "The routes read failed before producing entries."}


# ---------------------------------------------------------------------------
# Goal subtasks — bounded wrappers around the goal_state.py CLI contract:
#   add-subtask "<description>"  /  complete-subtask <id>
# ---------------------------------------------------------------------------

def _run_goal_state(*cli_args: str) -> dict[str, Any]:
    import subprocess

    command = [sys.executable, str(SCRIPTS_DIR / "goal_state.py"), *cli_args]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=15)
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        return {"ok": False, "error": f"goal_state returned non-JSON (rc={completed.returncode})"}
    return payload if isinstance(payload, dict) else {"ok": False, "error": "goal_state returned a non-object"}


@router.get("/goal")
def get_goal() -> dict[str, Any]:
    summary = _goal_summary()
    summary["schema"] = "sips.goal.v1"
    summary["subtask_list"] = [
        {
            "id": str(item.get("id") or "")[:60],
            "description": str(item.get("description") or "")[:220],
            "status": str(item.get("status") or "pending"),
        }
        for item in (_read_json(goal_state_path()) or {}).get("subtasks", [])
        if isinstance(item, dict)
    ]
    summary["claim_boundary"] = "Goal state is a bounded read of persisted loop state; it does not prove any improvement claim."
    return summary


@router.post("/goal/subtask")
def post_goal_subtask(body: dict[str, Any]) -> dict[str, Any]:
    description = str((body or {}).get("description") or "").strip()
    if not description:
        raise HTTPException(status_code=422, detail="description_required")

    result = _run_goal_state("add-subtask", description[:220])
    ok = bool(result.get("ok"))
    subtask = result.get("subtask") or {}
    return {
        "schema": "sips.goal.mutation.v1",
        "op": "add-subtask",
        "ok": ok,
        "subtask": {k: str(subtask.get(k) or "")[:220] for k in ("id", "description", "status")} if isinstance(subtask, dict) else {},
        "error": None if ok else str(result.get("error") or "add-subtask failed"),
        "completed_at": _now(),
        "claim_boundary": "Adding a subtask persists loop state; it does not execute or verify anything.",
    }


@router.post("/goal/subtask/complete")
def post_goal_subtask_complete(body: dict[str, Any]) -> dict[str, Any]:
    subtask_id = str((body or {}).get("id") or "").strip()
    if not subtask_id:
        raise HTTPException(status_code=422, detail="id_required")

    result = _run_goal_state("complete-subtask", subtask_id[:60])
    ok = bool(result.get("ok"))
    return {
        "schema": "sips.goal.mutation.v1",
        "op": "complete-subtask",
        "ok": ok,
        "id": subtask_id[:60],
        "error": None if ok else str(result.get("error") or f"complete-subtask {subtask_id} failed"),
        "completed_at": _now(),
        "claim_boundary": "Completing a subtask records progress only; evidence still comes from verification runs.",
    }
