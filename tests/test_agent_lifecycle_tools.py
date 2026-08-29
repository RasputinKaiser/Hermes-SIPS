"""Tests for the agent-side lifecycle lens and board snapshot MCP tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_REPO_ROOT / "scripts"),):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import harness_homebase_mcp as hb  # noqa: E402


@pytest.fixture()
def sips_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(hb, "hook_events_path", lambda: tmp_path / "hook_events.jsonl", raising=False)
    (tmp_path / "scripts").mkdir(exist_ok=True)
    return tmp_path


def _hook_event(**overrides: object) -> dict:
    base = {
        "schema": "hermes.sips.event.v1",
        "id": "test-event",
        "ts": "2026-08-29T02:00:00+00:00",
        "event": "post_tool_call",
        "session_id": "s-1",
        "tool_name": "terminal",
        "status": "ok",
    }
    base.update(overrides)
    return base


def _write_hook_events(events: list[dict], sips_root: Path) -> None:
    (sips_root / "hook_events.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8"
    )


def test_tool_catalog_declares_new_tools() -> None:
    names = {tool["name"] for tool in hb.TOOLS}
    assert "homebase_lifecycle" in names
    assert "homebase_board_snapshot" in names
    for tool in hb.TOOLS:
        if tool["name"] in ("homebase_lifecycle", "homebase_board_snapshot"):
            assert tool["annotations"]["readOnlyHint"] is True
            assert tool["annotations"]["destructiveHint"] is False


def test_call_tool_homebase_lifecycle_returns_bounded_summary(sips_root: Path) -> None:
    _write_hook_events(
        [
            _hook_event(),
            _hook_event(status="error"),
            _hook_event(event="on_session_start"),
        ],
        sips_root,
    )

    result = hb.call_tool("homebase_lifecycle", {})
    payload = result["structuredContent"]
    markdown = result["content"][0]["text"]

    assert payload["available"] is True
    assert payload["window_events"] == 3
    tools = {row["tool"]: row for row in payload["tools"]}
    assert tools["terminal"]["total"] == 2
    assert tools["terminal"]["issues"] == 1
    assert payload["histogram"] and payload["histogram"][0]["hour"] == "2026-08-29T02"
    assert "# SIPS Lifecycle Lens" in markdown
    assert "**terminal** `2 calls (1 issues)`" in markdown


def test_call_tool_homebase_lifecycle_window_bounds(sips_root: Path) -> None:
    _write_hook_events([_hook_event()], sips_root)

    ok = hb.call_tool("homebase_lifecycle", {"window": 100})
    assert ok["structuredContent"]["available"] is True

    with pytest.raises(hb.JsonRpcError):
        hb.call_tool("homebase_lifecycle", {"window": 50})
    with pytest.raises(hb.JsonRpcError):
        hb.call_tool("homebase_lifecycle", {"window": 9000})


def test_call_tool_homebase_lifecycle_unavailable(sips_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # No stream file written under sips_root and hook_events_path points there.
    result = hb.call_tool("homebase_lifecycle", {})
    payload = result["structuredContent"]
    assert payload["available"] is False
    assert "unavailable" in result["content"][0]["text"]


def test_board_snapshot_joins_board_goal_lifecycle(sips_root: Path) -> None:
    _write_hook_events([_hook_event()], sips_root)
    # Minimal goal_state stub so the subprocess call succeeds.
    goal_state = sips_root / "scripts" / "goal_state.py"
    goal_state.write_text(
        "import json, sys\n"
        "print(json.dumps({'status': 'active', 'mode': 'legacy', 'focus': 'panel', 'objective': 'test'}))\n",
        encoding="utf-8",
    )

    result = hb.call_tool("homebase_board_snapshot", {})
    payload = result["structuredContent"]
    markdown = result["content"][0]["text"]

    assert payload["schema"] == "sips.board-snapshot.v1"
    assert "board" in payload and "goal" in payload and "lifecycle" in payload
    assert payload["lifecycle"]["available"] is True
    assert payload["lifecycle"]["top_tools"][0]["tool"] == "terminal"
    assert payload["goal"].get("mode") == "selfloop"  # from the goal_state stub's resolve_mode default
    assert "# SIPS Board Snapshot" in markdown
    assert "**top tool** `terminal x1`" in markdown


def test_board_snapshot_degrades_without_goal_state(sips_root: Path) -> None:
    _write_hook_events([_hook_event()], sips_root)

    result = hb.call_tool("homebase_board_snapshot", {})
    payload = result["structuredContent"]
    # Goal state missing -> empty goal, but the snapshot itself stays usable.
    assert payload["goal"] == {} or "objective" in payload["goal"]
    assert payload["claim_boundary"]


def test_lifecycle_markdown_renders_bars_and_sparkline(sips_root: Path) -> None:
    _write_hook_events(
        [
            _hook_event(ts="2026-08-29T02:10:00+00:00"),
            _hook_event(ts="2026-08-29T02:20:00+00:00"),
            _hook_event(ts="2026-08-29T02:30:00+00:00"),
            _hook_event(ts="2026-08-29T03:10:00+00:00"),
        ],
        sips_root,
    )

    result = hb.call_tool("homebase_lifecycle", {})
    markdown = result["content"][0]["text"]

    assert "█" in markdown  # tool bars
    assert "▁" in markdown or "█" in markdown.split("**activity**")[1][:20]  # sparkline
    assert "◐" in markdown  # session glyph


def test_bar_of_max_gives_nonzero_values_a_visible_floor() -> None:
    assert hb._bar_of_max(1, [100, 1]) == "█░░░░░░░░░"
    assert hb._bar_of_max(100, [100, 1]) == "██████████"
    assert hb._bar_of_max(0, [100, 1]) == "░░░░░░░░░░"


def test_fmt_value_never_dumps_collections() -> None:
    assert hb._fmt_value({"a": 1}) == "dict(1 keys)"
    assert hb._fmt_value([1, 2, 3]) == "list(3 items)"
    assert hb._fmt_value("x" * 200).endswith("…")
    assert len(hb._fmt_value("x" * 200)) <= 91


def test_homebase_status_renders_lifecycle_section(sips_root: Path) -> None:
    _write_hook_events([_hook_event()], sips_root)

    payload = hb.status_payload(sips_root)
    payload["lifecycle"] = hb.lifecycle_summary(sips_root)
    markdown = hb.render(payload, "Harness Homebase Status")
    assert "## Lifecycle Lens" in markdown
    assert "**terminal** `1 calls`" in markdown
