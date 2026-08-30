"""Context-lens cards: rich chat renderers for context_scan + distill_context.

Both tools answer "how do I touch this codebase without blowing the context
budget" — scan finds oversized files + the exact bounded-read command to run
instead; distill returns source-linked excerpts. The raw dicts are already
machine-friendly; these renderers make them scannable at a glance.
"""

from __future__ import annotations

from typing import Any

from sips_chat_cards import _footer, _header, bar, tool_icon


def _fmt_bytes(n: Any) -> str:
    try:
        v = float(n or 0)
    except (TypeError, ValueError):
        v = 0.0
    if v >= 1_048_576:
        return f"{v / 1_048_576:.1f}MB"
    if v >= 1024:
        return f"{v / 1024:.0f}KB"
    return f"{int(v)}B"


def context_scan_card(payload: dict[str, Any]) -> str:
    """Oversized-file risks with estimated token cost + bounded-read commands."""
    lines = _header("📦", "Context Scan", "oversized files + bounded-read commands")
    risks = payload.get("risks") or []
    if not risks:
        lines.append("*No oversized files matched — context is clean.*")
        lines.extend(_footer(payload.get("claim_boundary", "")))
        return "\n".join(lines).rstrip() + "\n"

    lines.append(
        f"**{payload.get('risk_count', len(risks))} risks** under `{payload.get('max_bytes', '?')}` cap · "
        f"est total `{_fmt_bytes(sum(r.get('bytes', 0) for r in risks))}`"
    )
    lines.append("")
    peak = max((r.get("estimated_tokens") or 0 for r in risks), default=1) or 1
    for r in risks[:8]:
        tokens = r.get("estimated_tokens") or 0
        tone = "🔴" if tokens > 25_000 else ("🟡" if tokens > 10_000 else "🟢")
        cmd = str(r.get("bounded_read") or "").strip()
        lines.append(
            f"- {bar(tokens, peak)} {tone} `{_fmt_bytes(r.get('bytes'))}` ≈`{tokens}` tok — `{r.get('path', '?')}`"
        )
        if cmd:
            lines.append(f"  ↳ bounded read: `{cmd}`")
    shown = len(risks[:8])
    if len(risks) > shown:
        lines.append(f"- … {len(risks) - shown} more")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def distill_card(payload: dict[str, Any]) -> str:
    """Distilled source-linked excerpts: which file, which query, what came out."""
    sources = payload.get("sources") or []
    lines = _header("💧", "Context Distill", "bounded source-linked excerpts")
    query = payload.get("query")
    if query:
        lines.append(f"**Query** `{query}`")
    if not sources:
        lines.append("*No sources distilled.*")
        lines.extend(_footer(payload.get("claim_boundary", "")))
        return "\n".join(lines).rstrip() + "\n"

    for src in sources[:6]:
        if not isinstance(src, dict):
            continue
        path = str(src.get("input") or src.get("path") or "?")
        icon = tool_icon("read_file")
        excerpt = (src.get("excerpt") or src.get("content") or "").strip()
        matched = src.get("matched_lines")
        lines.append("")
        lines.append(f"{icon} `{path}`" + (f" — `{len(matched)} matched lines`" if isinstance(matched, list) else ""))
        if excerpt:
            body = excerpt.replace("\n", " ⏎ ")
            shown = body[:280]
            lines.append(f"  > {shown}{'…' if len(body) > 280 else ''}")
    if len(sources) > 6:
        lines.append(f"- … {len(sources) - 6} more sources")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"
