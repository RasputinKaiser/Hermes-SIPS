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
import time
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


@router.get("/runtime")
def get_runtime() -> dict[str, Any]:
    """Bounded view of the graph-runtime Goal Board (latest run auto-discovered).

    Surfaces the runtime-backed session runs the session bridge writes: one
    run per Hermes session, receipts and gate evidence included. Read-only —
    no mutation endpoint exists for the runtime here.
    """
    try:
        from harness_homebase_mcp import goal_board_payload

        payload = goal_board_payload(PLUGIN_ROOT, "", None, 12)
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {
            "schema": "sips.runtime.view.v1",
            "available": False,
            "reason": f"runtime unavailable: {type(exc).__name__}",
            "generated_at": _now(),
            "claim_boundary": "The runtime read failed before producing board state.",
        }

    if not payload.get("ok"):
        return {
            "schema": "sips.runtime.view.v1",
            "available": False,
            "reason": str(payload.get("error") or "no runtime event stream"),
            "generated_at": _now(),
            "claim_boundary": "No runtime run was available to read.",
        }

    raw_data = payload.get("data")
    data = raw_data if isinstance(raw_data, dict) else {}
    tasks_out: list[dict[str, Any]] = []
    for task in (data.get("tasks") or [])[:6]:
        if not isinstance(task, dict):
            continue
        raw_receipt = task.get("receipt")
        receipt = raw_receipt if isinstance(raw_receipt, dict) else {}
        raw_structured = receipt.get("structured")
        structured = raw_structured if isinstance(raw_structured, dict) else {}
        raw_gates = structured.get("gates")
        gates = raw_gates if isinstance(raw_gates, dict) else {}
        tasks_out.append(
            {
                "id": str(task.get("id") or "")[:60],
                "title": str(task.get("title") or "")[:220],
                "status": str(task.get("status") or "unknown"),
                "attempts": int(task.get("attempts") or 0),
                "phase": str(task.get("phase") or "")[:40],
                "answer": str(structured.get("answer") or "")[:400],
                "gate_status": {str(name)[:40]: str(gate.get("status") or "unknown")[:40] for name, gate in list(gates.items())[:6] if isinstance(gate, dict)},
                "has_receipt": bool(receipt),
            }
        )
    raw_progress = data.get("progress")
    progress = raw_progress if isinstance(raw_progress, dict) else {}
    raw_provenance = data.get("provenance")
    provenance = raw_provenance if isinstance(raw_provenance, dict) else {}
    return {
        "schema": "sips.runtime.view.v1",
        "available": True,
        "authority": str(data.get("authority") or "unknown"),
        "run_id": str(data.get("run_id") or "")[:80],
        "status": str(data.get("status") or "unknown"),
        "objective": str(data.get("objective") or "")[:320],
        "revision": int(data.get("revision") or 0),
        "progress": {
            "complete": int(progress.get("complete") or 0),
            "total": int(progress.get("total") or 0),
            "ratio": float(progress.get("ratio") or 0.0),
        },
        "counts": {str(k)[:30]: int(v) for k, v in (data.get("counts") or {}).items() if isinstance(v, int)},
        "tasks": tasks_out,
        "source_path": str(provenance.get("source_path") or "")[:300],
        "last_updated_at": provenance.get("last_updated_at"),
        "generated_at": _now(),
        "claim_boundary": "Read-only projection of the SIPS graph-runtime Goal Board; receipts are summaries, not full evidence.",
    }


def _read_run_annotations(run_dir: Path) -> list[dict[str, Any]]:
    """Load panel-side labels from a run's annotations.json (newest last)."""
    path = run_dir / "annotations.json"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    labels = loaded.get("labels") if isinstance(loaded, dict) else None
    if not isinstance(labels, list):
        return []
    return [
        {"label": str(e.get("label") or "")[:200], "at": str(e.get("at") or "")[:40]}
        for e in labels[-3:]
        if isinstance(e, dict)
    ]


