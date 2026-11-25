"""Diagnose execution-vs-record gaps and seed overlap for completed v6 runs.

The analysis is deliberately read-only with respect to experiment artifacts. It
loads only frozen v6 rows and raw model predictions, then replays the committed
scorer and fail-closed executor. It does not choose a checkpoint or alter gold.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from eval_exec_v6 import aligned_raw, evaluate_v6
from run_e1 import constraint_key, core_key, eval_subsets, load_jsonl, score, strict_parse
from analyze_v6_main import current_data_hashes, file_sha256, verified_science_run


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _matched_indices(gold: list[dict[str, Any]], pred: list[dict[str, Any]], key_fn):
    """Deterministically match equal keys as multisets; return pairs and leftovers."""
    buckets: dict[Any, list[int]] = defaultdict(list)
    for index, item in enumerate(pred):
        buckets[key_fn(item)].append(index)
    pairs: list[tuple[int, int]] = []
    unmatched_gold: list[int] = []
    used: set[int] = set()
    for gi, item in enumerate(gold):
        candidates = buckets.get(key_fn(item), [])
        pi = next((candidate for candidate in candidates if candidate not in used), None)
        if pi is None:
            unmatched_gold.append(gi)
        else:
            used.add(pi)
            pairs.append((gi, pi))
    unmatched_pred = [index for index in range(len(pred)) if index not in used]
    return pairs, unmatched_gold, unmatched_pred


def record_diagnostic(row: dict[str, Any], raw: str, execution: dict[str, Any]) -> dict[str, Any]:
    parsed = strict_parse(raw)
    gold = [item for item in row["gold"]["constraints"] if isinstance(item, dict)]
    pred = [item for item in (parsed or {}).get("constraints", []) if isinstance(item, dict)]
    exact_pairs, exact_missing, exact_extra = _matched_indices(gold, pred, constraint_key)
    core_pairs, core_missing, core_extra = _matched_indices(gold, pred, core_key)

    fields = Counter()
    type_fields: dict[str, Counter] = defaultdict(Counter)
    for gi, pi in core_pairs:
        g, p = gold[gi], pred[pi]
        if constraint_key(g)[3] != constraint_key(p)[3]:
            fields["scope"] += 1
            type_fields[g["type"]]["scope"] += 1
        if g.get("state") != p.get("state"):
            fields["constraint_state"] += 1
            type_fields[g["type"]]["constraint_state"] += 1
        if g.get("severity") != p.get("severity"):
            fields["severity"] += 1
            type_fields[g["type"]]["severity"] += 1
        if (g.get("evidence_span") or "") != (p.get("evidence_span") or ""):
            fields["evidence_span"] += 1
            type_fields[g["type"]]["evidence_span"] += 1

    top_state_ok = parsed is not None and parsed.get("query_state") == row["gold"]["query_state"]
    return {
        "sample_id": row["sample_id"],
        "group_id": row["group_id"],
        "variant": row["variant"],
        "faithful": bool(execution["faithful_success"]),
        "safe": bool(execution["safe_success"]),
        "strict_record_exact": bool(parsed is not None and top_state_ok and not exact_missing and not exact_extra),
        "core_record_exact": bool(parsed is not None and top_state_ok and not core_missing and not core_extra),
        "top_state_correct": bool(top_state_ok),
        "strict_matched_constraints": len(exact_pairs),
        "core_matched_constraints": len(core_pairs),
        "core_missing": len(core_missing),
        "core_extra": len(core_extra),
        "field_mismatches_among_core_matches": dict(fields),
        "field_mismatches_by_type": {name: dict(counts) for name, counts in type_fields.items()},
    }


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _binary_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(records)
    faithful = sum(item["faithful"] for item in records)
    exact = sum(item["strict_record_exact"] for item in records)
    return {
        "constrained_records": n,
        "faithful_success": faithful,
        "faithful_rate": _rate(faithful, n),
        "strict_record_exact": exact,
        "strict_record_exact_rate": _rate(exact, n),
        "faithful_but_not_strict_exact": sum(item["faithful"] and not item["strict_record_exact"] for item in records),
        "strict_exact_but_not_faithful": sum(item["strict_record_exact"] and not item["faithful"] for item in records),
        "neither": sum(not item["strict_record_exact"] and not item["faithful"] for item in records),
        "faithful_and_strict_exact": sum(item["faithful"] and item["strict_record_exact"] for item in records),
    }


def _failure_overlap(by_seed: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    failure_sets: dict[str, set[str]] = {}
    for seed, records in by_seed.items():
        by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in records.values():
            if item["variant"] in ("explicit", "implicit"):
                by_group[item["group_id"]].append(item)
        failure_sets[seed] = {group for group, values in by_group.items() if any(not item["faithful"] for item in values)}
    seeds = sorted(failure_sets)
    pairs = {}
    for index, seed_a in enumerate(seeds):
        for seed_b in seeds[index + 1 :]:
            intersection = failure_sets[seed_a] & failure_sets[seed_b]
            union = failure_sets[seed_a] | failure_sets[seed_b]
            pairs[f"{seed_a}_vs_{seed_b}"] = {
                "seed_a_failed_groups": len(failure_sets[seed_a]),
                "seed_b_failed_groups": len(failure_sets[seed_b]),
                "intersection": len(intersection),
                "union": len(union),
                "jaccard": _rate(len(intersection), len(union)),
            }
    return pairs


def analyze(data_dir: Path, runs_root: Path, seeds: tuple[int, ...]) -> dict[str, Any]:
    subsets = eval_subsets(data_dir)
    manifests = {}
    stored_metrics = {}
    for seed in seeds:
        run = runs_root / f"Qwen3-1.7B-v6-seed{seed}"
        valid, reason = verified_science_run(run, data_dir, subsets, seed, "models/Qwen3-1.7B")
        if not valid:
            raise ValueError(f"Refusing incomplete/unverified seed {seed}: {reason}")
        completion = json.loads((run / "completion.json").read_text(encoding="utf-8"))
        manifests[str(seed)] = {
            "fingerprint": completion["fingerprint"],
            "artifact_sha256": completion["artifact_sha256"],
        }
        stored_metrics[seed] = json.loads((run / "metrics.json").read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "analysis": "v6 execution-versus-record diagnostic",
        "seeds": list(seeds),
        "data_sha256": current_data_hashes(data_dir, subsets),
        "diagnostic_source_sha256": file_sha256(Path(__file__)),
        "verified_runs": manifests,
        "subsets": {},
        "limitations": [
            "The planner consumes type and params, but not compiler scope/state/severity/evidence; the diagnostic does not treat these record fields as execution causes.",
            "Seed-overlap comparisons are conditional on the listed completed seeds and do not estimate seed-population uncertainty.",
            "All labels remain generator-constructed; this analysis does not establish human recoverability.",
        ],
    }
    for subset in subsets:
        rows = load_jsonl(data_dir / f"{subset}.jsonl")
        by_seed: dict[str, dict[str, dict[str, Any]]] = {}
        split_result: dict[str, Any] = {"per_seed": {}, "field_mismatch_counts_on_core_matches": {}}
        field_totals: Counter = Counter()
        type_field_totals: dict[str, Counter] = defaultdict(Counter)
        for seed in seeds:
            pred_path = runs_root / f"Qwen3-1.7B-v6-seed{seed}" / "trained_predictions" / f"{subset}.jsonl"
            if not pred_path.is_file():
                continue
            pred_rows = load_jsonl(pred_path)
            raw = aligned_raw(rows, pred_rows)
            field_metrics = score(rows, [None] * len(rows), raw)
            _, outcomes = evaluate_v6(rows, raw)
            outcome_by_id = {item["sample_id"]: item for item in outcomes}
            diagnostics = {
                row["sample_id"]: record_diagnostic(row, pred, outcome_by_id[row["sample_id"]])
                for row, pred in zip(rows, raw)
            }
            by_seed[str(seed)] = diagnostics
            constrained = [item for item in diagnostics.values() if item["variant"] in ("explicit", "implicit")]
            field_counts = Counter()
            for item in constrained:
                field_counts.update(item["field_mismatches_among_core_matches"])
                for constraint_type, counts in item["field_mismatches_by_type"].items():
                    type_field_totals[constraint_type].update(counts)
            summary = _binary_summary(constrained)
            if abs(sum(item["strict_record_exact"] for item in diagnostics.values()) / len(rows)
                   - field_metrics["record_exact_match"]) > 1e-12:
                raise ValueError(f"Record exactness disagrees with frozen scorer: {seed}/{subset}")
            saved = stored_metrics[seed]["trained"][subset]
            if (field_metrics["constraint_micro"] != saved["constraint_micro"]
                    or field_metrics["record_exact_match"] != saved["record_exact_match"]
                    or round(summary["faithful_rate"], 4) != saved["exec"]["faithful_success_constrained"]):
                raise ValueError(f"Rescoring disagrees with saved metrics: {seed}/{subset}")
            summary.update({
                "strict_constraint_f1": field_metrics["constraint_micro"]["f1"],
                "core_constraint_f1": field_metrics["constraint_core_micro"]["f1"],
                "record_exact_match": field_metrics["record_exact_match"],
                "evidence_exact_rate": field_metrics["evidence_exact_rate"],
                "state_accuracy": field_metrics["state_accuracy"],
                "n_alarm": None,
                "field_mismatch_counts_on_core_matches": dict(field_counts),
            })
            none_rows = [row for row in rows if row["variant"] == "none"]
            pred_by_id = {item["sample_id"]: item["raw"] for item in pred_rows}
            parsed_none = [strict_parse(pred_by_id[row["sample_id"]]) for row in none_rows]
            alarms = [value is None or bool(value["constraints"]) or value["query_state"] != "none" for value in parsed_none]
            summary["n_alarm"] = {"count": sum(alarms), "total": len(alarms), "rate": _rate(sum(alarms), len(alarms))}
            summary["core_missing_constraints"] = sum(item["core_missing"] for item in constrained)
            summary["core_extra_constraints"] = sum(item["core_extra"] for item in constrained)
            split_result["per_seed"][str(seed)] = summary
            for item in constrained:
                field_totals.update(item["field_mismatches_among_core_matches"])
        split_result["field_mismatch_counts_on_core_matches"] = dict(field_totals)
        split_result["field_mismatch_counts_by_type_on_core_matches"] = {
            constraint_type: dict(counts) for constraint_type, counts in sorted(type_field_totals.items())
        }
        split_result["record_failure_overlap_by_seed_pair"] = _failure_overlap(by_seed)
        split_result["field_error_record_overlap_by_seed_pair"] = {}
        present_seeds = sorted(by_seed)
        for i, seed_a in enumerate(present_seeds):
            for seed_b in present_seeds[i + 1 :]:
                shared_ids = set(by_seed[seed_a]) & set(by_seed[seed_b])
                per_field = {}
                for field in ("scope", "constraint_state", "severity", "evidence_span"):
                    errors_a = {sid for sid in shared_ids if by_seed[seed_a][sid]["field_mismatches_among_core_matches"].get(field, 0)}
                    errors_b = {sid for sid in shared_ids if by_seed[seed_b][sid]["field_mismatches_among_core_matches"].get(field, 0)}
                    intersection, union = len(errors_a & errors_b), len(errors_a | errors_b)
                    per_field[field] = {
                        "seed_a_error_records": len(errors_a),
                        "seed_b_error_records": len(errors_b),
                        "intersection": intersection,
                        "union": union,
                        "jaccard": _rate(intersection, union),
                    }
                split_result["field_error_record_overlap_by_seed_pair"][f"{seed_a}_vs_{seed_b}"] = per_field
        result["subsets"][subset] = split_result
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed_v6"))
    parser.add_argument("--runs-root", type=Path, default=Path("outputs/e1_v6"))
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.data_dir, args.runs_root, tuple(args.seeds))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"saved": str(args.out), "available_seeds": args.seeds, "splits": list(report["subsets"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
