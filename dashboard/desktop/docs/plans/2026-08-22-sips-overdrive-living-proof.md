# SIPS Overdrive + Delight — "Living Proof" Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the SIPS Control Plane feel like a living instrument where proof movement is *felt* — spring-physics orb, evidence-gated celebration, cinematic tab morphs, and an ambient heartbeat tied to the real selfloop — while keeping the Operate-mode reliability floor intact.

**Architecture:** All motion in one file (`plugin.js`) via a small hand-rolled spring solver + Web Animations API (no dependencies, per the non-goals). One injected `<style>` tag (already exists for focus-visible) carries `@property` registrations and keyframes. Every effect is progressive-enhancement gated and evidence-gated: celebration fires only when the persisted proof trend advances, never on routine clicks.

**Tech Stack:** Web Animations API, CSS `@property`, View Transitions API (same-document), injected stylesheet, existing `useQuery` polling as the data source. No new dependencies.

---

## Ground rules (from overdrive.md + delight.md, non-negotiable)

1. **Evidence gate:** celebration only when persisted `proof_trend` last value > previous value. Never on clicks, never on refresh.
2. **Progressive enhancement:** every API feature-detected; the page must be complete without any effect.
3. **60fps floor:** springs on `transform`/`opacity`/`--orb` custom props only. If jank, simplify — never ship jank.
4. **Repetition-safe:** celebration intensity scales down with frequency (cooldown ≥ 60s between celebrations).
5. **Respect reduced motion:** `matchMedia('(prefers-reduced-motion: reduce)')` disables springs/celebration/heartbeat; state changes remain instant.
6. **No sound.** No fake work. No delay added to any primary action.

---

## Phase A — Living Proof (core identity)

### Task A1: Spring solver + motion primitives

**Objective:** A tiny reusable spring animation engine for numeric props.

**Files:** Modify `~/.hermes/desktop-plugins/harness-self-improvement/plugin.js` (top-level helpers).

**Step 1:** Add after COLORS/styles:

```js
// Minimal spring solver: returns an rAF-driven animation of a numeric value.
// Respects prefers-reduced-motion by snapping instantly.
function springTo({ from, to, onFrame, stiffness = 170, damping = 22, onDone }) {
  if (typeof window === 'undefined') return () => {}
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    onFrame(to); if (onDone) onDone(); return () => {}
  }
  let value = from, velocity = 0, raf = 0, last = performance.now()
  const step = (now) => {
    const dt = Math.min((now - last) / 1000, 1 / 30); last = now
    const force = (to - value) * stiffness
    velocity += force * dt; velocity *= Math.exp(-damping * dt)
    value += velocity * dt
    if (Math.abs(to - value) < 0.1 && Math.abs(velocity) < 0.1) {
      onFrame(to); if (onDone) onDone(); return
    }
    onFrame(value); raf = requestAnimationFrame(step)
    return
  }
  raf = requestAnimationFrame(step)
  return () => cancelAnimationFrame(raf)
}
```

**Step 2:** Verify: `npx esbuild --loader:.js=jsx --jsx=automatic --outfile=/dev/null <file>` clean.

### Task A2: `@property` registrations + keyframes in the injected stylesheet

**Objective:** Animatable custom props for the orb and a celebration keyframe.

**Files:** `plugin.js` — extend the `sips-focus-style` tag in `register()`.

**Step 1:** Extend `styleTag.textContent` with:

```css
@property --sips-orb { syntax: '<percentage>'; inherits: false; initial-value: 0%; }
@keyframes sips-celebrate {
  0% { box-shadow: 0 0 0 0 rgba(105,211,154,0.45); }
  100% { box-shadow: 0 0 0 26px rgba(105,211,154,0); }
}
@keyframes sips-breathe {
  0%, 100% { opacity: 0.55; } 50% { opacity: 1; }
}
```

**Step 2:** esbuild clean (CSS in JS string — no lint impact).

### Task A3: Living orb

**Objective:** The hero proof orb springs to new coverage values and morphs hue with posture.

**Files:** `plugin.js` — `StatusOverview` orb.

**Step 1:** Track previous coverage in a ref-like module map keyed by nothing (single instance): `let lastCoverage = null` module-scope; in StatusOverview, `useEffect(() => { springTo({ from: lastCoverage ?? coverage, to: coverage, onFrame: (v) => orbRef.current?.style.setProperty('--sips-orb', v + '%') }) }, [coverage])`.

**Step 2:** Orb background becomes `conic-gradient(var(--orb-color) var(--sips-orb), rgba(255,255,255,0.1) 0)`; orb color also springs (lerp between good/warn/bad RGB by posture tone change).

**Data source:** the existing 15s status polling — no new polling.

**Verify:** change coverage in a fixture; orb animates smoothly, no jump-cut.

### Task A4: Evidence-gated celebration ring

**Objective:** When persisted proof trend advances, the orb emits one expanding ring + count-up.

