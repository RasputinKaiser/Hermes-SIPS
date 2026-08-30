"""Fleet/run timeline lens: recent runs + fleet campaigns on one time axis.

Backs the panel's FleetTimelineCard via /timeline and the chat's
/sips-timeline command. Merges two read-only sources:

- runtime runs (``$SIPS_HOME/runtime/v1/runs``): one row per session run,
  placed at its last-activity timestamp with status + event count
- fleet campaigns (CampaignFleet.read): one row per campaign, placed at its
  own timestamp, with child counts

Bounded to the most recent N entries; ids and statuses only — no event
payloads, no campaign bodies.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_MAX_ENTRIES = 20


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fleet_campaigns() -> list[dict[str, Any]]:
    """Read fleet campaigns via the same MCP route the /fleet endpoint uses."""
    try:
        from harness_homebase_mcp import call_tool

        result = call_tool(
            "homebase_campaign_fleet_read",
            {"root": str(Path(__file__).resolve().parents[1]), "operation": "list", "limit": 12},
        )
        raw = result.get("data") if isinstance(result, dict) else None
        if raw is None:
            raw = result.get("structuredContent") if isinstance(result, dict) else None
        if isinstance(raw, dict):
            raw = raw.get("campaigns")
        if not isinstance(raw, list):
            return []
        return [c for c in raw if isinstance(c, dict)]
    except Exception:
        return []


def timeline_payload(limit: int = _MAX_ENTRIES) -> dict[str, Any]:
    limit = max(4, min(int(limit or _MAX_ENTRIES), 40))
    entries: list[dict[str, Any]] = []

    # Runtime runs: last-activity timestamp per run.
    try:
        from sips_runtime.controller import runtime_root

        runs_root = runtime_root()
        run_dirs = (
            sorted(
                (d for d in runs_root.iterdir() if (d / "events.jsonl").exists()),
                key=lambda d: d.stat().st_mtime,
                reverse=True,
            )
            if runs_root.is_dir()
            else []
        )
    except Exception:
        run_dirs = []
    for run_dir in run_dirs[: limit * 2]:
        try:
            mtime = run_dir.stat().st_mtime
        except OSError:
            continue
        events = 0
        status = "unknown"
        try:
            with (run_dir / "events.jsonl").open(encoding="utf-8") as handle:
                for line in handle:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    events += 1
                    event_type = str(event.get("event_type") or "")
                    if event_type in ("run.submitted", "run.created"):
                        status = "running" if event_type == "run.submitted" else status
                    elif event_type == "task.advanced":
                        result = event.get("payload") or {}
                        result_status = str((result.get("result") or {}).get("status") or "")
                        if result_status.lower() in {"complete", "completed", "done", "succeeded"}:
                            status = "succeeded"
                        elif result_status.lower() in {"failed", "blocked", "canceled", "cancelled"}:
                            status = "failed"
        except (OSError, UnicodeDecodeError):
            continue
        entries.append(
            {
                "kind": "run",
                "id": run_dir.name[:80],
                "status": status[:24],
                "events": events,
                "ts": mtime,
            }
        )

    # Fleet campaigns: one entry per campaign.
    for campaign in _fleet_campaigns():
        campaign_id = str(campaign.get("campaign_id") or "")[:60]
        if not campaign_id:
            continue
        children = campaign.get("children")
        child_count = len(children) if isinstance(children, list) else 0
        entries.append(
            {
                "kind": "campaign",
                "id": campaign_id,
                "status": str(campaign.get("status") or "unknown")[:24],
                "children": child_count,
                "ts": _parse_ts(campaign.get("updated_at") or campaign.get("created_at")),
            }
        )

    entries = [e for e in entries if e.get("ts") is not None]
    entries.sort(key=lambda e: e["ts"], reverse=True)
    shown = entries[:limit]

    return {
        "schema": "sips.timeline.v1",
        "available": True,
        "entries": shown,
        "total_tracked": len(entries),
        "window_hours": _window_hours(shown),
        "generated_at": _now(),
        "claim_boundary": (
            "Timeline is a bounded read-only merge of runtime run mtimes and fleet "
            "campaign metadata. No event payloads or campaign bodies are included."
        ),
    }


def _parse_ts(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _window_hours(entries: list[dict[str, Any]]) -> int:
    if not entries:
        return 0
    newest = max(e["ts"] for e in entries)
    oldest = min(e["ts"] for e in entries)
    return max(1, int((newest - oldest) / 3600))
