"""Regression coverage for Frontier backlog 1-3 (temporary legacy path)."""
import json

import pytest

import memory_fabric_search as search
import recall_ranker as ranker


@pytest.fixture(autouse=True)
def no_personal_eval_history(monkeypatch):
    monkeypatch.setattr(ranker, "_recent_failed_eval_cases", lambda: set())


def record(id="one", **changes):
    return {"id": id, "title": "orchard harvest", "body": "apples", "tags": [],
            "scope": "/fixture", "tier": "learning", "status": "active",
            "confidence": "high", "provenance": {"type": "source_backed"},
            "created_at": "2026-09-01T00:00:00Z", **changes}


def store(tmp_path, records):
    path = tmp_path / "memory.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return path


def test_no_match_has_zero_score():
    assert search.match_score(record(), "quasar") == 0


def test_no_match_query_returns_no_records(tmp_path):
    result = search.search_records(query="quasar", path=store(tmp_path, [record()]))
    assert result["records"] == []
    assert result["count"] == 0


def test_blank_query_preserves_explicit_browse(tmp_path):
    result = search.search_records(query="  ", scope="/fixture", path=store(tmp_path, [record()]))
    assert [r["id"] for r in result["records"]] == ["one"]


def test_search_preserves_base_score_for_reranking(tmp_path):
    result = search.search_records(query="orchard", path=store(tmp_path, [record()]))
    assert result["records"][0]["_score"] == search.match_score(record(), "orchard")
    assert result["records"][0]["_score"] > 0


@pytest.mark.parametrize("tags,confidence", [(["failure"], "low"), (["success"], "high"), ([], "low")])
def test_equal_relevance_and_category_returns_newest_first(tags, confidence):
    old = record("old", tags=tags, confidence=confidence, _score=8)
    new = record("new", tags=tags, confidence=confidence, _score=8, created_at="2026-09-15T00:00:00Z")
    assert [r["id"] for r in ranker.rank([old, new])] == ["new", "old"]


def test_weak_failure_cannot_override_strong_relevance():
    strong = record("strong", _score=20, confidence="low")
    weak = record("weak", _score=2, tags=["failure"])
    assert ranker.rank([weak, strong])[0]["id"] == "strong"


def test_eval_boost_cannot_override_strong_relevance(monkeypatch):
    monkeypatch.setattr(ranker, "_recent_failed_eval_cases", lambda: {"case-1"})
    strong = record("strong", _score=20, confidence="low")
    weak = record("weak", _score=2, tags=["case-1"])
    assert ranker.rank([weak, strong])[0]["id"] == "strong"


def test_failure_boost_still_breaks_equal_relevance_ties():
    strong = record("neutral", _score=8, confidence="low")
    failure = record("failure", _score=8, tags=["failure"])
    assert ranker.rank([strong, failure])[0]["id"] == "failure"


def test_recency_compares_instants_not_offset_strings():
    older = record("older", _score=8, created_at="2026-09-15T01:00:00+02:00")
    newer = record("newer", _score=8, created_at="2026-09-15T00:00:00Z")
    assert ranker.rank([older, newer])[0]["id"] == "newer"


def test_search_then_rank_keeps_relevant_record_ahead_of_failure(tmp_path):
    relevant = record("relevant", title="orchard", body="orchard", confidence="low")
    failure = record("failure", title="other", body="orchard", tags=["failure"])
    results = search.search_records(query="orchard", path=store(tmp_path, [failure, relevant]))
    assert [r["id"] for r in ranker.rank(results["records"])] == ["relevant", "failure"]