@router.get("/runs")
def get_runs() -> dict[str, Any]:
    """Bounded history of runtime session runs (most recent first).

    Each Hermes session writes one graph-runtime run under
    ``$SIPS_HOME/runtime/v1/runs``. This surfaces every run as a summary row
    derived from its event stream — read-only, no run payloads leave the host.
    """
    try:
        from sips_runtime.controller import runtime_root

        runs_root = runtime_root()
        run_dirs = [d for d in runs_root.iterdir() if (d / "events.jsonl").exists()] if runs_root.is_dir() else []
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {
            "schema": "sips.runs.view.v1",
            "available": False,
            "reason": f"runtime unavailable: {type(exc).__name__}",
            "runs": [],
            "generated_at": _now(),
            "claim_boundary": "The runtime read failed before producing run history.",
        }

    run_dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    runs_out: list[dict[str, Any]] = []
    for run_dir in run_dirs[:12]:
        events_path = run_dir / "events.jsonl"
        objective = ""
        last_event = ""
        submitted = False
        event_count = 0
        try:
            with events_path.open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    event_count += 1
                    event_type = str(event.get("event_type") or "")
                    if event_type == "run.created":
                        payload = event.get("payload")
                        if isinstance(payload, dict):
                            objective = str(payload.get("objective") or "")
                    elif event_type == "run.submitted":
                        submitted = True
                    last_event = event_type
        except OSError:
            continue
        mtime = events_path.stat().st_mtime
        annotations = _read_run_annotations(run_dir)
        if last_event == "task.result":
            status = "succeeded"
        elif not submitted:
            status = "created"
        elif time.time() - mtime > 6 * 3600:
            # A session that never landed its result and has been silent for
            # 6h+ is stale, not running (crashed host, killed process, etc.).
            status = "stale"
        else:
            status = "running"
        runs_out.append(
            {
                "run_id": run_dir.name[:80],
                "objective": objective[:320],
                "label": annotations[-1]["label"] if annotations else "",
                "status": status,
                "last_event": last_event[:40],
                "events": event_count,
                "updated_at": datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(),
            }
        )
    return {
        "schema": "sips.runs.view.v1",
        "available": True,
        "total": len(run_dirs),
        "runs": runs_out,
        "generated_at": _now(),
        "claim_boundary": "Run summaries derive from event streams; task results live in the runtime, not here.",
    }


@router.get("/fleet")
def get_fleet() -> dict[str, Any]:
    """Bounded view of the campaign fleet (event-backed campaign spines)."""
    try:
        from harness_homebase_mcp import call_tool

        result = call_tool("homebase_campaign_fleet_read", {"root": str(PLUGIN_ROOT), "operation": "list", "limit": 12})
        structured = result.get("structuredContent") or {}
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {
            "schema": "sips.fleet.view.v1",
            "available": False,
            "reason": f"fleet unavailable: {type(exc).__name__}",
            "campaigns": [],
            "generated_at": _now(),
            "claim_boundary": "The fleet read failed before producing campaign state.",
        }

    raw_data = structured.get("data")
    campaigns_raw = raw_data if isinstance(raw_data, list) else []
    campaigns: list[dict[str, Any]] = []
    for item in campaigns_raw[:12]:
        if not isinstance(item, dict):
            continue
        campaigns.append(
            {
                "campaign_id": str(item.get("campaign_id") or "")[:80],
                "objective": str(item.get("objective") or "")[:320],
                "status": str(item.get("status") or "unknown")[:40],
                "child_count": int(item.get("child_count") or 0),
                "archived_child_count": int(item.get("archived_child_count") or 0),
                "runtime_run_id": str(item.get("runtime_run_id") or "")[:80],
                "tags": [str(t)[:40] for t in (item.get("tags") or [])[:6] if isinstance(t, (str, int))],
                "updated_at": str(item.get("updated_at") or "")[:40],
            }
        )
    return {
        "schema": "sips.fleet.view.v1",
        "available": True,
        "total": len(campaigns_raw),
        "storage_root": str(structured.get("storage_root") or "")[:300],
        "campaigns": campaigns,
        "generated_at": _now(),
        "claim_boundary": "Fleet metadata is event-backed; child conversations are enumerated by the host, not here.",
    }


