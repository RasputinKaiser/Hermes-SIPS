"""Tests for context-lens cards vol.2 (repro / tool-factory / perception)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import context_lens_cards2 as c2  # noqa: E402


def test_repro_card_renders_symptoms_plan_verification() -> None:
    payload = {
        "goal": "flaky water test",
        "symptoms": ["test_river fails 1/10 on M1"],
        "repro_steps": ["Confirm the symptom", "Run smallest validation", "Rerun after fix"],
        "verification_commands": ["pytest -k river", "python3 scripts/validate_v2.py"],
        "claim_boundary": "plan only",
    }
    card = c2.execution_repro_card(payload)
    assert "🧪 Execution Repro" in card
    assert "goal: `flaky water test`" in card
    assert "🔴 test_river fails 1/10 on M1" in card
    assert "1. Confirm the symptom" in card and "3. Rerun after fix" in card
    assert "pytest -k river" in card
    assert "🛡️ plan only" in card


def test_repro_card_empty_state() -> None:
    card = c2.execution_repro_card({"goal": "g", "repro_steps": [], "verification_commands": [], "claim_boundary": "cb"})
    assert "No repro plan generated" in card


def test_tool_factory_card_verdict_and_next() -> None:
    payload = {
        "desired_tool": "flaky-tracker",
        "decision": "reuse_or_improve",
        "candidate_scripts": ["run_tests.py", "task_outcome_tracker.py"],
        "next_command": "python3 scripts/tool_factory.py validate run_tests",
        "claim_boundary": "advisory",
    }
    card = c2.tool_factory_card(payload)
    assert "🏭 Tool Factory" in card
    assert "🟢 `reuse_or_improve`" in card
    assert "📄 `run_tests.py`" in card
    assert "**Next** ```python3 scripts/tool_factory.py validate run_tests```" in card


def test_tool_factory_card_new_decision_tone() -> None:
    payload = {"desired_tool": "new-thing", "decision": "create_new", "candidate_scripts": [], "next_command": "x", "claim_boundary": ""}
    card = c2.tool_factory_card(payload)
    assert "🔵 `create_new`" in card


def test_perception_plan_card_checks_and_proof() -> None:
    payload = {
        "surface": "browser",
        "target": "localhost:5184",
        "expected_visible_state": ["water renders", "no console errors"],
        "checks": ["capture screenshot", "check console errors"],
        "proof_layers": {"visible_state": "required", "runtime_interaction": "optional"},
        "claim_boundary": "screenshot is bounded proof",
    }
    card = c2.perception_plan_card(payload)
    assert "🌍 Perception Plan" in card
    assert "browser → `localhost:5184`" in card
    assert "✅ water renders" in card
    assert "1. capture screenshot" in card and "2. check console errors" in card
    assert "`visible_state`" in card and "`runtime_interaction`" in card
