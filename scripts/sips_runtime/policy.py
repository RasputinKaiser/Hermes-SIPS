"""PolicyService — tool effect classification and approval outcomes.

Classifies tool calls into effect classes and maps each class to a default
policy outcome (auto / approval / block). High-impact effects require host
approval; critical effects are blocked unless explicitly approved.

The taxonomy is intentionally coarse — the goal is to prevent bypass via
equivalent phrasing, not to catalog every action.
"""
from __future__ import annotations

from typing import Any


class Effect:
    READ = "read"
    LOCAL_WRITE = "local_write"
    REPO_HISTORY_WRITE = "repo_history_write"
    EXTERNAL_WRITE = "external_write"
    CREDENTIAL_ACCESS = "credential_access"
    PRIVILEGED_EXECUTION = "privileged_execution"
    DESTRUCTIVE_LOCAL = "destructive_local"
    DESTRUCTIVE_REMOTE = "destructive_remote"
    FINANCIAL = "financial"


class Outcome:
    AUTO = "auto"
    APPROVAL = "approval"
    BLOCK = "block"


# Default policy: effect class -> outcome.
DEFAULT_POLICY: dict[str, str] = {
    Effect.READ: Outcome.AUTO,
    Effect.LOCAL_WRITE: Outcome.AUTO,
    Effect.REPO_HISTORY_WRITE: Outcome.APPROVAL,
    Effect.EXTERNAL_WRITE: Outcome.APPROVAL,
    Effect.CREDENTIAL_ACCESS: Outcome.BLOCK,
    Effect.PRIVILEGED_EXECUTION: Outcome.APPROVAL,
    Effect.DESTRUCTIVE_LOCAL: Outcome.BLOCK,
    Effect.DESTRUCTIVE_REMOTE: Outcome.BLOCK,
    Effect.FINANCIAL: Outcome.BLOCK,
}

# Tool name patterns mapped to effect classes.
TOOL_EFFECTS: dict[str, str] = {
    "Read": Effect.READ,
    "Glob": Effect.READ,
    "Grep": Effect.READ,
    "Edit": Effect.LOCAL_WRITE,
    "Write": Effect.LOCAL_WRITE,
    "MultiEdit": Effect.LOCAL_WRITE,
    "Delete": Effect.DESTRUCTIVE_LOCAL,
    "Bash": Effect.PRIVILEGED_EXECUTION,
    "Terminal": Effect.PRIVILEGED_EXECUTION,
    "WebFetch": Effect.READ,
    "WebSearch": Effect.READ,
    "GitPush": Effect.EXTERNAL_WRITE,
    "GitCommit": Effect.REPO_HISTORY_WRITE,
    "GitReset": Effect.REPO_HISTORY_WRITE,
}


def classify_effect(tool_name: str, tool_input: dict[str, Any] | None = None) -> str:
    """Classify a tool call into an effect class.

    Falls back to PRIVILEGED_EXECUTION for unknown tools — unknown tools should
    be treated as potentially high-impact until classified.
    """
    name = (tool_name or "").strip()
    if name in TOOL_EFFECTS:
        return TOOL_EFFECTS[name]
    tool_input = tool_input or {}
    # Heuristic: file-write tools
    if name in {"FileWrite", "FileEdit", "WriteFile"}:
        return Effect.LOCAL_WRITE
    if name in {"Rm", "Remove", "Unlink"}:
        return Effect.DESTRUCTIVE_LOCAL
    return Effect.PRIVILEGED_EXECUTION


def policy_for(effect: str, policy_overrides: dict[str, str] | None = None) -> str:
    """Return the default policy outcome for an effect class."""
    overrides = policy_overrides or {}
    if effect in overrides:
        return overrides[effect]
    return DEFAULT_POLICY.get(effect, Outcome.APPROVAL)


def decide(
    tool_name: str,
    tool_input: dict[str, Any] | None = None,
    *,
    policy_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Classify and decide a tool call."""
    effect = classify_effect(tool_name, tool_input)
    outcome = policy_for(effect, policy_overrides)
    return {
        "tool_name": tool_name,
        "effect": effect,
        "outcome": outcome,
        "requires_approval": outcome == Outcome.APPROVAL,
        "blocked": outcome == Outcome.BLOCK,
        "reason": f"{effect}:{outcome}",
    }
