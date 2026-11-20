"""Audit saved E1 predictions by constraint field without changing headline metrics."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


FIELDS = ("type", "state", "severity", "params", "scope", "evidence_span")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def freeze(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def signature(item: dict[str, Any], fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(freeze(item.get(field)) for field in fields)


def prf(tp: int, fp: int, fn: int) -> dict[str, float | int]:
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": 2 * precision * recall / max(precision + recall, 1e-12)}


def score_rows(rows: list[dict[str, Any]], pred_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    levels = {
        "type_state": ("type", "state"),
        "type_state_severity": ("type", "state", "severity"),
        "type_state_severity_params": ("type", "state", "severity", "params"),
        "strict_without_scope": ("type", "state", "severity", "params"),
        "strict_without_params": ("type", "state", "severity", "scope"),
        "strict_constraint_key": ("type", "state", "severity", "scope", "params"),
    }
    totals = {name: [0, 0, 0] for name in levels}
    field_counts = {field: [0, 0] for field in FIELDS if field not in {"type", "state"}}
    by_type: dict[str, dict[str, list[int]]] = defaultdict(lambda: {name: [0, 0, 0] for name in levels})
    mismatch = Counter()
    state_correct = 0
    parseable = 0

    for row in rows:
        pred_record = pred_by_id[row["sample_id"]]
        pred = pred_record.get("prediction", {})
        gold_items = row["gold"].get("constraints", [])
        pred_items = [item for item in pred.get("constraints", []) if isinstance(item, dict)]
        state_correct += int(pred.get("query_state") == row["gold"].get("query_state"))
        parseable += int(isinstance(pred_record.get("raw"), str) and bool(pred_record["raw"].strip()))

        for name, fields in levels.items():
            gold_keys = Counter(signature(item, fields) for item in gold_items)
            pred_keys = Counter(signature(item, fields) for item in pred_items)
            tp = sum((gold_keys & pred_keys).values())
            fp, fn = sum(pred_keys.values()) - tp, sum(gold_keys.values()) - tp
            for index, value in enumerate((tp, fp, fn)):
                totals[name][index] += value
            for type_name in {item.get("type", "?") for item in gold_items + pred_items}:
                type_gold = Counter(signature(item, fields) for item in gold_items
                                    if item.get("type", "?") == type_name)
                type_pred = Counter(signature(item, fields) for item in pred_items
                                    if item.get("type", "?") == type_name)
                type_tp = sum((type_gold & type_pred).values())
                by_type[type_name][name][0] += type_tp
                by_type[type_name][name][1] += sum(type_pred.values()) - type_tp
                by_type[type_name][name][2] += sum(type_gold.values()) - type_tp

        # Match same-type/state pairs, then measure whether remaining fields agree.
        candidates: list[tuple[int, int, int]] = []
        for gi, gold in enumerate(gold_items):
            for pi, pred_item in enumerate(pred_items):
                if gold.get("type") != pred_item.get("type") or gold.get("state") != pred_item.get("state"):
                    continue
                matches = sum(freeze(gold.get(field)) == freeze(pred_item.get(field)) for field in FIELDS[2:])
                candidates.append((matches, gi, pi))
        used_gold: set[int] = set()
        used_pred: set[int] = set()
        for _matches, gi, pi in sorted(candidates, reverse=True):
            if gi in used_gold or pi in used_pred:
                continue
            used_gold.add(gi)
            used_pred.add(pi)
            gold, pred_item = gold_items[gi], pred_items[pi]
            exact_fields = []
            for field in FIELDS[2:]:
                ok = freeze(gold.get(field)) == freeze(pred_item.get(field))
                field_counts[field][1] += 1
                field_counts[field][0] += int(ok)
                if ok:
                    exact_fields.append(field)
            missing = [field for field in FIELDS[2:] if field not in exact_fields]
            mismatch["+".join(missing) if missing else "all_non_type_fields_match"] += 1

    return {
        "records": len(rows),
        "state_accuracy": state_correct / max(len(rows), 1),
        "raw_output_nonempty_rate": parseable / max(len(rows), 1),
        "constraint_metrics": {name: prf(*counts) for name, counts in totals.items()},
        "per_type_strict": {kind: prf(*levels["strict_constraint_key"]) for kind, levels in by_type.items()},
        "conditional_field_accuracy_given_type_and_state_match": {
            field: {"correct": counts[0], "matched_pairs": counts[1],
                    "accuracy": counts[0] / max(counts[1], 1)}
            for field, counts in field_counts.items()
        },
        "mismatch_patterns_given_type_and_state_match": dict(mismatch),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed_v2"))
    parser.add_argument("--prediction-dir", type=Path,
                        default=Path("outputs/e1/Qwen3-0.6B/trained_predictions"))
    parser.add_argument("--output", type=Path, default=Path("outputs/analysis_e1_0.6b.json"))
    args = parser.parse_args()
    subsets = ("dev", "test_tpl_ho", "test_tool_ho")
    result: dict[str, Any] = {"model": "Qwen3-0.6B trained LoRA", "seed": 42,
                              "diagnostic_only": True, "subsets": {}}
    for subset in subsets:
        rows = load_jsonl(args.data_dir / f"{subset}.jsonl")
        predictions = load_jsonl(args.prediction_dir / f"{subset}.jsonl")
        pred_by_id = {item["sample_id"]: item for item in predictions}
        if len(pred_by_id) != len(predictions):
            raise ValueError(f"duplicate prediction sample_id in {subset}")
        expected_ids = {row["sample_id"] for row in rows}
        if expected_ids != set(pred_by_id):
            raise ValueError(f"sample_id mismatch for {subset}: missing={len(expected_ids-set(pred_by_id))}, "
                             f"extra={len(set(pred_by_id)-expected_ids)}")
        for variant in ("explicit", "implicit", "none"):
            group = [row for row in rows if row["variant"] == variant]
            result["subsets"].setdefault(subset, {})[variant] = score_rows(group, pred_by_id)
        result["subsets"][subset]["all"] = score_rows(rows, pred_by_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.output), "subsets": list(result["subsets"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
