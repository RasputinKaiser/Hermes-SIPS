#!/usr/bin/env python3
"""SIPS HTML report generator — writes a self-contained dark-theme dashboard.

Consumes the lens payloads (usage, gate matrix, timeline) and renders them as
a single styled HTML file the desktop chat can display inline via ::preview.
Pure string templating — no JS deps.

Design notes (impeccable polish + delight + critique-fix pass):
- One accent hue (cyan) carries magnitude/structure; green/amber/red are
  reserved for judgment TEXT (cache health, gate outcomes) — never for bar
  length — so every element encodes exactly one variable.
- Thresholds are unified everywhere: green >=90, amber 80-90, red <80.
- The posture chip honors its contract ("worst known signal wins"): failed
  gates, any full day under 80% cache, or an aggregate under 80% all surface.
  Today renders as a PARTIAL day (gray, excluded from judgment) until the day
  closes; cold days under _COLD_DAY_FRESH new tokens are never judged.
- Runs and quality gates render as ONE merged table (status, recency, gate
  dots per run); campaigns keep a compact strip below.
- --dim meets WCAG AA (>=4.5:1) on both background tokens; every status dot
  carries role="img", a title, and an aria-label — color is never the only
  channel for a pass/fail signal.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

_REPORT_PATH = Path.home() / ".hermes" / "sips" / "report.html"

# Days with fewer new tokens than this are cold samples — their cache-hit
# percentage is noise, so neither the daily table nor the posture chip judges them.
_COLD_DAY_FRESH = 100_000

_CSS = """
:root { color-scheme: dark; --bg:#0f1117; --panel:#171a22;
        --panel3:#20242e; --line:#242a36; --ink:#dfe2ea; --mut:#8b91a0;
        --dim:#7d8394; --neutral:#39404e;
        --accent:#7dd3fc; --good:#69d39a; --warn:#f4c76b; --bad:#f28b8b; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--ink);
  font: 14px/1.6 ui-sans-serif, -apple-system, 'Segoe UI', sans-serif;
  padding: 40px 36px 56px; max-width: 1060px; margin: 0 auto; }
header { display: flex; align-items: baseline; justify-content: space-between;
  gap: 16px; flex-wrap: wrap; border-bottom: 1px solid var(--line); padding-bottom: 18px; }
h1 { font-size: 24px; font-weight: 800; letter-spacing: -0.02em; }
h1 .thin { font-weight: 400; color: var(--mut); }
.posture { font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 0.1em; padding: 5px 12px; border-radius: 99px; border: 1px solid var(--line); }
.posture.good { color: var(--good); border-color: color-mix(in srgb, var(--good) 45%, transparent);
  background: color-mix(in srgb, var(--good) 8%, transparent); }
.posture.warn { color: var(--warn); border-color: color-mix(in srgb, var(--warn) 45%, transparent);
  background: color-mix(in srgb, var(--warn) 8%, transparent); }
.sub { color: var(--mut); font-size: 12px; margin: 8px 0 30px; }
.sub .sep { color: var(--dim); margin: 0 6px; }
h2 { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--dim); margin: 38px 0 14px; display: flex; align-items: center; gap: 10px; }
h2::before { content: ''; width: 14px; height: 2px; background: var(--accent); border-radius: 2px; flex-shrink: 0; }
h2::after { content: ''; flex: 1; height: 1px; background: var(--line); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 10px; }
.grid > .stat { min-width: 0; }
.stat { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px;
  transition: border-color .15s ease; }
.stat:hover { border-color: color-mix(in srgb, var(--accent) 40%, var(--line)); }
.stat .v { font-size: 22px; font-weight: 750; font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
.stat .l { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--mut); margin-top: 3px; }
.stat .d { font-size: 11px; color: var(--dim); margin-top: 4px; }
.good { color: var(--good); } .warn { color: var(--warn); } .bad { color: var(--bad); } .accent { color: var(--accent); }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
td, th { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--line); font-size: 13px; }
tbody tr { transition: background .12s ease; }
tbody tr:hover { background: color-mix(in srgb, var(--accent) 4%, transparent); }
th { color: var(--dim); font-size: 10px; text-transform: uppercase; letter-spacing: 0.09em;
  border-bottom-color: var(--line); }
