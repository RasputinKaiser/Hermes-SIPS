"""Paired SIPS-off/on runner produces a valid report with both modes."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sips_ab_run import build_report, load_manifest


@pytest.fixture
def fileexists_fixture() -> list[dict]:
    return [
        {
            "id": "fileexists_pass",
            "prompt": "create hello.txt",
            "grading": [{"kind": "fileExists", "arguments": {"path": "hello.txt"}, "weight": 1}],
            "sandboxFiles": {"hello.txt": "hello world"},
            "toolSequence": ["Write"],
        }
    ]


def test_report_has_both_modes(fileexists_fixture: list[dict]) -> None:
    manifest = load_manifest(Path(__file__).resolve().parents[1] / "references" / "ab_manifest.v1.json")
    manifest["cases"] = ["fileexists_pass"]
    report = build_report(manifest, fileexists_fixture)
    assert report["schema"] == "hermes.sips.ab_report.v1"
    assert len(report["cases"]) == 1
    case = report["cases"][0]
    assert case["sips_off"]["mode"] == "sips_off"
    assert case["sips_on"]["mode"] == "sips_on"
    assert case["sips_off"]["passed"] is True
    assert case["sips_on"]["passed"] is True


def test_weak_baseline_skips_transcript_sequence() -> None:
    manifest = {
        "run_id": "seq-run",
        "created_at": "2026-09-17T00:00:00Z",
        "description": "seq",
        "mode_comparison": {"sips_off_weak_baseline": True, "sips_on_full_contract": True},
        "cases": [],
        "fixture_dir": None,
    }
    fixtures = [
        {
            "id": "seq",
            "prompt": "read then write",
            "grading": [{"kind": "transcriptSequence", "arguments": {"first": "Read", "before": "Write"}, "weight": 1}],
            "sandboxFiles": {},
            "toolSequence": ["Read", "Write"],
        }
    ]
    report = build_report(manifest, fixtures)
    case = report["cases"][0]
    assert case["sips_off"]["skipped_checks"] == 1
    assert case["sips_off"]["score"] == 0.0
    assert case["sips_on"]["skipped_checks"] == 0
    assert case["sips_on"]["score"] == 1.0


def test_empty_fixtures_produces_empty_report(fileexists_fixture: list[dict]) -> None:
    manifest = {
        "run_id": "empty-run",
        "created_at": "2026-09-17T00:00:00Z",
        "description": "empty",
        "mode_comparison": {"sips_off_weak_baseline": True, "sips_on_full_contract": True},
        "cases": [],
        "fixture_dir": None,
    }
    report = build_report(manifest, [])
    assert report["cases"] == []
