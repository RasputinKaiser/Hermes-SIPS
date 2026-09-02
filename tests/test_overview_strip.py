"""Tests for the /overview-strip composed glance endpoint."""

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


def _stub_verdicts_module(payload: dict) -> types.ModuleType:
    stub = types.ModuleType("tool_latency")
    stub.verdicts_payload = lambda window_hours=24: payload
    stub.tool_latency_payload = lambda window_hours=24: {}
    return stub


@pytest.fixture()
def healthy_legs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        plugin_api,
        "_goal_summary",
        lambda: {
            "available": True,
            "status": "active",
            "objective": "test objective",
            "subtasks": {"total": 4, "done": 2, "pending": 2, "failed": 0},
        },
        raising=False,
    )
    monkeypatch.setattr(
        plugin_api,
        "_memory_summary",
        lambda: {"available": True, "record_count": 10, "verified_or_active_count": 8},
        raising=False,
    )
    monkeypatch.setattr(
        plugin_api,
        "get_fleet",
        lambda: {
            "schema": "sips.fleet.view.v1",
            "available": True,
            "total": 2,
            "campaigns": [
                {"campaign_id": "a", "status": "active", "child_count": 2},
                {"campaign_id": "b", "status": "archived", "child_count": 1},
            ],
        },
        raising=False,
    )
    monkeypatch.setitem(
        sys.modules,
        "tool_latency",
        _stub_verdicts_module(
            {
                "schema": "sips.verdicts.v1",
                "available": True,
                "window_hours": 24,
                "verdicts": [
                    {"tool": "vision_analyze", "verdict": "stalled", "calls": 3, "denials": 0, "p95_ms": 240000, "median_ms": 200000},
                    {"tool": "terminal", "verdict": "ok", "calls": 40, "denials": 0, "p95_ms": 900, "median_ms": 400},
                ],
            }
        ),
    )


def test_strip_all_legs_present(healthy_legs) -> None:
    strip = plugin_api.get_overview_strip()
    assert strip["schema"] == "sips.overview-strip.v1"
    assert strip["available"] is True
    assert strip["claim_boundary"]
    assert strip["goal"]["available"] is True
    assert strip["goal"]["progress_pct"] == 50
    assert strip["goal"]["status"] == "active"
    assert strip["fleet"]["available"] is True
    assert strip["fleet"]["total"] == 2
    assert strip["fleet"]["statuses"] == {"active": 1, "archived": 1}
    assert strip["verdicts"]["available"] is True
    assert strip["verdicts"]["worst_tool"] == "vision_analyze"
    assert strip["verdicts"]["worst_verdict"] == "stalled"
    assert strip["memory"]["available"] is True
    assert strip["memory"]["record_count"] == 10


def test_strip_leg_degrades_independently(healthy_legs, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> dict:
        raise RuntimeError("goal read exploded")

    monkeypatch.setattr(plugin_api, "_goal_summary", boom, raising=False)
    strip = plugin_api.get_overview_strip()
    assert strip["goal"]["available"] is False
    assert "goal" in strip["goal"]["note"].lower()
    assert "RuntimeError" in strip["goal"]["note"]
    # Other legs unaffected; top-level still available.
    assert strip["fleet"]["available"] is True
    assert strip["verdicts"]["available"] is True
    assert strip["available"] is True


def test_strip_all_legs_degraded_never_500(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> dict:
        raise RuntimeError("nope")

    monkeypatch.setattr(plugin_api, "_goal_summary", boom, raising=False)
    monkeypatch.setattr(plugin_api, "_memory_summary", boom, raising=False)
    monkeypatch.setattr(plugin_api, "get_fleet", boom, raising=False)
    monkeypatch.setitem(sys.modules, "tool_latency", types.ModuleType("tool_latency_missing_attr"))
    strip = plugin_api.get_overview_strip()
    assert strip["available"] is False
    for leg in ("goal", "fleet", "verdicts", "memory"):
        assert strip[leg]["available"] is False
        assert strip[leg]["note"]


def test_strip_progress_pct_zero_when_no_subtasks(healthy_legs, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        plugin_api,
        "_goal_summary",
        lambda: {
            "available": True,
            "status": "active",
            "objective": "empty",
            "subtasks": {"total": 0, "done": 0, "pending": 0, "failed": 0},
        },
        raising=False,
    )
    strip = plugin_api.get_overview_strip()
    assert strip["goal"]["progress_pct"] == 0


def test_strip_verdicts_leg_missing_payload_is_honest(monkeypatch: pytest.MonkeyPatch) -> None:
    # verdicts payload returns available:false (no stream) — strip must pass that
    # through as an honest degraded leg, not fabricate zeros.
    monkeypatch.setattr(
        plugin_api, "_goal_summary", lambda: {"available": False, "status": "none"}, raising=False
    )
    monkeypatch.setattr(
        plugin_api, "_memory_summary", lambda: {"available": True, "record_count": 0}, raising=False
    )
    monkeypatch.setattr(
        plugin_api,
        "get_fleet",
        lambda: {"available": False, "reason": "fleet unavailable: RuntimeError", "campaigns": []},
        raising=False,
    )
    monkeypatch.setitem(
        sys.modules,
        "tool_latency",
        _stub_verdicts_module({"available": False, "verdicts": [], "note": "no hook stream"}),
    )
    strip = plugin_api.get_overview_strip()
    assert strip["verdicts"]["available"] is False
    assert strip["verdicts"]["note"]
    assert strip["available"] is True  # memory leg still alive