td.r, th.r { text-align: right; }
.bar-wrap { background: var(--panel3); border-radius: 99px; height: 6px; overflow: hidden; min-width: 90px; }
.bar { height: 100%; border-radius: 99px; background: var(--accent); opacity: .85;
  transform-origin: left center; animation: grow .7s cubic-bezier(.16,1,.3,1) both; }
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.bar.n { background: var(--neutral); }
.mono { font-family: ui-monospace, 'SF Mono', Menlo, monospace; font-size: 12px; }
.ellip { display: inline-block; max-width: 240px; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; vertical-align: bottom; }
@media (max-width: 560px) { .ellip { max-width: 150px; } }
.dim { color: var(--dim); }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
.g { background: var(--good); } .w { background: var(--warn); } .b { background: var(--bad); }
.n { background: var(--neutral); }
.legend { margin-top: 10px; font-size: 12px; color: var(--mut); }
.delta { margin-top: 10px; font-size: 12px; color: var(--mut); }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 36px; }
@media (max-width: 760px) { .two { grid-template-columns: 1fr; } body { padding: 24px 18px 40px; } }
.foot { margin-top: 44px; color: var(--dim); font-size: 11px; border-top: 1px solid var(--line);
  padding-top: 14px; display: flex; justify-content: space-between; gap: 14px; flex-wrap: wrap; }
.seal { display: inline-flex; align-items: center; gap: 7px; color: var(--mut); }
.seal svg { flex-shrink: 0; }
/* Animate pass: sections fade up once, staggered; bars grow from left.
   All of it collapses under prefers-reduced-motion. */