@router.get("/runs/{run_id}")
def get_run_detail(run_id: str) -> dict[str, Any]:
    """Bounded detail of one runtime session run: status, tasks, and events.

    Backed by the graph runtime's read API (status/events), the same source the
    CLI uses — read-only, safe identifiers only.
    """
    safe_id = run_id.strip()[:80]
    try:
        from sips_runtime.api import RuntimeAPI
    except Exception as exc:  # pragma: no cover - defensive API boundary
        return {
            "schema": "sips.run.detail.v1",
            "available": False,
            "reason": f"runtime unavailable: {type(exc).__name__}",
            "run_id": safe_id,
            "generated_at": _now(),
            "claim_boundary": "The runtime read failed before producing run detail.",
        }

    api = RuntimeAPI()
    status_read = api.read("status", {"run_id": safe_id})
    if not status_read.get("ok"):
        return {
            "schema": "sips.run.detail.v1",
            "available": False,
            "reason": str(status_read.get("error") or "run_not_found"),
            "run_id": safe_id,
            "generated_at": _now(),
            "claim_boundary": "No runtime run matched that id.",
        }

    status_data = status_read.get("data") if isinstance(status_read.get("data"), dict) else {}
    events_read = api.read("events", {"run_id": safe_id})
    events_data = events_read.get("data")
    raw_events = events_data if isinstance(events_data, list) else []
    try:
        from sips_runtime.controller import runtime_root

        annotations = _read_run_annotations(runtime_root() / safe_id)
    except Exception:
        annotations = []
    events_out = [
        {
            "type": str(e.get("event_type") or "")[:40],
            "at": str(e.get("timestamp") or "")[:40],
            "revision": int(e.get("revision") or 0),
            "actor": str(e.get("actor") or "")[:40],
        }
        for e in raw_events[-15:]
        if isinstance(e, dict)
    ]
    raw_tasks = status_data.get("tasks")
    task_items = raw_tasks.values() if isinstance(raw_tasks, dict) else (raw_tasks or [])
    tasks_out: list[dict[str, Any]] = []
    for item in list(task_items)[:8]:
        if not isinstance(item, dict):
            continue
        spec = item.get("spec") if isinstance(item.get("spec"), dict) else {}
        result = item.get("result") if isinstance(item.get("result"), dict) else {}
        tasks_out.append(
            {
                "id": str(item.get("id") or spec.get("id") or "")[:60],
                "objective": str(spec.get("objective") or item.get("objective") or "")[:320],
                "status": str(item.get("status") or "")[:40],
                "attempts": int(item.get("attempts") or 0),
                "description": str(spec.get("description") or "")[:220],
                "answer": str(result.get("summary") or "")[:300],
            }
        )
    budget_usage = status_data.get("budget_usage")
    budgets = status_data.get("budgets")
    return {
        "schema": "sips.run.detail.v1",
        "available": True,
        "run_id": str(status_data.get("run_id") or safe_id)[:80],
        "status": str(status_data.get("status") or "unknown")[:40],
        "objective": str(status_data.get("objective") or "")[:320],
        "labels": annotations,
        "revision": int(status_data.get("revision") or 0),
        "workspace_root": str(status_data.get("workspace_root") or "")[:300],
        "budgets": {str(k)[:40]: int(v) for k, v in (budgets or {}).items() if isinstance(v, int)},
        "budget_usage": {str(k)[:40]: int(v) for k, v in (budget_usage or {}).items() if isinstance(v, int)},
        "tasks": tasks_out,
        "events": events_out,
        "generated_at": _now(),
        "claim_boundary": "Read-only projection of one runtime run; event payloads stay in the runtime store.",
    }


