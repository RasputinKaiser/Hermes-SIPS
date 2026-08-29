"""Usage lens: read-only LLM token analytics from the Hermes session store.

Backs the dashboard's TokenUsageCard via /token-usage. Everything here is a
bounded summary — session ids, counts, and aggregate token numbers only. No
message content, tool arguments, prompts, or credentials ever leave the host.

The store lives at ~/.hermes/state.db (override: SIPS_HERMES_STATE_DB or
HERMES_STATE_DB). It is opened with SQLite's read-only URI mode so the lens
can never mutate live Hermes state, and every query is wrapped so a
missing/locked/corrupt store fails closed to available=False.
"""

from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_WINDOW_DAYS = 7
_REPLAY_CACHE_TTL = 60.0
_MAX_TOP_SESSIONS = 6
_MAX_MODEL_ROWS = 6

_CLAIM_BOUNDARY = (
    "Token usage lens is a read-only aggregate over the Hermes session store: "
    "counts and token totals only. No message content, tool arguments, prompts, "
    "or credentials are included."
)

_replay_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_db_path() -> Path:
    override = os.environ.get("SIPS_HERMES_STATE_DB") or os.environ.get("HERMES_STATE_DB")
    if override:
        return Path(override)
    return Path.home() / ".hermes" / "state.db"


def _connect_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{path}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=2.0)


def _window_bounds(days: int) -> tuple[float, float]:
    end = time.time()
    return end - days * 86400.0, end


def _totals(conn: sqlite3.Connection, start: float, end: float) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT COUNT(DISTINCT s.id), COALESCE(SUM(m.api_call_count), 0),
               COALESCE(SUM(m.input_tokens), 0), COALESCE(SUM(m.output_tokens), 0),
               COALESCE(SUM(m.cache_read_tokens), 0), COALESCE(SUM(m.reasoning_tokens), 0),
               COALESCE(SUM(m.estimated_cost_usd), 0)
        FROM sessions s JOIN session_model_usage m ON m.session_id = s.id
        WHERE s.started_at >= ? AND s.started_at < ?
        """,
        (start, end),
    ).fetchone()
    sessions, api_calls, fresh_in, out_tok, cache_read, reasoning, cost = row
    total_in = (fresh_in or 0) + (cache_read or 0)
    hit = round(100.0 * (cache_read or 0) / total_in, 1) if total_in else None
    out_in_ratio = round((fresh_in or 0) / (out_tok or 1), 1) if out_tok else None
    return {
        "sessions": sessions,
        "api_calls": api_calls,
        "fresh_input_tokens": fresh_in,
        "output_tokens": out_tok,
        "cache_read_tokens": cache_read,
        "reasoning_tokens": reasoning,
        "total_input_tokens": total_in,
        "cache_hit_pct": hit,
        "output_per_1k_fresh_input": round(1000.0 * (out_tok or 0) / fresh_in, 1) if fresh_in else None,
        "fresh_to_output_ratio": f"{out_in_ratio}:1" if out_in_ratio else None,
        "estimated_cost_usd": round(cost or 0, 4),
    }


def _daily(conn: sqlite3.Connection, start: float, end: float) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT date(s.started_at, 'unixepoch', 'localtime') AS day,
               COUNT(DISTINCT s.id), SUM(m.api_call_count),
               SUM(m.input_tokens), SUM(m.output_tokens),
               SUM(m.cache_read_tokens), SUM(m.reasoning_tokens),
               ROUND(SUM(m.estimated_cost_usd), 4)
        FROM sessions s JOIN session_model_usage m ON m.session_id = s.id
        WHERE s.started_at >= ? AND s.started_at < ?
        GROUP BY day ORDER BY day
        """,
        (start, end),
    ).fetchall()
    daily = []
    for day, sess, api, fresh, out, cr, rt, cost in rows:
        total_in = (fresh or 0) + (cr or 0)
        daily.append(
            {
                "day": day,
                "sessions": sess,
                "api_calls": api or 0,
                "fresh_input_tokens": fresh or 0,
                "output_tokens": out or 0,
                "cache_read_tokens": cr or 0,
                "reasoning_tokens": rt or 0,
                "cache_hit_pct": round(100.0 * (cr or 0) / total_in, 1) if total_in else None,
                "estimated_cost_usd": cost or 0.0,
            }
        )
    return daily


def _split(conn: sqlite3.Connection, start: float, end: float) -> dict[str, Any]:
    rows = conn.execute(
        """
        SELECT CASE WHEN s.parent_session_id IS NOT NULL THEN 'subagent' ELSE 'direct' END AS kind,
               COUNT(DISTINCT s.id), SUM(m.api_call_count),
               SUM(m.input_tokens), SUM(m.output_tokens), SUM(m.cache_read_tokens)
        FROM sessions s JOIN session_model_usage m ON m.session_id = s.id
        WHERE s.started_at >= ? AND s.started_at < ?
        GROUP BY kind
        """,
        (start, end),
    ).fetchall()
    out: dict[str, Any] = {}
    for kind, sess, api, fresh, outp, cr in rows:
        out[kind] = {
            "sessions": sess,
            "api_calls": api or 0,
            "fresh_input_tokens": fresh or 0,
            "output_tokens": outp or 0,
            "avg_fresh_input_per_call": round((fresh or 0) / api, 0) if api else None,
        }
    return out


