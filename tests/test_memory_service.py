"""Tests for the unified MemoryService over the indexed Memory Frontier."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from sips_runtime.memory_service import retrieve


@pytest.fixture
def memory_store(tmp_path: Path) -> Path:
    store = tmp_path / "memory.jsonl"
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
            "provenance": {"type": "source_backed_agent_run", "evidence_path": str(tmp_path / "ev1.json")},
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
            "provenance": {"type": "source_backed_agent_run", "evidence_path": str(tmp_path / "ev2.json")},
            "created_at": "2026-09-02T00:00:00Z",
        },
    ]
    for rec in records:
        (tmp_path / f"ev{rec['id'][-1]}.json").write_text("{}")
    store.write_text("".join(json.dumps(r) + "\n" for r in records))
    return store


def test_empty_query_returns_no_records(memory_store: Path) -> None:
    result = retrieve(query="   ", store=str(memory_store))
    assert result["source"] == "none"
    assert result["records"] == []


def test_frontier_path_returns_records(memory_store: Path) -> None:
    result = retrieve(query="SQLite index", store=str(memory_store))
    assert result["ok"] is True
    assert result["source"] in {"frontier", "flat"}
    assert len(result["records"]) >= 1


def test_retrieve_respects_limit(memory_store: Path) -> None:
    result = retrieve(query="index", store=str(memory_store), limit=1)
    assert len(result["records"]) <= 1


def test_shadow_mode_includes_shadow_block(memory_store: Path) -> None:
    result = retrieve(query="index", store=str(memory_store), shadow=True)
    assert "shadow" in result
    assert "legacy_record_ids" in result["shadow"]


def test_untrusted_excluded_by_default(memory_store: Path) -> None:
    result = retrieve(query="index", store=str(memory_store), include_untrusted=False)
    for rec in result["records"]:
        assert rec.get("verify_before_use") in (False, None, 0)
