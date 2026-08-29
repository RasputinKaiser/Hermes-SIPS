"""Rich in-chat cards for the SIPS Hermes slash commands.

The commands used to dump raw JSON. These renderers give each command a
colorful, structured markdown card — the same visual vocabulary as the
desktop panel: unicode bars, status glyphs, accent tables, claim boundaries.
Everything here is monospace-safe and needs no images.
"""
from __future__ import annotations

from typing import Any

BAR_WIDTH = 12
_FILL = "█"
_EMPTY = "░"
_SPARK = "▁▂▃▄▅▆▇█"

# ── primitives ──────────────────────────────────────────────────────────────

def bar(value: Any, total: Any, width: int = BAR_WIDTH) -> str:
    try:
        v, t = max(0.0, float(value)), max(0.0, float(total))
    except (TypeError, ValueError):
        return _EMPTY * width
    ratio = 0.0 if t <= 0 else min(1.0, v / t)
    filled = round(ratio * width)
    return _FILL * filled + _EMPTY * (width - filled)


def bar_of_max(value: Any, values: list[Any], width: int = BAR_WIDTH) -> str:
    try:
        cands = [abs(float(v)) for v in values]
        v = abs(float(value))
    except (TypeError, ValueError):
        cands, v = [], 0.0
    peak = max(cands) if cands else 0.0
    if peak <= 0:
        return _EMPTY * width
    filled = round(min(1.0, v / peak) * width)
    if v > 0 and filled == 0:
        filled = 1
    return _FILL * filled + _EMPTY * (width - filled)


def glyph(status: Any) -> str:
    v = str(status or "").strip().lower()
    if v in {"succeeded", "done", "passed", "ok", "healthy", "fresh", "verified", "active", "recorded", "inspected"}:
        return "✅" if v in {"succeeded", "done", "passed", "ok", "verified"} else "🟢"
    if v in {"failed", "error", "stale", "blocked", "denied"}:
        return "🔴"
    if v in {"running", "executing", "improved"}:
        return "🟡"
    if v in {"pending", "planned", "queued", "ready"}:
        return "⚪"
    return "·"


def sparkline(counts: list[Any]) -> str:
    try:
        nums = [max(0.0, float(c)) for c in counts]
    except (TypeError, ValueError):
        return ""
    peak = max(nums) if nums else 0.0
    if peak <= 0:
        return _SPARK[0] * len(nums)
    return "".join(_SPARK[min(7, int((c / peak) * 7.99))] for c in nums)


def fmt(value: Any, limit: int = 100) -> str:
    if isinstance(value, bool) or isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        text = value.replace("\n", " ").strip()
        return text[:limit] + ("…" if len(text) > limit else "")
    if isinstance(value, dict):
        return f"dict({len(value)} keys)"
    if isinstance(value, (list, tuple)):
        return f"list({len(value)} items)"
    if value is None:
        return "—"
    return str(value)[:limit]


def _header(icon: str, title: str, subtitle: str = "") -> list[str]:
    lines = [f"## {icon} {title}"]
    if subtitle:
        lines.append(f"*{subtitle}*")
    lines.append("")
    return lines


def _footer(claim: str) -> list[str]:
    return ["", f"> 🛡️ {claim}" if claim else ""]


def _chip(label: str, tone: str = "neutral") -> str:
    tone_icon = {"good": "🟢", "warn": "🟡", "bad": "🔴", "neutral": "⚪", "accent": "🔵"}.get(tone, "⚪")
    return f"`{tone_icon} {label}`"


# ── cards ───────────────────────────────────────────────────────────────────

