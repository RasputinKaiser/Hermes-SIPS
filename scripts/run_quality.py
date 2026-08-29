"""Run-quality drill-down: bounded per-run quality lens from graph receipts.

Backs the panel's RunQualityCard via /runs/{run_id}/quality and the chat's
/sips-quality command. Read-only over
``$SIPS_HOME/runtime/v1/runs/<run_id>/receipts/graph-receipt.json``.

What surfaces (bounded, no payload bodies):
- per-gate status + evidence counts (the "how do we know?" numbers)
- impact / risk_tags / reviewer_tags / failed_gates
- session task summary from the receipt's structured.answer_units and the
  per-task answer strip already carried by /runs/{run_id}
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GATE_ORDER = ("integrity", "correctness", "regression", "resource", "benefit")
_MAX_EVIDENCE_ITEMS = 8


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _receipt_path(run_id: str) -> Path | None:
    try:
        from sips_runtime.controller import runtime_root

        # validate_safe_identifier mirrors the API's run_id guard.
        from sips_runtime.contracts import validate_safe_identifier

        validate_safe_identifier(run_id, label="run_id")
        path = runtime_root() / run_id.strip()[:80] / "receipts" / "graph-receipt.json"
        return path if path.exists() else None
    except Exception:
        return None


def _normalize_gate(entry: dict[str, Any]) -> dict[str, Any]:
    evidence = [
        {
            "path": str(e.get("evidence_path") or "")[-120:],
            "count": int(e.get("count") or 0),
            "status": str(e.get("status") or "")[:20],
        }
        for e in (entry.get("evidence") or [])
        if isinstance(e, dict)
    ][:_MAX_EVIDENCE_ITEMS]
    reasons = [str(r)[:160] for r in (entry.get("reasons") or [])][:6]
    ok = entry.get("ok")
    if ok is True:
        status = "ok"
    elif ok is False:
        status = "failed"
    else:
        status = "unknown"
    return {
        "name": str(entry.get("name") or "")[:30],
        "status": status,
        "reasons": reasons,
        "evidence_total": sum(item["count"] for item in evidence),
        "evidence": evidence,
    }


def run_quality_payload(run_id: str) -> dict[str, Any]:
    safe_id = str(run_id or "").strip()[:80]
    path = _receipt_path(safe_id)
    claim_boundary = (
        "Run quality lens is a bounded read-only view of one graph receipt: "
        "gate statuses, evidence counts, and tag summaries. No receipt bodies, "
        "task answers, or event payloads are included."
    )
    if path is None:
        return {
            "schema": "sips.run-quality.v1",
            "available": False,
            "run_id": safe_id,
            "reason": "no graph receipt for this run (still running, legacy, or unknown id)",
            "gates": [],
            "generated_at": _now(),
            "claim_boundary": claim_boundary,
        }
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "schema": "sips.run-quality.v1",
            "available": False,
            "run_id": safe_id,
            "reason": f"graph receipt unreadable: {type(exc).__name__}",
            "gates": [],
            "generated_at": _now(),
            "claim_boundary": claim_boundary,
        }

    structured = receipt.get("structured") if isinstance(receipt.get("structured"), dict) else {}
    quality = structured.get("quality") if isinstance(structured.get("quality"), dict) else {}

    # Merge per-task gate lists (real session shape): a gate is ok only if
    # every task's instance passed; evidence counts accumulate.
    merged: dict[str, dict[str, Any]] = {}
    for task_entry in quality.values():
        if not isinstance(task_entry, dict):
            continue
        for entry in task_entry.get("gates") or []:
            if not isinstance(entry, dict) or not entry.get("name"):
                continue
            name = str(entry["name"])[:30]
            norm = _normalize_gate(entry)
            bucket = merged.setdefault(
                name,
                {"name": name, "status": "ok", "reasons": [], "evidence_total": 0, "evidence": []},
            )
            if norm["status"] == "failed" or bucket["status"] == "failed":
                bucket["status"] = "failed"
            elif norm["status"] != "ok" and bucket["status"] == "ok":
                bucket["status"] = norm["status"]
            bucket["reasons"] = (bucket["reasons"] + norm["reasons"])[:6]
            bucket["evidence_total"] += norm["evidence_total"]
            bucket["evidence"] = (bucket["evidence"] + norm["evidence"])[:_MAX_EVIDENCE_ITEMS]

    gates_out = [merged[name] for name in GATE_ORDER if name in merged]
    gates_out += [merged[k] for k in merged if k not in GATE_ORDER]

    # Session-level quality flags (first task entry that carries them).
    session_q: dict[str, Any] = {}
    for task_entry in quality.values():
        if isinstance(task_entry, dict) and "impact" in task_entry:
            session_q = task_entry
            break
    failed_gates = [str(g)[:30] for g in (session_q.get("failed_gates") or [])][:8]
    if not failed_gates:
        # Derive from the merged gate map when the receipt has no explicit list.
        failed_gates = [g["name"] for g in gates_out if g["status"] == "failed"][:8]

    budget_usage = structured.get("budget_usage") if isinstance(structured.get("budget_usage"), dict) else None

    return {
        "schema": "sips.run-quality.v1",
        "available": True,
        "run_id": safe_id,
        "status": str(receipt.get("status") or "unknown")[:30],
        "gates": gates_out,
        "impact": str(session_q.get("impact") or "unknown")[:20],
        "risk_tags": [str(t)[:30] for t in (session_q.get("risk_tags") or [])][:8],
        "reviewer_tags": [str(t)[:30] for t in (session_q.get("reviewer_tags") or [])][:8],
        "failed_gates": failed_gates,
        "evidence_required": bool(session_q.get("evidence_required")),
        "budget_usage": {
            "charged_tokens": int(budget_usage.get("charged_tokens") or 0),
            "released_token_limit": int(budget_usage.get("released_token_limit") or 0),
        }
        if budget_usage
        else None,
        "generated_at": _now(),
        "claim_boundary": claim_boundary,
    }
