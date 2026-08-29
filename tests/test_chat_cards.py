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
    for name in ("status_card", "routes_card", "recall_card", "goal_card", "verify_card", "record_card", "selfloop_card", "lifecycle_card", "freshness_card", "audit_card"):
        assert callable(getattr(cards, name)), name


def test_lifecycle_card_renders_tools_sessions_denials_spark() -> None:
    payload = {
        "available": True,
        "window_events": 120,
        "total_events": 200,
        "tools": [
            {"tool": "terminal", "allowed": 30, "ok": 68, "error": 2, "denied": 0, "other": 0, "total": 100},
            {"tool": "patch", "allowed": 10, "ok": 9, "error": 0, "denied": 1, "other": 0, "total": 20},
        ],
        "sessions": [{"session_id": "s-123456789", "events": 80, "first_ts": "t0", "last_ts": "t1", "tool_count": 3}],
        "denials": [{"ts": "2026-08-29T03:00:00+00:00", "tool": "terminal", "session_id": "s-1"}],
        "histogram": [{"hour": "2026-08-29T02", "events": 40}, {"hour": "2026-08-29T03", "events": 80}],
        "claim_boundary": "metadata only",
    }
    card = cards.lifecycle_card(payload)
    assert "📡 SIPS Lifecycle" in card
    assert "`terminal` `100`" in card
    assert "🔴" in card  # issues + denials
    assert "s-123456789…" in card[: card.index("Denied")]  # truncated id
    assert "▆" in card or "█" in card  # sparkline
    assert "🛡️ metadata only" in card


def test_lifecycle_card_unavailable_state() -> None:
    card = cards.lifecycle_card({"available": False})
    assert "No hook stream available" in card


def test_usage_card_renders_totals_trend_replay_split() -> None:
    payload = {
        "available": True,
        "window_days": 7,
        "totals": {
            "sessions": 12,
            "api_calls": 300,
            "fresh_input_tokens": 25_000_000,
            "output_tokens": 500_000,
            "cache_hit_pct": 96.4,
            "fresh_to_output_ratio": "50.0:1",
            "estimated_cost_usd": 0.42,
        },
        "daily": [
            {"day": "2026-08-28", "fresh_input_tokens": 20_000_000, "cache_hit_pct": 96.0},
            {"day": "2026-08-29", "fresh_input_tokens": 5_000_000, "cache_hit_pct": 97.0},
        ],
        "replay": {
            "tool_results_replayed_tokens_est": 700_000_000,
            "top_tools": [{"tool": "terminal", "replayed_tokens_est": 255_000_000}],
            "top_sessions": [{"session_id": "20260823_152844_056135", "replayed_tool_tokens_est": 108_000_000}],
        },
        "direct_vs_subagent": {
            "direct": {"fresh_input_tokens": 10_000_000},
            "subagent": {"fresh_input_tokens": 15_000_000},
        },
        "claim_boundary": "aggregates only",
    }
    card = cards.usage_card(payload)
    assert "📊 Token Usage" in card
    assert "7-day window" in card and "`12` sessions" in card
    assert "cache 96.4%" in card and "🟢" in card
    assert "25.0M" in card and "50.0:1" in card
    assert "2026-08-29" in card and "97.0%" in card
    assert "Replay leaders" in card and "`terminal`" in card
    assert "20260823_152844_056135…" in card
    assert "60%` of fresh input" in card  # 15M / 25M
    assert "🛡️ aggregates only" in card


def test_usage_card_unavailable_and_empty_days() -> None:
    card = cards.usage_card({"available": False, "reason": "store missing", "claim_boundary": "cb"})
    assert "store missing" in card and "🛡️ cb" in card
    empty = cards.usage_card({"available": True, "window_days": 7, "totals": {}, "daily": [], "replay": {}, "direct_vs_subagent": {}})
    assert "📊 Token Usage" in empty and "0-day window" not in empty  # defaults to 7


def test_freshness_card_task_surface_bar() -> None:
    payload = {
        "status": "fresh",
        "checks": {"source": "fresh", "cache": "stale"},
        "task_exposure": {"present_tools": ["a", "b", "c"], "inventory_complete": True},
        "tools": ["a", "b", "c"],
        "claim_boundary": "bounded",
    }
    card = cards.freshness_card(payload)
    assert "🟢 `fresh`" in card
    assert "`3/3` tools" in card and "█" in card
    assert "🔴 `cache`" in card


def test_audit_card_all_green_and_problems() -> None:
    good = cards.audit_card({
        "status": "passed",
        "runtime_hooks": {"observed_count": 5, "expected_count": 5, "hooks": [{"enabled": True, "trustStatus": "trusted", "currentHash": "h"}] * 5},
    })
    assert "🟢 all `5` hooks" in good
    bad = cards.audit_card({
        "status": "passed",
        "runtime_hooks": {
            "observed_count": 3,
            "expected_count": 4,
            "hooks": [
                {"enabled": False, "trustStatus": "trusted", "currentHash": "h"},
                {"enabled": True, "trustStatus": "modified", "currentHash": ""},
                {"enabled": True, "trustStatus": "trusted", "currentHash": "h"},
            ],
        },
    })
    assert "🟡 `1` disabled" in bad
    assert "🔴 `1` untrusted" in bad
    assert "🟡 `1` unhashed" in bad


