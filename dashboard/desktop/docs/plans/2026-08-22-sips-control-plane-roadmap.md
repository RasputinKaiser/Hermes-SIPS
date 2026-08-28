# SIPS Control Plane — Full Functionality & Layout Roadmap

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Evolve the SIPS desktop add-on from an interactive dashboard into the mission-control surface for the whole self-improvement loop: live goal execution, proof-driven verification history, and memory curation — all inside Hermes.app.

**Architecture:** Two files only. Backend `~/.hermes/plugins/harness-self-improvement/dashboard/plugin_api.py` (FastAPI, bounded wrappers over `harness_homebase_mcp.call_tool` + direct state reads). Frontend `~/.hermes/desktop-plugins/harness-self-improvement/plugin.js` (jsx/jsxs runtime, inline styles, tabbed workspace). No new dependencies. Every write stays allowlisted and claim-bound.

**Tech Stack:** FastAPI (existing venv), @hermes/plugin-sdk (Badge/Button/Codicon/useQuery/useMutation), esbuild for syntax checks.

**Current state (baseline):** Tabbed workspace (Overview/Verification/Memory/Activity), selfloop controls, recall search, record form, routes view, run-all-recommended, 12-sample sparkline history, statusbar pulse. Backend endpoints: /status /actions GET+POST /selfloop GET+POST /recall POST /record POST /routes /health.

---

## Phase 1 — Persistence & Continuity (small, immediate)

### Task 1.1: Persist active tab across sessions

**Objective:** The dashboard reopens on the tab last used.

**Files:**
- Modify: `~/.hermes/desktop-plugins/harness-self-improvement/plugin.js` (Dashboard component, `activeTab` state ~line 1017)

**Step 1:** Replace `useState('overview')` with a localStorage-backed lazy initializer and a persistence effect:

```js
const SIPS_TAB_KEY = 'sips-control-plane-tab'   // top of file, near ROUTE

const [activeTab, setActiveTab] = useState(() => {
  try { return localStorage.getItem(SIPS_TAB_KEY) || 'overview' } catch { return 'overview' }
})
useEffect(() => {
  try { localStorage.setItem(SIPS_TAB_KEY, activeTab) } catch { /* private mode */ }
}, [activeTab])
```

**Step 2:** Verify: `npx esbuild --loader:.js=jsx --jsx=automatic --outfile=/dev/null <plugin.js>` → clean.

**Step 3:** Manual: switch to Memory, reload Hermes → Memory tab active.

### Task 1.2: Deep-link tabs from the statusbar pulse

**Objective:** Clicking the statusbar `SIPS partial` pulse jumps straight to Verification.

**Files:** Modify `plugin.js` — `SipsPulse` component + `Dashboard` props.

**Step 1:** Lift tab state: `Dashboard` accepts `initialTab` prop; `SipsPulse` navigates with `host.navigate(ROUTE + '?tab=verification')` when posture tone is warn/bad (unchanged for good).

**Step 2:** In Dashboard, read the query param once in the `activeTab` initializer:

```js
const initialTab = new URLSearchParams(window.location?.search || '').get('tab')
const [activeTab, setActiveTab] = useState(() =>
  initialTab || readStoredTab() || 'overview')
```

**Verify:** esbuild clean; click pulse with partial posture → lands on Verification.

---

## Phase 2 — Verification History & Proof Trend (the "proof" differentiator)

### Task 2.1: Backend — action history ledger

**Objective:** Persist every action run with before/after proof snapshots so the dashboard can show proof *movement*, not just current state.

**Files:**
- Modify: `~/.hermes/plugins/harness-self-improvement/dashboard/plugin_api.py`

**Step 1:** Add module constant + helper:

```python
ACTION_HISTORY_PATH = PLUGIN_ROOT / "dashboard" / "action_history.jsonl"  # under plugin dir; gitignored

def _append_action_history(entry: dict[str, Any]) -> None:
    try:
        with ACTION_HISTORY_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # history is best-effort; never block the action result

def _read_action_history(limit: int = 30) -> list[dict[str, Any]]:
    try:
        lines = ACTION_HISTORY_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries = []
    for line in lines[-limit:]:
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                entries.append(item)
        except ValueError:
            continue
    return entries
```

**Step 2:** In `run_action`, after building `result`, record history (before returning):

```python
_append_action_history({
    "action_id": action_id,
    "ok": result["ok"],
    "status": result["status"],
    "proof_layers": result.get("summary", {}).get("proof_layers", {}),
    "completed_at": result["completed_at"],
})
```

**Step 3:** New endpoint:

```python
@router.get("/action-history")
def get_action_history() -> dict[str, Any]:
    entries = _read_action_history()
    return {
        "schema": "sips.action.history.v1",
        "entries": entries,
        "generated_at": _now(),
        "claim_boundary": "History records bounded action outcomes only; no raw tool payloads.",
    }
```

**Step 4:** Verify in-process:

```bash
cd ~/.hermes/plugins/harness-self-improvement/dashboard
python3 -c "import plugin_api as p; r=p.run_action('inspect_routes',None); print(p.get_action_history()['entries'][-1]['action_id'])"
```
Expected: `inspect_routes`.

### Task 2.2: Frontend — HistoryCard with proof deltas

**Objective:** Verification tab shows recent runs and whether each made proof coverage go up.