@router.get("/fleet/{campaign_id}")
def get_fleet_campaign(campaign_id: str) -> dict[str, Any]:
    """Bounded detail view of one campaign spine, including attached children."""
    safe_id = campaign_id.strip()[:80]
    if not safe_id or any(ch in safe_id for ch in "/\\"):
        raise HTTPException(status_code=422, detail="campaign_id_invalid")
    try:
        from harness_homebase_mcp import call_tool

        result = call_tool(
            "homebase_campaign_fleet_read",
            {"root": str(PLUGIN_ROOT), "operation": "campaign", "campaign_id": safe_id},
        )
        structured = result.get("structuredContent") or {}
    except Exception as exc:  # pragma: no cover - defensive API boundary
        reason = "campaign_not_found" if type(exc).__name__ == "CampaignNotFound" else f"fleet unavailable: {type(exc).__name__}"
        return {
            "schema": "sips.fleet.campaign.v1",
            "available": False,
            "reason": reason,
            "campaign_id": safe_id,
            "generated_at": _now(),
            "claim_boundary": "The fleet read failed before producing campaign detail.",
        }

    raw_data = structured.get("data")
    data = raw_data if isinstance(raw_data, dict) else {}
    if not data:
        return {
            "schema": "sips.fleet.campaign.v1",
            "available": False,
            "reason": "campaign_not_found",
            "campaign_id": safe_id,
            "generated_at": _now(),
            "claim_boundary": "No campaign spine matched that id.",
        }

    children_out: list[dict[str, Any]] = []
    for child in (data.get("children") or [])[:20]:
        if not isinstance(child, dict):
            continue
        children_out.append(
            {
                "child_id": str(child.get("child_id") or child.get("id") or "")[:80],
                "title": str(child.get("title") or child.get("objective") or "")[:220],
                "role": str(child.get("role") or "")[:40],
                "thread_id": str(child.get("thread_id") or "")[:80],
                "status": str(child.get("status") or "")[:40],
                "archived": bool(child.get("archived_at")),
                "objective": str(child.get("objective") or "")[:220],
                "summary": str(child.get("summary") or "")[:300],
                "incarnation_count": int(child.get("incarnation_count") or 0),
            }
        )
    activity_out = [
        {
            "kind": str(entry.get("event_type") or entry.get("kind") or "")[:40],
            "at": str(entry.get("timestamp") or entry.get("at") or "")[:40],
            "detail": str(entry.get("reason") or entry.get("summary") or "")[:200],
            "child_id": str(entry.get("child_id") or "")[:80],
            "status": str(entry.get("status") or "")[:40],
        }
        for entry in (data.get("activity") or [])[-10:]
        if isinstance(entry, dict)
    ]
    return {
        "schema": "sips.fleet.campaign.v1",
        "available": True,
        "campaign_id": str(data.get("campaign_id") or safe_id)[:80],
        "objective": str(data.get("objective") or "")[:320],
        "status": str(data.get("status") or "unknown")[:40],
        "status_reason": str(data.get("status_reason") or "")[:120],
        "revision": int(data.get("revision") or 0),
        "child_count": int(data.get("child_count") or 0),
        "visible_child_count": int(data.get("visible_child_count") or 0),
        "runtime_run_id": str(data.get("runtime_run_id") or "")[:80],
        "workspace_root": str(data.get("workspace_root") or "")[:300],
        "tags": [str(t)[:40] for t in (data.get("tags") or [])[:6] if isinstance(t, (str, int))],
        "children": children_out,
        "activity": activity_out,
        "generated_at": _now(),
        "claim_boundary": "Children are metadata pointers; their conversations live in the host, not here.",
    }


@router.post("/fleet/create")
def post_fleet_create(body: dict[str, Any]) -> dict[str, Any]:
    """Create a campaign spine (bounded, validated write via the fleet registry)."""
    data = body if isinstance(body, dict) else {}
    objective = str(data.get("objective") or "").strip()
    if not objective:
        raise HTTPException(status_code=422, detail="objective_required")
    campaign_id = str(data.get("campaign_id") or "").strip() or None
    if campaign_id and (len(campaign_id) > 80 or any(ch in campaign_id for ch in "/\\ \t")):
        raise HTTPException(status_code=422, detail="campaign_id_invalid")
    tags_raw = data.get("tags")
    tags = [str(t).strip()[:40] for t in tags_raw[:6] if str(t).strip()] if isinstance(tags_raw, list) else []
    try:
        from harness_homebase_mcp import call_tool

        request: dict[str, Any] = {"objective": objective[:2000], "tags": tags}
        if campaign_id:
            request["campaign_id"] = campaign_id
        result = call_tool(
            "homebase_campaign_fleet_write",
            {"root": str(PLUGIN_ROOT), "operation": "create", "request_json": json.dumps(request)},
        )
        structured = result.get("structuredContent") or {}
    except Exception as exc:
        return {
            "schema": "sips.fleet.write.v1",
            "available": False,
            "reason": f"fleet write failed: {type(exc).__name__}",
            "generated_at": _now(),
            "claim_boundary": "The fleet write failed before producing state.",
        }
    raw_campaign = structured.get("data")
    campaign = raw_campaign if isinstance(raw_campaign, dict) else {}
    return {
        "schema": "sips.fleet.write.v1",
        "available": True,
        "campaign_id": str(campaign.get("campaign_id") or campaign_id or "")[:80],
        "objective": str(campaign.get("objective") or objective)[:320],
        "status": str(campaign.get("status") or "unknown")[:40],
        "revision": int(campaign.get("revision") or 0),
        "generated_at": _now(),
        "claim_boundary": "Campaign spine created; attach children via POST /fleet/attach.",
    }


