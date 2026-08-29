"""Visual-format tests for the scoped-recall block in scripts/recall_ranker.py."""
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import recall_ranker as rr


def _rec(tags=None, conf=None, title="t", body="b", tier="learning"):
    return {"tags": tags or [], "confidence": conf, "title": title,
            "body": body, "tier": tier}


FAILURE = "⚠ PRIOR FAILURE"
SUCCESS = "✓ prior success"
GLYPHS = ("🔴", "🟢", "⚪")


def _render(records):
    """rank() emits JSON via main()'s emit(); build_context returns the text directly."""
    return rr.build_context("query here", rr.rank(records))


def test_glyph_starts_each_record_line():
    text = _render([_rec(), _rec(tags=["failure"]), _rec(conf="high")])
    lines = [ln for ln in text.split("\n") if ln.startswith(tuple(GLYPHS))]
    assert len(lines) == 3, text
    for ln in lines:
        assert ln.split(" - ", 1)[0] in GLYPHS, ln


def test_failure_glyph_and_ordering_before_success():
    records = [
        _rec(conf="high", title="good"),
        _rec(tags=["failure"], title="bad"),
        _rec(title="meh"),
    ]
    text = _render(records)
    fail_idx = text.index("🔴")
    succ_idx = text.index("🟢")
    assert fail_idx < succ_idx
    # markers stay verbatim after the glyph
    assert f"🔴 - {FAILURE}  [" in text
    assert f"🟢 - {SUCCESS}  [" in text


def test_neutral_records_get_white_glyph():
    text = _render([_rec(conf="medium")])
    assert "⚪" in text
    assert "🔴" not in text and "🟢" not in text


def test_blank_line_after_header():
    text = _render([_rec()])
    lines = text.split("\n")
    assert lines[0].startswith("🧠 scoped recall (1 lessons)")
    assert lines[1] == ""
    assert lines[2].startswith(("🔴", "🟢", "⚪"))


def test_markers_and_tier_conf_still_present():
    text = _render([
        _rec(tags=["failure"], tier="work", conf="low"),
        _rec(conf="high", tier="knowledge"),
    ])
    assert FAILURE in text
    assert SUCCESS in text
    assert "[work|conf=low]" in text
    assert "[knowledge|conf=high]" in text


def test_header_contains_count_and_query():
    text = _render([_rec(), _rec(), _rec()])
    assert "🧠 scoped recall (3 lessons)" in text
    assert "query 'query here'" in text
    assert "advisory — verify before relying on claims" in text
