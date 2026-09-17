"""Required transcript events must exist before ordering can pass."""
from pathlib import Path

import pytest

from eval_harness import grade


@pytest.mark.parametrize("sequence,passed", [
    ([], False),
    (["Bash"], False),
    (["Read"], False),
    (["Write"], False),
    (["Write", "Read"], False),
    (["Read", "Write"], True),
    (["Bash", "Read", "Edit"], True),
    (["Read", "Read", "Write"], True),
    (["Write", "Read", "Write"], False),
])
def test_required_sequence(sequence, passed):
    results, score = grade([{
        "kind": "transcriptSequence",
        "arguments": {"first": "Read", "before": "Edit|Write"},
    }], Path("."), sequence)
    assert results[0]["passed"] is passed
    assert score == float(passed)


@pytest.mark.parametrize("arguments", [
    {"before": "Write"},
    {"first": "", "before": "Write"},
    {"first": "Read"},
    {"first": "[", "before": "Write"},
    {"first": "Read", "before": "["},
])
def test_invalid_sequence_contract_fails_even_with_empty_transcript(arguments):
    results, score = grade([{"kind": "transcriptSequence", "arguments": arguments}], Path("."), [])
    assert results[0]["passed"] is False
    assert score == 0.0


@pytest.mark.parametrize("sequence,optional,passed", [
    (["Read"], True, True),
    ([], True, False),  # first remains mandatory
    (["Bash"], True, False),
    (["Write"], True, False),
    (["Write", "Read"], True, False),
    (["Read", "Write"], True, True),
    (["Read"], False, False),
    (["Read"], "true", False),  # truthy strings must not weaken a check
])
def test_only_explicit_before_optional_allows_missing_target(sequence, optional, passed):
    results, score = grade([{
        "kind": "transcriptSequence",
        "arguments": {"first": "Read", "before": "Write", "beforeOptional": optional},
    }], Path("."), sequence)
    assert results[0]["passed"] is passed
    assert score == float(passed)


def test_matching_same_event_does_not_satisfy_strict_order():
    results, score = grade([{
        "kind": "transcriptSequence",
        "arguments": {"first": "Read|Write", "before": "Write"},
    }], Path("."), ["Write"])
    assert results[0]["passed"] is False
    assert score == 0.0
