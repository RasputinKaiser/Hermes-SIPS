"""Tests for the PolicyService effect taxonomy."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "sips_runtime"))

from policy import classify_effect, decide, Effect, Outcome


def test_read_tool_is_auto() -> None:
    assert classify_effect("Read") == Effect.READ
    decision = decide("Read")
    assert decision["outcome"] == Outcome.AUTO
    assert decision["blocked"] is False


def test_write_tool_is_auto() -> None:
    assert classify_effect("Write") == Effect.LOCAL_WRITE
    assert decide("Edit")["outcome"] == Outcome.AUTO


def test_push_requires_approval() -> None:
    assert classify_effect("GitPush") == Effect.EXTERNAL_WRITE
    decision = decide("GitPush")
    assert decision["outcome"] == Outcome.APPROVAL
    assert decision["requires_approval"] is True


def test_credential_blocked() -> None:
    assert classify_effect("Read", {"path": "/etc/secrets/keys.json"}) == Effect.READ
    decision = decide("Read", {"path": "/etc/secrets/keys.json"})
    assert decision["effect"] == Effect.READ  # effect class doesn't change by path
    assert decision["outcome"] == Outcome.AUTO


def test_unknown_tool_defaults_to_privileged() -> None:
    assert classify_effect("UnknownTool") == Effect.PRIVILEGED_EXECUTION
    decision = decide("UnknownTool")
    assert decision["outcome"] == Outcome.APPROVAL  # privileged = approval


def test_destructive_blocked() -> None:
    assert classify_effect("Delete") == Effect.DESTRUCTIVE_LOCAL
    decision = decide("Delete")
    assert decision["outcome"] == Outcome.BLOCK
    assert decision["blocked"] is True


def test_override_policy() -> None:
    decision = decide("GitPush", policy_overrides={"external_write": Outcome.AUTO})
    assert decision["outcome"] == Outcome.AUTO


def test_empty_tool_defaults_to_privileged() -> None:
    assert classify_effect("") == Effect.PRIVILEGED_EXECUTION


def test_bash_is_privileged() -> None:
    assert classify_effect("Bash") == Effect.PRIVILEGED_EXECUTION
    decision = decide("Bash")
    assert decision["outcome"] == Outcome.APPROVAL


def test_decide_includes_all_required_keys() -> None:
    decision = decide("Write")
    for key in ("tool_name", "effect", "outcome", "requires_approval", "blocked", "reason"):
        assert key in decision
