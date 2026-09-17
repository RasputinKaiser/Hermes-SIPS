"""Tests for the memory relevance label corpus and precision report."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from sips_runtime.memory_service import retrieve
from memory_relevance_report import evaluate


@pytest.fixture
def store(tmp_path: Path) -> str:
    path = tmp_path / "memory.jsonl"
    records = [
        {
            "id": "rec-1",
            "tier": "learning",
            "title": "SQLite index rebuild",
            "body": "Rebuild the graph index when schema drifts.",
            "scope": "global",
            "tags": ["index", "sqlite"],
            "status": "active",
            "confidence": "high",
            "verify_before_use": False,
            "provenance": {"type": "source_backed_agent_run", "evidence_path": "ev1.json"},
            "created_at": "2026-09-01T00:00:00Z",
        },
        {
            "id": "rec-2",
            "tier": "learning",
            "title": "frontier fanout",
            "body": "Bounded graph fanout keeps retrieval cheap.",
            "scope": "global",
            "tags": ["frontier", "graph"],
            "status": "active",
            "confidence": "high",
            "verify_before_use": False,
            "provenance": {"type": "source_backed_agent_run", "evidence_path": "ev2.json"},
            "created_at": "2026-09-02T00:00:00Z",
        },
    ]
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return str(path)


def test_perfect_precision_when_all_expected_returned(store: str) -> None:
    labels = [
        {"prompt": "SQLite index rebuild", "expected_ids": ["rec-1"], "forbidden_ids": []},
        {"prompt": "frontier fanout", "expected_ids": ["rec-2"], "forbidden_ids": []},
    ]
    report = evaluate(labels, store, limit=4)
    assert report["precision"] == 1.0
    assert report["harmful_recalls"] == 0


def test_harmful_recall_counted(store: str) -> None:
    labels = [
        {"prompt": "SQLite", "expected_ids": ["rec-1"], "forbidden_ids": ["rec-2"]},
    ]
    report = evaluate(labels, store, limit=4)
    assert report["harmful_recalls"] == 0
    assert report["tp"] >= 1


def test_superseded_records_counted_as_harmful(store: str) -> None:
    with open(store, "a") as f:
        f.write(json.dumps({
            "id": "rec-superseded",
            "tier": "learning",
            "title": "old SQLite approach",
            "body": "SQLite index rebuild superseded by rec-1",
            "scope": "global",
            "tags": ["index", "sqlite"],
            "status": "superseded",
            "confidence": "high",
            "verify_before_use": False,
            "provenance": {"type": "source_backed_agent_run", "evidence_path": "ev3.json"},
            "created_at": "2026-08-01T00:00:00Z",
        }) + "\n")

    labels = [
        {"prompt": "SQLite index", "expected_ids": ["rec-1"], "forbidden_ids": ["rec-superseded"]},
    ]
    report = evaluate(labels, store, limit=4)
    assert report["superseded_recalls"] == 0
    assert report["tp"] >= 1


def test_empty_labels_produce_zero_metrics(store: str) -> None:
    report = evaluate([], store, limit=4)
    assert report["corpus_size"] == 0
    assert report["precision"] == 0.0


def test_fn_counted_when_expected_not_returned(store: str) -> None:
    labels = [
        {"prompt": "nonexistent topic xyz", "expected_ids": ["rec-missing"], "forbidden_ids": []},
    ]
    report = evaluate(labels, store, limit=4)
    assert report["fn"] == 1
    assert report["tp"] == 0
