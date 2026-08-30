"""Tests for the context-lens cards (context_scan + distill renderers)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import context_lens_cards as clc  # noqa: E402


SCAN_PAYLOAD = {
    "schema": "homebase.context_scan.v1",
    "root": ".",
    "max_bytes": 50000,
    "risk_count": 2,
    "risks": [
        {"path": "big.py", "bytes": 120_000, "estimated_tokens": 30_000, "bounded_read": "sed -n '1,160p' big.py"},
        {"path": "smaller.py", "bytes": 44_000, "estimated_tokens": 11_000, "bounded_read": "sed -n '1,160p' smaller.py"},
        {"path": "tiny.py", "bytes": 8_000, "estimated_tokens": 2_000, "bounded_read": "sed -n '1,160p' tiny.py"},
    ],
    "claim_boundary": "bounded metadata only",
}


def test_context_scan_card_risks_bars_and_commands() -> None:
    card = clc.context_scan_card(SCAN_PAYLOAD)
    assert "📦 Context Scan" in card
    assert "**2 risks**" in card  # from payload risk_count
    assert "🔴" in card and "🟡" in card and "🟢" in card  # tone tiers
    assert "bounded read: `sed -n '1,160p' big.py`" in card
    assert "117KB" in card or "120.0KB" in card
    assert "🛡️ bounded metadata only" in card


def test_context_scan_card_empty_and_truncation() -> None:
    empty = clc.context_scan_card({"risks": [], "risk_count": 0, "claim_boundary": "cb"})
    assert "No oversized files matched" in empty and "🛡️ cb" in empty
    many = dict(SCAN_PAYLOAD, risks=[dict(SCAN_PAYLOAD["risks"][0], path=f"f{i}.py") for i in range(12)], risk_count=12)
    card = clc.context_scan_card(many)
    assert "… 4 more" in card  # shows 8, truncates rest


def test_distill_card_renders_sources_and_excerpts() -> None:
    payload = {
        "schema": "homebase.distill_context.v1",
        "query": "build_context",
        "sources": [
            {"input": "scripts/recall_ranker.py", "excerpt": "def build_context(query, ranked):\n    header = ...\n    return text"},
            {"input": "other.py", "matched_lines": [10, 22, 48], "excerpt": "short"},
        ],
        "claim_boundary": "excerpts bounded",
    }
    card = clc.distill_card(payload)
    assert "💧 Context Distill" in card
    assert "**Query** `build_context`" in card
    assert "📖 `scripts/recall_ranker.py`" in card
    assert "build_context" in card
    assert "`3 matched lines`" in card
    assert "🛡️ excerpts bounded" in card


def test_distill_card_truncates_long_excerpts() -> None:
    payload = {
        "query": "q",
        "sources": [{"input": "x.py", "excerpt": "y" * 500}],
        "claim_boundary": "",
    }
    card = clc.distill_card(payload)
    assert "…" in card
    assert ("y" * 280) in card  # shown portion
    assert ("y" * 400) not in card  # truncated away