def status_card(payload: dict[str, Any]) -> str:
    lines = _header("🧭", "SIPS Status", "homebase control-plane inspection")
    status = payload.get("status", "unknown")
    lines.append(f"**Health** {glyph(status)} `{status}`")
    raw_manifest = payload.get("manifest")
    manifest: dict[str, Any] = dict(raw_manifest) if isinstance(raw_manifest, dict) else {}
    lines.append(f"**Plugin** `{manifest.get('name', '?')}` v`{manifest.get('version', '?')}`")
    surfaces = payload.get("surfaces") or {}
    counts = {key: len(value) for key, value in surfaces.items() if isinstance(value, list)}
    if counts:
        lines.append("")
        lines.append("| Surface | Count | |---|---|")
        lines = [line for line in lines]  # keep; table built below instead
        lines = lines[:-2]
        lines.append("")
        lines.append("**Capability footprint**")
        peak = max(counts.values()) if counts else 1
        for key, value in sorted(counts.items(), key=lambda kv: -kv[1]):
            lines.append(f"- {bar_of_max(value, list(counts.values()))} **{key.replace('_', ' ')}** `{value}`")
    proof = payload.get("proof_layers") or {}
    if proof:
        lines.append("")
        lines.append("**Proof layers**")
        ready = {"inspected", "active", "done", "verified", "connected", "ready", "healthy", "ok", "source_present"}
        good = sum(1 for v in proof.values() if str(v).lower() in ready)
        lines.append(f"- {bar(good, len(proof))} ready `{good}/{len(proof)}`")
        for key, value in proof.items():
            lines.append(f"  - {glyph('ok' if str(value).lower() in ready else 'pending')} `{key}` — `{value}`")
    lifecycle = payload.get("lifecycle") or {}
    if lifecycle.get("available"):
        lines.append("")
        lines.append(f"**Lifecycle** `{lifecycle.get('window_events', 0)}` hook events in window")
        tool_rows = lifecycle.get("tools") or []
        totals = [row.get("total", 0) for row in tool_rows]
        for row in tool_rows[:5]:
            issues = row.get("issues") or 0
            suffix = f" · 🔴 {issues}" if issues else ""
            lines.append(f"- {bar_of_max(row.get('total', 0), totals)} `{row['tool']}` `{row.get('total', 0)}`{suffix}")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def routes_card(payload: dict[str, Any]) -> str:
    routes = payload.get("routes") or []
    lines = _header("🚏", "SIPS Routes", "command → tool → fallback mapping")
    if routes:
        lines.append("| Route | MCP tool | Fallback |")
        lines.append("|---|---|---|")
        for item in routes[:20]:
            if not isinstance(item, dict):
                continue
            lines.append(f"| `{item.get('route', '?')}` | `{item.get('mcp_tool', '?')}` | `{item.get('fallback', '—')}` |")
    else:
        lines.append("*No routes registered.*")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def recall_card(payload: dict[str, Any]) -> str:
    lines = _header("🧠", "SIPS Recall", "scoped Memory Fabric search")
    records = payload.get("records") or []
    if not records:
        lines.append("*No scoped lessons matched this query — the fabric stays quiet rather than guessing.*")
        lines.extend(_footer(payload.get("claim_boundary", "")))
        return "\n".join(lines).rstrip() + "\n"
    failures = [r for r in records if "failure" in (r.get("tags") or [])]
    successes = [r for r in records if r not in failures]
    if failures:
        lines.append(f"### ⚠️ Prior failures first ({len(failures)})")
        lines.append("")
        for rec in failures[:4]:
            lines.append(f"**🔴 {rec.get('title', 'untitled')}** · `{rec.get('tier', '?')}` conf `{rec.get('confidence', '?')}`")
            body = (rec.get("body") or "").strip().replace("\n", " ")[:220]
            lines.append(f"↳ {body}")
            lines.append("")
    if successes:
        lines.append(f"### ✅ Prior successes ({len(successes)})")
        lines.append("")
        for rec in successes[:6]:
            conf = rec.get("confidence") or "medium"
            tone = "🟢" if conf == "high" else "⚪"
            lines.append(f"**{tone} {rec.get('title', 'untitled')}** · `{rec.get('tier', '?')}` conf `{conf}`")
            body = (rec.get("body") or "").strip().replace("\n", " ")[:200]
            lines.append(f"↳ {body}")
            lines.append("")
    lines.append("> 💡 Recall is advisory — verify against the live repo before relying on a lesson.")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def goal_card(payload: dict[str, Any]) -> str:
    lines = _header("🎯", "SIPS Goal", "persisted loop state")
    if not payload.get("available"):
        lines.append("*No active goal — start one with `/goal <objective>` or `/selfloop start`.*")
        return "\n".join(lines).rstrip() + "\n"
    status = payload.get("status", "unknown")
    lines.append(f"**State** {glyph(status)} `{status}` · mode `{payload.get('mode', 'legacy')}`")
    lines.append(f"**Objective** {fmt(payload.get('objective', ''), 160)}")
    subtasks = payload.get("subtasks") or {}
    total, done = subtasks.get("total", 0), subtasks.get("done", 0)
    lines.append("")
    lines.append(f"**Subtasks** `{done}/{total}` {bar(done, total)}")
    failed = subtasks.get("failed", 0)
    if failed:
        lines.append(f"- 🔴 `{failed}` failed")
    if payload.get("current_subtask"):
        lines.append(f"**Next up** ▶️ {fmt(payload.get('current_subtask'), 160)}")
    turns, cycles = payload.get("turn_count", 0), payload.get("cycle_count", 0)
    plateau = payload.get("plateau_streak", 0)
    stats = f"`{turns}` turns · `{cycles}` cycles"
    if plateau:
        stats += f" · 🟡 plateau `{plateau}`"
    lines.append(f"**Loop** {stats}")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def verify_card(payload: dict[str, Any]) -> str:
    lines = _header("🛡️", "SIPS Verify", "source + manifest validation")
    status = payload.get("status", "unknown")
    lines.append(f"**Result** {glyph(status)} `{status}`")
    receipts = payload.get("receipts") or []
    if receipts:
        ok = sum(1 for r in receipts if isinstance(r, dict) and r.get("ok"))
        lines.append("")
        lines.append(f"**Receipts** `{ok}/{len(receipts)}` {bar(ok, len(receipts))}")
        for item in receipts[:12]:
            if not isinstance(item, dict):
                continue
            label = item.get("label") or "receipt"
            mark = glyph("ok" if item.get("ok") else "failed")
            rc = item.get("returncode")
            lines.append(f"- {mark} `{label}` rc `{rc}`")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def record_card(payload: dict[str, Any]) -> str:
    lines = _header("📝", "SIPS Record", "Memory Fabric write receipt")
    if payload.get("ok") is False:
        lines.append(f"🔴 **Not recorded** — {fmt(payload.get('error', 'unknown error'), 160)}")
        lines.extend(_footer(payload.get("claim_boundary", "")))
        return "\n".join(lines).rstrip() + "\n"
    raw_record = payload.get("record")
    record: dict[str, Any] = dict(raw_record) if isinstance(raw_record, dict) else {}
    title = record.get("title") or payload.get("title") or "learning"
    lines.append(f"🟢 **Recorded** `{fmt(title, 80)}`")
    meta = {
        "tier": record.get("tier") or payload.get("tier"),
        "confidence": record.get("confidence") or payload.get("confidence"),
        "status": record.get("status") or payload.get("status"),
    }
    chips = [f"`{key}: {val}`" for key, val in meta.items() if val]
    if chips:
        lines.append(" ".join(chips))
    record_id = record.get("id") or payload.get("id")
    if record_id:
        lines.append(f"**id** `{record_id}`")
    lines.extend(_footer(payload.get("claim_boundary", "") or "A recorded lesson is candidate knowledge; it does not become practice until independently verified."))
    return "\n".join(lines).rstrip() + "\n"


