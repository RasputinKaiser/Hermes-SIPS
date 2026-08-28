# Hermes-SIPS

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Status: dev](https://img.shields.io/badge/status-dev-orange)
![Hermes Agent plugin](https://img.shields.io/badge/Hermes_Agent-plugin-7C3AED)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/W7W7C9TC7)

**SIPS Homebase, as a first-class Hermes Agent plugin.** Hermes-SIPS is the Hermes-focused distribution of [SIPS](https://github.com/RasputinKaiser/Self-Improvement-Plugin) (Self-Improvement Plugin System): memory-aware startup, safer tool use, verification hooks, bounded fresh-context delegation, session closeout, plus a desktop Control-Plane panel — wired natively into Hermes Agent.

It does not try to make an agent smarter by swapping models. It improves the *work loop* around whatever model you already run.

> Experimental, but CI-backed. The core is a deterministic graph runtime, SIPS-owned Memory Fabric recall, lifecycle hooks, native Hermes tools, and focused regression suites.

Each session can answer:

- What did we learn last time?
- Is this edit risky?
- Did the changed script still pass a smoke check?
- Is this task stuck enough to split out?
- What should future sessions remember?
- Which agent patterns have worked or failed before?

## What's Hermes-specific here

The [upstream repo](https://github.com/RasputinKaiser/Self-Improvement-Plugin) carries the harness-agnostic SIPS core (Claude Code / Codex manifests, scripts, commands, skills, MCP server). Hermes-SIPS keeps that core intact and adds the Hermes-native layer:

| Hermes surface | Implementation |
|---|---|
| Native tools (`sips_homebase` toolset) | `__init__.py` registers every MCP tool from `scripts/harness_homebase_mcp.py` via `ctx.register_tool` — status, verify, route, repo-map, context scan, recall, record, goal, selfloop, campaign fleet, goal board, runtime read/write |
| Lifecycle hooks | `hermes_adapter.py` maps Hermes `pre_llm_call` / `pre_tool_call` / `post_tool_call` / session hooks onto SIPS hook tooling; advisory output is bounded and consumed on the next `pre_llm_call` |
| Slash commands | SIPS commands registered via `ctx.register_command` |
| Skills | SIPS `skills/*/SKILL.md` published through `ctx.register_skill` |
| MCP server (optional) | `scripts/hermes_mcp_wrapper.py` runs the same server with profile-safe paths (`$HERMES_HOME/sips`) |
| Desktop panel | `dashboard/` — the SIPS Control Plane add-on for Hermes Desktop: live selfloop control, goal subtasks, memory recall/record, verification history, health telemetry |

Profile-safe runtime state lives under `$HERMES_HOME/sips/`, kept separate from the source tree. `state.yaml` files are local runtime state and are never committed.

## Install (Hermes Agent)

From a clone of this repo:

```bash
hermes plugins install --enable /path/to/Hermes-SIPS
hermes plugins list | grep harness-self-improvement   # expect: enabled
```

The plugin takes effect on the next session (`/reset` or restart).

Optional MCP server registration (same tooling over stdio, useful outside the plugin path):

```bash
hermes mcp add sips-homebase \
  --command /path/to/python \
  --env PYTHONUNBUFFERED=1 \
  --args /absolute/path/to/Hermes-SIPS/scripts/hermes_mcp_wrapper.py
```

Pick the advertised tools in the interactive tool-selection prompt, then verify:

```bash
hermes config check
hermes mcp list
hermes mcp test sips-homebase
```

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.10+ | stdlib only for the core runtime |
| Hermes Agent | plugin API: `ctx.register_tool` / `ctx.register_hook` / `ctx.register_command` / `ctx.register_skill` |
| No model requirement | delegation agents declare `model: inherit` — they run on whatever the session already uses |

## Verify

```bash
python3 -m compileall -q scripts hermes_adapter.py __init__.py
pytest
```

## Layout

```
├── plugin.yaml              # Hermes manifest (name, version, provides_tools, hooks)
├── __init__.py              # register(ctx): tools, skills, commands, hooks
├── hermes_adapter.py        # Hermes hook/tool mapping + profile-safe env
├── scripts/
│   ├── harness_homebase_mcp.py   # SIPS MCP server (JSON-RPC over stdio)
│   ├── hermes_mcp_wrapper.py     # stdio entrypoint with $HERMES_HOME paths
│   └── ...                       # harness-agnostic SIPS core
├── dashboard/               # Hermes Desktop Control-Plane panel
│   ├── manifest.json
│   ├── plugin_api.py
│   └── dist/index.js
├── commands/ skills/ agents/ hooks/   # shared SIPS surfaces
└── tests/
```

## Relationship to upstream

- **[Self-Improvement-Plugin](https://github.com/RasputinKaiser/Self-Improvement-Plugin)** — harness-agnostic SIPS core (Claude Code + Codex installs).
- **Hermes-SIPS (this repo)** — the same core, vendored intact, plus the Hermes plugin adapter and desktop panel.

Both repos are MIT-licensed. The core is kept in sync with upstream; the Hermes layer is additive.

## Security notes

- Hook callbacks are fail-open for advisory work; only the explicit autonomy-gate critical decision blocks a tool call.
- Event logs store bounded metadata (event, session/turn IDs, tool name, status, duration) — never prompts, tool outputs, or credentials.
- Runtime state (`$HERMES_HOME/sips/`, `state.yaml`, `dashboard/action_history.jsonl`) is local-only and git-ignored.

## License

MIT — see [LICENSE](LICENSE).
