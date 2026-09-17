#!/usr/bin/env python3
"""Recall ranker — scoped UserPromptSubmit hook.

Replaces the raw memory_fabric_prompt_search at the UserPromptSubmit slot.
Searches Memory Fabric for the user's prompt, scoped to the current working
directory, then RANKS the results without discarding search relevance:

  1. Higher base search relevance first.
  2. For equal relevance: recent eval failures, failure-tagged records,
     then success-tagged / high-confidence records, then other records.
  3. Within equal relevance and outcome class: newest first.

Outcome annotations are advisory tie-breakers, not proof of correctness.

Same depth on every model — v2 has no model routing. The harness's versatility
comes from delegation (fresh-context subagents) and forced lesson capture, not
from tuning recall depth per model.

Advisory-only, non-blocking, silent on failure.

Hook input:
  {"hook_event_name": "UserPromptSubmit", "cwd": "...", "prompt": "...", ...}
Hook output:
  {"additionalContext": "scoped recall:\n..."}  or {} on no hits
"""
import json
import os
import re
import subprocess
import sys
import worktree_scope
from datetime import datetime, timezone
from pathlib import Path

from sips_paths import eval_results_path

LIMIT = 4
MAX_CHARS = 1800
MIN_QUERY_LEN = 4
MAX_QUERY_LEN = 200

STOPWORDS = {
    "the", "a", "an", "is", "are", "to", "in", "on", "of", "for", "and", "or",
    "but", "with", "this", "that", "it", "we", "you", "i", "do", "does", "did",
    "what", "how", "why", "when", "where", "can", "could", "would", "should",
    "will", "may", "might", "please", "yes", "no", "ok", "okay",
}


from sips_memory_fabric import find_memory_fabric_cli as find_cli


def extract_query(prompt):
    if not prompt:
        return ""
    text = prompt.strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^/\S+\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < MIN_QUERY_LEN:
        return ""
    if len(text) <= MAX_QUERY_LEN:
        return text
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b", text)
    keywords = [w for w in words if w.lower() not in STOPWORDS]
    if not keywords:
        return text[:MAX_QUERY_LEN]
    return " ".join(keywords[:8])[:MAX_QUERY_LEN]


def _recent_failed_eval_cases(max_age_seconds=7 * 86400):
    """Return set of caseIds whose latest run failed within max_age_seconds.

    Empty set if results.jsonl is missing or no recent failures.
    """
    path = eval_results_path()
    if not path.exists():
        return set()
    try:
        with open(path, encoding="utf-8") as fp:
            lines = [ln.strip() for ln in fp if ln.strip()]
    except OSError:
        return set()

    runs_by_case = {}
    now = datetime.now(timezone.utc).timestamp()
    for line in lines:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        ft = r.get("finishedAtISO", "")
        try:
            ts = datetime.fromisoformat(ft.replace("Z", "+00:00")).timestamp()
        except (ValueError, TypeError):
            continue
        if now - ts > max_age_seconds:
            continue
        cid = r.get("caseId", "")
        if cid:
            runs_by_case.setdefault(cid, []).append(r)

    failed = set()
    for cid, runs in runs_by_case.items():
        runs.sort(key=lambda x: x.get("finishedAtISO", ""))
        if runs[-1].get("errorMessage"):
            continue  # didn't really run, don't boost
        if not runs[-1].get("passed"):
            failed.add(cid)
    return failed


def rank(records):
    """Preserve relevance; use outcome boosts then newest-first for ties.

    Legacy callers without scores retain outcome ordering. Production search
    carries `_score`, which always takes precedence over outcome annotations.
    """
    failed_eval_cases = _recent_failed_eval_cases()

    def key(rec):
        tags = rec.get("tags") or []
        conf = rec.get("confidence") or ""
        raw_ts = rec.get("created_at") or rec.get("updated_at") or ""
        try:
            dt = datetime.fromisoformat(str(raw_ts).replace("Z", "+00:00"))
            ts = dt.replace(tzinfo=timezone.utc).timestamp() if dt.tzinfo is None else dt.timestamp()
        except (ValueError, OverflowError, OSError):
            ts = 0.0
        body = rec.get("body") or ""

        # Outcome signals are tie-breakers, never category overrides.
        boost = 0
        if any(cid in tags or cid in body for cid in failed_eval_cases):
            boost = 3
        elif "failure" in tags:
            boost = 2
        elif "success" in tags or conf == "high":
            boost = 1
        return (-int(rec.get("_score") or 0), -boost, -ts)
    return sorted(records, key=key)


