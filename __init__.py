"""Hermes plugin entry point for the vendored SIPS Homebase source."""
from __future__ import annotations

import json
import logging
import os
import re
import shlex
import sys
from functools import partial
from pathlib import Path
from typing import Any

_PLUGIN_ROOT = Path(__file__).resolve().parent
_SCRIPTS_ROOT = _PLUGIN_ROOT / "scripts"

try:
    from . import hermes_adapter
except ImportError as exc:
    # pytest and a few standalone plugin scanners import a directory-level
    # __init__.py without assigning it a package name. Keep that mode usable
    # without weakening normal package imports.
    if "attempted relative import" not in str(exc):
        raise
    if str(_PLUGIN_ROOT) not in sys.path:
        sys.path.insert(0, str(_PLUGIN_ROOT))
    import hermes_adapter  # type: ignore[no-redef]


def _load_homebase():
    hermes_adapter.configure_environment()
    script_dir = str(_SCRIPTS_ROOT)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    import harness_homebase_mcp  # type: ignore

    return harness_homebase_mcp


def _tool_handler(homebase: Any, name: str, args: dict[str, Any], **_kwargs: Any) -> str:
    try:
        result = homebase.call_tool(name, args if isinstance(args, dict) else {})
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
    except Exception as exc:
        from tools.registry import tool_error

        logger.warning("SIPS tool %s failed: %s", name, type(exc).__name__)
        return tool_error(f"SIPS {name} failed: {type(exc).__name__}")


def _json_tool(homebase: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    raw = _tool_handler(homebase, name, args)
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"value": value}
    except json.JSONDecodeError:
        return {"text": raw}


def _pretty_result(payload: dict[str, Any]) -> str:
    content = payload.get("content")
    if isinstance(content, list):
        texts = [item.get("text") for item in content if isinstance(item, dict) and item.get("text")]
        if texts:
            return "\n".join(str(text) for text in texts)
    structured = payload.get("structuredContent")
    if isinstance(structured, dict):
        return json.dumps(structured, ensure_ascii=False, indent=2)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _workspace_root() -> str:
    try:
        return str(Path.cwd().resolve())
    except OSError:
        return os.getcwd()


def _command_status(homebase: Any, _raw: str) -> str:
    return _pretty_result(_json_tool(homebase, "homebase_status", {"root": str(_PLUGIN_ROOT)}))


def _command_routes(homebase: Any, _raw: str) -> str:
    return _pretty_result(_json_tool(homebase, "homebase_routes", {"root": _workspace_root()}))


def _command_recall(homebase: Any, raw: str) -> str:
    query = raw.strip()
    if not query:
        return "Usage: /recall <what to search for>"
    return _pretty_result(
        _json_tool(homebase, "homebase_recall", {"root": _workspace_root(), "query": query, "limit": 4})
    )


def _command_goal(homebase: Any, _raw: str) -> str:
    return _pretty_result(_json_tool(homebase, "homebase_goal", {"root": _workspace_root()}))


def _command_selfloop(homebase: Any, raw: str) -> str:
    parts = shlex.split(raw) if raw.strip() else ["status"]
    action = parts[0].lower()
    args: dict[str, Any] = {"root": _workspace_root(), "action": action}
    if action == "start":
        args["focus"] = " ".join(parts[1:])
    elif action == "record":
        if len(parts) < 3:
            return "Usage: /selfloop record <improved|plateau|blocked> <proof-bearing summary>"
        args["outcome"] = parts[1]
        args["summary"] = " ".join(parts[2:])
    return _pretty_result(_json_tool(homebase, "homebase_selfloop", args))


def _command_verify(homebase: Any, raw: str) -> str:
    run_tests = any(token in {"--tests", "tests", "--run-tests"} for token in raw.split())
    return _pretty_result(
        _json_tool(homebase, "homebase_verify", {"root": str(_PLUGIN_ROOT), "run_tests": run_tests})
    )


def _command_record(homebase: Any, raw: str) -> str:
    if "::" not in raw:
        return "Usage: /sips-record <title> :: <body>"
    title, body = (part.strip() for part in raw.split("::", 1))
    if not title or not body:
        return "Usage: /sips-record <title> :: <body>"
    return _pretty_result(
        _json_tool(
            homebase,
            "homebase_record",
            {
                "root": _workspace_root(),
                "tier": "learning",
                "title": title,
                "body": body,
                "scope": _workspace_root(),
                "tags": "learning,hermes,sips",
                "confidence": "medium",
                "status": "active",
                "provenance": "Hermes /sips-record command",
            },
        )
    )


