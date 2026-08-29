"""Tests for the run-quality lens (run_quality.py + /runs/{id}/quality)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DASHBOARD = _REPO_ROOT / "dashboard"
for _path in (str(_DASHBOARD), str(_REPO_ROOT / "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    import plugin_api  # noqa: E402
    import run_quality  # noqa: E402
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise


def _write_receipt(runs_root: Path, run_id: str, receipt: dict) -> None:
    rec_dir = runs_root / run_id / "receipts"
    rec_dir.mkdir(parents=True, exist_ok=True)
    (rec_dir / "graph-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")


@pytest.fixture()
def runs_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setattr(
        "sips_runtime.controller.runtime_root", lambda *_a, **_k: root, raising=False
    )
    return root


def _session_receipt(gates: list[dict], *, impact: str = "normal") -> dict:
    return {
        "status": "succeeded",
        "structured": {
            "quality": {
                "session": {
                    "impact": impact,
                    "risk_tags": ["memory"],
                    "reviewer_tags": ["security"],
                    "failed_gates": [g["name"] for g in gates if g.get("ok") is False],
                    "evidence_required": True,
                    "gates": gates,
                }
            },
            "budget_usage": {"charged_tokens": 123456, "released_token_limit": 4000000},
        },
    }


def test_quality_lens_extracts_gates_evidence_and_tags(runs_root: Path) -> None:
    _write_receipt(runs_root, "run-q", _session_receipt([
        {"name": "integrity", "ok": True, "evidence": [{"evidence_path": "/x/hook_events.jsonl", "count": 634, "status": "passed"}]},
        {"name": "correctness", "ok": True},
        {"name": "regression", "ok": True},
        {"name": "resource", "ok": True},
        {"name": "benefit", "ok": True},
    ]))
    payload = run_quality.run_quality_payload("run-q")
    assert payload["available"] is True
    assert payload["status"] == "succeeded"
    assert payload["impact"] == "normal"
    assert payload["risk_tags"] == ["memory"]
    assert payload["failed_gates"] == []
    assert [g["name"] for g in payload["gates"]] == list(run_quality.GATE_ORDER)
    integrity = payload["gates"][0]
    assert integrity["status"] == "ok" and integrity["evidence_total"] == 634
    assert payload["budget_usage"] == {"charged_tokens": 123456, "released_token_limit": 4000000}


def test_quality_lens_merges_multi_task_failures(runs_root: Path) -> None:
    _write_receipt(runs_root, "run-multi", {
        "status": "failed",
        "structured": {
            "quality": {
                "task-a": {"gates": [{"name": "integrity", "ok": True}, {"name": "benefit", "ok": True}]},
                "task-b": {"gates": [{"name": "integrity", "ok": False, "reasons": ["digest mismatch"]}]},
            }
        },
    })
    payload = run_quality.run_quality_payload("run-multi")
    gates = {g["name"]: g for g in payload["gates"]}
    assert gates["integrity"]["status"] == "failed"
    assert "digest mismatch" in gates["integrity"]["reasons"][0]
    assert gates["benefit"]["status"] == "ok"
    assert payload["failed_gates"] == ["integrity"]


def test_quality_lens_fails_closed(runs_root: Path) -> None:
    missing = run_quality.run_quality_payload("no-such-run")
    assert missing["available"] is False and "no graph receipt" in missing["reason"]
    # invalid id rejected by the safe-identifier guard
    invalid = run_quality.run_quality_payload("../escape")
    assert invalid["available"] is False


def test_quality_endpoint_serves_payload(runs_root: Path) -> None:
    _write_receipt(runs_root, "run-ep", _session_receipt([{"name": "integrity", "ok": True}]))
    data = plugin_api.get_run_quality("run-ep")
    assert data["schema"] == "sips.run-quality.v1"
    assert data["available"] is True
    assert data["gates"][0]["name"] == "integrity"
