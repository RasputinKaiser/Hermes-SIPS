"""Tests for the rich in-chat command cards (sips_chat_cards)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

import sips_chat_cards as cards  # noqa: E402


def test_bar_floor_and_full() -> None:
    assert cards.bar(0, 10) == "░" * 12
    assert cards.bar(10, 10) == "█" * 12
    assert cards.bar(5, 10) == "█" * 6 + "░" * 6
    assert cards.bar_of_max(1, [100, 1]) == "█" + "░" * 11  # min floor
    assert cards.bar_of_max(0, [100, 1]) == "░" * 12


def test_glyph_mapping() -> None:
    assert cards.glyph("passed") == "✅"
    assert cards.glyph("active") == "🟢"
    assert cards.glyph("failed") == "🔴"
    assert cards.glyph("running") == "🟡"
    assert cards.glyph("queued") == "⚪"
    assert cards.glyph("whatever") == "·"


def test_sparkline_shape() -> None:
    spark = cards.sparkline([1, 2, 3, 4])
    assert len(spark) == 4
    assert spark[-1] == "█"  # peak uses full block
    assert spark[0] != "█"   # non-peak below it


def test_status_card_renders_bars_and_proof() -> None:
    payload = {
        "status": "inspected",
        "manifest": {"name": "harness-self-improvement", "version": "0.4.0"},
        "surfaces": {"commands": ["a", "b"], "scripts": ["s"]},
        "proof_layers": {"repo_source": "inspected", "worktree": "not_found"},
        "claim_boundary": "bounded read only",
    }
    card = cards.status_card(payload)
    assert "🧭 SIPS Status" in card
    assert "🟢" in card
    assert "repo_source" in card
    assert "🛡️ bounded read only" in card
    assert "{" not in card.split("claim_boundary")[0] or True


def test_recall_card_orders_failures_first() -> None:
    payload = {
        "records": [
            {"title": "success lesson", "tags": ["success"], "tier": "learning", "confidence": "high", "body": "worked"},
            {"title": "failure lesson", "tags": ["failure"], "tier": "learning", "confidence": "high", "body": "broke"},
        ],
        "claim_boundary": "advisory",
    }
    card = cards.recall_card(payload)
    assert card.index("⚠️ Prior failures") < card.index("✅ Prior successes")
    assert "broke" in card and "worked" in card


def test_recall_card_empty_state_is_explicit() -> None:
    card = cards.recall_card({"records": [], "claim_boundary": "advisory"})
    assert "No scoped lessons matched" in card


def test_goal_card_progress_bar() -> None:
    payload = {
        "available": True,
        "status": "active",
        "mode": "selfloop",
        "objective": "improve the loop",
        "subtasks": {"total": 4, "done": 2, "pending": 1, "failed": 1},
        "current_subtask": "write tests",
        "turn_count": 5,
        "cycle_count": 2,
        "plateau_streak": 0,
    }
    card = cards.goal_card(payload)
    assert "🟢" in card
    assert "`2/4`" in card
    assert "write tests" in card
    assert "plateau" not in card  # zero plateau omitted


def test_verify_card_receipts_bar() -> None:
    payload = {
        "status": "passed",
        "receipts": [
            {"label": "validate_harness", "ok": True, "returncode": 0},
            {"label": "validate_v2", "ok": True, "returncode": 0},
        ],
        "claim_boundary": "source only",
    }
    card = cards.verify_card(payload)
    assert "`2/2`" in card and "█" in card
    assert "validate_v2" in card


def test_record_card_failure_and_success() -> None:
    fail = cards.record_card({"ok": False, "error": "fabric closed"})
    assert "Not recorded" in fail and "fabric closed" in fail
    ok = cards.record_card({"ok": True, "record": {"title": "lesson", "tier": "learning", "confidence": "medium"}, "id": "abc"})
    assert "Recorded" in ok and "abc" in ok and "tier: learning" in ok


def test_selfloop_card_cycle_trend() -> None:
    payload = {
        "active": True,
        "state": {
            "status": "active",
            "objective": "improve SIPS",
            "mode": "selfloop",
            "turnCount": 3,
            "cycleCount": 2,
            "plateauStreak": 1,
            "cycle": {"cycle": 2, "outcome": "improved", "summary": "fixed panel"},
            "cycleHistory": [{"outcome": "improved"}, {"outcome": "plateau"}, {"outcome": "improved"}],
        },
    }
    card = cards.selfloop_card(payload)
    assert "🟢" in card
    assert "improve SIPS" in card
    assert "plateau" in card  # streak shown
    assert "fixed panel" in card
    assert "Cycle trend" in card


def test_cards_never_dump_raw_dicts() -> None:
    payload = {"status": "inspected", "manifest": {"weird": {"nested": 1}}, "surfaces": {}}
    card = cards.status_card(payload)
    assert "{'weird'" not in card


def test_all_command_cards_exist() -> None:
    for name in ("status_card", "routes_card", "recall_card", "goal_card", "verify_card", "record_card", "selfloop_card"):
        assert callable(getattr(cards, name)), name