@router.post("/fleet/attach")
def post_fleet_attach(body: dict[str, Any]) -> dict[str, Any]:
    """Attach a child thread to a campaign spine (bounded, validated write)."""
    data = body if isinstance(body, dict) else {}
    campaign_id = str(data.get("campaign_id") or "").strip()
    title = str(data.get("title") or "").strip()
    if not campaign_id or len(campaign_id) > 80 or any(ch in campaign_id for ch in "/\\"):
        raise HTTPException(status_code=422, detail="campaign_id_invalid")
    if not title:
        raise HTTPException(status_code=422, detail="title_required")
    role = str(data.get("role") or "Worker").strip()
    if role not in {"Worker", "Scout", "Judge", "Reviewer"}:
        raise HTTPException(status_code=422, detail="role_invalid")
    objective = str(data.get("objective") or "").strip()[:2000]
    summary = str(data.get("summary") or "").strip()[:2000]
    thread_id = str(data.get("thread_id") or "").strip()[:80]
    try:
        from harness_homebase_mcp import call_tool

        request: dict[str, Any] = {"campaign_id": campaign_id, "title": title[:220], "role": role}
        if objective:
            request["objective"] = objective
        if summary:
            request["summary"] = summary
        if thread_id:
            request["thread_id"] = thread_id
        result = call_tool(
            "homebase_campaign_fleet_write",
            {"root": str(PLUGIN_ROOT), "operation": "attach", "request_json": json.dumps(request)},
        )
        structured = result.get("structuredContent") or {}
    except Exception as exc:
        reason = "campaign_not_found" if type(exc).__name__ == "CampaignNotFound" else f"fleet write failed: {type(exc).__name__}"
        return {
            "schema": "sips.fleet.write.v1",
            "available": False,
            "reason": reason,
            "campaign_id": campaign_id,
            "generated_at": _now(),
            "claim_boundary": "The fleet write failed before producing state.",
        }
    raw_campaign = structured.get("data")
    campaign = raw_campaign if isinstance(raw_campaign, dict) else {}
    return {
        "schema": "sips.fleet.write.v1",
        "available": True,
        "campaign_id": str(campaign.get("campaign_id") or campaign_id)[:80],
        "child_count": int(campaign.get("child_count") or 0),
        "revision": int(campaign.get("revision") or 0),
        "generated_at": _now(),
        "claim_boundary": "Child attached as metadata; the conversation lives in the host, not here.",
    }


@router.post("/fleet/child-status")
def post_fleet_child_status(body: dict[str, Any]) -> dict[str, Any]:
    """Set a child's status within a campaign spine (bounded, validated write)."""
    data = body if isinstance(body, dict) else {}
    campaign_id = str(data.get("campaign_id") or "").strip()
    child_id = str(data.get("child_id") or "").strip()
    status = str(data.get("status") or "").strip()
    if not campaign_id or len(campaign_id) > 80 or any(ch in campaign_id for ch in "/\\"):
        raise HTTPException(status_code=422, detail="campaign_id_invalid")
    if not child_id or len(child_id) > 80 or any(ch in child_id for ch in "/\\"):
        raise HTTPException(status_code=422, detail="child_id_invalid")
    if status not in {"planned", "active", "waiting", "blocked", "completed", "failed", "abandoned", "canceled", "archived"}:
        raise HTTPException(status_code=422, detail="status_invalid")
    reason = str(data.get("reason") or "").strip()[:300]
    try:
        from harness_homebase_mcp import call_tool

        request: dict[str, Any] = {"campaign_id": campaign_id, "child_id": child_id, "status": status}
        if reason:
            request["reason"] = reason
        result = call_tool(
            "homebase_campaign_fleet_write",
            {"root": str(PLUGIN_ROOT), "operation": "set_child_status", "request_json": json.dumps(request)},
        )
        structured = result.get("structuredContent") or {}
    except Exception as exc:
        reason_out = "campaign_not_found" if type(exc).__name__ == "CampaignNotFound" else f"fleet write failed: {type(exc).__name__}"
        return {
            "schema": "sips.fleet.write.v1",
            "available": False,
            "reason": reason_out,
            "campaign_id": campaign_id,
            "child_id": child_id,
            "generated_at": _now(),
            "claim_boundary": "The fleet write failed before producing state.",
        }
    raw_campaign = structured.get("data")
    campaign = raw_campaign if isinstance(raw_campaign, dict) else {}
    return {
        "schema": "sips.fleet.write.v1",
        "available": True,
        "campaign_id": campaign_id,
        "child_id": child_id,
        "status": status,
        "revision": int(campaign.get("revision") or 0),
        "generated_at": _now(),
        "claim_boundary": "Child status is campaign metadata; the conversation lives in the host.",
    }


