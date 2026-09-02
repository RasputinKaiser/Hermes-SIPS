"""Tests for the /widgets endpoint and the inline_widget panel-facing probes."""

from __future__ import annotations

import sys
import types
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


def _stub_renderer_module(briefs: list[dict] | None = None, kinds: list[str] | None = None,
                         raise_on: str | None = None) -> types.ModuleType:
    stub = types.ModuleType("inline_widget")
    stub.widget_kinds = lambda: kinds if kinds is not None else ["board", "memory"]
    def _brief(kind):
        if raise_on and kind == raise_on:
            raise RuntimeError("boom")
        return {"kind": kind, "available": True}
    stub.widget_brief = _brief
    stub._briefs = briefs
    return stub


def test_widgets_endpoint_lists_kinds_with_briefs(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _stub_renderer_module()
    monkeypatch.setitem(sys.modules, "inline_widget", stub)
    payload = plugin_api.get_widgets()
    assert payload["schema"] == "sips.widgets.v1"
    assert payload["available"] is True
    assert payload["kinds"] == ["board", "memory"]
    assert [w["kind"] for w in payload["widgets"]] == ["board", "memory"]
    assert payload["claim_boundary"]


def test_widgets_endpoint_renderer_missing_is_honest(monkeypatch: pytest.MonkeyPatch) -> None:
    # None in sys.modules makes `import inline_widget` raise ImportError —
    # simulates the renderer module being absent from the deploy.
    monkeypatch.setitem(sys.modules, "inline_widget", None)
    payload = plugin_api.get_widgets()
    assert payload["available"] is False
    assert payload["kinds"] == []
    assert payload["note"]
    assert "unavailable" in payload["note"].lower() or "missing" in payload["note"].lower()
    assert payload["claim_boundary"]


def test_widgets_endpoint_renderer_failure_is_honest(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = _stub_renderer_module(raise_on="board")
    monkeypatch.setitem(sys.modules, "inline_widget", stub)
    payload = plugin_api.get_widgets()
    assert payload["available"] is False
    assert "boom" in payload["note"]


def test_widget_brief_real_module_available_kind(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import inline_widget

    def fake_loader() -> dict:
        return {"status": "active"}

    monkeypatch.setitem(inline_widget.RENDERERS, "board", (fake_loader, lambda data: "<html></html>"))
    brief = inline_widget.widget_brief("board")
    assert brief == {"kind": "board", "available": True}


def test_widget_brief_real_module_failing_kind_never_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import inline_widget

    def bad_loader() -> dict:
        raise FileNotFoundError("no hook stream")

    monkeypatch.setitem(inline_widget.RENDERERS, "lifecycle", (bad_loader, lambda data: "<html></html>"))
    brief = inline_widget.widget_brief("lifecycle")
    assert brief["available"] is False
    assert brief["kind"] == "lifecycle"
    assert brief["note"]


def test_widget_kinds_covers_every_renderer() -> None:
    import inline_widget

    assert inline_widget.widget_kinds() == sorted(inline_widget.RENDERERS)
    assert "board" in inline_widget.widget_kinds()