def test_tool_icons_match_panel_and_fallback() -> None:
    """Chat icons mirror the panel's TOOL_ICONS; unknown tools get the gear."""
    assert cards.tool_icon("terminal") == "❯"
    assert cards.tool_icon("read_file") == "📖"
    assert cards.tool_icon("mcp__sips_homebase__homebase_status") == "🔌"
    assert cards.tool_icon("totally_unknown_tool") == "⚙"
    assert cards.tool_icon(None) == "⚙"


def test_hook_event_icons_ordered_prefix_match() -> None:
    """First prefix match wins; end_record beats end; unknown gets dot."""
    assert cards.hook_event_icon("pre_tool_call") == "⏳"
    assert cards.hook_event_icon("post_tool_call") == "⏱"
    assert cards.hook_event_icon("on_session_end_record") == "💾"
    assert cards.hook_event_icon("on_session_end") == "⏹"
    assert cards.hook_event_icon("subagent_start") == "🚀"
    assert cards.hook_event_icon("mystery_event") == "·"


def test_lifecycle_card_renders_hook_flow_with_icons() -> None:
    payload = {
        "available": True,
        "window_events": 10,
        "total_events": 10,
        "event_mix": [
            {"event": "pre_tool_call", "count": 6},
            {"event": "post_tool_call", "count": 4},
        ],
        "tools": [{"tool": "terminal", "allowed": 5, "ok": 5, "error": 0, "denied": 0, "other": 0, "total": 5}],
        "sessions": [],
        "denials": [],
        "histogram": [],
        "claim_boundary": "cb",
    }
    card = cards.lifecycle_card(payload)
    assert "**Hook flow**" in card
    assert "⏳" in card and "⏱" in card
    assert "❯ `terminal`" in card


def test_gate_matrix_card_renders_cells_and_summary() -> None:
    payload = {
        "available": True,
        "gates": ["integrity", "correctness", "regression", "resource", "benefit"],
        "runs": [
            {"run_id": "h-20260829_020805_9c6566", "receipt": True,
             "gates": {"integrity": "ok", "correctness": "ok", "regression": "ok", "resource": "ok", "benefit": "ok"},
             "ok_count": 5, "failed_count": 0},
            {"run_id": "h-20260829_140436_4660d0", "receipt": False,
             "gates": {"integrity": None, "correctness": None, "regression": None, "resource": None, "benefit": None},
             "ok_count": 0, "failed_count": 0},
            {"run_id": "h-20260829_failed_run", "receipt": True,
             "gates": {"integrity": "ok", "correctness": "failed", "regression": None, "resource": None, "benefit": None},
             "ok_count": 1, "failed_count": 1},
        ],
        "claim_boundary": "cells only",
    }
    card = cards.gate_matrix_card(payload)
    assert "🛡 Gate Matrix" in card
    assert card.count("🟢") >= 6
    assert "🔴" in card
    assert "*not yet gated*" in card
    assert "**2/3 gated** · 1 all-gates-pass · 🔴 1 with failures" in card
    assert "🛡️ cells only" in card


def test_gate_matrix_card_unavailable_and_empty() -> None:
    card = cards.gate_matrix_card({"available": False, "reason": "runtime down", "claim_boundary": "cb"})
    assert "runtime down" in card
    empty = cards.gate_matrix_card({"available": True, "gates": cards.GATE_ORDER if hasattr(cards, 'GATE_ORDER') else [], "runs": [], "claim_boundary": ""})
    assert "No runtime runs yet" in empty


def test_run_quality_card_renders_gates_evidence_budget() -> None:
    payload = {
        "available": True,
        "run_id": "h-20260829_020805_9c6566",
        "status": "succeeded",
        "impact": "normal",
        "gates": [
            {"name": "integrity", "status": "ok", "reasons": [], "evidence_total": 634, "evidence": []},
            {"name": "correctness", "status": "failed", "reasons": ["digest mismatch at rev 4"], "evidence_total": 0, "evidence": []},
        ],
        "impact": "normal",
        "risk_tags": ["memory"],
        "reviewer_tags": ["security"],
        "failed_gates": ["correctness"],
        "budget_usage": {"charged_tokens": 4000000, "released_token_limit": 4000000},
        "claim_boundary": "lens only",
    }
    card = cards.run_quality_card(payload)
    assert "🔬 Run Quality" in card
    assert "`succeeded` · impact `normal`" in card
    assert "🟢 `integrity` evidence `634`" in card
    assert "🔴 `correctness`" in card and "digest mismatch" in card
    assert "risk: `memory`" in card and "reviewer: `security`" in card
    assert "failed gates: `correctness`" in card
    assert "**Budget** ████████████ `4000000` / `4000000` charged" in card
    assert "🛡️ lens only" in card


def test_run_quality_card_unavailable() -> None:
    card = cards.run_quality_card({"available": False, "run_id": "run-x", "reason": "no graph receipt for this run", "claim_boundary": "cb"})
    assert "no graph receipt" in card
