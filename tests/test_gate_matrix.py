"""Tests for the gate-evidence matrix (gate_matrix.py + /gate-matrix endpoint).

Isolated: each test builds its own runtime runs tree via monkeypatched
runtime_root; no live state under ~/.hermes/sips is touched.
"""

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

try:
    import plugin_api  # noqa: E402
    import gate_matrix  # noqa: E402
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise


def _write_run(runs_root: Path, run_id: str, gates: dict | None, *, age_s: float = 0.0) -> None:
    run_dir = runs_root / run_id
    (run_dir / "receipts").mkdir(parents=True, exist_ok=True)
    if gates is not None:
        receipt = {"gates": gates}
        (run_dir / "receipts" / "graph-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    stamp = time.time() - age_s
    import os
    os.utime(run_dir, (stamp, stamp))


@pytest.fixture()
def runs_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    root = tmp_path / "runs"
    root.mkdir()
    monkeypatch.setattr(
        "sips_runtime.controller.runtime_root", lambda *_a, **_k: root, raising=False
    )
    monkeypatch.setattr(gate_matrix, "_MAX_RUNS", 12, raising=False)
    return root


def test_matrix_maps_receipt_gates_to_normalized_cells(runs_root: Path) -> None:
    _write_run(runs_root, "run-ok", {
        "integrity": "ok", "correctness": "pass", "regression": "ok",
        "resource": {"status": "ok"}, "benefit": "satisfied",
    })
    payload = gate_matrix.gate_matrix_payload()
    assert payload["available"] is True
    assert payload["gates"] == ["integrity", "correctness", "regression", "resource", "benefit"]
    row = payload["runs"][0]
    assert row["run_id"] == "run-ok" and row["receipt"] is True
    assert all(row["gates"][g] == "ok" for g in payload["gates"])
    assert row["ok_count"] == 5 and row["failed_count"] == 0


def test_matrix_normalizes_failures_and_partials(runs_root: Path) -> None:
    _write_run(runs_root, "run-mixed", {
        "integrity": "ok", "correctness": "failed", "regression": "warn",
        "resource": "skipped", "benefit": "",
    })
    row = gate_matrix.gate_matrix_payload()["runs"][0]
    assert row["gates"]["correctness"] == "failed"
    assert row["gates"]["regression"] == "partial"
    assert row["gates"]["resource"] == "skipped"
    assert row["gates"]["benefit"] is None  # empty -> omitted -> null cell
    assert row["failed_count"] == 1 and row["ok_count"] == 1


def test_matrix_shows_recent_receiptless_runs_as_not_gated(runs_root: Path) -> None:
    _write_run(runs_root, "run-active", None, age_s=60)
    payload = gate_matrix.gate_matrix_payload()
    row = payload["runs"][0]
    assert row["receipt"] is False
    assert all(v is None for v in row["gates"].values())


def test_matrix_drops_old_receiptless_runs(runs_root: Path) -> None:
    _write_run(runs_root, "run-dead", None, age_s=8 * 86400)
    payload = gate_matrix.gate_matrix_payload()
    assert payload["runs"] == []


def test_matrix_orders_recent_first_and_bounds(runs_root: Path) -> None:
    for i in range(15):
        _write_run(runs_root, f"run-{i:02d}", {"integrity": "ok"}, age_s=i * 60)
    payload = gate_matrix.gate_matrix_payload(limit=12)
    assert len(payload["runs"]) == 12
    assert payload["runs"][0]["run_id"] == "run-00"  # newest first


def test_matrix_handles_corrupt_receipt(runs_root: Path) -> None:
    run_dir = runs_root / "run-corrupt"
    (run_dir / "receipts").mkdir(parents=True)
    (run_dir / "receipts" / "graph-receipt.json").write_text("{not json", encoding="utf-8")
    payload = gate_matrix.gate_matrix_payload()
    # Corrupt receipt = unreadable -> treated as receiptless recent run
    assert payload["runs"][0]["receipt"] is False


def test_endpoint_serves_matrix(runs_root: Path) -> None:
    _write_run(runs_root, "run-ep", {"integrity": "ok"})
    data = plugin_api.get_gate_matrix()
    assert data["schema"] == "sips.gate-matrix.v1"
    assert data["available"] is True
    assert data["runs"][0]["gates"]["integrity"] == "ok"


def test_matrix_reads_real_session_receipt_shape(runs_root: Path) -> None:
    """Shape 3: structured.quality.<task>.gates = [{name, ok}, ...]."""
    run_dir = runs_root / "run-real"
    rec_dir = run_dir / "receipts"
    rec_dir.mkdir(parents=True)
    receipt = {
        "structured": {
            "quality": {
                "session": {
                    "gates": [
                        {"name": "integrity", "ok": True},
                        {"name": "correctness", "ok": True},
                        {"name": "regression", "ok": True},
                        {"name": "resource", "ok": True},
                        {"name": "benefit", "ok": True},
                    ]
                }
            }
        }
    }
    (rec_dir / "graph-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    row = gate_matrix.gate_matrix_payload()["runs"][0]
    assert row["receipt"] is True
    assert all(row["gates"][g] == "ok" for g in gate_matrix.GATE_ORDER)


def test_matrix_merges_multi_task_gate_failures(runs_root: Path) -> None:
    """A gate fails if ANY task's instance failed; ok only if all ok."""
    run_dir = runs_root / "run-multi"
    rec_dir = run_dir / "receipts"
    rec_dir.mkdir(parents=True)
    receipt = {
        "structured": {
            "quality": {
                "task-a": {"gates": [{"name": "integrity", "ok": True}, {"name": "benefit", "ok": True}]},
                "task-b": {"gates": [{"name": "integrity", "ok": False}, {"name": "benefit", "ok": True}]},
            }
        }
    }
    (rec_dir / "graph-receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    row = gate_matrix.gate_matrix_payload()["runs"][0]
    assert row["gates"]["integrity"] == "failed"
    assert row["gates"]["benefit"] == "ok"
    assert row["failed_count"] == 1 and row["ok_count"] == 1
