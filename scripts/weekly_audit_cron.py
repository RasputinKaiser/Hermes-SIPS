#!/usr/bin/env python3
"""Weekly SIPS token-health audit — cron script (no_agent mode).

Reads ~/.hermes/state.db read-only and prints a compact digest ONLY when
something regressed vs the prior week; empty stdout sends nothing (watchdog
pattern, per hermes cron semantics). State (prior week's numbers) lives in
$SIPS_HOME/weekly_audit_state.json.
"""
import json
import sqlite3
import sys
import time
from pathlib import Path

DB = Path.home() / ".hermes" / "state.db"
STATE = Path.home() / ".hermes" / "sips" / "weekly_audit_state.json"
if not DB.exists():
    sys.exit(0)

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
now = time.time()
this_week = now - 7 * 86400


def window(start):
    row = conn.execute(
        """SELECT COALESCE(SUM(m.api_call_count),0), COALESCE(SUM(m.input_tokens),0),
                  COALESCE(SUM(m.cache_read_tokens),0)
           FROM sessions s JOIN session_model_usage m ON m.session_id = s.id
           WHERE s.started_at >= ?""",
        (start,),
    ).fetchone()
    calls, fresh, cached = row
    total_in = fresh + cached
    hit = 100.0 * cached / total_in if total_in else 0.0
    return {"calls": calls, "fresh": fresh, "cached": cached, "hit": round(hit, 1)}


cur = window(this_week)
prev = window(this_week - 7 * 86400)

# Replay-weight estimate (bounded): tool-result mass x later assistant calls
replay_est = 0
try:
    row = conn.execute(
        """SELECT COALESCE(SUM(LENGTH(COALESCE(m.content,'')) * (
             SELECT COUNT(*) FROM messages a
             WHERE a.session_id = m.session_id AND a.role='assistant' AND a.timestamp >= m.timestamp)), 0)
           FROM messages m
           WHERE m.role='tool' AND m.timestamp >= ?""",
        (this_week,),
    ).fetchone()
    replay_est = int(row[0] or 0) // 4
except Exception:
    pass
conn.close()

prior = {}
if STATE.exists():
    try:
        prior = json.loads(STATE.read_text())
    except Exception:
        prior = {}

alerts = []
if prior.get("hit") is not None and cur["hit"] < prior["hit"] - 5:
    alerts.append(f"cache hit fell {prior['hit']}% -> {cur['hit']}%")
if prior.get("fresh") and cur["fresh"] > prior["fresh"] * 1.5 and cur["calls"] > 100:
    alerts.append(f"fresh input grew {prior['fresh']/1e6:.1f}M -> {cur['fresh']/1e6:.1f}M")
if cur["hit"] < 80 and cur["calls"] > 200:
    alerts.append(f"cache hit {cur['hit']}% below 80%")

STATE.parent.mkdir(parents=True, exist_ok=True)
STATE.write_text(json.dumps(cur))

if alerts:
    def fm(n):
        if n >= 1e9:
            return f"{n/1e9:.2f}B"
        if n >= 1e6:
            return f"{n/1e6:.1f}M"
        return f"{n/1e3:.1f}K"

    print("## Weekly SIPS token-health alerts")
    for a in alerts:
        print(f"- {a}")
    print()
    print(f"This week: {cur['calls']} calls | fresh {fm(cur['fresh'])} | cache {cur['hit']}% | replay(tool) ~{fm(replay_est)}")
    print(f"Prev week: {prev['calls']} calls | fresh {fm(prev['fresh'])} | cache {prev['hit']}%")
