"""Regression: unrelated memory must not receive positive relevance."""
from memory_fabric_semantic_match import match_score


def test_unrelated_memory_has_zero_relevance():
    record = {"title": "SwiftUI window layout"}
    profile = {"direct_terms": ["sqlite"], "expanded_terms": ["database"]}
    assert match_score(record, profile, [(record["title"].lower(), 8)]) == 0
