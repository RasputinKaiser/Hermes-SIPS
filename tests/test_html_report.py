"""Tests for the HTML report generator (html_report.py)."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import html_report  # noqa: E402


def _usage(**overrides):
    base = {
        "available": True, "window_days": 7,
        "totals": {"sessions": 3, "api_calls": 40, "fresh_input_tokens": 5000000,
                   "output_tokens": 100000, "cache_hit_pct": 96.4,
                   "fresh_to_output_ratio": "50:1",
                   "total_input_tokens": 130000000},
        "daily": [{"day": "2026-08-29", "fresh_input_tokens": 5000000, "cache_hit_pct": 96.4}],
        "replay": {"tool_results_replayed_tokens_est": 700000000,
                   "top_tools": [{"tool": "terminal", "replayed_tokens_est": 300000000}]},
        "direct_vs_subagent": {"direct": {"fresh_input_tokens": 2000000},
                               "subagent": {"fresh_input_tokens": 3000000}},
    }
    base.update(overrides)
    return base


def test_render_usage_handles_payload():
    usage = _usage()
    html = html_report._render_usage(usage)
    assert "96.4%" in html and "5.0M" in html and "60%" in html
    assert "2026-08-29" in html and "terminal" in html


def test_render_usage_unavailable_is_empty():
    out = html_report._render_usage({"available": False})
    assert "unavailable" in out and "session store not readable" in out


def test_daily_partial_day_is_gray_and_marked():
    """Today renders as a partial sample: gray bar, dim %, '(partial)' label."""
    usage = _usage(daily=[{"day": html_report._today(), "fresh_input_tokens": 158000,
                           "cache_hit_pct": 70.5},
                          {"day": "2026-08-29", "fresh_input_tokens": 5000000,
                           "cache_hit_pct": 96.4}])
    html = html_report._render_usage(usage)
    assert "(partial)" in html
    assert "bar n" in html  # gray neutral bar for today
    # The partial day's low % must NOT get judgment color (bad class).
    partial_row = [ln for ln in html.splitlines() if "(partial)" in ln][0]
    assert "'bad'" not in partial_row and "class='r bad'" not in partial_row


def test_full_day_cache_regression_gets_bad_color():
    usage = _usage(daily=[{"day": "2026-08-29", "fresh_input_tokens": 5000000,
                           "cache_hit_pct": 70.5}])
    html = html_report._render_usage(usage)
    assert "class='r bad'" in html


def test_render_runs_merged_table():
    """Merged run table: one row per run — status, recency, and gate dots."""
    matrix = {
        "available": True, "gates": ["integrity", "correctness"],
        "runs": [
            {"run_id": "r-ok", "receipt": True,
             "gates": {"integrity": "ok", "correctness": "ok"}, "ok_count": 2,
             "failed_count": 0},
            {"run_id": "r-bad", "receipt": False,
             "gates": {"integrity": None, "correctness": None}, "ok_count": 0,
             "failed_count": 0},
        ],
    }
    html = html_report._render_runs(matrix, {"available": False})
    assert "<b class=\"good\">1 passed all gates</b>" in html
    assert "not gated" in html
    assert 'title="Integrity"' in html  # jargon-free column labels


def test_run_dots_carry_aria_and_title():
    """Status dots are never color-only: role, title, and aria-label."""
    matrix = {
        "available": True, "gates": ["integrity"],
        "runs": [{"run_id": "r1", "receipt": True,
                  "gates": {"integrity": "ok"}, "ok_count": 1, "failed_count": 0}],
    }
    html = html_report._render_runs(matrix, {"available": False})
    assert "role='img'" in html
    assert "aria-label='r1" in html
    assert "title='r1" in html


def test_posture_failed_gate_surfaces():
    matrix = {"available": True, "runs": [{"run_id": "r", "failed_count": 2}]}
    chip = html_report._posture(_usage(), matrix)
    assert "Needs attention" in chip


def test_posture_full_day_regression_surfaces():
    """A full (non-today) day under 80% cache trips the chip — the P0 fix."""
    usage = _usage(daily=[{"day": "2026-08-28", "fresh_input_tokens": 5000000,
                           "cache_hit_pct": 70.5}])
    chip = html_report._posture(usage, {"runs": []})
    assert "Needs attention" in chip


def test_posture_ignores_today_partial_and_cold_days():
    """Today's partial sample and cold (<_COLD_DAY_FRESH) days never judge."""
    usage = _usage(daily=[
        {"day": html_report._today(), "fresh_input_tokens": 158000,
         "cache_hit_pct": 70.5},                     # today partial → ignore
        {"day": "2026-08-27", "fresh_input_tokens": 500, "cache_hit_pct": 12.0},  # cold → ignore
    ])
    chip = html_report._posture(usage, {"runs": []})
    assert "All healthy" in chip


def test_delta_line_needs_two_full_weeks():
    rows = [{"day": f"2026-08-{d:02d}", "fresh_input_tokens": 1_000_000,
             "cache_read_tokens": 19_000_000, "output_tokens": 50_000,
             "api_calls": 100, "sessions": 5} for d in range(1, 8)]
    prev = [{"day": f"2026-08-{d:02d}", "fresh_input_tokens": 2_000_000,
             "cache_read_tokens": 38_000_000, "output_tokens": 50_000,
             "api_calls": 100, "sessions": 5} for d in range(1, 8)]
    line = html_report._delta_line(rows, prev)
    assert "vs previous week" in line and "-50%" in line
    assert html_report._delta_line(rows[:5], prev) == ""  # incomplete week → no line


def test_generate_report_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(html_report, "_REPORT_PATH", tmp_path / "report.html")
    import usage_lens, gate_matrix, fleet_timeline
    monkeypatch.setattr(usage_lens, "usage_payload", lambda days=7: {"available": False})
    monkeypatch.setattr(gate_matrix, "gate_matrix_payload", lambda: {"available": False})
    monkeypatch.setattr(fleet_timeline, "timeline_payload", lambda: {"available": False})
    path = html_report.generate_report()
    content = path.read_text(encoding="utf-8")
    assert content.startswith("<!DOCTYPE html>") and "SIPS Control Report" in content
