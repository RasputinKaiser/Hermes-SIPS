"""ExperimentService — champion/challenger experiment schema and manual command.

An experiment records:
  - hypothesis: what we expect to change
  - target_metric: the metric expected to change
  - champion_commit: the stable baseline commit
  - challenger_commit: the candidate commit
  - allowed_paths: paths the candidate may change
  - benchmark_manifest_hash: hash of the benchmark manifest used
  - public_runs / heldout_runs: run results
  - quality_gate_result: pass/fail
  - decision: promoted | rejected | inconclusive
  - decision_reasons: list of reasons
  - rollback_ref: reference for rollback

This module provides the schema and a manual command runner. Autonomous
experiment execution is deferred until the manual path is proven.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPERIMENT_SCHEMA = "hermes.sips.experiment.v1"


def create_experiment(
    *,
    hypothesis: str,
    target_metric: str,
    champion_commit: str,
    challenger_commit: str,
    allowed_paths: list[str] | None = None,
    benchmark_manifest_hash: str = "",
    public_runs: list[dict[str, Any]] | None = None,
    heldout_runs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new experiment record."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema": EXPERIMENT_SCHEMA,
        "id": f"exp-{uuid.uuid4().hex[:12]}",
        "created_at": now,
        "updated_at": now,
        "hypothesis": str(hypothesis),
        "target_metric": str(target_metric),
        "champion_commit": str(champion_commit),
        "challenger_commit": str(challenger_commit),
        "allowed_paths": list(allowed_paths or []),
        "benchmark_manifest_hash": str(benchmark_manifest_hash),
        "public_runs": list(public_runs or []),
        "heldout_runs": list(heldout_runs or []),
        "quality_gate_result": None,
        "decision": "inconclusive",
        "decision_reasons": [],
        "rollback_ref": f"rollback-{champion_commit[:12]}",
    }


def compute_manifest_hash(manifest: dict[str, Any] | str | Path) -> str:
    """Compute a stable hash of a benchmark manifest."""
    if isinstance(manifest, Path):
        data = manifest.read_text()
    elif isinstance(manifest, dict):
        data = json.dumps(manifest, sort_keys=True)
    else:
        data = str(manifest)
    return hashlib.sha256(data.encode()).hexdigest()


def evaluate_experiment(
    experiment: dict[str, Any],
    *,
    public_pass_rate: float,
    heldout_pass_rate: float,
    tolerance: float = 0.05,
) -> dict[str, Any]:
    """Evaluate an experiment and update its decision.

    Rules:
    - If heldout regression beyond tolerance: rejected
    - If public improvement and heldout within tolerance: promoted
    - Otherwise: inconclusive
    """
    champion_rate = public_pass_rate
    challenger_rate = heldout_pass_rate

    regression = challenger_rate < champion_rate - tolerance
    improvement = challenger_rate > champion_rate + tolerance

    if regression:
        decision = "rejected"
        reasons = [f"heldout regression: {challenger_rate:.3f} < {champion_rate:.3f} - {tolerance}"]
    elif improvement:
        decision = "promoted"
        reasons = [f"heldout improvement: {challenger_rate:.3f} > {champion_rate:.3f} + {tolerance}"]
    else:
        decision = "inconclusive"
        reasons = [f"heldout delta within tolerance: {challenger_rate:.3f} vs {champion_rate:.3f}"]

    experiment["decision"] = decision
    experiment["decision_reasons"] = reasons
    experiment["quality_gate_result"] = "passed" if decision == "promoted" else "failed"
    experiment["updated_at"] = datetime.now(timezone.utc).isoformat()
    return experiment


def validate_experiment(experiment: dict[str, Any]) -> list[str]:
    """Validate an experiment record. Returns list of errors."""
    errors = []
    required = ["id", "hypothesis", "target_metric", "champion_commit", "challenger_commit"]
    for key in required:
        if not experiment.get(key):
            errors.append(f"missing required field: {key}")
    if experiment.get("decision") not in {"promoted", "rejected", "inconclusive"}:
        errors.append(f"invalid decision: {experiment.get('decision')}")
    return errors
