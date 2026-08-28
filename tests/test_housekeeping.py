"""Tests for the SIPS state-root housekeeping script.

Each test uses an isolated SIPS_HOME sandbox (tmp_path) so no run state
leaks between tests or into a developer's live state root.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import sips_housekeeping as hk  # noqa: E402


@pytest.fixture()
def hk_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "sips-home"
    home.mkdir()
    (home / "logs").mkdir()
    (home / "pending").mkdir()
    (home / "hook_events.jsonl").write_text('{"event": "probe"}\n')
    monkeypatch.setenv("SIPS_HOME", str(home))
    return home


def _age(path: Path, days: float) -> None:
    old = time.time() - days * 86400
    os.utime(path, (old, old))


def test_oversize_log_archived_and_recreated(hk_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    big = hk_home / "hook_events.jsonl"
    monkeypatch.setenv("SIPS_HOUSEKEEP_MAX_BYTES", "1024")
    big.write_text("x" * 4096 + "\n")

    summary = hk.run_housekeeping(hk_home, dry_run=False)

    assert summary["archived_bytes"] == 4097
    archives = list((hk_home / "logs").glob("hook_events-*.jsonl"))
    assert len(archives) == 1
    # Archive is a move of the original payload, timestamped in UTC shape.
    assert archives[0].read_text() == "x" * 4096 + "\n"
    assert archives[0].name.startswith("hook_events-")
    stamp = archives[0].stem.removeprefix("hook_events-")
    assert len(stamp) == 15 and stamp[8] == "-"
    assert stamp[:8].isdigit() and stamp[9:].isdigit()
    # Live log recreated empty and small.
    assert big.exists()
    assert big.stat().st_size == 0


def test_small_log_not_archived(hk_home: Path) -> None:
    summary = hk.run_housekeeping(hk_home, dry_run=False)
    assert summary["archived_bytes"] == 0
    assert not list((hk_home / "logs").glob("hook_events-*.jsonl"))
    assert (hk_home / "hook_events.jsonl").stat().st_size > 0


def test_pending_zero_byte_old_removed_fresh_kept(hk_home: Path) -> None:
    pending = hk_home / "pending"
    stale = pending / "stale.jsonl"
    fresh = pending / "fresh.jsonl"
    nonzero = pending / "nonzero.jsonl"
    stale.touch()
    fresh.touch()
    nonzero.write_text("data\n")
    _age(stale, 8)
    _age(fresh, 1)
    _age(nonzero, 8)

    summary = hk.run_housekeeping(hk_home, dry_run=False)

    assert summary["pending_removed"] == 1
    assert not stale.exists()
    assert fresh.exists()
    assert nonzero.exists()


def test_dry_run_removes_nothing(hk_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIPS_HOUSEKEEP_MAX_BYTES", "16")
    (hk_home / "hook_events.jsonl").write_text("x" * 128 + "\n")
    stale = hk_home / "pending" / "stale.jsonl"
    stale.touch()
    _age(stale, 9)
    old_archive = hk_home / "logs" / "hook_events-20200101-000000.jsonl"
    old_archive.write_text("old\n")
    _age(old_archive, 40)

    summary = hk.run_housekeeping(hk_home, dry_run=True)

    assert summary["dry_run"] is True
    assert summary["archived_bytes"] == 129
    assert summary["pending_removed"] == 1
    assert (hk_home / "hook_events.jsonl").stat().st_size == 129
    assert stale.exists()
    assert old_archive.exists()
    assert not list((hk_home / "logs").glob("hook_events-2020*.jsonl")) or old_archive.exists()


def test_archive_retention_bounded(hk_home: Path) -> None:
    logs = hk_home / "logs"
    for i in range(5):
        archive = logs / f"hook_events-2020010{i}-000000.jsonl"
        archive.write_text("a\n")
        _age(archive, 1)
    (hk_home / "hook_events.jsonl").write_text("x" * 100)
    os.environ["SIPS_HOUSEKEEP_MAX_BYTES"] = "16"

    try:
        summary = hk.run_housekeeping(hk_home, dry_run=False)
    finally:
        os.environ.pop("SIPS_HOUSEKEEP_MAX_BYTES", None)

    assert summary["archived_bytes"] == 100
    remaining = sorted(logs.glob("hook_events-*.jsonl"))
    assert len(remaining) == 3  # keep default 3, oldest 2 pruned
    assert (hk_home / "hook_events.jsonl").stat().st_size == 0


def test_archive_age_cleanup(hk_home: Path) -> None:
    logs = hk_home / "logs"
    old_archive = logs / "hook_events-20200101-000000.jsonl"
    old_archive.write_text("old\n")
    _age(old_archive, 31)
    new_archive = logs / "hook_events-20200102-000000.jsonl"
    new_archive.write_text("new\n")
    _age(new_archive, 1)

    summary = hk.run_housekeeping(hk_home, dry_run=False)

    assert summary["archives_removed"] == 1
    assert not old_archive.exists()
    assert new_archive.exists()


def test_once_per_24h_guard(hk_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The adapter only invokes housekeeping once per 24h per process."""
    import importlib.util

    adapter_path = Path(__file__).resolve().parent.parent / "hermes_adapter.py"
    spec = importlib.util.spec_from_file_location("hermes_adapter_hk_test", adapter_path)
    adapter = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(adapter)

    monkeypatch.setenv("SIPS_HOUSEKEEP_MAX_BYTES", "16")
    (hk_home / "hook_events.jsonl").write_text("x" * 128 + "\n")

    calls: list[int] = []
    real_run = hk.run_housekeeping

    def counting_run(*args: object, **kwargs: object) -> dict:
        calls.append(1)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(hk, "run_housekeeping", counting_run)

    # Reset the module-level guard so this test starts fresh.
    adapter._HK_LAST_RUN = 0.0
    adapter._maybe_run_housekeeping()
    adapter._maybe_run_housekeeping()
    assert len(calls) == 1

    # Simulate 24h passing: the guard opens again.
    adapter._HK_LAST_RUN = time.time() - 24 * 86400 - 1
    adapter._maybe_run_housekeeping()
    assert len(calls) == 2
    assert adapter._HK_LAST_RUN > time.time() - 24 * 86400


def test_cli_summary_line(hk_home: Path, capsys: pytest.CaptureFixture) -> None:
    pending = hk_home / "pending"
    stale = pending / "stale.jsonl"
    stale.touch()
    _age(stale, 8)

    rc = hk.main(["--dry-run"])
    captured = capsys.readouterr()
    assert rc == 0
    lines = [line for line in captured.out.strip().splitlines() if line]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert set(payload) == {"scanned", "archived_bytes", "pending_removed", "archives_removed", "dry_run"}
    assert payload["dry_run"] is True
    assert payload["pending_removed"] == 1