**Files:** Modify `plugin.js`.

**Step 1:** Query: `useQuery({ queryKey: ['sips-control-plane','action-history'], queryFn: () => api.rest('/action-history'), refetchInterval: 20000 })`.

**Step 2:** `HistoryCard` renders entries newest-first: action label, relative time, ok/fail badge, and a delta chip computed from consecutive `proof_layers` ready-counts (`+1 layer` in good color, `no change` muted). Reuse `formatRelativeTimestamp`, `StateBadge`, `toneFor`.

**Step 3:** Add `HistoryCard` to the Verification tab grid (between ActionCenter and ProofCard).

**Verify:** esbuild clean; run a check; history entry appears within 20s with a delta chip.

### Task 2.3: Backend + frontend — proof coverage trend over real history

**Objective:** The hero sparkline for proof coverage uses the persisted ledger, so the trend survives restarts.

**Files:** `plugin_api.py` (`get_status` gains `"proof_trend": [ready_counts…]` computed from history, oldest→newest, capped 24); `plugin.js` (StatusOverview: if `data.proof_trend?.length >= 2`, use it for the proof Signal's `trend` prop instead of session-local history).

**Verify:** restart Hermes; hero proof sparkline still shows the pre-restart shape.

---

## Phase 3 — Goal Execution Loop (the big one)

### Task 3.1: Backend — goal subtask endpoints

**Objective:** Create/advance/complete goal subtasks from the dashboard.

**Files:** `plugin_api.py`.

**Step 1:** Read the goal state schema first: `~/.hermes/plugins/harness-self-improvement/scripts/goal_state.py` — inspect its subtask shape (id/description/status) before writing any code. Do not guess.

**Step 2:** Add `POST /goal/subtask` `{ description }` → calls the same CLI `goal_state.py` uses to add a subtask (mirror its exact command; wrap in try/except like `post_selfloop`).

**Step 3:** Add `POST /goal/subtask/advance` `{ }` → marks the current pending subtask done (same CLI contract).

**Step 4:** Add `GET /goal` → full `_goal_summary()` (already exists as a helper — expose it).

**Step 5:** Verify: create a probe subtask, advance it, confirm `goal_state.py status` reflects it; delete probe goal.

### Task 3.2: Frontend — subtask checklist in GoalCard

**Objective:** Overview tab shows the goal's subtasks as an interactive checklist.

**Files:** `plugin.js` — extend GoalCard.

**Step 1:** `useQuery` for `/goal` (refetch on selfloop mutations — same invalidateKeys).

**Step 2:** Render subtasks: done → strikethrough muted; pending → checkbox button that fires `advance`; input row "Add subtask…" + Add button.

**Step 3:** Optimistic update: advance removes the row immediately, rolls back on error (per desktop AGENTS.md: optimistic then honest).

**Verify:** esbuild; add a subtask in UI; confirm it appears in `goal_state.py status`.

### Task 3.3: Frontend — cycle timer & streak

**Objective:** Overview shows time since last recorded cycle and the improvement streak, pulled from action-history + selfloop state.

**Files:** `plugin.js` — small strip inside GoalCard hint line: `last cycle 2h ago · 3 improved streak`.

**Verify:** visual only; esbuild clean.

---

## Phase 4 — Command Surface (power users)

### Task 4.1: Copyable route commands

**Objective:** Each route row in RoutesCard gets a copy button for its CLI fallback.

**Files:** `plugin.js` — RoutesCard rows.

**Step 1:** `navigator.clipboard?.writeText(route.fallback)` on click; swap button label to "Copied" for 1.5s (setTimeout + cleanup).

**Step 2:** Guard: if `navigator.clipboard` is undefined (Electron sandbox), fall back to a `title` tooltip with the command and keep the row non-interactive. Do not throw.

**Verify:** esbuild; click copy; paste into a terminal shows the command.

### Task 4.2: Keyboard tab switching

**Objective:** ⌘1–4 switches tabs while the SIPS page is focused.

**Files:** `plugin.js` — Dashboard useEffect keydown listener scoped to `[data-sips-page]` focus (check `document.activeElement?.closest('[data-sips-page]')` to avoid hijacking composer shortcuts).

**Verify:** esbuild; focus page, ⌘2 → Verification tab.

---

## Phase 5 — Polish & Hardening

### Task 5.1: Empty/edge audit
Walk every card with: no data, error data, huge data (40+ events, 10+ records), and offline backend. Fix truncation/overflow. Detector must stay exit 0.

### Task 5.2: Re-run `/impeccable critique`
Target: ≥34/40 (baseline 30). Persist snapshot; record trend.

### Task 5.3: Version bump + changelog
`dashboard/manifest.json` version → 0.3.0; note interactive endpoints + tabbed workspace in description.

---

## Explicit non-goals (YAGNI)
- No arbitrary command execution from the UI (security boundary).
- No raw memory record display (claim boundary).
- No websocket/live-push (15s polling is adequate; adds main-process complexity).
- No new npm dependencies.

## Suggested order & effort
Phase 1 (~20 min) → Phase 2 (~45 min) → Phase 3 (~90 min, needs goal_state.py inspection first) → Phase 4 (~30 min) → Phase 5 (~30 min). Phases are independent; 1–2 can ship together immediately.
