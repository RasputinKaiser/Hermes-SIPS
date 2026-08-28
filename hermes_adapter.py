"""Hermes-native adapter for the SIPS lifecycle and memory surfaces.

The upstream project speaks Claude/Codex hook JSON. Hermes has a native Python
plugin API instead, so this module translates the small, documented Hermes hook
payloads into the upstream scripts' portable stdin contract. It is deliberately
fail-open for advisory work and fail-closed only for the upstream autonomy gate's
explicit critical decisions.
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)
_PLUGIN_ROOT = Path(__file__).resolve().parent
_SCRIPTS_ROOT = _PLUGIN_ROOT / "scripts"
_LOCK = threading.RLock()
_MAX_STDOUT = 64 * 1024
_SECRET_KEY = re.compile(r"(?:api[_-]?key|access[_-]?token|password|secret|authorization)", re.I)
_SECRET_VALUE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|password|secret|authorization)(\s*[:=]\s*)\S+"
)
# Housekeeping runs at most once per 24h per process (module-level guard).
_HK_LAST_RUN = 0.0
_HK_INTERVAL_SECONDS = 24 * 3600


def configure_environment() -> Path:
    """Set profile-safe SIPS paths and create only the runtime directories."""
    try:
        from hermes_constants import get_hermes_home

        hermes_home = Path(get_hermes_home()).expanduser().resolve()
    except Exception:
        hermes_home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser().resolve()

    sips_home = Path(os.environ.get("SIPS_HOME") or (hermes_home / "sips")).expanduser().resolve()
    os.environ.setdefault("SIPS_HOME", str(sips_home))
    os.environ.setdefault("SIPS_PLUGIN_ROOT", str(_PLUGIN_ROOT))
    os.environ.setdefault("PLUGIN_ROOT", str(_PLUGIN_ROOT))
    for child in ("logs", "pending", "sessions", "eval"):
        (sips_home / child).mkdir(parents=True, exist_ok=True)
    # Lifecycle hooks (on_session_start) can fire before register(ctx) puts
    # scripts/ on sys.path via _load_homebase(); make bridge imports work
    # regardless of hook ordering.
    scripts_dir = str(_SCRIPTS_ROOT)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    return sips_home


def _sips_home() -> Path:
    return configure_environment()


def _safe_id(value: Any) -> str:
    text = str(value or "unknown")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)[:120] or "unknown"


def _scrub(value: Any, key: str = "") -> Any:
    """Keep hook classification useful without persisting or forwarding secrets."""
    if _SECRET_KEY.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {str(k): _scrub(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub(v, key) for v in value[:50]]
    if isinstance(value, str):
        return _SECRET_VALUE.sub(r"\1\2<redacted>", value)[:16000]
    return value


def _session_id(kwargs: dict[str, Any]) -> str:
    return str(kwargs.get("session_id") or kwargs.get("conversation_id") or "unknown")


def _cwd(kwargs: dict[str, Any]) -> str:
    value = kwargs.get("cwd") or os.getcwd()
    try:
        return str(Path(str(value)).expanduser().resolve())
    except Exception:
        return os.getcwd()


def _event_path() -> Path:
    return _sips_home() / "hook_events.jsonl"


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    except OSError:
        logger.debug("SIPS event append failed", exc_info=True)


def _record_event(event: str, kwargs: dict[str, Any], **fields: Any) -> None:
    """Write bounded metadata only; never write prompts, tool args, or outputs."""
    record = {
        "schema": "hermes.sips.event.v1",
        "id": uuid.uuid4().hex,
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "session_id": _safe_id(_session_id(kwargs)),
        "task_id": _safe_id(kwargs.get("task_id")) if kwargs.get("task_id") else None,
        "turn_id": _safe_id(kwargs.get("turn_id")) if kwargs.get("turn_id") else None,
        "tool_name": str(kwargs.get("tool_name") or "")[:120] or None,
        "platform": str(kwargs.get("platform") or "")[:40] or None,
        "model": str(kwargs.get("model") or "")[:120] or None,
    }
    record.update({k: _scrub(v, k) for k, v in fields.items()})
    _append_jsonl(_event_path(), {k: v for k, v in record.items() if v is not None})


def _run_command(command: list[str], *, payload: dict[str, Any] | None = None, timeout: float = 8.0) -> dict[str, Any]:
    configure_environment()
    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"
    env["SIPS_PLUGIN_ROOT"] = str(_PLUGIN_ROOT)
    env["PLUGIN_ROOT"] = str(_PLUGIN_ROOT)
    input_data = json.dumps(_scrub(payload or {}), ensure_ascii=False) if payload is not None else None
    try:
        completed = subprocess.run(
            command,
            cwd=str(_PLUGIN_ROOT),
            env=env,
            input=input_data,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        stdout = (completed.stdout or "")[:_MAX_STDOUT]
        stderr = (completed.stderr or "")[:4000]
        result: dict[str, Any] = {
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "ok": completed.returncode == 0,
        }
        if stdout.strip():
            try:
                result["json"] = json.loads(stdout)
            except json.JSONDecodeError:
                pass
        return result
    except subprocess.TimeoutExpired:
        return {"returncode": None, "stdout": "", "stderr": "timeout", "ok": False, "timed_out": True}
    except OSError as exc:
        return {"returncode": None, "stdout": "", "stderr": type(exc).__name__, "ok": False}


def _run_script(name: str, payload: dict[str, Any], *, timeout: float = 8.0) -> dict[str, Any]:
    script = _SCRIPTS_ROOT / name
    if not script.is_file():
        return {"ok": False, "stderr": "script_missing", "returncode": None}
    return _run_command([sys.executable, str(script)], payload=payload, timeout=timeout)


def _json_output(result: dict[str, Any]) -> dict[str, Any]:
    value = result.get("json")
    return value if isinstance(value, dict) else {}


def _pending_path(session_id: str) -> Path:
    return _sips_home() / "pending" / f"{_safe_id(session_id)}.jsonl"


def _queue_context(session_id: str, context: str, source: str) -> None:
    if not context or not context.strip():
        return
    _append_jsonl(
        _pending_path(session_id),
        {"schema": "hermes.sips.context.v1", "source": source, "context": context.strip()[:12000]},
    )


def _consume_context(session_id: str) -> list[str]:
    path = _pending_path(session_id)
    try:
        with _LOCK:
            lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
            path.write_text("", encoding="utf-8")
        contexts = []
        for line in lines[-8:]:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            context = item.get("context") if isinstance(item, dict) else None
            if isinstance(context, str) and context.strip():
                contexts.append(context.strip())
        return contexts
    except OSError:
        return []


def _state_path() -> Path:
    return _sips_home() / "sessions" / "hermes_sessions.json"


def _load_state() -> dict[str, Any]:
    try:
        raw = json.loads(_state_path().read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _update_session(session_id: str, **changes: Any) -> dict[str, Any]:
    """Persist counters only; raw conversation and tool payloads never enter this file."""
    sid = _safe_id(session_id)
    with _LOCK:
        state = _load_state()
        sessions = state.setdefault("sessions", {})
        current = sessions.setdefault(
            sid,
            {"turns": 0, "tool_calls": 0, "edits": 0, "failures": 0, "started_at": datetime.now(timezone.utc).isoformat()},
        )
        for key, value in changes.items():
            if isinstance(value, int):
                current[key] = int(current.get(key, 0)) + value
            else:
                current[key] = value
        state["sessions"] = dict(list(sessions.items())[-100:])
        path = _state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
        return dict(current)


def _translated_tool(kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    name = str(kwargs.get("tool_name") or kwargs.get("name") or "")
    args = kwargs.get("args") or kwargs.get("tool_input") or kwargs.get("arguments") or {}
    args = dict(args) if isinstance(args, dict) else {}
    if name == "write_file":
        return "Write", {"file_path": args.get("path") or args.get("file_path") or ""}
    if name == "patch":
        return "Edit", {"file_path": args.get("path") or args.get("file_path") or ""}
    if name in {"terminal", "execute_code"}:
        return "Bash", {"command": args.get("command") or args.get("code") or ""}
    return name, args


def _maybe_run_housekeeping() -> None:
    """Run state-root housekeeping at most once per 24h per process.

    Mirrors the sips_session_bridge pattern: import inside try/except so a
    missing or broken script never breaks the session-start hook path.
    """
    global _HK_LAST_RUN
    now = time.time()
    if now - _HK_LAST_RUN < _HK_INTERVAL_SECONDS:
        return
    _HK_LAST_RUN = now
    try:
        from sips_housekeeping import run_housekeeping

        run_housekeeping(dry_run=False)
    except Exception:
        logger.debug("SIPS housekeeping skipped", exc_info=True)


def _on_session_start(**kwargs: Any) -> None:
    configure_environment()
    sid = _session_id(kwargs)
    try:
        from sips_session_bridge import start_session

        start_session(sid, _cwd(kwargs), evidence_path=str(_event_path()))
    except Exception:
        logger.debug("SIPS runtime session start skipped", exc_info=True)
    _maybe_run_housekeeping()
    result = _run_script(
        "improvement_injector.py",
        {"hook_event_name": "SessionStart", "session_id": sid, "cwd": _cwd(kwargs)},
        timeout=5,
    )
    context = _json_output(result).get("additionalContext")
    if isinstance(context, str) and context.strip():
        _queue_context(sid, context, "improvement_injector")
    _record_event("on_session_start", kwargs, status="ok" if result.get("ok") else "advisory_unavailable")


def _on_pre_llm_call(**kwargs: Any) -> dict[str, str] | None:
    configure_environment()
    sid = _session_id(kwargs)
    _update_session(sid, turns=1)
    contexts = _consume_context(sid)
    prompt = kwargs.get("user_message") or ""
    recall = _run_script(
        "recall_ranker.py",
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": sid,
            "task_id": kwargs.get("task_id") or "",
            "turn_id": kwargs.get("turn_id") or "",
            "cwd": _cwd(kwargs),
            "prompt": prompt,
        },
        timeout=8,
    )
    recall_context = _json_output(recall).get("additionalContext")
    if isinstance(recall_context, str) and recall_context.strip():
        contexts.append(recall_context.strip())
    if not contexts:
        _record_event("pre_llm_call", kwargs, status="no_context")
        return None
    _record_event("pre_llm_call", kwargs, status="context_injected", context_count=len(contexts))
    return {"context": "\n\n".join(contexts)[:24000]}


def _on_pre_tool_call(**kwargs: Any) -> dict[str, str] | None:
    name, args = _translated_tool(kwargs)
    if not name:
        return None
    sid = _session_id(kwargs)
    _update_session(sid, tool_calls=1)
    result = _run_script(
        "autonomy_gate.py",
        {
            "hook_event_name": "PreToolUse",
            "session_id": sid,
            "tool_name": name,
            "tool_input": args,
            "cwd": _cwd(kwargs),
        },
        timeout=5,
    )
    data = _json_output(result)
    if data.get("decision") == "block":
        reason = str(data.get("reason") or "SIPS autonomy gate blocked this action")[:1200]
        _record_event("pre_tool_call", kwargs, status="blocked", classification="critical")
        return {"action": "block", "message": reason}
    feedback = data.get("decisionFeedback")
    if feedback:
        _queue_context(sid, json.dumps(feedback, ensure_ascii=False), "autonomy_gate")
    _record_event("pre_tool_call", kwargs, status="allowed" if result.get("ok") else "advisory_unavailable")
    return None


def _on_post_tool_call(**kwargs: Any) -> None:
    name, args = _translated_tool(kwargs)
    sid = _session_id(kwargs)
    success = kwargs.get("success")
    if success is False or kwargs.get("error"):
        _update_session(sid, failures=1)
    if name in {"Edit", "Write", "MultiEdit"}:
        _update_session(sid, edits=1)
        result = _run_script(
            "escalation_advisor.py",
            {
                "hook_event_name": "PostToolUse",
                "session_id": sid,
                "tool_name": name,
                "tool_input": args,
                "cwd": _cwd(kwargs),
            },
            timeout=8,
        )
        feedback = _json_output(result).get("decisionFeedback")
        if feedback:
            _queue_context(
                sid,
                "SIPS escalation advisor (advisory):\n" + json.dumps(feedback, ensure_ascii=False),
                "escalation_advisor",
            )
    try:
        from sips_session_bridge import record_tool_call

        record_tool_call(sid)
    except Exception:
        logger.debug("SIPS runtime beat skipped", exc_info=True)
    _record_event("post_tool_call", kwargs, status="ok" if success is not False else "failed")


def _on_pre_verify(**kwargs: Any) -> dict[str, str] | None:
    changed = kwargs.get("changed_paths") or []
    if not isinstance(changed, list):
        changed = []
    plugin_changed = any("harness-self-improvement" in str(path) for path in changed)
    if not plugin_changed:
        return None
    result = _run_command([sys.executable, str(_SCRIPTS_ROOT / "validate_v2.py")], timeout=20)
    _record_event("pre_verify", kwargs, status="passed" if result.get("ok") else "failed")
    if not result.get("ok"):
        return {
            "action": "continue",
            "message": "SIPS source validation failed. Inspect `scripts/validate_v2.py` output and fix the integration before finishing.",
        }
    return None


def _record_learning(sid: str, kwargs: dict[str, Any], metrics: dict[str, Any]) -> None:
    if int(metrics.get("tool_calls", 0)) <= 0:
        return
    completed = bool(kwargs.get("completed")) and not bool(kwargs.get("failed")) and not bool(kwargs.get("interrupted"))
    outcome = "success" if completed else "failure"
    cwd = _cwd(kwargs)
    events = _event_path()
    body = "\n".join(
        [
            f"session: {sid}",
            f"cwd: {cwd}",
            f"completed: {completed}",
            f"turns: {metrics.get('turns', 0)}",
            f"tool_calls: {metrics.get('tool_calls', 0)}",
            f"edits: {metrics.get('edits', 0)}",
            f"failures: {metrics.get('failures', 0)}",
            f"exit_reason: {kwargs.get('turn_exit_reason') or 'unknown'}",
        ]
    )
    command = [
        sys.executable,
        str(_SCRIPTS_ROOT / "memory_fabric.py"),
        "record",
        "--tier",
        "learning",
        "--title",
        f"Hermes task {sid[:12]} — {outcome}",
        "--body",
        body,
        "--scope",
        cwd,
        "--tags",
        f"outcome,hermes,sips,{outcome}",
        "--provenance-type",
        "source_backed_agent_run",
        "--provenance",
        f"hermes_hook=on_session_end; session_id={sid}",
        "--evidence-path",
        str(events),
        "--confidence",
        "high" if completed else "medium",
        "--status",
        "active",
    ]
    result = _run_command(command, timeout=12)
    _record_event("on_session_end_record", kwargs, status="recorded" if result.get("ok") else "memory_fabric_unavailable")


def _on_session_end(**kwargs: Any) -> None:
    sid = _session_id(kwargs)
    metrics = _update_session(sid)
    _record_learning(sid, kwargs, metrics)
    _record_event("on_session_end", kwargs, status="ok", metrics={k: metrics.get(k, 0) for k in ("turns", "tool_calls", "edits", "failures")})
    try:
        from sips_session_bridge import finish_session

        finish_session(
            sid,
            completed=True,
            turns=metrics.get("turns", 0),
            tool_calls=metrics.get("tool_calls", 0),
            failures=metrics.get("failures", 0),
            exit_reason="session_end",
        )
    except Exception:
        logger.debug("SIPS runtime session end skipped", exc_info=True)


def _on_session_finalize(**kwargs: Any) -> None:
    _record_event("on_session_finalize", kwargs, status="ok")


def _on_session_reset(**kwargs: Any) -> None:
    sid = _session_id(kwargs)
    try:
        _pending_path(sid).unlink(missing_ok=True)
    except OSError:
        pass
    _record_event("on_session_reset", kwargs, status="ok")


def _on_skill_lifecycle(**kwargs: Any) -> None:
    _record_event("on_skill_lifecycle", kwargs, status="ok", action=kwargs.get("action"))


def _on_subagent_start(**kwargs: Any) -> None:
    _record_event("subagent_start", kwargs, status="ok")


def _on_subagent_stop(**kwargs: Any) -> None:
    _record_event("subagent_stop", kwargs, status="ok")


def register_hooks(ctx: Any) -> None:
    configure_environment()
    hooks: list[tuple[str, Callable[..., Any]]] = [
        ("on_session_start", _on_session_start),
        ("pre_llm_call", _on_pre_llm_call),
        ("pre_tool_call", _on_pre_tool_call),
        ("post_tool_call", _on_post_tool_call),
        ("pre_verify", _on_pre_verify),
        ("on_session_end", _on_session_end),
        ("on_session_finalize", _on_session_finalize),
        ("on_session_reset", _on_session_reset),
        ("on_skill_lifecycle", _on_skill_lifecycle),
        ("subagent_start", _on_subagent_start),
        ("subagent_stop", _on_subagent_stop),
    ]
    for name, callback in hooks:
        ctx.register_hook(name, callback)
