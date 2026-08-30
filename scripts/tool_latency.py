"""Tool-latency lens: per-tool duration statistics from the hook stream.

Backs the panel's ToolLatencyCard via /tool-latency and the chat's
/sips-latency command. Sources post_tool_call events that carry
``duration_ms`` (recorded by hermes_adapter since 0.19.2); older events
without durations are skipped, so the lens improves as the stream grows.

Bounded summary only: tool names, call counts, and millisecond aggregates.
No tool arguments, outputs, or timestamps beyond the window boundary.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_MAX_TOOLS = 10
_MAX_WINDOW_EVENTS = 20000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percentile(sorted_vals: list[int], pct: float) -> int:
    """Lower-interpolation percentile on a pre-sorted list (never exceeds max)."""
    if not sorted_vals:
        return 0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = pct * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return int(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac)


def _read_events(path: Path, cutoff: float) -> list[dict[str, Any]]:
    """Read the stream tail-first, bounded, keeping only timed post_tool_calls."""
    events: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return events
    for line in reversed(lines[-_MAX_WINDOW_EVENTS * 4 :]):
        try:
            event = json_loads(line)
        except Exception:
            continue
        if event.get("event") != "post_tool_call":
            continue
        duration = event.get("duration_ms")
        if not isinstance(duration, (int, float)) or duration <= 0:
            continue
        events.append(event)
        if len(events) >= _MAX_WINDOW_EVENTS:
            break
    return events


def json_loads(line: str) -> dict[str, Any]:
    import json

    return json.loads(line)


def tool_latency_payload(window_hours: int = 24) -> dict[str, Any]:
    window_hours = max(1, min(int(window_hours or 24), 168))
    cutoff = time.time() - window_hours * 3600
    claim_boundary = (
        "Tool latency lens is a bounded aggregate of hook-stream durations: "
        "tool names, call counts, and millisecond percentiles only. No tool "
        "arguments, outputs, or per-call timestamps are included."
    )
    try:
        from sips_paths import hook_events_path

        path = hook_events_path()
    except Exception:
        path = Path.home() / ".hermes" / "sips" / "hook_events.jsonl"

    if not path.exists():
        return {
            "schema": "sips.tool-latency.v1",
            "available": False,
            "reason": f"hook stream not found at {path}",
            "window_hours": window_hours,
            "tools": [],
            "generated_at": _now(),
            "claim_boundary": claim_boundary,
        }

    events = _read_events(path, cutoff)
    by_tool: dict[str, list[int]] = {}
    for event in events:
        name = str(event.get("tool_name") or "unknown")[:40]
        by_tool.setdefault(name, []).append(int(event["duration_ms"]))

    tools_out = []
    for name, durations in by_tool.items():
        ordered = sorted(durations)
        total = sum(ordered)
        n = len(ordered)
        tools_out.append(
            {
                "tool": name,
                "calls": n,
                "timed_calls": n,
                "median_ms": _percentile(ordered, 0.5),
                "p90_ms": _percentile(ordered, 0.9),
                "max_ms": ordered[-1],
                "total_ms": total,
                "total_s": round(total / 1000.0, 1),
            }
        )
    tools_out.sort(key=lambda row: -row["total_ms"])

    timed_calls = sum(row["timed_calls"] for row in tools_out)
    return {
        "schema": "sips.tool-latency.v1",
        "available": True,
        "window_hours": window_hours,
        "timed_calls": timed_calls,
        "tools": tools_out[:_MAX_TOOLS],
        "note": "durations appear in the stream from hermes_adapter 0.19.2 onward; older events are skipped",
        "generated_at": _now(),
        "claim_boundary": claim_boundary,
    }


_STATIC_SLOW_MS = 5_000
_STATIC_STALLED_MS = 120_000


def _verdict(calls: int, p95_ms: int, denials: int) -> str:
    """Classify one tool's window: denied > stalled > slow > ok.

    Static duration lines only (5s slow, 120s stalled); ``calls`` is kept
    in the signature for future self-relative tuning.
    """
    if denials > 0:
        return "denied"
    if p95_ms >= _STATIC_STALLED_MS:
        return "stalled"
    if p95_ms >= _STATIC_SLOW_MS:
        return "slow"
    return "ok"


def verdicts_payload(window_hours: int = 24) -> dict[str, Any]:
    """Per-tool verdict lens: ok | slow | stalled | denied for the panel.

    Reuses the bounded post_tool_call window from tool_latency_payload and
    adds a verdict classification per tool. Verdicts are heuristic: a tool
    with >= 5 timed calls is judged against its own p95 vs the static slow
    line; denial count always wins when nonzero.
    """
    window_hours = max(1, min(int(window_hours or 24), 168))
    claim_boundary = (
        "Verdicts are derived from hook events in the window only: heuristic "
        "classification (ok/slow/stalled/denied) from duration percentiles "
        "and denial counts. No tool arguments or outputs are included."
    )
    try:
        from sips_paths import hook_events_path

        path = hook_events_path()
    except Exception:
        path = Path.home() / ".hermes" / "sips" / "hook_events.jsonl"

    if not path.exists():
        return {
            "schema": "sips.verdicts.v1",
            "available": False,
            "reason": f"hook stream not found at {path}",
            "window_hours": window_hours,
            "verdicts": [],
            "generated_at": _now(),
            "claim_boundary": claim_boundary,
        }

    cutoff = time.time() - window_hours * 3600
    events = _read_events(path, cutoff)
    if not events:
        return {
            "schema": "sips.verdicts.v1",
            "available": False,
            "reason": "no timed post_tool_call events in the window",
            "window_hours": window_hours,
            "verdicts": [],
            "generated_at": _now(),
            "claim_boundary": claim_boundary,
        }

    by_tool: dict[str, list[int]] = {}
    denials_by_tool: dict[str, int] = {}
    for event in events:
        name = str(event.get("tool_name") or "unknown")[:40]
        by_tool.setdefault(name, []).append(int(event["duration_ms"]))
        if str(event.get("status") or "") in ("denied", "blocked"):
            denials_by_tool[name] = denials_by_tool.get(name, 0) + 1

    verdicts = []
    for name, durations in by_tool.items():
        ordered = sorted(durations)
        p95_ms = _percentile(ordered, 0.95)
        denials = denials_by_tool.get(name, 0)
        verdicts.append(
            {
                "tool": name,
                "verdict": _verdict(len(ordered), p95_ms, denials),
                "calls": len(ordered),
                "denials": denials,
                "p95_ms": p95_ms,
                "median_ms": _percentile(ordered, 0.5),
            }
        )
    # Worst first: denied, then stalled, then slow, then ok; ties by p95.
    rank = {"denied": 0, "stalled": 1, "slow": 2, "ok": 3}
    verdicts.sort(key=lambda row: (rank.get(row["verdict"], 4), -row["p95_ms"]))
    return {
        "schema": "sips.verdicts.v1",
        "available": True,
        "window_hours": window_hours,
        "verdicts": verdicts[:_MAX_TOOLS],
        "generated_at": _now(),
        "claim_boundary": claim_boundary,
    }
