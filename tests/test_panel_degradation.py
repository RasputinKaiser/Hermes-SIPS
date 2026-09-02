"""Degradation-contract tests: no SIPS endpoint returns a bare empty success.

The panel renders every card from these payloads; a healthy-but-empty
collection without a note renders as a bare [] and reads as a bug. Every
empty state must explain itself (empty_note), every failure must be
available:false with a reason.
"""

from __future__ import annotations

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
except ImportError as _exc:  # pragma: no cover - fastapi absent in CI
    if "fastapi" in str(_exc):
        pytest.skip("fastapi not installed in this environment", allow_module_level=True)
    raise


@pytest.fixture()
def empty_sips_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("SIPS_HOME", str(tmp_path))
    (tmp_path / "runtime" / "v1" / "runs").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_timeline_empty_state_carries_note(empty_sips_home: Path) -> None:
    from fleet_timeline import timeline_payload

    payload = timeline_payload()
    assert payload["available"] is True
    assert payload["entries"] == []
    assert payload.get("empty_note"), "empty timeline must explain itself"


def test_runs_empty_state_carries_note(empty_sips_home: Path) -> None:
    runs = plugin_api.get_runs()
    assert runs["available"] is True
    assert runs["runs"] == []
    assert runs.get("empty_note"), "empty runs history must explain itself"


def test_runs_failure_is_honest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import sips_runtime.controller as controller

    def boom(root=None):  # noqa: ANN001, ARG001
        raise RuntimeError("no runtime")

    monkeypatch.setattr(controller, "runtime_root", boom)
    runs = plugin_api.get_runs()
    assert runs["available"] is False
    assert runs["reason"]


def test_runs_populated_state_has_no_empty_note(empty_sips_home: Path) -> None:
    import json
    import os
    import time

    run_dir = empty_sips_home / "runtime" / "v1" / "runs" / "run-demo"
    run_dir.mkdir(parents=True)
    (run_dir / "events.jsonl").write_text(
        json.dumps({"event_type": "run.created", "payload": {"objective": "demo", "tasks": []}}) + "\n",
        encoding="utf-8",
    )
    past = time.time() - 7200
    os.utime(run_dir / "events.jsonl", (past, past))
    runs = plugin_api.get_runs()
    assert runs["available"] is True
    assert len(runs["runs"]) == 1
    assert "empty_note" not in runs, "populated runs must not carry an empty note"


def test_widget_and_strip_payloads_carry_claim_boundary() -> None:
    # Contract: every card-facing payload names its claim boundary.
    assert plugin_api.get_widgets()["claim_boundary"]
    strip = plugin_api.get_overview_strip()
    assert strip["claim_boundary"]
    for leg in ("goal", "fleet", "verdicts", "memory"):
        assert leg in strip
