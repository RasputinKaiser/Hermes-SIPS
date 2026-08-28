#!/usr/bin/env python3
"""Retention/housekeeping for the SIPS state root ($SIPS_HOME).

Self-contained, stdlib-only, fail-open. Safe to run from a hook or cron:

  python3 sips_housekeeping.py [--dry-run]

What it does:
  (a) Archives $SIPS_HOME/hook_events.jsonl to $SIPS_HOME/logs/ when it
      exceeds a size threshold (default 5MB, override with
      SIPS_HOUSEKEEP_MAX_BYTES). The archive is a move named
      hook_events-YYYYMMDD-HHMMSS.jsonl; a fresh empty hook_events.jsonl
      is recreated. At most KEEP (default 3) archives are retained and
      archives older than ARCHIVE_MAX_AGE_DAYS (default 30) are removed.
  (b) Deletes zero-byte *.jsonl files under $SIPS_HOME/pending/ whose
      mtime is older than 7 days.
  (c) Deletes archive files in $SIPS_HOME/logs/ older than 30 days.

Prints exactly one bounded JSON summary line. Never prints file contents.
Every failure is swallowed and reported in the summary — the script never
raises, and a dry run removes nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_KEEP_ARCHIVES = 3
PENDING_MAX_AGE_SECONDS = 7 * 86400
ARCHIVE_MAX_AGE_SECONDS = 30 * 86400

_SUMMARY_KEYS = (
    "scanned",
    "archived_bytes",
    "pending_removed",
    "archives_removed",
    "dry_run",
)


def _empty_summary(dry_run: bool) -> dict[str, Any]:
    return {
        "scanned": 0,
        "archived_bytes": 0,
        "pending_removed": 0,
        "archives_removed": 0,
        "dry_run": bool(dry_run),
    }


def _int_env(name: str, default: int) -> int:
    try:
        raw = os.environ.get(name, "")
        value = int(raw) if raw.strip() else default
        return value if value > 0 else default
    except Exception:
        return default


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _prune_archives(logs_dir: Path, keep: int, now: float, dry_run: bool, summary: dict[str, Any]) -> None:
    try:
        archives = sorted(
            (p for p in logs_dir.glob("hook_events-*.jsonl") if p.is_file()),
            key=_mtime,
        )
    except OSError:
        return
    for archive in archives:
        # (c) Age-based archive cleanup: 30 days.
        if now - _mtime(archive) > ARCHIVE_MAX_AGE_SECONDS:
            summary["archives_removed"] += 1
            if not dry_run:
                try:
                    archive.unlink()
                except OSError:
                    summary["archives_removed"] -= 1
            continue
    # Count-bounded retention: newest `keep` archives survive.
    excess = archives[: max(len(archives) - max(keep, 0), 0)] if not dry_run else []
    for archive in excess:
        summary["archives_removed"] += 1
        try:
            archive.unlink()
        except OSError:
            summary["archives_removed"] -= 1


def run_housekeeping(sips_home: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    home = Path(sips_home or os.environ.get("SIPS_HOME") or Path.home() / ".hermes" / "sips")
    summary = _empty_summary(dry_run)
    now = time.time()
    max_bytes = _int_env("SIPS_HOUSEKEEP_MAX_BYTES", DEFAULT_MAX_BYTES)
    keep = _int_env("SIPS_HOUSEKEEP_KEEP_ARCHIVES", DEFAULT_KEEP_ARCHIVES)

    log_path = home / "hook_events.jsonl"
    logs_dir = home / "logs"
    pending_dir = home / "pending"

    # (a) Archive the append-only hook event log when it grows past the
    # threshold. Move, never copy, so the live file never doubles in size.
    try:
        size = log_path.stat().st_size if log_path.exists() else 0
        if size > max_bytes:
            timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
            archive_path = logs_dir / f"hook_events-{timestamp}.jsonl"
            if not dry_run:
                try:
                    logs_dir.mkdir(parents=True, exist_ok=True)
                    os.replace(log_path, archive_path)
                    log_path.touch()
                except OSError:
                    pass
            else:
                summary["scanned"] += 1
            summary["archived_bytes"] += size
    except OSError:
        pass

    if not dry_run:
        _prune_archives(logs_dir, keep, now, dry_run, summary)

    # (b) Zero-byte pending receipts older than 7 days are pure debris.
    try:
        if pending_dir.is_dir():
            for item in pending_dir.glob("*.jsonl"):
                summary["scanned"] += 1
                try:
                    if item.is_file() and item.stat().st_size == 0 and now - item.stat().st_mtime > PENDING_MAX_AGE_SECONDS:
                        summary["pending_removed"] += 1
                        if not dry_run:
                            item.unlink()
                except OSError:
                    summary["pending_removed"] = max(summary["pending_removed"] - 1, 0)
    except OSError:
        pass

    return {key: summary[key] for key in _SUMMARY_KEYS}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SIPS state-root housekeeping (fail-open).")
    parser.add_argument("--dry-run", action="store_true", help="Report what would happen; remove nothing.")
    args = parser.parse_args(argv)
    summary = run_housekeeping(dry_run=args.dry_run)
    sys.stdout.write(json.dumps(summary, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail-open: never break a caller (hook, cron, adapter) on any error.
        sys.stdout.write(json.dumps(_empty_summary(bool("--dry-run" in (sys.argv[1:] or []))), separators=(",", ":")) + "\n")
        sys.exit(0)