def _workflow_handler(ctx: Any, command: str, raw: str) -> str:
    skill = {
        "improve": "sips-control-plane",
        "retro": "sips-memory-fabric",
        "escalate": "sips-delegation-router",
        "fan-out": "sips-delegation-router",
        "brainstorm": "sips-control-plane",
        "teach": "sips-memory-fabric",
        "patterns": "sips-memory-fabric",
    }.get(command, "sips-control-plane")
    prompt = (
        f"Run the SIPS Hermes workflow `/{command}`.\n"
        f"Load the plugin skill `harness-self-improvement:{skill}` first.\n"
        f"User-supplied focus/arguments: {raw.strip() or '(none)'}\n"
        "Use the native SIPS Homebase tools where applicable, keep changes bounded, "
        "and report the proof boundary and verification evidence."
    )
    try:
        if ctx.inject_message(prompt):
            return f"Queued SIPS /{command} workflow for the next Hermes turn."
    except Exception:
        logger.debug("SIPS workflow injection unavailable", exc_info=True)
    return (
        f"SIPS /{command} is available, but this session cannot inject a follow-up turn. "
        f"Load `harness-self-improvement:{skill}` and continue with the Homebase tools."
    )


def _register_skills(ctx: Any) -> None:
    skills_root = _PLUGIN_ROOT / "skills"
    for skill_file in sorted(skills_root.glob("*/SKILL.md")):
        name = skill_file.parent.name
        description = "SIPS Hermes integration skill"
        try:
            first_lines = skill_file.read_text(encoding="utf-8", errors="replace").splitlines()[:8]
            for line in first_lines:
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"')
                    break
            ctx.register_skill(name, skill_file, description=description)
        except Exception:
            logger.warning("Unable to register SIPS skill %s", name, exc_info=True)


def _register_commands(ctx: Any, homebase: Any) -> None:
    direct = {
        "sips": (lambda raw: "SIPS commands: /sips-status, /sips-routes, /sips-recall, /sips-goal, /sips-verify, /sips-record, /selfloop", "Show Hermes SIPS command help", "[help]"),
        "sips-status": (partial(_command_status, homebase), "Inspect SIPS Homebase source status", ""),
        "sips-routes": (partial(_command_routes, homebase), "List SIPS Homebase routes", ""),
        "sips-recall": (partial(_command_recall, homebase), "Search scoped SIPS memory", "<query>"),
        "sips-goal": (partial(_command_goal, homebase), "Show SIPS goal state", ""),
        "sips-verify": (partial(_command_verify, homebase), "Verify the vendored SIPS source", "[--tests]"),
        "sips-record": (partial(_command_record, homebase), "Record a bounded SIPS learning", "<title> :: <body>"),
        "recall": (partial(_command_recall, homebase), "Recall scoped SIPS memory", "<query>"),
        "goal": (partial(_command_goal, homebase), "Show SIPS goal state", ""),
        "selfloop": (partial(_command_selfloop, homebase), "Inspect or update SIPS self-loop state", "<status|start|record> ..."),
        "verify": (partial(_command_verify, homebase), "Verify SIPS source wiring", "[--tests]"),
    }
    for name, (handler, description, args_hint) in direct.items():
        ctx.register_command(name, handler, description=description, args_hint=args_hint)

    for name, description, args_hint in (
        ("improve", "Run the SIPS improvement workflow", "[focus]"),
        ("retro", "Run the SIPS evidence-backed retrospective", "[focus]"),
        ("escalate", "Route a bounded stuck subtask through SIPS", "<subtask>"),
        ("fan-out", "Plan bounded SIPS delegation", "<task>"),
        ("brainstorm", "Start a bounded SIPS design exploration", "[focus]"),
        ("teach", "Capture a source-backed SIPS lesson", "[lesson]"),
        ("patterns", "Inspect SIPS outcome patterns", "[scope]"),
    ):
        ctx.register_command(
            name,
            partial(_workflow_handler, ctx, name),
            description=description,
            args_hint=args_hint,
        )


def register(ctx: Any) -> None:
    """Register native tools, skills, slash commands, and lifecycle hooks."""
    hermes_adapter.configure_environment()
    homebase = _load_homebase()

    for spec in homebase.TOOLS:
        name = str(spec["name"])
        schema = {
            "name": name,
            "description": str(spec.get("description") or spec.get("title") or name),
            "parameters": spec.get("inputSchema") or {"type": "object", "properties": {}},
        }
        ctx.register_tool(
            name=name,
            toolset="sips_homebase",
            schema=schema,
            handler=partial(_tool_handler, homebase, name),
            description=schema["description"],
            emoji="🧭",
        )

    _register_skills(ctx)
    _register_commands(ctx, homebase)
    hermes_adapter.register_hooks(ctx)
