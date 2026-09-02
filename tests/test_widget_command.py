"""Smoke tests for the /sips-widget chat command handler."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
for _p in (str(_REPO_ROOT), str(_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import __init__ as plugin  # noqa: E402


class FakeHomebase:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, name, args):
        self.calls.append((name, args))
        if self.error is not None:
            raise self.error
        return {"structuredContent": self.result}


_PAYLOAD = {
    "schema": "sips.inline-widget.v1",
    "ok": True,
    "kind": "board",
    "path": "/tmp/sips/widgets/board-widget.html",
    "media": "MEDIA:/tmp/sips/widgets/board-widget.html",
    "directive": '::preview{file="/tmp/sips/widgets/board-widget.html"}',
}


def test_command_widget_returns_directive_on_its_own_line():
    hb = FakeHomebase(_PAYLOAD)
    out = plugin._command_widget(hb, "board")
    assert '::preview{file="/tmp/sips/widgets/board-widget.html"}' in out
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines[-1].startswith("::preview{file=")


def test_command_widget_defaults_to_board_kind():
    hb = FakeHomebase(_PAYLOAD)
    plugin._command_widget(hb, "")
    assert hb.calls[0][1] == {"kind": "board"}


def test_command_widget_failure_is_graceful():
    hb = FakeHomebase(error=RuntimeError("renderer missing"))
    out = plugin._command_widget(hb, "board")
    assert "unavailable" in out.lower()
    assert "::preview" not in out


def test_command_widget_unknown_kind_is_graceful():
    hb = FakeHomebase(error=KeyError("bogus"))
    out = plugin._command_widget(hb, "bogus")
    assert "unavailable" in out.lower() or "unknown" in out.lower()
    assert "::preview" not in out


def test_sips_help_line_lists_widget_command():
    direct_source = Path(plugin.__file__).read_text(encoding="utf-8")
    assert "sips-widget" in direct_source
