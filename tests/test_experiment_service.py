"""Tests for the ExperimentService schema."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts" / "sips_runtime"))

from experiment import create_experiment, evaluate_experiment, validate_experiment, compute_manifest_hash


def test_create_experiment_has_all_required_fields() -> None:
    exp = create_experiment(
        hypothesis="frontier retrieval reduces irrelevant recall",
        target_metric="precision@4",
        champion_commit="abc123",
        challenger_commit="def456",
    )
    assert exp["id"].startswith("exp-")
    assert exp["hypothesis"] == "frontier retrieval reduces irrelevant recall"
    assert exp["target_metric"] == "precision@4"
    assert exp["decision"] == "inconclusive"
    assert exp["rollback_ref"] == "rollback-abc123"


def test_evaluate_promotes_on_improvement() -> None:
    exp = create_experiment(
        hypothesis="test",
        target_metric="precision",
        champion_commit="abc",
        challenger_commit="def",
    )
    evaluate_experiment(exp, public_pass_rate=0.5, heldout_pass_rate=0.7)
    assert exp["decision"] == "promoted"
    assert exp["quality_gate_result"] == "passed"


def test_evaluate_rejects_on_regression() -> None:
    exp = create_experiment(
        hypothesis="test",
        target_metric="precision",
        champion_commit="abc",
        challenger_commit="def",
    )
    evaluate_experiment(exp, public_pass_rate=0.7, heldout_pass_rate=0.5)
    assert exp["decision"] == "rejected"
    assert exp["quality_gate_result"] == "failed"


def test_evaluate_inconclusive_within_tolerance() -> None:
    exp = create_experiment(
        hypothesis="test",
        target_metric="precision",
        champion_commit="abc",
        challenger_commit="def",
    )
    evaluate_experiment(exp, public_pass_rate=0.7, heldout_pass_rate=0.72, tolerance=0.05)
    assert exp["decision"] == "inconclusive"


def test_validate_experiment_rejects_missing_fields() -> None:
    errors = validate_experiment({})
    assert any("hypothesis" in e for e in errors)
    assert any("target_metric" in e for e in errors)


def test_validate_experiment_rejects_invalid_decision() -> None:
    exp = create_experiment(
        hypothesis="test",
        target_metric="precision",
        champion_commit="abc",
        challenger_commit="def",
    )
    exp["decision"] = "invalid"
    errors = validate_experiment(exp)
    assert any("invalid decision" in e for e in errors)


def test_manifest_hash_is_deterministic() -> None:
    manifest = {"cases": ["a", "b"], "version": 1}
    h1 = compute_manifest_hash(manifest)
    h2 = compute_manifest_hash(manifest)
    assert h1 == h2
    assert len(h1) == 64


def test_manifest_hash_changes_with_content() -> None:
    h1 = compute_manifest_hash({"version": 1})
    h2 = compute_manifest_hash({"version": 2})
    assert h1 != h2
