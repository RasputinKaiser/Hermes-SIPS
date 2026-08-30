"""Tests for the fleet/run timeline (fleet_timeline.py + /timeline + card)."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DASHBOARD = _REPO_ROOT / "dashboard"
for _path in (str(_DASHBOARD), str(_REPO_ROOT / "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import fleet_timeline  # noqa: E402

try:
    import plugin_api  # noqa: E402
    import sips_chat_cards as cards  # noqa: E402
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise


def _write_run(runs_root: Path, run_id: str, *, events: int, age_s: float) -> None:
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(
        json.dumps({"event_type": "run.created", "payload": {}}) for _ in range(events)
    )
    (run_dir / "events.jsonl").write_text(lines + "\n", encoding="utf-8")
    import os

    stamp = time.time() - age_s
    os.utime(run_dir, (stamp, stamp))


@pytest.fixture()
def runs_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setattr(
        "sips_runtime.controller.runtime_root", lambda *_a, **_k: root, raising=False
    )
    monkeypatch.setattr(fleet_timeline, "_fleet_campaigns", lambda: [], raising=False)
    return root


def test_timeline_merges_runs_newest_first(runs_root: Path) -> None:
    _write_run(runs_root, "run-old", events=3, age_s=7200)
    _write_run(runs_root, "run-new", events=9, age_s=60)
    payload = fleet_timeline.timeline_payload()
    assert payload["available"] is True
    assert [e["id"] for e in payload["entries"]] == ["run-new", "run-old"]
    assert payload["window_hours"] >= 1


def test_timeline_includes_campaign_entries(runs_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_run(runs_root, "run-a", events=2, age_s=60)
    monkeypatch.setattr(
        fleet_timeline,
        "_fleet_campaigns",
        lambda: [{"campaign_id": "camp-1", "status": "active", "children": [1, 2], "updated_at": "2026-08-30T00:00:00+00:00"}],
    )
    payload = fleet_timeline.timeline_payload()
    kinds = {e["kind"] for e in payload["entries"]}
    assert kinds == {"run", "campaign"}
    camp = next(e for e in payload["entries"] if e["kind"] == "campaign")
    assert camp["children"] == 2 and camp["status"] == "active"


def test_timeline_bounds_entries(runs_root: Path) -> None:
    for i in range(30):
        _write_run(runs_root, f"run-{i:02d}", events=1, age_s=i * 60)
    payload = fleet_timeline.timeline_payload(limit=20)
    assert len(payload["entries"]) == 20
    assert payload["total_tracked"] == 30


def test_timeline_card_renders_runs_and_summary() -> None:
    payload = {
        "available": True,
        "entries": [
            {"kind": "run", "id": "h-20260829_213357_363c76", "status": "succeeded", "events": 10, "ts": time.time() - 300},
            {"kind": "campaign", "id": "camp-1", "status": "active", "children": 3, "ts": time.time() - 7200},
        ],
        "total_tracked": 2,
        "window_hours": 3,
        "claim_boundary": "bounded merge",
    }
    card = cards.timeline_card(payload)
    assert "🗓 Timeline" in card
    assert "🟢" in card and "succeeded" in card
    assert "🚩" in card and "campaign" in card and "`3` children" in card
    assert "**2 entries** (1 runs · 1 campaigns) over ~`3h`" in card
    assert "5m ago" in card or "2h ago" in card


def test_timeline_card_empty_and_unavailable() -> None:
    empty = cards.timeline_card({"available": True, "entries": [], "claim_boundary": "cb"})
    assert "No runtime runs or campaigns tracked yet" in empty
    un = cards.timeline_card({"available": False, "reason": "boom", "claim_boundary": "cb"})
    assert "boom" in un


def test_timeline_endpoint_serves(runs_root: Path) -> None:
    _write_run(runs_root, "run-ep", events=1, age_s=60)
    data = plugin_api.get_timeline()
    assert data["schema"] == "sips.timeline.v1"
    assert data["available"] is True
    assert data["entries"][0]["id"] == "run-ep"