def emit(context):
    sys.stdout.write(json.dumps({"additionalContext": context}))
    sys.stdout.flush()


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    prompt = payload.get("prompt") or ""
    query = extract_query(prompt)
    if not query:
        return

    mf = find_cli()
    if not mf:
        return

    cwd = worktree_scope.resolve_scope(payload.get("cwd") or os.getcwd())
    try:
        r = subprocess.run(
            ["python3", mf, "search",
             "--query", query, "--scope", cwd, "--limit", str(LIMIT)],
            capture_output=True, text=True, timeout=8
        )
        if r.returncode != 0:
            return
        data = json.loads(r.stdout) if r.stdout.strip() else {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return

    records = data.get("records") or []
    if not records:
        return

    ranked = rank(records)
    emit(build_context(query, ranked))


def density_glyph(rec):
    """Failure → 🔴, success / high-confidence → 🟢, else ⚪."""
    tags = rec.get("tags") or []
    conf = rec.get("confidence")
    if "failure" in tags:
        return "🔴"
    if "success" in tags or conf == "high":
        return "🟢"
    return "⚪"


def build_context(query, ranked):
    """Render header + record lines (+ truncation) for the injected block.

    Rich formatting: per-tier icons, source-provenance suffix (session link
    or evidence path basename) so a lesson can be traced without a follow-up
    search, and freshness age. Stays bounded by MAX_CHARS.
    """
    header = (f"🧠 scoped recall ({len(ranked)} lessons): query '{query[:60]}' "
              f"(advisory — verify before relying on claims).")
    lines = [header, ""]

    tier_icons = {
        "learning": "📘",
        "work": "🛠",
        "knowledge": "📚",
        "state": "📌",
    }
    now = datetime.now(timezone.utc)

    for rec in ranked:
        tags = rec.get("tags") or []
        title = rec.get("title", "")
        body = (rec.get("body") or "").strip().replace("\n", " ")[:200]
        conf = rec.get("confidence")
        marker = ""
        if "failure" in tags:
            marker = "⚠ PRIOR FAILURE  "
        elif "success" in tags or conf == "high":
            marker = "✓ prior success  "
        glyph = density_glyph(rec)
        tier_icon = tier_icons.get(rec.get("tier"), "•")

        # Provenance hint: source_backed runs link the originating session;
        # other provenance types show a compact evidence filename.
        prov = rec.get("provenance") if isinstance(rec.get("provenance"), dict) else {}
        prov_bits = []
        session_id = prov.get("session_id")
        if session_id:
            prov_bits.append(f"@session:{str(session_id)[:22]}")
        evidence_path = str(prov.get("evidence_path") or "")
        if evidence_path:
            prov_bits.append(evidence_path.rsplit("/", 1)[-1][:28])

        # Freshness age (records carry ISO created_at).
        created = rec.get("created_at") or ""
        age = ""
        if created:
            try:
                created_dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                age_days = (now - created_dt).days
                age = f" · {age_days}d" if age_days else " · today"
            except ValueError:
                pass

        suffix = f" ({' · '.join(prov_bits)})" if prov_bits else ""
        lines.append(
            f"{glyph} {tier_icon} - {marker}[{rec.get('tier','?')}|conf={conf}]{age} {title}: {body}{suffix}"
        )

    text = "\n".join(lines)
    if len(text) > MAX_CHARS:
        text = text[:MAX_CHARS] + "\n...(truncated)"
    return text


if __name__ == "__main__":
    if "--query" in sys.argv:
        # /recall command mode — emit JSON to stdout for the command wrapper
        mf = find_cli()
        if not mf:
            print("[]")
            sys.exit(0)
        idx = sys.argv.index("--query")
        q = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        cwd = worktree_scope.resolve_scope(os.getcwd())
        try:
            r = subprocess.run(
                ["python3", mf, "search", "--query", q, "--scope", cwd,
                 "--limit", str(LIMIT)],
                capture_output=True, text=True, timeout=8
            )
            data = json.loads(r.stdout) if r.stdout.strip() else {}
        except Exception:
            data = {}
        print(json.dumps({"records": data.get("records", [])}, indent=2))
        sys.exit(0)
    main()
    sys.exit(0)
