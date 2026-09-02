"""Tests for scripts/panel_self_report.py (plugin self-health snapshot)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_REPO_ROOT / "dashboard"), str(_REPO_ROOT / "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import panel_self_report as psr  # noqa: E402


@pytest.fixture()
def fake_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A fake repo root with manifest + a few watched files."""
    repo = tmp_path / "repo"
    (repo / "dashboard" / "desktop").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "dashboard" / "manifest.json").write_text(json.dumps({"version": "0.21.0"}), encoding="utf-8")
    (repo / "dashboard" / "plugin_api.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "dashboard" / "desktop" / "plugin.js").write_text("// js\n", encoding="utf-8")
    (repo / "scripts" / "harness_homebase_mcp.py").write_text("x = 2\n", encoding="utf-8")
    monkeypatch.setattr(psr, "REPO_ROOT", repo)
    monkeypatch.setattr(psr, "OUTPUT_PATH", tmp_path / "panel_self_report.json")
    return repo


def test_report_written_and_schema(fake_repo: Path, tmp_path: Path) -> None:
    payload = psr.main()
    assert payload is not None
    assert payload["schema"] == "sips.panel_self_report.v1"
    assert payload["manifest_version"] == "0.21.0"
    on_disk = json.loads((tmp_path / "panel_self_report.json").read_text(encoding="utf-8"))
    assert on_disk["schema"] == payload["schema"]
    assert "ts" in on_disk


def test_report_contains_endpoints_and_gates(fake_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Gates and endpoint discovery are environment-dependent; stub both and
    # assert main() threads them into the payload. (Real-import smoke run
    # happens in test_silent_on_bad_repo via the missing-repo branch and in
    # the deploy verification step.)
    monkeypatch.setattr(psr, "_gate", lambda name: name == "esbuild")
    monkeypatch.setattr(psr, "_endpoints", lambda: ["/report-status", "/verdicts"])
    payload = psr.main()
    assert payload["gates"] == {"pytest": False, "esbuild": True}
    assert "/report-status" in payload["endpoints"]
    assert "/verdicts" in payload["endpoints"]


def test_drift_detects_newer_repo_files(fake_repo: Path, tmp_path: Path) -> None:
    deployed = tmp_path / "deployed" / "harness-self-improvement"
    deployed.mkdir(parents=True)
    import shutil

    shutil.copy(fake_repo / "dashboard" / "plugin_api.py", deployed / "plugin_api.py")
    shutil.copy(fake_repo / "dashboard" / "desktop" / "plugin.js", deployed / "plugin.js")
    monkey_like_deployed = [("dashboard/plugin_api.py", deployed / "plugin_api.py")]
    drift = psr._drift_map(fake_repo, monkey_like_deployed)
    assert drift["dashboard/plugin_api.py"] is False
    # Identical content with a newer mtime is NOT drift (rsync -a keeps mtimes
    # only to whole seconds, so mtime comparison false-positives on equal files).
    import os
    import time

    newer = time.time() + 10
    os.utime(fake_repo / "dashboard" / "plugin_api.py", (newer, newer))
    drift = psr._drift_map(fake_repo, monkey_like_deployed)
    assert drift["dashboard/plugin_api.py"] is False
    # Different content is drift even when the deployed copy has a newer mtime.
    time.sleep(0.01)
    (deployed / "plugin_api.py").write_text("# stale deployed copy\n", encoding="utf-8")
    drift = psr._drift_map(fake_repo, monkey_like_deployed)
    assert drift["dashboard/plugin_api.py"] is True


def test_silent_on_bad_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(psr, "REPO_ROOT", tmp_path / "missing")
    monkeypatch.setattr(psr, "OUTPUT_PATH", tmp_path / "out.json")
    payload = psr.main()
    assert payload is None or payload.get("schema") == "sips.panel_self_report.v1"
    # Either way: no crash.
