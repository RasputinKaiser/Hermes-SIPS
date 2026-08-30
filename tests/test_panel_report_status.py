"""Tests for the /report-status endpoint (newest SIPS HTML report metadata)."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DASHBOARD = _REPO_ROOT / "dashboard"
for _path in (str(_DASHBOARD), str(_REPO_ROOT / "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    import plugin_api  # noqa: E402
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise

if not hasattr(plugin_api, "router"):  # pragma: no cover - defensive
    pytest.skip("fastapi not installed in this environment", allow_module_level=True)


@pytest.fixture()
def report_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    target = tmp_path / "report.html"
    monkeypatch.setattr(plugin_api, "_report_path", lambda: target, raising=False)
    return target


def test_report_status_available(report_path: Path) -> None:
    report_path.write_text("<html>SIPS Control Report</html>", encoding="utf-8")
    payload = plugin_api.get_report_status()
    assert payload["available"] is True
    assert payload["generated_at"] is not None
    assert isinstance(payload["age_hours"], float)
    assert payload["age_hours"] >= 0.0
    assert payload["path"] == str(report_path)
    assert payload["claim_boundary"]


def test_report_status_missing(report_path: Path) -> None:
    payload = plugin_api.get_report_status()
    assert payload["available"] is False
    assert "report" in (payload.get("note") or "").lower()
    assert payload["generated_at"] is None
    assert payload["claim_boundary"]


def test_report_status_age_matches_mtime(report_path: Path) -> None:
    report_path.write_text("<html></html>", encoding="utf-8")
    two_hours_ago = time.time() - 2 * 3600
    os.utime(report_path, (two_hours_ago, two_hours_ago))
    payload = plugin_api.get_report_status()
    assert 1.5 <= payload["age_hours"] <= 2.5