section { animation: rise .45s cubic-bezier(.16,1,.3,1) both; }
section:nth-of-type(2) { animation-delay: .08s; }
section:nth-of-type(3) { animation-delay: .16s; }
section:nth-of-type(4) { animation-delay: .24s; }
@keyframes rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) {
  section { animation: none; }
  .bar { animation: none; }
}
"""


def _fmt(n: Any) -> str:
    try:
        v = float(n or 0)
    except (TypeError, ValueError):
        v = 0.0
    if v != v:  # NaN guard
        v = 0.0
    v = max(0.0, v)
    if v >= 1e9:
        return f"{v/1e9:.2f}B"
    if v >= 1e6:
        return f"{v/1e6:.1f}M"
    if v >= 1e3:
        return f"{v/1e3:.1f}K"
    return f"{int(v)}"


def _esc(text: Any) -> str:
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _bar(pct: float, cls: str = "") -> str:
    return f'<div class="bar-wrap"><div class="bar {cls}" style="width:{max(1, min(100, round(pct)))}%"></div></div>'


def _dot(cls: str, label: str) -> str:
    """A status dot that is never color-only: role, title, and aria-label."""
    return (
        f"<span class='dot {cls}' role='img' title='{_esc(label)}' "
        f"aria-label='{_esc(label)}'></span>"
    )


def _hit_cls(pct: Any) -> str:
    """Unified judgment classes: green >=90, amber 80-90, red <80, no data = dim."""
    if pct is None:
        return "dim"
    if pct >= 90:
        return "good"
    if pct >= 80:
        return "warn"
    return "bad"


_SEAL = (
    '<span class="seal">'
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<path d="M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4-4.8-2.5-4.8 2.5.9-5.4L4.2 7.7l5.4-.8L12 2z"'
    ' fill="none" style="stroke:var(--good)" stroke-width="1.6" stroke-linejoin="round"/></svg>'
    "Verified read-only lens output</span>"
)


def _posture(usage: dict[str, Any], matrix: dict[str, Any]) -> str:
    """One honest posture chip: worst known signal wins, silence means healthy.

    Judged signals: failed gates, any FULL day (not today's partial) whose
    cache hit fell under 80 with a real sample, and the aggregate itself.
    """
    hit = (usage.get("totals") or {}).get("cache_hit_pct")
    dirty = [r for r in (matrix.get("runs") or []) if r.get("failed_count")]
    weak_days = [
        d
        for d in (usage.get("daily") or [])
        if d.get("day") != _today()
        and (d.get("fresh_input_tokens") or 0) >= _COLD_DAY_FRESH
        and d.get("cache_hit_pct") is not None
        and d["cache_hit_pct"] < 80
    ]
    if dirty or weak_days or (hit is not None and hit < 80):
        return '<span class="posture warn">Needs attention</span>'
    if hit is not None and hit >= 90:
        return '<span class="posture good">All healthy</span>'
    return '<span class="posture">Operational</span>'


def _week_agg(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fresh = sum((d.get("fresh_input_tokens") or 0) for d in rows)
    cr = sum((d.get("cache_read_tokens") or 0) for d in rows)
    out = sum((d.get("output_tokens") or 0) for d in rows)
    calls = sum((d.get("api_calls") or 0) for d in rows)
    sessions = sum((d.get("sessions") or 0) for d in rows)
    hit = round(100.0 * cr / (cr + fresh), 1) if (cr + fresh) else None
    return {"fresh": fresh, "out": out, "calls": calls, "sessions": sessions, "hit": hit}


def _delta_line(this_rows: list[dict[str, Any]], prev_rows: list[dict[str, Any]]) -> str:
    """'vs previous week' line — only when both sides are full 7-day weeks."""
    if len(this_rows) < 7 or len(prev_rows) < 7:
        return ""
    a, b = _week_agg(this_rows), _week_agg(prev_rows)
    parts: list[str] = []
    if b["fresh"]:
        parts.append(f"new tokens {100.0 * (a['fresh'] - b['fresh']) / b['fresh']:+.0f}%")
    if a["hit"] is not None and b["hit"] is not None:
        pts = a["hit"] - b["hit"]
        cls = "good" if pts >= 0.5 else "warn" if pts <= -2 else ""
        c = f"<b class='{cls}'>{pts:+.1f} pts</b>" if cls else f"{pts:+.1f} pts"
        parts.append(f"cache hit {c}")
    parts.append(f"sessions {b['sessions']} &rarr; {a['sessions']}")
    return f"<p class='delta'>vs previous week: {' &middot; '.join(parts)}</p>"


def _render_usage(usage: dict[str, Any], prev_rows: list[dict[str, Any]] | None = None) -> str:
    if not usage.get("available"):
        return """
<section><h2>Token usage</h2>
<div class="stat"><div class="v dim">&mdash;</div>
<div class="l">unavailable</div><div class="d">session store not readable from this run</div></div></section>"""
    t = usage.get("totals") or {}
    hit = t.get("cache_hit_pct")
    hit_cls = _hit_cls(hit)
    replay = (usage.get("replay") or {}).get("tool_results_replayed_tokens_est") or 0
    today = _today()

    daily_rows = ""
    days = (usage.get("daily") or [])[-10:]
    peak = max((d.get("fresh_input_tokens") or 0 for d in days), default=1) or 1
    for d in days:
        day = d.get("day") or ""
        partial = day == today
        if partial:
            # Today is an incomplete sample: gray bar, unjudged percentage.
            day_hit = d.get("cache_hit_pct")
            pct_txt = f"{day_hit}%" if day_hit is not None else "&mdash;"
            pct_cls, bar_cls = "dim", "n"
            label = f"{_esc(day)} <span class='dim'>(partial)</span>"
        else:
            day_hit = d.get("cache_hit_pct")
            pct_txt = f"{day_hit}%" if day_hit is not None else "&mdash;"
            pct_cls, bar_cls = _hit_cls(day_hit), ""
            label = _esc(day)
        daily_rows += (
            f"<tr><td class='mono dim'>{label}</td>"
            f"<td class='r'>{_fmt(d.get('fresh_input_tokens'))}</td>"
            f"<td class='r {pct_cls}'>{pct_txt}</td>"
            f"<td style='width:34%'>{_bar(100.0 * (d.get('fresh_input_tokens') or 0) / peak, bar_cls)}</td></tr>"
        )
    daily_block = ""
    if daily_rows:
        daily_block = f"""<div><h3 style="font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.09em;margin:12px 0 4px;">New tokens per day</h3>
<table><tr><th>day</th><th class="r">new tokens</th><th class="r">served from cache</th><th></th></tr>{daily_rows}</table>
<p class="legend">bar length = new tokens sent &middot; cache % colored green &ge;90, amber 80&ndash;90, red &lt;80 &middot; today renders partial (gray) until the day closes</p></div>"""

    replay_rows = ""
    tools = (usage.get("replay") or {}).get("top_tools", [])
    rpeak = max((r.get("replayed_tokens_est") or 0 for r in tools), default=1) or 1
    for r in tools[:5]:
        replay_rows += (
            f"<tr><td class='mono'>{_esc(r['tool'])}</td>"
            f"<td class='r'>&asymp;{_fmt(r.get('replayed_tokens_est'))}</td>"
            f"<td style='width:38%'>{_bar(100.0 * (r.get('replayed_tokens_est') or 0) / rpeak)}</td></tr>"
        )

    split = usage.get("direct_vs_subagent") or {}
    sub = (split.get("subagent") or {}).get("fresh_input_tokens") or 0
    direct = (split.get("direct") or {}).get("fresh_input_tokens") or 0
    share = round(100 * sub / (sub + direct)) if (sub + direct) else 0

    replay_block = ""
    if replay_rows:
        top_tool = _esc(tools[0]["tool"]) if tools else ""
        lever = (
            f"Reread tool results are re-sent on every turn &mdash; capping {top_tool}'s output size is the cheapest lever. "
            if top_tool
            else ""
        )
        sub_note = " &mdash; over half; trim subagent briefs" if share >= 50 else ""
        replay_block = f"""<div><h3 style="font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.09em;margin:12px 0 4px;">Most reread tools</h3>
<table>{replay_rows}</table>
<p class="legend">{lever}Share of new tokens spent on subagents <b class="accent">{share}%</b> <span class="dim">({_fmt(sub)} / {_fmt(sub + direct)}{sub_note})</span></p></div>"""

    inner = daily_block + replay_block
    two = f'<div class="two">{inner}</div>' if inner else ""
    delta = _delta_line((usage.get("daily") or [])[-7:], prev_rows or [])

    return f"""
<section><h2>Token usage &middot; last {usage.get('window_days', 7)} days</h2>
<div class="grid">
  <div class="stat"><div class="v">{_fmt(t.get('fresh_input_tokens'))}</div><div class="l">new tokens sent</div></div>
  <div class="stat"><div class="v {hit_cls}">{hit}%</div><div class="l">served from cache</div><div class="d">of {_fmt(t.get('total_input_tokens'))} total &middot; green &ge;90, amber 80&ndash;90, red &lt;80</div></div>
  <div class="stat"><div class="v">{_fmt(t.get('output_tokens'))}</div><div class="l">tokens written back</div><div class="d">&asymp;{_esc(t.get('fresh_to_output_ratio') or '?')} new tokens read per token written back</div></div>
  <div class="stat"><div class="v">{_fmt(replay)}</div><div class="l">reread tool results</div></div>
  <div class="stat"><div class="v">{t.get('sessions', 0)}</div><div class="l">sessions</div></div>
</div>{delta}{two}</section>"""


_GATE_LABELS = {
    "integrity": "Integrity",
    "correctness": "Correct",
    "regression": "No regressions",
    "resource": "Resources",
    "benefit": "Benefit",
}

_GATE_STATE_LABELS = {"ok": "pass", "failed": "FAIL", "partial": "partial"}


def _gate_cells(run: dict[str, Any], gate_names: list[str], rid: str) -> str:
    gates = run.get("gates") or {}
    cells = ""
    for g in gate_names:
        state = gates.get(g)
        dot_cls = "g" if state == "ok" else "b" if state == "failed" else "w" if state == "partial" else "n"
        state_txt = _GATE_STATE_LABELS.get(state or "", "not run")
        label = f"{rid} &middot; {_esc(_GATE_LABELS.get(g, g))}: {state_txt}"
        cells += f"<td class='r'>{_dot(dot_cls, label)}</td>"
    return cells


def _render_runs(matrix: dict[str, Any], timeline: dict[str, Any]) -> str:
    """Merged run table: one row per run — status, recency, and gate dots.

    Replaces the old separate 'Quality gates per run' + 'Recent activity'
    tables, which listed the same run IDs twice.
    """
    if not matrix.get("available") and not timeline.get("available"):
        return ""
    gate_names = matrix.get("gates") or []
    runs = matrix.get("runs") or []
    entries = [e for e in (timeline.get("entries") or []) if e.get("kind") == "run"]
    campaigns = [e for e in (timeline.get("entries") or []) if e.get("kind") != "run"]

    if not runs and not entries:
        return """
<h2>Runs &middot; status &amp; quality gates</h2>
<div class="stat"><div class="v dim">&mdash;</div><div class="l">no runs tracked yet</div>
<div class="d">runs land here as graph receipts arrive</div></div>"""

    tmap = {str(e["id"]): e for e in entries}
    all_ts = [e["ts"] for e in (timeline.get("entries") or [])]
    newest = max(all_ts) if all_ts else 0

    head = "".join(
        f'<th class="r" title="{_esc(_GATE_LABELS.get(g, g))}">{_esc(_GATE_LABELS.get(g, g))}</th>'
        for g in gate_names
    )
    rows = ""
    seen: set[str] = set()
    for run in runs[:12]:
        rid = str(run.get("run_id"))
        seen.add(rid)
        e = tmap.get(rid)
        if e is not None:
            delta_h = max(0.0, (newest - e["ts"]) / 3600)
            recency = f"{delta_h:.1f}h ago"
            st = e.get("status")
            icon = {"succeeded": "g", "failed": "b", "stale": "w"}.get(st, "n")
        else:
            recency = "&mdash;"
            st = "verified" if run.get("receipt") else "not gated"
            icon = "g" if run.get("receipt") else "n"
        note = " <span class='dim' style='font-size:11px'>&middot; not gated</span>" if not run.get("receipt") else ""
        rows += (
            f"<tr><td class='mono'><span class='ellip' title='{_esc(rid)}'>{_esc(rid[:26])}&hellip;</span>{note}</td>"
            f"<td>{_dot(icon, f'{rid}: {st}')}{_esc(st)}</td>"
            f"{_gate_cells(run, gate_names, rid)}"
            f"<td class='r dim'>{recency}</td></tr>"
        )
    # Runs seen in the activity stream but absent from the gate matrix.
    for e in entries:
        rid = str(e["id"])
        if rid in seen or rows.count("<tr>") >= 14:
            continue
        seen.add(rid)
        delta_h = max(0.0, (newest - e["ts"]) / 3600)
        st = e.get("status")
        icon = {"succeeded": "g", "failed": "b", "stale": "w"}.get(st, "n")
        rows += (
            f"<tr><td class='mono'><span class='ellip' title='{_esc(rid)}'>{_esc(rid[:26])}&hellip;</span></td>"
            f"<td>{_dot(icon, f'{rid}: {st}')}{_esc(st)}</td>"
            f"{_gate_cells({}, gate_names, rid)}"
            f"<td class='r dim'>{delta_h:.1f}h ago</td></tr>"
        )

    gated = sum(1 for r in runs if r.get("receipt"))
    all_ok = sum(1 for r in runs if r.get("receipt") and not r.get("failed_count"))
    failed_runs = [r for r in runs if r.get("failed_count")]
    failed_checks = sum(r.get("failed_count") or 0 for r in failed_runs)
    guidance = (
        f"<p class='bad' style='margin-top:10px;font-size:12px;'>{failed_checks} gate checks failed across {len(failed_runs)} runs &mdash; inspect receipts with /sips-quality in chat.</p>"
        if failed_checks
        else ""
    )
    campaign_bits = []
    for c in campaigns[:3]:
        delta_h = max(0.0, (newest - c["ts"]) / 3600)
        campaign_bits.append(
            f"<span class='mono'>{_esc(str(c.get('id'))[:20])}&hellip;</span> "
            f"({_esc(c.get('children', 0))} children, {delta_h:.1f}h ago)"
        )
    campaign_note = (
        f"<p class='legend'>Campaigns: {' &middot; '.join(campaign_bits)}</p>" if campaign_bits else ""
    )

    return f"""
<h2>Runs &middot; status &amp; quality gates</h2>
<table><tr><th>run</th><th>status</th>{head}<th class="r">recent</th></tr>{rows}</table>
<p class="legend">{gated}/{len(runs)} runs verified &middot;
<b class="{'good' if all_ok == gated and gated else 'warn'}">{all_ok} passed all gates</b>
&middot; each dot = did that quality check pass for the run, from its receipt</p>{guidance}{campaign_note}"""


def generate_report() -> Path:
    # Local imports so tests can monkeypatch module-level names.
    from usage_lens import usage_payload
    from gate_matrix import gate_matrix_payload
    from fleet_timeline import timeline_payload

    usage = usage_payload(days=7)
    try:
        rows14 = [d for d in (usage_payload(days=14).get("daily") or []) if d.get("day") != _today()]
        prev_rows = rows14[:-7] if len(rows14) > 7 else None
    except Exception:
        prev_rows = None
    matrix = gate_matrix_payload()
    timeline = timeline_payload()

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SIPS Control Report</title><style>{_CSS}</style></head>
<body>
<header>
  <h1>SIPS <span class="thin">Control Report</span></h1>
  {_posture(usage, matrix)}
</header>
<div class="sub">Generated {generated}<span class="sep">·</span>read-only aggregates from the session store, graph receipts, and the hook stream</div>
{_render_usage(usage, prev_rows)}
{_render_runs(matrix, timeline)}
<div class="foot">{_SEAL}<span>18 lens commands in chat &middot; /sips for the full list</span></div>
</body></html>"""

    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text(html, encoding="utf-8")
    return _REPORT_PATH


if __name__ == "__main__":
    print(generate_report())
