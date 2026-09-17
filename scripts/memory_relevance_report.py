#!/usr/bin/env python3
"""Frozen memory relevance label corpus and precision/harmful-recall report.

The label corpus is a small set of (prompt, expected_record_ids,
forbidden_record_ids) tuples. Each tuple records a human judgment about
which records should and should not be retrieved for a given query.

A precision/harmful-recall report runs the MemoryService against the corpus
and aggregates:
  - Precision@k: fraction of retrieved records that are in expected_ids
  - Harmful recall: retrieved records that are in forbidden_ids
  - Superseded recall: retrieved records whose status is superseded

Usage:
  python3 scripts/memory_relevance_report.py --store path/to/memory.jsonl \
      --labels fixtures/relevance_labels.json --output /tmp/report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "sips_runtime"))

from memory_service import retrieve


def load_labels(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text()) if path.exists() else []


def evaluate(labels: list[dict[str, Any]], store: str, limit: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    tp = 0
    fp = 0
    fn = 0
    harmful = 0
    superseded = 0
    total_expected = 0

    for case in labels:
        prompt = case.get("prompt", "")
        expected = set(case.get("expected_ids") or [])
        forbidden = set(case.get("forbidden_ids") or [])
        total_expected += len(expected)

        result = retrieve(query=prompt, store=store, limit=limit)
        retrieved_ids = [r.get("id") for r in result.get("records") or []]

        case_tp = len(expected & set(retrieved_ids))
        case_fp = len([i for i in retrieved_ids if i not in expected])
        case_fn = len(expected - set(retrieved_ids))
        case_harmful = len(forbidden & set(retrieved_ids))

        tp += case_tp
        fp += case_fp
        fn += case_fn
        harmful += case_harmful

        for rec in result.get("records") or []:
            if str(rec.get("status", "")).lower() == "superseded":
                superseded += 1

        rows.append({
            "prompt": prompt[:100],
            "retrieved": retrieved_ids,
            "expected": sorted(expected),
            "forbidden": sorted(forbidden),
            "precision": round(case_tp / max(1, len(retrieved_ids)), 3),
            "recall": round(case_tp / max(1, len(expected)), 3),
            "harmful_recalls": sorted(forbidden & set(retrieved_ids)),
        })

    total_retrieved = tp + fp
    precision = tp / max(1, total_retrieved)
    recall = tp / max(1, total_expected)
    f1 = 2 * precision * recall / max(1e-9, precision + recall)

    return {
        "schema": "hermes.sips.relevance_report.v1",
        "corpus_size": len(labels),
        "limit": limit,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "harmful_recalls": harmful,
        "superseded_recalls": superseded,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--limit", type=int, default=4)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    labels = load_labels(Path(args.labels))
    report = evaluate(labels, args.store, args.limit)
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(json.dumps({
        "corpus": report["corpus_size"],
        "precision": report["precision"],
        "recall": report["recall"],
        "f1": report["f1"],
        "harmful": report["harmful_recalls"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
