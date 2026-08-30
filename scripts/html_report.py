#!/usr/bin/env python3
"""SIPS HTML report generator — writes a self-contained dark-theme dashboard.

Consumes the lens payloads (usage, gate matrix, timeline, lifecycle, quality)
and renders them as a single styled HTML file the desktop chat can display
inline via the ::preview directive. Pure string templating — no JS deps.

Design notes (impeccable polish + delight pass):
- One accent hue (cyan) carries state; green/amber/red are reserved for
  judgment (cache health, gate outcomes) so color always means something.
- Numerals are tabular everywhere data shifts; labels whisper in small caps.
- Delight is concentrated in two earned moments: the header ("report card"
  posture chip) and the footer seal — the rest stays quiet, per Operate mode.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

_REPORT_PATH = Path.home() / ".hermes" / "sips" / "report.html"

_CSS = """
:root { color-scheme: dark; --bg:#0f1117; --panel:#171a22; --panel2:#1d212b;
        --line:#242a36; --ink:#dfe2ea; --mut:#8b91a0; --dim:#626879;
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
.bar-wrap { background: #20242e; border-radius: 99px; height: 6px; overflow: hidden; min-width: 90px; }
.bar { height: 100%; border-radius: 99px; background: var(--accent); opacity: .85;
  transform-origin: left center; animation: grow .7s cubic-bezier(.16,1,.3,1) both; }
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.bar.g { background: var(--good); } .bar.w { background: var(--warn); } .bar.b { background: var(--bad); }
.mono { font-family: ui-monospace, 'SF Mono', Menlo, monospace; font-size: 12px; }
.ellip { display: inline-block; max-width: 240px; overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; vertical-align: bottom; }
@media (max-width: 560px) { .ellip { max-width: 150px; } }
.dim { color: var(--dim); }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
.g { background: var(--good); } .w { background: var(--warn); } .b { background: var(--bad); } .n { background: #39404e; }
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


def _bar(pct: float, cls: str = "") -> str:
    return f'<div class="bar-wrap"><div class="bar {cls}" style="width:{max(1, min(100, round(pct)))}%"></div></div>'


_SEAL = (
    '<span class="seal">'
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">'
    '<path d="M12 2l2.4 4.9 5.4.8-3.9 3.8.9 5.4-4.8-2.5-4.8 2.5.9-5.4L4.2 7.7l5.4-.8L12 2z"'
    ' fill="none" stroke="#69d39a" stroke-width="1.6" stroke-linejoin="round"/></svg>'
    "Verified read-only lens output</span>"
)


def _posture(usage: dict[str, Any], matrix: dict[str, Any]) -> str:
    """One honest posture chip: worst known signal wins, silence means healthy."""
    hit = (usage.get("totals") or {}).get("cache_hit_pct")
    dirty = [r for r in (matrix.get("runs") or []) if r.get("failed_count")]
    if (hit is not None and hit < 80) or dirty:
        return '<span class="posture warn">Needs attention</span>'
    if hit is not None and hit >= 90:
        return '<span class="posture good">All healthy</span>'
    return '<span class="posture">Operational</span>'


def _render_usage(usage: dict[str, Any]) -> str:
    if not usage.get("available"):
        return """
<section><h2>Token usage</h2>
<div class="stat"><div class="v dim">&mdash;</div>
<div class="l">unavailable</div><div class="d">session store not readable from this run</div></div></section>"""
    t = usage.get("totals") or {}
    hit = t.get("cache_hit_pct")
    hit_cls = "good" if (hit or 0) >= 90 else "warn"
    replay = (usage.get("replay") or {}).get("tool_results_replayed_tokens_est") or 0

    daily_rows = ""
    days = (usage.get("daily") or [])[-10:]
    peak = max((d.get("fresh_input_tokens") or 0 for d in days), default=1) or 1
    for d in days:
        day_hit = d.get("cache_hit_pct") or 0
        cls = "g" if day_hit >= 90 else "w"
        daily_rows += (
            f"<tr><td class='mono dim'>{_esc(d.get('day'))}</td>"
            f"<td class='r'>{_fmt(d.get('fresh_input_tokens'))}</td>"
            f"<td class='r'>{day_hit}%</td>"
            f"<td style='width:34%'>{_bar(100.0 * (d.get('fresh_input_tokens') or 0) / peak, cls)}</td></tr>"
        )

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

    daily_block = (
        f"""<div><h3 style="font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.09em;margin:12px 0 4px;">New tokens per day</h3>
<table>{daily_rows}</table></div>"""
        if daily_rows
        else ""
    )
    replay_block = (
        f"""<div><h3 style="font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.09em;margin:12px 0 4px;">Most reread tools</h3>
<table>{replay_rows}</table>
<p style="margin-top:12px;font-size:12px;color:var(--mut);">Share of new tokens spent on subagents
<b class="accent">{share}%</b> <span class="dim">({_fmt(sub)} / {_fmt(sub + direct)})</span></p>
</div>"""
        if replay_rows
        else ""
    )
    inner = daily_block + replay_block
    two = f'<div class="two">{inner}</div>' if inner else ""

    return f"""
<section><h2>Token usage &middot; last {usage.get('window_days', 7)} days</h2>
<div class="grid">
  <div class="stat"><div class="v">{_fmt(t.get('fresh_input_tokens'))}</div><div class="l">new tokens sent</div></div>
  <div class="stat"><div class="v {hit_cls}">{hit}%</div><div class="l">served from cache</div><div class="d">of {_fmt(t.get('total_input_tokens'))} total</div></div>
  <div class="stat"><div class="v">{_fmt(t.get('output_tokens'))}</div><div class="l">tokens written back</div><div class="d">ratio {t.get('fresh_to_output_ratio')} to new input</div></div>
  <div class="stat"><div class="v">{_fmt(replay)}</div><div class="l">reread tool results</div></div>
  <div class="stat"><div class="v">{t.get('sessions', 0)}</div><div class="l">sessions</div></div>
</div>{two}</section>"""


_GATE_LABELS = {
    "integrity": "Integrity",
    "correctness": "Correct",
    "regression": "No regressions",
    "resource": "Resources",
    "benefit": "Benefit",
}


def _render_gates(matrix: dict[str, Any]) -> str:
    if not matrix.get("available"):
        return ""
    gate_names = matrix.get("gates") or []
    runs = matrix.get("runs") or []
    if not runs:
        return """
<h2>Quality gates per run</h2>
<div class="stat"><div class="v dim">&mdash;</div><div class="l">no gated runs yet</div>
<div class="d">the matrix fills as sessions land graph receipts</div></div>"""
    head = "".join(
        f'<th class="r" title="{_esc(_GATE_LABELS.get(g, g))}">{_esc(_GATE_LABELS.get(g, g))}</th>'
        for g in gate_names
    )
    body = ""
    for run in runs[:12]:
        gates = run.get("gates") or {}
        cells = "".join(
            f"<td class='r'><span class='dot {'g' if gates.get(g) == 'ok' else 'b' if gates.get(g) == 'failed' else 'w' if gates.get(g) == 'partial' else 'n'}'></span></td>"
            for g in gate_names
        )
        note = " <span class='dim' style='font-size:11px'>&middot; not gated</span>" if not run.get("receipt") else ""
        body += (
            f"<tr><td class='mono'><span class='ellip'>{_esc(str(run.get('run_id'))[:26])}&hellip;</span>{note}</td>{cells}</tr>"
        )
    gated = sum(1 for r in runs if r.get("receipt"))
    all_ok = sum(1 for r in runs if r.get("receipt") and not r.get("failed_count"))
    return f"""
<h2>Quality gates per run</h2>
<table><tr><th>run</th>{head}</tr>{body}</table>
<p style="margin-top:10px;font-size:12px;color:var(--mut);">{gated}/{len(runs)} runs verified &middot;
<b class="{ 'good' if all_ok == gated and gated else 'warn' }">{all_ok} passed all gates</b>
<span class="dim">&middot; each dot = did that quality check pass for the run, from its receipt</span></p>"""


def _render_timeline(timeline: dict[str, Any]) -> str:
    if not timeline.get("available"):
        return ""
    entries = timeline.get("entries") or []
    if not entries:
        return """
<h2>Timeline</h2>
<div class="stat"><div class="v dim">&mdash;</div><div class="l">nothing tracked yet</div>
<div class="d">runs and campaigns appear as they happen</div></div>"""
    newest = max(e["ts"] for e in entries)
    rows = ""
    for e in entries[:14]:
        delta_h = max(0.0, (newest - e["ts"]) / 3600)
        icon = {"succeeded": "g", "failed": "b", "stale": "w"}.get(e.get("status"), "n")
        kind_label = (
            f"{_esc(e.get('events', 0))} events"
            if e.get("kind") == "run"
            else f"campaign · {_esc(e.get('children', 0))} children"
        )
        rows += (
            f"<tr><td><span class='dot {icon}'></span><span class='mono ellip'>{_esc(str(e.get('id'))[:30])}&hellip;</span></td>"
            f"<td>{_esc(e.get('status'))}</td><td class='dim'>{kind_label}</td>"
            f"<td class='r' style='color:var(--mut)'>{delta_h:.1f}h ago</td></tr>"
        )
    return f"""
<section><h2>Recent activity &middot; last {timeline.get('window_hours', '?')} hours</h2>
<table>{rows}</table></section>"""


def generate_report() -> Path:
    # Local imports so tests can monkeypatch module-level names.
    from usage_lens import usage_payload
    from gate_matrix import gate_matrix_payload
    from fleet_timeline import timeline_payload

    usage = usage_payload(days=7)
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
{_render_usage(usage)}
{_render_gates(matrix)}
{_render_timeline(timeline)}
<div class="foot">{_SEAL}<span>18 lens commands in chat &middot; /sips for the full list</span></div>
</body></html>"""

    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text(html, encoding="utf-8")
    return _REPORT_PATH


if __name__ == "__main__":
    print(generate_report())
