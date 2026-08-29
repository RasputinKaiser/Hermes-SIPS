"""Tests for the token-usage lens: /token-usage endpoint and usage_lens module.

Each test uses an isolated SQLite store via the SIPS_HERMES_STATE_DB override
so no live state under ~/.hermes is ever touched. Handlers are called
in-process, the same verification the Hermes desktop skill prescribes.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DASHBOARD = _REPO_ROOT / "dashboard"
_SCRIPTS = _REPO_ROOT / "scripts"
for _path in (str(_DASHBOARD), str(_SCRIPTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    import plugin_api  # noqa: E402
    import usage_lens  # noqa: E402
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise

if not hasattr(plugin_api, "router"):  # pragma: no cover - defensive
    pytest.skip("fastapi not installed in this environment", allow_module_level=True)


SCHEMA = """
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    parent_session_id TEXT,
    started_at REAL NOT NULL,
    title TEXT
);
CREATE TABLE session_model_usage (
    session_id TEXT NOT NULL,
    model TEXT NOT NULL,
    api_call_count INTEGER NOT NULL DEFAULT 0,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cache_read_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens INTEGER NOT NULL DEFAULT 0,
    reasoning_tokens INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (session_id, model)
);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT,
    tool_calls TEXT,
    reasoning TEXT,
    reasoning_content TEXT,
    tool_name TEXT,
    timestamp REAL NOT NULL
);
"""


@pytest.fixture()
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolated state.db + cache reset for each test."""
    db = tmp_path / "state.db"
    monkeypatch.setenv("SIPS_HERMES_STATE_DB", str(db))
    monkeypatch.setattr(usage_lens, "_replay_cache", {}, raising=False)
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return db


def _add_usage(db: Path, session_id: str, *, parent: str | None = None, started: float | None = None,
               model: str = "test-model", calls: int = 10, fresh: int = 1000, out: int = 100,
               cache_read: int = 5000, cost: float = 0.0) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO sessions (id, source, parent_session_id, started_at) VALUES (?, 'desktop', ?, ?)",
        (session_id, parent, started if started is not None else time.time()),
    )
    conn.execute(
        """INSERT INTO session_model_usage
           (session_id, model, api_call_count, input_tokens, output_tokens, cache_read_tokens, estimated_cost_usd)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session_id, model, calls, fresh, out, cache_read, cost),
    )
    conn.commit()
    conn.close()


def _add_message(db: Path, session_id: str, role: str, content: str, ts: float, tool_name: str | None = None) -> None:
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO messages (session_id, role, content, tool_name, timestamp) VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, tool_name, ts),
    )
    conn.commit()
    conn.close()


def test_totals_derive_cache_hit_and_ratio(store: Path) -> None:
    _add_usage(store, "s-1", fresh=1000, out=100, cache_read=9000)
    payload = usage_lens.usage_payload(days=7)
    assert payload["available"] is True
    totals = payload["totals"]
    assert totals["sessions"] == 1
    assert totals["cache_hit_pct"] == 90.0
    assert totals["fresh_to_output_ratio"] == "10.0:1"
    assert totals["total_input_tokens"] == 10000


def test_split_separates_subagents(store: Path) -> None:
    _add_usage(store, "direct-1", fresh=2000, calls=20)
    _add_usage(store, "child-1", parent="direct-1", fresh=8000, calls=20)
    payload = usage_lens.usage_payload(days=7)
    split = payload["direct_vs_subagent"]
    assert split["direct"]["fresh_input_tokens"] == 2000
    assert split["subagent"]["fresh_input_tokens"] == 8000
    assert split["subagent"]["avg_fresh_input_per_call"] == 400.0
    assert split["direct"]["avg_fresh_input_per_call"] == 100.0


def test_replay_mass_weights_by_later_calls(store: Path) -> None:
    # 40KB tool result + 2 assistant messages AFTER it => replayed 2x
    _add_usage(store, "s-1", calls=3)
    base = time.time() - 60
    _add_message(store, "s-1", "tool", "x" * 40960, base, tool_name="read_file")
    _add_message(store, "s-1", "assistant", "ok-1", base + 10)
    _add_message(store, "s-1", "assistant", "ok-2", base + 20)
    payload = usage_lens.usage_payload(days=7)
    replay = payload["replay"]
    # 40960 bytes * 2 later calls / 4 bytes-per-token = 20480
    assert replay["tool_results_replayed_tokens_est"] == 20480
    assert replay["top_tools"][0]["tool"] == "read_file"
    assert replay["top_sessions"][0]["session_id"] == "s-1"


def test_outside_window_excluded(store: Path) -> None:
    _add_usage(store, "old-1", started=time.time() - 30 * 86400)
    payload = usage_lens.usage_payload(days=7)
    assert payload["available"] is True
    assert payload["totals"]["api_calls"] == 0
    assert payload["daily"] == []


def test_missing_store_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SIPS_HERMES_STATE_DB", str(tmp_path / "nope.db"))
    monkeypatch.setattr(usage_lens, "_replay_cache", {}, raising=False)
    payload = usage_lens.usage_payload(days=7)
    assert payload["available"] is False
    assert "not readable" in payload["reason"]


def test_corrupt_store_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db = tmp_path / "state.db"
    db.write_bytes(b"this is not sqlite")
    monkeypatch.setenv("SIPS_HERMES_STATE_DB", str(db))
    monkeypatch.setattr(usage_lens, "_replay_cache", {}, raising=False)
    payload = usage_lens.usage_payload(days=7)
    assert payload["available"] is False
    assert "query failed" in payload["reason"]


def test_endpoint_serves_payload(store: Path) -> None:
    _add_usage(store, "s-ep", fresh=1234, out=56, cache_read=789)
    data = plugin_api.get_token_usage(days=7)
    assert data["schema"] == "sips.token-usage.v1"
    assert data["available"] is True
    assert data["totals"]["fresh_input_tokens"] == 1234
    assert "claim_boundary" in data


def test_endpoint_days_clamped(store: Path) -> None:
    data = plugin_api.get_token_usage(days=999)
    assert data["window_days"] == 30
