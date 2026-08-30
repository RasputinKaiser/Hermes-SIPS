"""Tests for the HTML report generator (html_report.py)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import html_report  # noqa: E402


def test_render_usage_handles_payload():
    usage = {
        "available": True, "window_days": 7,
        "totals": {"sessions": 3, "api_calls": 40, "fresh_input_tokens": 5000000,
                   "output_tokens": 100000, "cache_hit_pct": 96.4,
                   "fresh_to_output_ratio": "50:1"},
        "daily": [{"day": "2026-08-29", "fresh_input_tokens": 5000000, "cache_hit_pct": 96.4}],
        "replay": {"tool_results_replayed_tokens_est": 700000000,
                   "top_tools": [{"tool": "terminal", "replayed_tokens_est": 300000000}]},
        "direct_vs_subagent": {"direct": {"fresh_input_tokens": 2000000},
                               "subagent": {"fresh_input_tokens": 3000000}},
    }
    html = html_report._render_usage(usage)
    assert "96.4%" in html and "5.0M" in html and "60%" in html
    assert "2026-08-29" in html and "terminal" in html


def test_render_usage_unavailable_is_empty():
    out = html_report._render_usage({"available": False})
    assert "unavailable" in out and "session store not readable" in out


def test_render_gates_cells_and_summary():
    matrix = {
        "available": True, "gates": ["integrity", "correctness"],
        "runs": [
            {"run_id": "r-ok", "receipt": True,
             "gates": {"integrity": "ok", "correctness": "ok"}, "ok_count": 2, "failed_count": 0},
            {"run_id": "r-bad", "receipt": False,
             "gates": {"integrity": None, "correctness": None}, "ok_count": 0, "failed_count": 0},
        ],
    }
    html = html_report._render_gates(matrix)
    assert "<b class=\"good\">1 clean</b>" in html and "not gated" in html


def test_generate_report_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(html_report, "_REPORT_PATH", tmp_path / "report.html")
    import usage_lens, gate_matrix, fleet_timeline
    monkeypatch.setattr(usage_lens, "usage_payload", lambda days=7: {"available": False})
    monkeypatch.setattr(gate_matrix, "gate_matrix_payload", lambda: {"available": False})
    monkeypatch.setattr(fleet_timeline, "timeline_payload", lambda: {"available": False})
    path = html_report.generate_report()
    content = path.read_text(encoding="utf-8")
    assert content.startswith("<!DOCTYPE html>") and "SIPS Control Report" in content