@router.get("/memory")
def get_memory(tier: str = "", status: str = "", query: str = "", limit: int = 20) -> dict[str, Any]:
    """Bounded browse view of the Memory Fabric store, filterable by tier/status.

    Newest first; strings truncated; never returns record bodies over the
    summary length. This is a browser, not a ranked recall — use the panel's
    Recall card for relevance-ranked search.
    """
    if load_records is None or store_path is None:
        return {
            "schema": "sips.memory.browse.v1",
            "available": False,
            "reason": "memory_fabric_unavailable",
            "records": [],
            "generated_at": _now(),
            "claim_boundary": "Memory Fabric is not importable in this process.",
        }
    tier = tier.strip().lower()[:20]
    status = status.strip().lower()[:20]
    query = query.strip().lower()[:200]
    if tier and tier not in {"work", "knowledge", "learning"}:
        raise HTTPException(status_code=422, detail="tier_invalid")
    if status and status not in {"active", "candidate", "superseded", "archived"}:
        raise HTTPException(status_code=422, detail="status_invalid")
    limit = max(1, min(int(limit or 20), 50))
    try:
        records = load_records()
    except Exception as exc:
        return {
            "schema": "sips.memory.browse.v1",
            "available": False,
            "reason": f"store read failed: {type(exc).__name__}",
            "records": [],
            "generated_at": _now(),
            "claim_boundary": "The memory store could not be read.",
        }
    filtered = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        if tier and rec.get("tier") != tier:
            continue
        if status and rec.get("status") != status:
            continue
        if query:
            haystack = f"{rec.get('title') or ''} {rec.get('body') or ''}".lower()
            if query not in haystack:
                continue
        filtered.append(rec)
    filtered.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    out = [
        {
            "id": str(r.get("id") or "")[:80],
            "title": str(r.get("title") or "")[:200],
            "tier": str(r.get("tier") or "")[:20],
            "status": str(r.get("status") or "")[:20],
            "confidence": str(r.get("confidence") or "")[:20],
            "tags": [str(t)[:40] for t in (r.get("tags") or [])[:6] if isinstance(t, (str, int))],
            "scope": str(r.get("scope") or "")[:160],
            "created_at": str(r.get("created_at") or "")[:40],
            "preview": str(r.get("body") or "")[:260],
        }
        for r in filtered[:limit]
    ]
    return {
        "schema": "sips.memory.browse.v1",
        "available": True,
        "total_matched": len(filtered),
        "total_records": len(records),
        "records": out,
        "generated_at": _now(),
        "claim_boundary": "Bounded browse projection; full bodies stay in the store.",
    }


