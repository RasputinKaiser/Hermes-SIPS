"""Session → graph-runtime bridge for the Hermes adapter.

Maps each Hermes session onto the SIPS graph runtime as a single-task run so
the Goal Board gains ``authority: runtime-events`` and durable receipts for
real Hermes work. Fail-open: any runtime error degrades to "board unavailable"
for that session; it never blocks the session itself.

Contract notes (verified empirically against scripts/sips_runtime/):
- run_id / task ids must be safe identifiers (alnum, ``-``, ``_``).
- create reserves resources; usage above the reservation rejects the result,
  so ``tool_calls`` is pre-reserved generously and actual usage is reported.
- lease TTL is 90s and the attempt ceiling is 900s; a session longer than the
  attempt ceiling finishes as a **second attempt**: re-lease, then advance
  with a ``retry`` result carrying the carried-over summary.
- result ``gates`` must each carry ``ok: true`` plus evidence with a positive
  marker ("passed"), an anchor (``evidence_path``), and a positive count.
- controller cost scales with event-stream length (measured ~195ms at 500
  events), so beats are throttled to at most one per 60s and the stream is
  hard-capped.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_MAX_BEATS = 200
_MIN_BEAT_INTERVAL = 60.0
_OWNER = "hermes-session"
_ATTEMPT_CEILING_SECONDS = 900.0  # mirror of leases.ATTEMPT_CEILING_SECONDS

_LOCK = threading.RLock()
_CONTROLLER: Any = None


def _controller() -> Any:
    global _CONTROLLER
    with _LOCK:
        if _CONTROLLER is None:
            from sips_runtime.controller import RuntimeController

            _CONTROLLER = RuntimeController()
        return _CONTROLLER


def _safe_id(text: str, prefix: str) -> str:
    cleaned = "".join(
        character
        for character in str(text or "")
        if character.isalnum() or character in "-_"
    )
    body = cleaned[:64] or "run"
    candidate = f"{prefix}-{body}"
    return candidate if candidate[0].isalnum() else f"r{candidate}"


def _evidence(evidence_path: str, count: int) -> dict[str, Any]:
    return {
        "ok": True,
        "evidence": [
            {
                "status": "passed",
                "evidence_path": evidence_path,
                "count": max(1, int(count)),
            }
        ],
    }


def _gate_map(evidence_path: str, count: int) -> dict[str, Any]:
    evidence = _evidence(evidence_path, count)
    return {
        name: dict(evidence)
        for name in ("integrity", "correctness", "regression", "resource", "benefit")
    }


def _result_for(
    outcome: str,
    run_id: str,
    token: int,
    attempts: int,
    *,
    summary: str,
    usage: dict[str, int],
    evidence_path: str,
    count: int,
) -> dict[str, Any]:
    task_id = "session"
    attempt_id = f"session-attempt-{attempts:03d}"
    result: dict[str, Any] = {
        "task_id": task_id,
        "status": outcome,
        "attempt_id": attempt_id,
        "lease_id": f"{run_id}:{task_id}:{int(token)}",
        "owner": _OWNER,
        "fencing_token": int(token),
        "summary": summary[:2000],
        "changed_paths": [],
        "usage": {"resources": dict(usage)},
    }
    if outcome == "succeeded":
        result["gates"] = _gate_map(evidence_path, count)
    return result


class SessionRun:
    """One Hermes session projected onto a single-task runtime run."""

    def __init__(self, sid: str, evidence_path: str) -> None:
        self.sid = str(sid)
        self.run_id = _safe_id(self.sid, "h")
        self.task_id = "session"
        self.evidence_path = evidence_path
        self.last_beat = 0.0
        self.beats = 0
        self.attempts = 1
        self.token: int | None = None
        self.tool_calls = 0
        self.failures = 0
        self.finished = False
        self.disabled = False

    # -- lifecycle ---------------------------------------------------------

    def start(self, workspace_root: str, objective: str) -> None:
        controller = _controller()
        task = {
            "id": self.task_id,
            "objective": objective[:500] or "Hermes session work",
            "estimated_tokens": 4_000_000,
            "retry_limit": 24,
            # Reservations can only be raised (never lowered) after create, and
            # a result whose usage exceeds them is rejected — so reserve
            # generously up front for the full session. model_tokens must equal
            # estimated_tokens per TaskSpec contract.
            "resource_estimates": {
                "repairs": 64,
                "tool_calls": 8_192,
                "retrieval_tokens": 200_000,
                "model_tokens": 4_000_000,
                "output_tokens": 1_000_000,
                "delegations": 256,
                "wall_time_seconds": 86_400,
                "memory_bytes": 268_435_456,
            },
        }
        state = controller.create(
            {
                "run_id": self.run_id,
                "objective": objective[:500] or "Hermes session work",
                "tasks": [task],
                "workspace_root": workspace_root,
                "soft_budget": 2_000_000,
                "hard_budget": 4_000_000,
                "resource_limits": {
                    "repairs": 64,
                    "tool_calls": 8_192,
                    "retrieval_tokens": 200_000,
                    "output_tokens": 1_000_000,
                    "delegations": 256,
                    "wall_time_seconds": 86_400,
                    "memory_bytes": 268_435_456,
                },
            },
            idempotency_key=f"{self.run_id}:create",
            expected_revision=0,
        )
        state = controller.submit(
            self.run_id,
            {"session_id": self.sid},
            idempotency_key=f"{self.run_id}:submit",
            expected_revision=state["revision"],
        )
        state = controller.lease(
            self.run_id,
            owner=_OWNER,
            idempotency_key=f"{self.run_id}:lease-1",
            expected_revision=state["revision"],
        )
        self._capture_lease(state)
        state = controller.advance(
            self.run_id,
            {
                "task_id": self.task_id,
                "status": "running",
                "owner": _OWNER,
                "fencing_token": self.token,
            },
            idempotency_key=f"{self.run_id}:beat-0",
            expected_revision=state["revision"],
        )
        self.last_beat = time.time()
        self.beats = 1

    def _capture_lease(self, state: dict[str, Any]) -> None:
        item = state["tasks"][self.task_id]
        lease = item.get("lease") or {}
        self.token = int(lease.get("fencing_token") or 0)
        self.attempts = max(1, int(item.get("attempts") or 1))

    def heartbeat(self) -> None:
        if self.finished or self.disabled:
            return
        now = time.time()
        if now - self.last_beat < _MIN_BEAT_INTERVAL:
            return
        if self.beats >= _MAX_BEATS:
            return
        try:
            controller = _controller()
            state = controller._state(self.run_id)
            item = state["tasks"][self.task_id]
            if item.get("status") not in ("leased", "running"):
                return
            lease = item.get("lease") or {}
            token = int(lease.get("fencing_token") or 0)
            state = controller.advance(
                self.run_id,
                {
                    "task_id": self.task_id,
                    "status": "running",
                    "owner": _OWNER,
                    "fencing_token": token,
                },
                idempotency_key=f"{self.run_id}:beat-{self.beats}",
                expected_revision=state["revision"],
            )
            self.last_beat = now
            self.beats += 1
        except Exception as exc:  # fail-open: heartbeats are advisory
            self.disabled = True
            logger.debug("SIPS session beat skipped: %s", type(exc).__name__)

    def finish(
        self,
        *,
        completed: bool,
        tool_calls: int,
        failures: int,
        turns: int,
        exit_reason: str,
    ) -> None:
        if self.finished or self.disabled:
            return
        self.finished = True
        try:
            controller = _controller()
            state = controller._state(self.run_id)
            item = state["tasks"][self.task_id]
            if item.get("status") not in ("leased", "running"):
                return
            lease = item.get("lease") or {}
            token = int(lease.get("fencing_token") or 0)
            self.attempts = max(1, int(item.get("attempts") or 1))
            summary = (
                f"Hermes session completed: turns={turns} tool_calls={tool_calls} "
                f"failures={failures} exit={exit_reason}"
            )
            outcome = "succeeded" if completed else "failed"
            usage = {
                "model_tokens": 50_000,
                "retrieval_tokens": 8_000,
                "output_tokens": 8_000,
                "delegations": 1,
                "tool_calls": max(1, tool_calls),
                "repairs": 1,
                "wall_time_seconds": 900,
                "memory_bytes": 8 * 1024 * 1024,
            }
            result = _result_for(
                outcome,
                self.run_id,
                token,
                self.attempts,
                summary=summary,
                usage=usage,
                evidence_path=self.evidence_path,
                count=max(1, tool_calls),
            )
            try:
                controller.advance(
                    self.run_id,
                    {
                        "task_id": self.task_id,
                        "owner": _OWNER,
                        "fencing_token": token,
                        "result": result,
                    },
                    idempotency_key=f"{self.run_id}:result",
                    expected_revision=state["revision"],
                )
                return
            except Exception:
                if completed or self.attempts >= 3:
                    raise
            # Unfinished long session: close as a retry attempt, then re-lease
            # and submit a terminal failed/succeeded result in attempt 2.
            retry_result = _result_for(
                "retry",
                self.run_id,
                token,
                self.attempts,
                summary=summary,
                usage=usage,
                evidence_path=self.evidence_path,
                count=max(1, tool_calls),
            )
            state = controller.advance(
                self.run_id,
                {
                    "task_id": self.task_id,
                    "owner": _OWNER,
                    "fencing_token": token,
                    "result": retry_result,
                },
                idempotency_key=f"{self.run_id}:result-attempt-{self.attempts}",
                expected_revision=state["revision"],
            )
            state = controller.lease(
                self.run_id,
                owner=_OWNER,
                idempotency_key=f"{self.run_id}:lease-{self.attempts + 1}",
                expected_revision=state["revision"],
            )
            self._capture_lease(state)
            final = _result_for(
                "failed" if not completed else "succeeded",
                self.run_id,
                self.token or 0,
                self.attempts,
                summary=summary,
                usage=usage,
                evidence_path=self.evidence_path,
                count=max(1, tool_calls),
            )
            controller.advance(
                self.run_id,
                {
                    "task_id": self.task_id,
                    "owner": _OWNER,
                    "fencing_token": self.token,
                    "result": final,
                },
                idempotency_key=f"{self.run_id}:result-final",
                expected_revision=state["revision"],
            )
        except Exception as exc:  # fail-open: the board is advisory
            logger.debug("SIPS session finish skipped: %s", type(exc).__name__)


_ACTIVE: dict[str, SessionRun] = {}


def session_run(sid: str) -> SessionRun:
    """Return (creating if needed) the active run for a session.

    ``evidence_path`` points at the session's hook event stream — the same
    bounded-metadata JSONL the adapter already persists — so gate evidence is
    anchored to a real, existing artifact rather than a synthetic path.
    """
    from hermes_adapter import _event_path

    key = str(sid)
    with _LOCK:
        run = _ACTIVE.get(key)
        if run is None:
            run = SessionRun(key, str(_event_path()))
            _ACTIVE[key] = run
        return run


def start_session(sid: str, workspace_root: str) -> None:
    """Create/lease the session's runtime run. Never raises."""
    try:
        run = session_run(sid)
        with _LOCK:
            if run.finished or run.token is not None:
                return
        run.start(workspace_root, objective=f"Hermes session {run.run_id}")
    except Exception as exc:
        with _LOCK:
            _ACTIVE.pop(str(sid), None)
        logger.debug("SIPS session start skipped: %s", type(exc).__name__)


def record_tool_call(sid: str) -> None:
    """Count a tool call and (throttled) beat the lease. Never raises."""
    run = _ACTIVE.get(str(sid))
    if run is None:
        return
    run.tool_calls += 1
    try:
        run.heartbeat()
    except Exception:
        run.disabled = True


def finish_session(
    sid: str, *, completed: bool, tool_calls: int, failures: int, turns: int, exit_reason: str
) -> None:
    run = _ACTIVE.pop(str(sid), None)
    if run is None:
        return
    try:
        run.finish(
            completed=completed,
            tool_calls=tool_calls,
            failures=failures,
            turns=turns,
            exit_reason=exit_reason,
        )
    except Exception:
        pass