def lifecycle_card(payload: dict[str, Any]) -> str:
    """Hook-stream lens: tool bars, session rollup, denials, activity sparkline."""
    lines = _header("📡", "SIPS Lifecycle", "agent hook stream, metadata only")
    if not payload.get("available"):
        lines.append("*No hook stream available yet — it fills as SIPS lifecycle hooks observe tool calls and sessions.*")
        lines.extend(_footer(payload.get("claim_boundary", "")))
        return "\n".join(lines).rstrip() + "\n"
    lines.append(f"**Window** `{payload.get('window_events', 0)}` events (of ~`{payload.get('total_events', 0)}` total)")
    tool_rows = payload.get("tools") or []
    totals = [row.get("total", 0) for row in tool_rows]
    if tool_rows:
        lines.append("")
        lines.append("**Tool calls**")
        for row in tool_rows:
            issues = (row.get("error") or 0) + (row.get("denied") or 0)
            tone = "🔴" if issues else "🟢"
            track = bar_of_max(row.get("total", 0), totals)
            suffix = f" · 🔴 `{issues}` issues" if issues else ""
            lines.append(f"- {track} `{row['tool']}` `{row.get('total', 0)}` {tone}{suffix}")
    sessions = payload.get("sessions") or []
    if sessions:
        lines.append("")
        lines.append("**Recent sessions**")
        peak = max((s.get("events", 0) for s in sessions), default=1) or 1
        for session in sessions[:6]:
            track = bar(session.get("events", 0), peak)
            lines.append(f"- {track} `{str(session.get('session_id', ''))[:12]}…` `{session.get('events', 0)}` events · `{session.get('tool_count', 0)}` tools")
    denials = payload.get("denials") or []
    if denials:
        lines.append("")
        lines.append(f"**Denied / blocked** 🔴 `{len(denials)}`")
        for denial in denials[:5]:
            lines.append(f"- 🔴 `{denial.get('tool', '?')}` at `{denial.get('ts', '?')}`")
    histogram = payload.get("histogram") or []
    if histogram:
        spark = sparkline([col.get("events", 0) for col in histogram])
        peak_col = max(histogram, key=lambda col: col.get("events", 0))
        lines.append("")
        lines.append(f"**Activity (UTC)** `{spark}` peak `{peak_col.get('hour')} ×{peak_col.get('events')}`")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def freshness_card(payload: dict[str, Any]) -> str:
    """MCP freshness: overall verdict + per-layer glyph rows."""
    lines = _header("⟳", "SIPS MCP Freshness", "source → cache → config → task surface")
    status = payload.get("status", payload.get("overall_status", "unknown"))
    lines.append(f"**Verdict** {glyph(status)} `{status}`")
    checks = payload.get("checks") or {}
    if checks:
        lines.append("")
        lines.append("**Layer checks**")
        for key, value in checks.items():
            lines.append(f"- {glyph('ok' if value in (True, 'ok', 'passed', 'fresh') else value)} `{key}` — `{fmt(value, 60)}`")
    task = payload.get("task_exposure") if isinstance(payload.get("task_exposure"), dict) else {}
    if task:
        lines.append("")
        present = len(task.get("present_tools") or [])
        expected = len(payload.get("tools") or [])
        lines.append(f"**Task surface** `{present}/{expected}` tools {bar(present, expected or 1)}")
        lines.append(f"- inventory complete: {glyph('ok' if task.get('inventory_complete') else 'pending')} `{task.get('inventory_complete', False)}`")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def audit_card(payload: dict[str, Any]) -> str:
    """Host audit: hook trust/enablement at a glance."""
    lines = _header("🩺", "SIPS Host Audit", "live hook wiring and trust")
    status = payload.get("status", "unknown")
    lines.append(f"**Result** {glyph(status)} `{status}`")
    runtime = payload.get("runtime_hooks") if isinstance(payload.get("runtime_hooks"), dict) else {}
    if runtime:
        hooks = [item for item in (runtime.get("hooks") or []) if isinstance(item, dict)]
        observed = runtime.get("observed_count", 0)
        expected = runtime.get("expected_count", 0)
        lines.append("")
        lines.append(f"**Hook coverage** `{observed}/{expected}` {bar(observed, expected or 1)}")
        disabled = sum(item.get("enabled") is not True for item in hooks)
        untrusted = sum(item.get("trustStatus") != "trusted" for item in hooks)
        unhashed = sum(not item.get("currentHash") for item in hooks)
        if disabled:
            lines.append(f"- 🟡 `{disabled}` disabled")
        if untrusted:
            lines.append(f"- 🔴 `{untrusted}` untrusted")
        if unhashed:
            lines.append(f"- 🟡 `{unhashed}` unhashed")
        if not (disabled or untrusted or unhashed):
            lines.append(f"- 🟢 all `{len(hooks)}` hooks enabled, trusted, hashed")
        if runtime.get("error"):
            lines.append(f"- 🔴 probe error: `{fmt(runtime['error'], 80)}`")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def selfloop_card(payload: dict[str, Any]) -> str:
    lines = _header("🔁", "SIPS Selfloop", "persistent improvement loop")
    raw_state = payload.get("state")
    state: dict[str, Any] = dict(raw_state) if isinstance(raw_state, dict) else {}
    active = bool(payload.get("active", state.get("status") == "active"))
    status = state.get("status") or ("active" if active else "idle")
    lines.append(f"**Loop** {glyph(status)} `{status}`")
    objective = state.get("objective")
    if objective:
        lines.append(f"**Objective** {fmt(objective, 180)}")
    focus = state.get("focus")
    if focus:
        lines.append(f"**Focus** `{fmt(focus, 60)}`")
    mode = state.get("mode")
    if mode:
        lines.append(f"**Mode** `{mode}`")
    turns, cycles = state.get("turnCount", 0), state.get("cycleCount", 0)
    plateau = state.get("plateauStreak", 0)
    lines.append(f"**Progress** `{turns}` turns · `{cycles}` cycles" + (f" · 🟡 plateau `{plateau}`" if plateau else ""))
    cycle = state.get("cycle") if isinstance(state.get("cycle"), dict) else {}
    if cycle:
        outcome = cycle.get("outcome", "?")
        lines.append(f"**Current cycle** `{cycle.get('cycle', '?')}` → {glyph(outcome)} `{outcome}`")
        summary = cycle.get("summary")
        if summary:
            lines.append(f"↳ {fmt(summary, 200)}")
    history = state.get("cycleHistory") if isinstance(state.get("cycleHistory"), list) else []
    if history:
        outcomes = [entry.get("outcome", "?") for entry in history[-12:] if isinstance(entry, dict)]
        spark = "".join({"improved": "▇", "plateau": "▅", "blocked": "▂"}.get(str(o), "▃") for o in outcomes)
        improved = sum(1 for o in outcomes if o == "improved")
        lines.append(f"**Cycle trend** `{spark}` improved `{improved}/{len(outcomes)}`")
    lines.extend(_footer(payload.get("claim_boundary", "") or "Selfloop state is a bounded projection; runtime events remain authoritative."))
    return "\n".join(lines).rstrip() + "\n"
