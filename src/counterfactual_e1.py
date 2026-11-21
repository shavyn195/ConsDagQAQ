"""Counterfactual field-repair diagnostics for saved E1 predictions.

This does not change headline metrics. For each prediction, align one predicted
constraint to a same type/state gold constraint and replace exactly one field
with the gold field. The resulting strict F1 estimates how much that field
alone limits the compiler on the fixed evaluation set.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


FIELDS = ("severity", "params", "scope", "evidence_span")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def freeze(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def key(item: dict[str, Any]) -> tuple[str, ...]:
    scope = item.get("scope")
    if isinstance(scope, list):
        scope = sorted(scope)
    return tuple(
        freeze(value)
        for value in (item.get("type"), item.get("state"), item.get("severity"), scope, item.get("params"))
    )


def prf(tp: int, fp: int, fn: int) -> dict[str, float | int]:
    p = tp / max(tp + fp, 1)
    r = tp / max(tp + fn, 1)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r,
            "f1": 2 * p * r / max(p + r, 1e-12)}


def score(rows: list[dict[str, Any]], pred_by_id: dict[str, dict[str, Any]], repair: str | None) -> dict[str, Any]:
    tp = fp = fn = aligned = 0
    for row in rows:
        record = pred_by_id[row["sample_id"]]
        pred = record.get("prediction") or {}
        gold_items = [x for x in row["gold"].get("constraints", []) if isinstance(x, dict)]
        pred_items = [x.copy() for x in pred.get("constraints", []) if isinstance(x, dict)]

        # Greedy best alignment by type/state and number of already matching fields.
        candidates: list[tuple[int, int, int]] = []
        for gi, gold in enumerate(gold_items):
            for pi, item in enumerate(pred_items):
                if gold.get("type") != item.get("type") or gold.get("state") != item.get("state"):
                    continue
                matches = sum(freeze(gold.get(f)) == freeze(item.get(f)) for f in FIELDS)
                candidates.append((matches, gi, pi))
        used_g: set[int] = set()
        used_p: set[int] = set()
        for _matches, gi, pi in sorted(candidates, reverse=True):
            if gi in used_g or pi in used_p:
                continue
            used_g.add(gi)
            used_p.add(pi)
            aligned += 1
            if repair is not None:
                pred_items[pi][repair] = gold_items[gi].get(repair)

        gold_keys = Counter(key(item) for item in gold_items)
        pred_keys = Counter(key(item) for item in pred_items)
        matched = sum((gold_keys & pred_keys).values())
        tp += matched
        fp += sum(pred_keys.values()) - matched
        fn += sum(gold_keys.values()) - matched
    result = prf(tp, fp, fn)
    result["aligned_pairs"] = aligned
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed_v2"))
    parser.add_argument("--prediction-dir", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result: dict[str, Any] = {"model": args.model, "diagnostic_only": True, "subsets": {}}
    for subset in ("dev", "test_tpl_ho", "test_tool_ho"):
        rows = load_jsonl(args.data_dir / f"{subset}.jsonl")
        predictions = load_jsonl(args.prediction_dir / f"{subset}.jsonl")
        pred_by_id = {item["sample_id"]: item for item in predictions}
        if set(pred_by_id) != {row["sample_id"] for row in rows}:
            raise ValueError(f"sample_id mismatch in {subset}")
        result["subsets"][subset] = {
            "observed": score(rows, pred_by_id, None),
            "repair_each_field": {field: score(rows, pred_by_id, field) for field in FIELDS},
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.output), "model": args.model}, ensure_ascii=False))


if __name__ == "__main__":
    main()
