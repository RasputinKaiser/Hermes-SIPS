#!/usr/bin/env python3
"""Plugin self-report: the SIPS plugin snapshots its own health to disk.

Every improvement round should start from evidence, not re-discovery. This
script writes one bounded JSON snapshot the next round can read:

- manifest version
- gate status (pytest, esbuild) as observed right now
- the plugin's exposed API endpoints
- repo-vs-deployed mtime drift for the hot files (repo newer => deployed copy
  is stale and a deploy is due)

Read-only except one JSON write to ``$SIPS_HOME/panel_self_report.json``.
Silent on failure: return None, exit 0, never break a session that runs it.
Run via ``python3 scripts/panel_self_report.py`` (or a cron tick).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = Path(os.environ.get("SIPS_HOME") or (Path.home() / ".hermes" / "sips")) / "panel_self_report.json"

# repo-relative path -> deployed absolute path (deploy mapping lives HERE so
# the report can never disagree with it)
_DEPLOYED_BASE = Path.home() / ".hermes" / "plugins" / "harness-self-improvement"
_WATCHED: list[tuple[str, Path]] = [
    ("dashboard/plugin_api.py", _DEPLOYED_BASE / "dashboard" / "plugin_api.py"),
    ("dashboard/desktop/plugin.js", Path.home() / ".hermes" / "desktop-plugins" / "harness-self-improvement" / "plugin.js"),
    ("scripts/harness_homebase_mcp.py", _DEPLOYED_BASE / "scripts" / "harness_homebase_mcp.py"),
    ("scripts/tool_latency.py", _DEPLOYED_BASE / "scripts" / "tool_latency.py"),
    ("scripts/panel_self_report.py", _DEPLOYED_BASE / "scripts" / "panel_self_report.py"),
]

_TIMEOUT_S = 120


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _manifest_version(repo: Path) -> str | None:
    try:
        return str(json.loads((repo / "dashboard" / "manifest.json").read_text(encoding="utf-8")).get("version"))
    except Exception:
        return None


def _endpoints() -> list[str]:
    """Endpoint paths exposed by plugin_api's router (import-side, bounded)."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "dashboard"))
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        import plugin_api  # type: ignore[no-redef]

        return sorted({route.path for route in plugin_api.router.routes})
    except Exception:
        return []


def _gate(name: str) -> bool:
    """Run one repo gate; True only on clean exit."""
    try:
        if name == "pytest":
            cmd = [sys.executable, "-m", "pytest", "-q"]
        elif name == "esbuild":
            cmd = ["npx", "esbuild", "--loader:.js=jsx", "--jsx=automatic", "--outfile=/dev/null", "dashboard/desktop/plugin.js"]
        else:
            return False
        result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, timeout=_TIMEOUT_S)
        return result.returncode == 0
    except Exception:
        return False


def _drift_map(repo: Path, watched: list[tuple[str, Path]] | None = None) -> dict[str, bool]:
    """repo-relative -> True when the deployed twin's content differs from the repo copy.

    Content-based, not mtime-based: rsync -a preserves mtimes only to whole-second
    precision, so comparing mtimes false-positives on byte-identical files whose
    sub-second components differ.
    """
    drift: dict[str, bool] = {}
    for rel, deployed in watched or _WATCHED:
        repo_file = repo / rel
        try:
            repo_bytes = repo_file.read_bytes()
        except OSError:
            continue
        try:
            drift[rel] = deployed.read_bytes() != repo_bytes
        except OSError:
            drift[rel] = True  # deployed twin missing entirely
    return drift


def main() -> dict[str, Any] | None:
    try:
        payload = {
            "schema": "sips.panel_self_report.v1",
            "ts": _now(),
            "manifest_version": _manifest_version(REPO_ROOT),
            "gates": {"pytest": _gate("pytest"), "esbuild": _gate("esbuild")},
            "endpoints": _endpoints(),
            "deployed_mtime_vs_repo": _drift_map(REPO_ROOT),
            "notes": [],
        }
        _write(payload)
        return payload
    except Exception:
        return None


def _write(payload: dict[str, Any] | None) -> None:
    if payload is None:
        return
    try:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    _report = main()
    if _report is not None:
        print(json.dumps({"wrote": str(OUTPUT_PATH), "manifest_version": _report["manifest_version"]}))
