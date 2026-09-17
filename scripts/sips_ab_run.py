#!/usr/bin/env python3
"""Paired SIPS-off/on deterministic eval runner (M0 baseline scaffold).

Reads a frozen run manifest and a set of fixture transcripts (no live model
required) and produces a paired comparison report. Each case is graded twice:

  - SIPS_ON: full contract — file, grep and transcriptSequence checks.
  - SIPS_OFF: weak baseline — file and grep checks only (transcriptSequence
    cases are skipped), simulating the pre-contract grader.

The output report contains stable run IDs, mode, score, pass/fail and the
contract fields required by the run manifest (tokens recorded as zero for the
deterministic grader; live-model runs would populate them).

Usage:
  python3 scripts/sips_ab_run.py --manifest references/ab_manifest.v1.json \\
      --fixtures fixtures/ab_cases --output /tmp/ab_report.json
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from eval_harness import grade


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    for key in ("run_id", "created_at", "sips_off_result", "sips_on_result"):
        data.setdefault(key, None)
    data.setdefault("cases", [])
    data.setdefault("fixture_dir", None)
    data.setdefault("mode_comparison", {"sips_off_weak_baseline": True, "sips_on_full_contract": True})
    return data


def load_fixtures(fixture_dir: Path) -> list[dict[str, Any]]:
    if not fixture_dir.is_dir():
        return []
    return [json.loads(p.read_text()) for p in sorted(fixture_dir.glob("*.json"))]


def run_case(fixture: dict[str, Any], *, sips_on: bool, sandbox: Path) -> dict[str, Any]:
    checks = fixture.get("grading", []) if sips_on else [
        c for c in fixture.get("grading", []) if c.get("kind") in {"fileExists", "fileMissing", "grep"}
    ]
    check_results, score = grade(checks, sandbox, fixture.get("toolSequence", []))
    return {
        "id": fixture["id"],
        "mode": "sips_on" if sips_on else "sips_off",
        "score": score,
        "passed": bool(fixture.get("passThreshold", 1.0) <= score and score > 0),
        "skipped_checks": 0 if sips_on else len(fixture.get("grading", [])) - len(checks),
        "check_results": check_results,
        "tool_count": len(fixture.get("toolSequence", [])),
        "total_tokens": 0,
        "wall_time_ms": 0,
        "contract": "full" if sips_on else "weak_baseline",
    }


def build_report(manifest: dict[str, Any], fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    run_id = manifest.get("run_id") or f"run-{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    cases = []
    for fixture in fixtures:
        sandbox = Path(fixture.get("_sandbox", "/tmp")).resolve()
        sandbox.mkdir(parents=True, exist_ok=True)
        for name, content in fixture.get("sandboxFiles", {}).items():
            (sandbox / name).write_text(content)
        off = run_case(fixture, sips_on=False, sandbox=sandbox)
        on = run_case(fixture, sips_on=True, sandbox=sandbox)
        cases.append({"fixture_id": fixture["id"], "sips_off": off, "sips_on": on})

    return {
        "schema": "hermes.sips.ab_report.v1",
        "run_id": run_id,
        "created_at": created_at,
        "manifest": {k: v for k, v in manifest.items() if k not in {"cases", "fixture_dir"}},
        "cases": cases,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Paired SIPS-off/on deterministic eval runner")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--fixtures", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    manifest = load_manifest(Path(args.manifest))
    fixtures = load_fixtures(Path(args.fixtures))
    report = build_report(manifest, fixtures)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(json.dumps({"run_id": report["run_id"], "cases": len(report["cases"])}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