**Files:** `plugin.js` — StatusOverview + a `celebrateProofGain` helper.

**Step 1:** In Dashboard's data effect, compare last two `data.proof_trend` values:

```js
const trend = data.proof_trend || []
const prev = trend[trend.length - 2], curr = trend[trend.length - 1]
const now = Date.now()
if (curr > prev && now - (window.__sipsLastCelebrate || 0) > 60000) {
  window.__sipsLastCelebrate = now
  celebrateProofGain(orbRef, coverageRef)
}
```

**Step A4.2:** `celebrateProofGain`: WAAPI `animate()` on the orb wrapper with `sips-celebrate` keyframes (one iteration), plus spring count-up of the readiness value from previous to new coverage.

**Verify:** append a synthetic history entry with higher ready-count; run a check that advances coverage; ring fires once; second advance within 60s does NOT re-fire.

### Task A5: Count-up numerics on the signal tiles

**Objective:** All four signal values spring to new numbers instead of jumping.

**Files:** `plugin.js` — `Signal` component.

**Step 1:** `useEffect` on `value` change → `springTo` from previous numeric, formatting via existing `compactNumber` on each frame; store previous in a module WeakMap keyed by label.

**Verify:** esbuild clean; values roll rather than jump.

---

## Phase B — Command Deck (cinematic transitions)

### Task B1: View Transitions for tab switches

**Objective:** Tab switches morph instead of hard-swap.

**Files:** `plugin.js` — tab click handler.

**Step 1:** Because React state updates are async, wrap the swap so the transition captures the DOM change:

```js
const switchTab = (id) => {
  const doc = document
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (doc.startViewTransition && !reduced) {
    doc.startViewTransition(() => new Promise((resolve) => {
      setActiveTab(id)
      requestAnimationFrame(() => requestAnimationFrame(resolve))
    }))
  } else {
    setActiveTab(id)
  }
}
```

**Step 2:** Wire every tab button's `onClick` to `switchTab(tab.id)` (replacing the direct `setActiveTab`). The ⌘1–4 handler switches through `switchTab` too.

**Step 3:** Extend the injected stylesheet with transition CSS:

```css
::view-transition-old(root) { animation: sips-vt-out 120ms ease-in both; }
::view-transition-new(root) { animation: sips-vt-in 160ms ease-out both; }
@keyframes sips-vt-out { to { opacity: 0; } }
@keyframes sips-vt-in { from { opacity: 0; transform: translateY(8px); } }
```

**Verify:** tab switch visibly cross-fades with a rise; reduced-motion → instant.

### Task B2: Dialog-grow from trigger

**Objective:** The Record-a-lesson form grows out of its own button on first open.

**B2.1:** RecordCard body wrapped in a container with `view-transition-name: sips-record` only while opening; the Record button gets `view-transition-name: sips-record-btn`. On click, `startViewTransition` swaps the collapsed→expanded states; shared name morphs button→form.

**Verify:** click Record → form appears to grow from the button; Escape/blur closes normally.

---

## Phase C — Signal Room (ambient heartbeat)

### Task C1: Heartbeat layer

**Objective:** A subtle breathing glow behind the hero, driven by real selfloop state and real event flow.

**Files:** `plugin.js` — StatusOverview hero.

**Step 1:** Hero gains a pseudo-glow div (absolute, behind content) whose `sips-breathe` animation runs ONLY when `selfloop.active === true`; paused (animation-play-state) when idle. Opacity ceiling 0.5 — never distracting.

**Step 2:** On each new lifecycle event batch (compare `events.event_count` changes), the statusbar pulse dot emits one soft ping animation (scale 1→1.35→1, 300ms). Cooldown 5s.

**Verify:** start selfloop → hero breathes; clear → stops; reduced-motion → nothing.

### Task C2: Quiet-hours respect (delight guard)

**Objective:** No ambient motion at all if the user hasn't interacted with the page for 10 minutes.

**Files:** `plugin.js` — module-scope `lastInteraction` updated on pointerdown/keydown; heartbeat and ping check it before animating.

**Verify:** idle 10 min → page is fully still; any interaction resumes.

---

## Phase 5 — Verification

### Task V1: Full verification sweep

- esbuild clean; detector exit 0
- Reduced-motion pass: all effects off, page complete
- Cooldown tests: celebration fires once per genuine advance; heartbeat stops when idle/selfloop cleared
- `/impeccable critique` re-score (target ≥36/40; baseline 30 → current ~33 est.)

### Task V2: Version bump 0.4.0 + changelog line in manifest description.

---

## Explicit non-goals
- No sound, no WebGL, no particles — wrong register for Operate mode.
- No effect may delay any action's execution (celebration is fire-and-forget overlay).
- No new dependencies.

## Effort
Phase A ~90 min (the identity piece), Phase B ~60 min, Phase C ~45 min, Verification ~30 min.
