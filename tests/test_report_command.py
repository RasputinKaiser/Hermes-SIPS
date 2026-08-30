"""Smoke tests for the /sips-report chat command handler."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
for _p in (str(_REPO_ROOT), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import __init__ as plugin  # noqa: E402
import html_report  # the top-level module the handler's fallback import binds # noqa: E402


def test_command_report_returns_media_path(monkeypatch, tmp_path):
    monkeypatch.setattr(html_report, "_REPORT_PATH", tmp_path / "report.html")
    out = plugin._command_report(None, "")
    assert "MEDIA:" in out
    assert str(tmp_path / "report.html") in out
    assert (tmp_path / "report.html").exists()


def test_command_report_failure_is_graceful(monkeypatch):
    def boom():
        raise RuntimeError("session store unreadable")

    monkeypatch.setattr(html_report, "generate_report", boom)
    out = plugin._command_report(None, "")
    assert "failed" in out.lower() and "MEDIA:" not in out
