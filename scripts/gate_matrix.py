"""Gate-evidence matrix: recent runtime runs × the 5 verification gates.

Backs the Verification tab's GateMatrixCard via /gate-matrix. Read-only over
``$SIPS_HOME/runtime/v1/runs/<run_id>/receipts/graph-receipt.json``; only
bounded gate names/statuses and run ids leave the host — no event payloads,
task answers, or receipt bodies.

Cell statuses come from each run's GraphReceipt ``claims``/``evidence`` gate
map (quality.py GATE_ORDER). Runs without a graph receipt (still running,
legacy) appear as rows with ``receipt: false`` and ``null`` gate cells so the
matrix shows them as "not yet gated" rather than omitting them.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from sips_paths import harness_home  # noqa: F401  (consistency with siblings)

router = APIRouter()

GATE_ORDER = ("integrity", "correctness", "regression", "resource", "benefit")
_MAX_RUNS = 12
_GATE_OK = {"ok", "pass", "passed", "satisfied"}


def _gate_status(value: Any) -> str | None:
    """Normalize a raw gate value to ok|failed|partial|skipped|unknown."""
    text = str(value or "").strip().lower()
    if not text:
        return None
    if text in _GATE_OK:
        return "ok"
    if text in {"failed", "fail", "error", "missing", "blocked"}:
        return "failed"
    if text in {"partial", "degraded", "warn", "warning"}:
        return "partial"
    if text in {"skipped", "not_applicable", "na"}:
        return "skipped"
    return "unknown"


def _receipt_gates(receipt_path: Path) -> dict[str, str] | None:
    """Extract {gate: normalized_status} from one graph-receipt.json.

    Handles three receipt shapes seen in the wild:
    1. ``gates: {name: status-or-dict}`` (canonical reducer output)
    2. ``quality.gates: {name: ...}`` (legacy flat map)
    3. ``structured.quality.<task>.gates: [{name, ok, reasons}, ...]``
       (real session receipts — one entry per gate with a boolean ``ok``)
    """
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    gates_raw: Any = receipt.get("gates")
    if not isinstance(gates_raw, dict) or not gates_raw:
        gates_raw = None

    if gates_raw is None:
        structured = receipt.get("structured")
        quality = structured.get("quality") if isinstance(structured, dict) else None
        if isinstance(quality, dict) and quality:
            # Shape 3: per-task gate lists. Merge: a gate is ok only if every
            # task's instance of it is ok; any failure fails the cell.
            merged: dict[str, list[Any]] = {}
            for task_entry in quality.values():
                if not isinstance(task_entry, dict):
                    continue
                for gate in task_entry.get("gates") or []:
                    if isinstance(gate, dict) and gate.get("name"):
                        merged.setdefault(str(gate["name"]), []).append(gate.get("ok"))
            if merged:
                out: dict[str, str] = {}
                for name in GATE_ORDER:
                    oks = merged.get(name)
                    if oks is None:
                        continue
                    if all(o is True for o in oks):
                        out[name] = "ok"
                    elif any(o is False for o in oks):
                        out[name] = "failed"
                    else:
                        out[name] = "unknown"
                return out or None
        # Shape 2: legacy flat map under quality.gates.
        if isinstance(quality, dict):
            gates_raw = quality.get("gates")
    if not isinstance(gates_raw, dict):
        return None
    out = {}
    for name in GATE_ORDER:
        raw = gates_raw.get(name)
        if isinstance(raw, dict):
            raw = raw.get("status")
        normalized = _gate_status(raw)
        if normalized is not None:
            out[name] = normalized
    return out


def gate_matrix_payload(limit: int = _MAX_RUNS) -> dict[str, Any]:
    limit = max(1, min(int(limit or _MAX_RUNS), _MAX_RUNS))
    try:
        from sips_runtime.controller import runtime_root

        runs_root = runtime_root()
        run_dirs = (
            sorted(
                (d for d in runs_root.iterdir() if d.is_dir()),
                key=lambda d: d.stat().st_mtime,
                reverse=True,
            )
            if runs_root.is_dir()
            else []
        )
    except Exception as exc:
        return {
            "schema": "sips.gate-matrix.v1",
            "available": False,
            "reason": f"runtime unavailable: {type(exc).__name__}",
            "runs": [],
            "gates": list(GATE_ORDER),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "claim_boundary": "The runtime read failed before producing the gate matrix.",
        }

    rows: list[dict[str, Any]] = []
    for run_dir in run_dirs[: limit * 2]:
        if len(rows) >= limit:
            break
        receipt_path = run_dir / "receipts" / "graph-receipt.json"
        gates = _receipt_gates(receipt_path) if receipt_path.exists() else None
        try:
            updated_at = run_dir.stat().st_mtime
        except OSError:
            continue
        # Include runs with a receipt, plus non-receipted runs younger than 24h
        # so active work shows as "not yet gated" instead of vanishing.
        if gates is None and time.time() - updated_at > 86400:
            continue
        row: dict[str, Any] = {
            "run_id": run_dir.name[:80],
            "receipt": gates is not None,
            "gates": {name: (gates or {}).get(name) for name in GATE_ORDER},
            "ok_count": sum(1 for v in (gates or {}).values() if v == "ok"),
            "failed_count": sum(1 for v in (gates or {}).values() if v == "failed"),
            "updated_at": updated_at,
        }
        rows.append(row)

    return {
        "schema": "sips.gate-matrix.v1",
        "available": True,
        "runs": rows,
        "gates": list(GATE_ORDER),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": (
            "Gate matrix is a bounded read-only projection of graph receipts: "
            "run ids and gate statuses only. Receipt evidence bodies stay on the host."
        ),
    }
