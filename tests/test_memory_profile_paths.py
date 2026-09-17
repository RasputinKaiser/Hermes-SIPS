"""Profile-scoped defaults; explicit operator/CLI stores remain supported."""
from pathlib import Path

import memory_fabric_jsonl as memory
from memory_fabric_graph_index import index_path
import sips_paths


def clear_overrides(monkeypatch):
    for key in ("SIPS_HOME", "CODEX_MEMORY_FABRIC_STORE", "HERMES_HOME"):
        monkeypatch.delenv(key, raising=False)


def test_two_hermes_profiles_have_separate_store_and_index(monkeypatch, tmp_path):
    clear_overrides(monkeypatch)
    paths = []
    for name in ("alpha", "beta"):
        home = tmp_path / name
        monkeypatch.setenv("HERMES_HOME", str(home))
        expected = home / "sips" / "memory-fabric" / "memory.jsonl"
        assert sips_paths.harness_home() == home / "sips"
        assert memory.store_path() == expected
        assert memory.load_records() == []
        memory.append_record({"id": name})
        assert [r["id"] for r in memory.load_records()] == [name]
        assert index_path(memory.store_path()).parent == expected.parent
        paths.append(memory.store_path())
    assert paths[0] != paths[1]
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "alpha"))
    assert [r["id"] for r in memory.load_records()] == ["alpha"]


def test_adapter_supplied_sips_home_scopes_memory(monkeypatch, tmp_path):
    clear_overrides(monkeypatch)
    monkeypatch.setenv("SIPS_HOME", str(tmp_path / "sips"))
    assert memory.store_path() == tmp_path / "sips/memory-fabric/memory.jsonl"


def test_explicit_store_remains_available_for_migration(monkeypatch, tmp_path):
    clear_overrides(monkeypatch)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "profile"))
    monkeypatch.setenv("CODEX_MEMORY_FABRIC_STORE", str(tmp_path / "explicit.jsonl"))
    assert memory.store_path() == tmp_path / "explicit.jsonl"
    assert memory.store_path(tmp_path / "cli.jsonl") == tmp_path / "cli.jsonl"


def test_non_hermes_default_remains_compatible(monkeypatch, tmp_path):
    clear_overrides(monkeypatch)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert memory.store_path() == tmp_path / ".codex/memory-fabric/memory.jsonl"