@router.post("/fleet/campaign-status")
def post_fleet_campaign_status(body: dict[str, Any]) -> dict[str, Any]:
    """Set a campaign spine's status (transition-validated write)."""
    data = body if isinstance(body, dict) else {}
    campaign_id = str(data.get("campaign_id") or "").strip()
    status = str(data.get("status") or "").strip()
    if not campaign_id or len(campaign_id) > 80 or any(ch in campaign_id for ch in "/\\"):
        raise HTTPException(status_code=422, detail="campaign_id_invalid")
    if status not in {"active", "completed", "archived", "abandoned"}:
        raise HTTPException(status_code=422, detail="status_invalid")
    reason = str(data.get("reason") or "").strip()[:300]
    try:
        from harness_homebase_mcp import call_tool

        request: dict[str, Any] = {"campaign_id": campaign_id, "status": status}
        if reason:
            request["status_reason"] = reason
        result = call_tool(
            "homebase_campaign_fleet_write",
            {"root": str(PLUGIN_ROOT), "operation": "set_campaign_status", "request_json": json.dumps(request)},
        )
        structured = result.get("structuredContent") or {}
    except Exception as exc:
        name = type(exc).__name__
        if name == "CampaignNotFound":
            reason_out = "campaign_not_found"
        elif "open children" in str(exc):
            reason_out = "campaign_has_open_children"
        elif "cannot transition" in str(exc):
            reason_out = f"transition_invalid: {str(exc)[:160]}"
        else:
            reason_out = f"fleet write failed: {name}"
        return {
            "schema": "sips.fleet.write.v1",
            "available": False,
            "reason": reason_out,
            "campaign_id": campaign_id,
            "generated_at": _now(),
            "claim_boundary": "The fleet write failed before producing state.",
        }
    raw_campaign = structured.get("data")
    campaign = raw_campaign if isinstance(raw_campaign, dict) else {}
    return {
        "schema": "sips.fleet.write.v1",
        "available": True,
        "campaign_id": campaign_id,
        "status": str(campaign.get("status") or status)[:40],
        "revision": int(campaign.get("revision") or 0),
        "generated_at": _now(),
        "claim_boundary": "Campaign status is spine metadata; transitions are validated server-side.",
    }


@router.post("/runs/{run_id}/annotate")
def post_run_annotate(run_id: str, body: dict[str, Any]) -> dict[str, Any]:
    """Attach a human label to a runtime run (stored in run metadata)."""
    safe_id = run_id.strip()[:80]
    data = body if isinstance(body, dict) else {}
    label = str(data.get("label") or "").strip()[:200]
    if not label:
        raise HTTPException(status_code=422, detail="label_required")
    try:
        from sips_runtime.api import RuntimeAPI
        from sips_runtime.controller import runtime_root

        runs_root = runtime_root()
        events_path = runs_root / safe_id / "events.jsonl"
        if not (runs_root.is_dir() and events_path.exists()):
            return {
                "schema": "sips.run.annotate.v1",
                "available": False,
                "reason": "run_not_found",
                "run_id": safe_id,
                "generated_at": _now(),
                "claim_boundary": "No runtime run matched that id.",
            }
        with events_path.open(encoding="utf-8") as handle:
            revision = 0
            for line in handle:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                rev = event.get("revision")
                if isinstance(rev, int) and rev > revision:
                    revision = rev
        api = RuntimeAPI()
        # An annotation rides the lease-free metadata channel: cancel-with-reason
        # mutates the run, so instead we append via the promote path only if
        # terminal — otherwise use create-metadata-compatible advance? The runtime
        # has no metadata-write op; persist the label as a cancel-guarded no-op is
        # wrong. Correct channel: the event store accepts idempotent appends only
        # through write ops, so we store annotations out-of-band in the run dir.
        annotation_path = runs_root / safe_id / "annotations.json"
        annotations: dict[str, Any] = {}
        if annotation_path.exists():
            try:
                loaded = json.loads(annotation_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    annotations = loaded
            except (OSError, ValueError):
                annotations = {}
        entry = {
            "label": label,
            "at": _now(),
            "run_revision_seen": revision,
        }
        annotations.setdefault("labels", []).append(entry)
        annotation_path.write_text(json.dumps(annotations, indent=1), encoding="utf-8")
        return {
            "schema": "sips.run.annotate.v1",
            "available": True,
            "run_id": safe_id,
            "label": label,
            "labels": annotations["labels"][-5:],
            "generated_at": _now(),
            "claim_boundary": "Annotations live beside the run's event store; they are panel-side labels, not runtime events.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        return {
            "schema": "sips.run.annotate.v1",
            "available": False,
            "reason": f"annotation failed: {type(exc).__name__}",
            "run_id": safe_id,
            "generated_at": _now(),
            "claim_boundary": "The annotation write failed before producing state.",
        }


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