def _models(conn: sqlite3.Connection, start: float, end: float) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT m.model, COUNT(DISTINCT s.id), SUM(m.api_call_count),
               SUM(m.input_tokens), SUM(m.output_tokens), SUM(m.cache_read_tokens),
               ROUND(SUM(m.estimated_cost_usd), 4)
        FROM sessions s JOIN session_model_usage m ON m.session_id = s.id
        WHERE s.started_at >= ? AND s.started_at < ?
        GROUP BY m.model ORDER BY SUM(m.input_tokens) DESC LIMIT ?
        """,
        (start, end, _MAX_MODEL_ROWS),
    ).fetchall()
    return [
        {
            "model": model or "unknown",
            "sessions": sess,
            "api_calls": api or 0,
            "fresh_input_tokens": fresh or 0,
            "output_tokens": out or 0,
            "cache_read_tokens": cr or 0,
            "estimated_cost_usd": cost or 0.0,
        }
        for model, sess, api, fresh, out, cr, cost in rows
    ]


def _later_assistant_count_cte() -> str:
    return (
        "(SELECT COUNT(*) FROM messages a "
        "WHERE a.session_id = m.session_id AND a.role = 'assistant' "
        "AND a.timestamp >= m.timestamp)"
    )


def _replay_mass(conn: sqlite3.Connection, start: float, end: float) -> dict[str, Any]:
    """Estimate replayed context mass for tool results and assistant emissions.

    Each message is re-sent on every later API call of its session, so its
    replay weight is (size/4 tokens) * (number of later assistant messages).
    Results are estimates derived from message sizes, not provider-reported
    token counts.
    """
    later = _later_assistant_count_cte()

    tool_by_tool = conn.execute(
        f"""
        SELECT COALESCE(m.tool_name, 'unknown'), SUM(LENGTH(COALESCE(m.content, '')) * {later})
        FROM messages m
        WHERE m.role = 'tool' AND m.timestamp >= ? AND m.timestamp < ?
        GROUP BY 1 ORDER BY 2 DESC
        """,
        (start, end),
    ).fetchall()

    assistant_row = conn.execute(
        f"""
        SELECT COALESCE(SUM(
          (LENGTH(COALESCE(m.content, '')) + LENGTH(COALESCE(m.tool_calls, ''))
           + LENGTH(COALESCE(m.reasoning, '')) + LENGTH(COALESCE(m.reasoning_content, '')))
          * {later}), 0)
        FROM messages m
        WHERE m.role = 'assistant' AND m.timestamp >= ? AND m.timestamp < ?
        """,
        (start, end),
    ).fetchone()

    session_mass = conn.execute(
        f"""
        SELECT m.session_id, SUM(LENGTH(COALESCE(m.content, '')) * {later})
        FROM messages m
        WHERE m.role = 'tool' AND m.timestamp >= ? AND m.timestamp < ?
        GROUP BY m.session_id ORDER BY 2 DESC LIMIT ?
        """,
        (start, end, _MAX_TOP_SESSIONS),
    ).fetchall()

    tool_total = sum(int(mass or 0) for _tool, mass in tool_by_tool)
    assistant_total = int(assistant_row[0] or 0)
    top_tools = [
        {"tool": (tool or "unknown")[:32], "replayed_tokens_est": int(mass or 0) // 4}
        for tool, mass in tool_by_tool
        if mass
    ][:_MAX_TOP_SESSIONS]
    top_sessions = [
        {"session_id": (sid or "unknown")[:40], "replayed_tool_tokens_est": int(mass or 0) // 4}
        for sid, mass in session_mass
        if mass
    ]

    return {
        "tool_results_replayed_tokens_est": tool_total // 4,
        "assistant_replayed_tokens_est": assistant_total // 4,
        "top_tools": top_tools,
        "top_sessions": top_sessions,
        "method": "size/4 * later assistant messages per session; estimates from message sizes",
    }


def usage_payload(days: int = _WINDOW_DAYS) -> dict[str, Any]:
    days = max(1, min(days, 30))
    cache_key = str(days)
    cached = _replay_cache.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < _REPLAY_CACHE_TTL:
        return cached[1]

    path = state_db_path()
    unavailable = {
        "available": False,
        "reason": f"session store not readable at {path}",
        "window_days": days,
        "generated_at": _now(),
        "claim_boundary": _CLAIM_BOUNDARY,
    }
    if not path.exists():
        return unavailable

    conn = None
    try:
        conn = _connect_ro(path)
        start, end = _window_bounds(days)
        totals = _totals(conn, start, end)
        if not totals.get("api_calls"):
            payload = {
                "available": True,
                "window_days": days,
                "generated_at": _now(),
                "totals": totals,
                "daily": [],
                "direct_vs_subagent": {},
                "models": [],
                "replay": {
                    "tool_results_replayed_tokens_est": 0,
                    "assistant_replayed_tokens_est": 0,
                    "top_tools": [],
                    "top_sessions": [],
                },
                "claim_boundary": _CLAIM_BOUNDARY,
            }
        else:
            payload = {
                "available": True,
                "window_days": days,
                "generated_at": _now(),
                "totals": totals,
                "daily": _daily(conn, start, end),
                "direct_vs_subagent": _split(conn, start, end),
                "models": _models(conn, start, end),
                "replay": _replay_mass(conn, start, end),
                "claim_boundary": _CLAIM_BOUNDARY,
            }
    except sqlite3.Error as exc:
        return {
            "available": False,
            "reason": f"session store query failed: {exc}",
            "window_days": days,
            "generated_at": _now(),
            "claim_boundary": _CLAIM_BOUNDARY,
        }
    finally:
        if conn is not None:
            conn.close()

    _replay_cache[cache_key] = (now, payload)
    return payload
