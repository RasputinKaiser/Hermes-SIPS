"""Context-lens cards, volume 2: execution_repro + tool_factory + perception.

Same family as context_lens_cards.py — rich chat renderers for MCP tool
payloads the agent consumes raw today. Decision-shaped tools get verdict
headers; plan-shaped tools get numbered step blocks.
"""

from __future__ import annotations

from typing import Any

from sips_chat_cards import _footer, _header


def _decision_tone(decision: Any) -> str:
    text = str(decision or "").lower()
    if "reuse" in text or "improve" in text:
        return "🟢"
    if "new" in text or "create" in text or "scaffold" in text:
        return "🔵"
    if "block" in text or "invalid" in text:
        return "🔴"
    return "⚪"


def execution_repro_card(payload: dict[str, Any]) -> str:
    """Repro plan: symptoms → numbered steps → verification commands."""
    goal = str(payload.get("goal") or "?")[:80]
    lines = _header("🧪", "Execution Repro", f"goal: `{goal}`")
    steps = payload.get("repro_steps") or []
    commands = payload.get("verification_commands") or []
    symptoms = payload.get("symptoms") or []
    if not steps and not commands:
        lines.append("*No repro plan generated.*")
        lines.extend(_footer(payload.get("claim_boundary", "")))
        return "\n".join(lines).rstrip() + "\n"

    if symptoms:
        lines.append("**Symptoms**")
        for s in symptoms[:4]:
            lines.append(f"- 🔴 {str(s)[:140]}")
    if steps:
        lines.append("")
        lines.append("**Plan**")
        for i, step in enumerate(steps[:8], 1):
            lines.append(f"{i}. {str(step)[:160]}")
    if commands:
        lines.append("")
        lines.append("**Verification**")
        for cmd in commands[:5]:
            lines.append(f"- ```{str(cmd)[:160]}```" if not str(cmd).startswith("`") else f"- {cmd}")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def tool_factory_card(payload: dict[str, Any]) -> str:
    """Tool-factory verdict: reuse/improve/new with candidates + next command."""
    decision = payload.get("decision")
    tone = _decision_tone(decision)
    desired = str(payload.get("desired_tool") or "?")[:50]
    lines = _header("🏭", "Tool Factory", f"desired: `{desired}`")
    lines.append(f"**Decision** {tone} `{decision or 'unknown'}`")

    candidates = payload.get("candidate_scripts") or []
    if candidates:
        lines.append("")
        lines.append("**Candidates**")
        for c in candidates[:6]:
            lines.append(f"- 📄 `{str(c)[:80]}`")

    next_command = str(payload.get("next_command") or "").strip()
    if next_command:
        lines.append("")
        lines.append(f"**Next** ```{next_command[:140]}```")
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"


def perception_plan_card(payload: dict[str, Any]) -> str:
    """Perception plan: surface + target + expected state + ordered checks."""
    surface = str(payload.get("surface") or "?")
    target = str(payload.get("target") or "?")[:60]
    surface_icon = {"browser": "🌍", "screenshot": "📸", "ui": "🖥", "app": "🖥", "file": "📄"}.get(surface, "👁")
    lines = _header(surface_icon, "Perception Plan", f"{surface} → `{target}`")

    expected = payload.get("expected_visible_state") or []
    if expected:
        lines.append("**Expected visible state**")
        for item in expected[:6]:
            lines.append(f"- ✅ {str(item)[:120]}")

    checks = payload.get("checks") or []
    if checks:
        lines.append("")
        lines.append("**Checks (in order)**")
        for i, check in enumerate(checks[:10], 1):
            lines.append(f"{i}. {str(check)[:140]}")

    proof = payload.get("proof_layers")
    if isinstance(proof, dict) and proof:
        lines.append("")
        lines.append("**Proof layers** " + " ".join(f"`{k}`" for k in list(proof)[:5]))
    lines.extend(_footer(payload.get("claim_boundary", "")))
    return "\n".join(lines).rstrip() + "\n"
