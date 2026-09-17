"""Single importable MemoryService over the indexed Memory Frontier.

Wraps :func:`sips_runtime.memory_frontier.query_frontier` (and the flat
:func:`memory_fabric_search.search_records` fallback during shadow mode) and
applies trust/supersession gates so the rest of the system does not have to
reimplement eligibility logic. This module is the only public retrieval
surface — CLI wrappers, hooks and the MemoryProvider adapter all call in here.
"""
from __future__ import annotations

import time
from typing import Any

try:
    from memory_fabric_graph_index import open_index_with_receipt
    from memory_fabric_search import search_records
    from memory_fabric_search_filters import trust_status
    from memory_frontier import query_frontier
except ImportError:
    from sips_runtime.memory_frontier import query_frontier


DEFAULT_SCOPE = "global"
DEFAULT_LIMIT = 6
DEFAULT_TOKEN_BUDGET = 4000
SHADOW_SAMPLE_RATIO = 0.1


def retrieve(
    *,
    query: str,
    scope: str = DEFAULT_SCOPE,
    store: str | None = None,
    limit: int = DEFAULT_LIMIT,
    include_untrusted: bool = False,
    token_budget: int = DEFAULT_TOKEN_BUDGET,
    seed_limit: int = 8,
    fanout: int = 4,
    shadow: bool = False,
) -> dict[str, Any]:
    """Retrieve an eligibility-gated, bounded set of memory records.

    The primary path is the indexed frontier. The flat search fallback is used
    only when the frontier returns nothing AND we are not in strict mode, so
    existing prompt-text matches that fall outside any indexed scope still
    surface during the migration window.

    Returns a packet with ``source`` (``"frontier"``, ``"flat"``, or
    ``"none"``), ``records`` (the ranked subset), ``candidates`` (pre-gate
    count) and ``shadow`` comparison data when ``shadow=True``.
    """
    if not query or not query.strip():
        return {
            "ok": True,
            "source": "none",
            "reason": "empty_query",
            "query": query,
            "scope": scope,
            "candidates": 0,
            "records": [],
            "frontier": None,
            "flat": None,
        }

    started = time.monotonic()
    result: dict[str, Any] = {
        "ok": True,
        "source": "none",
        "query": query,
        "scope": scope,
        "candidates": 0,
        "records": [],
        "frontier": None,
        "flat": None,
    }

    # Primary: indexed frontier.
    try:
        frontier = query_frontier(
            scope=scope,
            query=query,
            store=store,
            include_untrusted=include_untrusted,
            seed_limit=seed_limit,
            fanout=fanout,
            token_budget=token_budget,
        )
    except Exception as exc:
        frontier = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "records": []}

    result["frontier"] = frontier
    frontier_records = list(frontier.get("records") or [])
    result["candidates"] = int(frontier.get("node_count") or len(frontier_records))

    if frontier_records:
        result["source"] = "frontier"
        result["records"] = frontier_records[:limit]
    elif not include_untrusted:
        # Fallback during migration only — trust/supersession are not enforced
        # here, so we additionally drop verify-before-use records and any whose
        # trust status is not "ready".
        try:
            flat = search_records(
                query=query,
                scope=scope,
                status="active",
                limit=limit * 2,
                path=store,
            )
        except Exception as exc:
            flat = {"ok": False, "error": f"{type(exc).__name__}: {exc}", "records": []}

        result["flat"] = flat
        flat_records = flat.get("records") or []
        safe: list[dict[str, Any]] = []
        for rec in flat_records:
            if bool(rec.get("verify_before_use")):
                continue
            if trust_status(rec) != "ready":
                continue
            safe.append(rec)
            if len(safe) >= limit:
                break
        if safe:
            result["source"] = "flat"
            result["records"] = safe

    if shadow:
        result["shadow"] = _shadow_compare(query=query, scope=scope, store=store, limit=limit)

    result["elapsed_ms"] = round((time.monotonic() - started) * 1000.0, 2)
    return result


def _shadow_compare(
    *,
    query: str,
    scope: str,
    store: str | None,
    limit: int,
) -> dict[str, Any]:
    """Run the flat legacy path without using its output, for comparison logs."""
    try:
        legacy = search_records(query=query, scope=scope, limit=limit * 2, path=store)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    legacy_ids = [str(r.get("id", "")) for r in legacy.get("records") or []]
    return {
        "ok": True,
        "legacy_record_ids": legacy_ids[:limit],
        "legacy_candidates": int(legacy.get("count") or len(legacy_ids)),
    }


def promote(record_id: str, *, evidence_path: str, tier: str = "learning") -> dict[str, Any]:
    """Promote a candidate memory to active status with proof anchoring.

    Thin wrapper so promotion logic has one call site. The actual status
    transition is append-only on the source store.
    """
    return {
        "ok": False,
        "error": "not_implemented",
        "detail": "Promotion must be performed through the Memory Fabric record CLI with an evidence anchor.",
        "record_id": str(record_id) if record_id else None,
        "evidence_path": str(evidence_path) if evidence_path else None,
        "tier": str(tier),
    }


def candidate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Record a candidate lesson (deferred to the Memory Fabric CLI)."""
    return {
        "ok": False,
        "error": "not_implemented",
        "detail": "Candidate recording must be performed through the Memory Fabric record CLI.",
    }
