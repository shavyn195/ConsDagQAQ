"""Paired, CPU-only diagnosis of the v5 seed-42/seed-43 1.7B runs.

This is a descriptive audit of two already completed runs. Group bootstrap
intervals quantify test-group uncertainty conditional on these two adapters;
they do not estimate the population of training seeds.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from rescore_v4_side import ROOT, aligned, outcome
from run_e1 import eval_subsets, load_jsonl, score


def group_bootstrap_delta(
    group_values: dict[str, tuple[int, int]], *, n_boot: int = 10_000, seed: int = 20261123
) -> list[float]:
    """Paired group bootstrap of A-B success-rate differences, resampling whole groups."""
    groups = sorted(group_values)
    if not groups:
        raise ValueError("No constrained task groups found")
    point_denominator = sum(group_values[g][1] for g in groups)
    point = sum(group_values[g][0] for g in groups) / point_denominator
    rng = random.Random(seed)
    samples: list[float] = []
    for _ in range(n_boot):
        picked = [groups[rng.randrange(len(groups))] for _ in groups]
        numerator = sum(group_values[g][0] for g in picked)
        denominator = sum(group_values[g][1] for g in picked)
        samples.append(numerator / denominator)
    samples.sort()
    return [round(point, 4), round(samples[int(.025 * n_boot)], 4),
            round(samples[int(.975 * n_boot) - 1], 4)]


def summarize_pair(data_dir: Path, pred_a: Path, pred_b: Path, subset: str) -> dict[str, Any]:
    rows = load_jsonl(data_dir / f"{subset}.jsonl")
    raw_a = aligned(rows, load_jsonl(pred_a / f"{subset}.jsonl"))
    raw_b = aligned(rows, load_jsonl(pred_b / f"{subset}.jsonl"))
    out_a = [outcome(row, raw) for row, raw in zip(rows, raw_a)]
    out_b = [outcome(row, raw) for row, raw in zip(rows, raw_b)]
    by_id_a = {o["sample_id"]: o for o in out_a}
    by_id_b = {o["sample_id"]: o for o in out_b}

    constrained = [row for row in rows if row["gold"]["constraints"]]
    ids_by_group: dict[str, list[str]] = defaultdict(list)
    type_values: dict[str, list[list[int]]] = defaultdict(lambda: [[], []])
    for row in constrained:
        gid = row["group_id"]
        ids_by_group[gid].append(row["sample_id"])
        for constraint in row["gold"]["constraints"]:
            type_values[constraint["type"]][0].append(int(by_id_a[row["sample_id"]]["faithful_success"]))
            type_values[constraint["type"]][1].append(int(by_id_b[row["sample_id"]]["faithful_success"]))

    group_delta: dict[str, tuple[int, int]] = {}
    group_win_a = group_win_b = group_tie = 0
    for gid, sample_ids in ids_by_group.items():
        # A group contributes its paired E/I records together.
        diff = sum(int(by_id_a[i]["faithful_success"]) - int(by_id_b[i]["faithful_success"])
                   for i in sample_ids)
        group_delta[gid] = (diff, len(sample_ids))
        if diff > 0:
            group_win_a += 1
        elif diff < 0:
            group_win_b += 1
        else:
            group_tie += 1

    item_a_wins = item_b_wins = item_ties = 0
    for row in constrained:
        a = int(by_id_a[row["sample_id"]]["faithful_success"])
        b = int(by_id_b[row["sample_id"]]["faithful_success"])
        if a > b:
            item_a_wins += 1
        elif b > a:
            item_b_wins += 1
        else:
            item_ties += 1

    def faithful(rows_out: list[dict[str, Any]], variant: str | None = None) -> float:
        subset_out = [o for o in rows_out if o["variant"] != "none" and
                      (variant is None or o["variant"] == variant)]
        return sum(bool(o["faithful_success"]) for o in subset_out) / max(len(subset_out), 1)

    raw_score_a = score(rows, [None] * len(rows), raw_a)
    raw_score_b = score(rows, [None] * len(rows), raw_b)
    group_ci = group_bootstrap_delta(group_delta)
    return {
        "subset": subset,
        "records": len(rows),
        "constrained_records": len(constrained),
        "constrained_groups": len(ids_by_group),
        "paired_seed42_seed43": {
            "seed42_faithful": round(faithful(out_a), 4),
            "seed43_faithful": round(faithful(out_b), 4),
            "difference_seed42_minus_seed43": group_ci[0],
            "paired_group_bootstrap_95ci_conditional_on_these_runs": group_ci[1:],
            "groups_seed42_better": group_win_a,
            "groups_seed43_better": group_win_b,
            "groups_tied": group_tie,
            "records_seed42_only_success": item_a_wins,
            "records_seed43_only_success": item_b_wins,
            "records_tied": item_ties,
        },
        "by_variant_faithful": {
            variant: {
                "seed42": round(faithful(out_a, variant), 4),
                "seed43": round(faithful(out_b, variant), 4),
            }
            for variant in ("explicit", "implicit")
        },
        "by_gold_constraint_type_record_faithful_descriptive": {
            ctype: {
                "seed42": round(sum(values[0]) / max(len(values[0]), 1), 4),
                "seed43": round(sum(values[1]) / max(len(values[1]), 1), 4),
                "constraint_instances": len(values[0]),
            }
            for ctype, values in sorted(type_values.items())
        },
        "field_diagnostics_seed42": {
            "state_accuracy": raw_score_a["state_accuracy"],
            "strict_f1": raw_score_a["constraint_micro"]["f1"],
            "core_f1": raw_score_a["constraint_core_micro"]["f1"],
            "record_exact_without_evidence": raw_score_a["record_exact_match"],
        },
        "field_diagnostics_seed43": {
            "state_accuracy": raw_score_b["state_accuracy"],
            "strict_f1": raw_score_b["constraint_micro"]["f1"],
            "core_f1": raw_score_b["constraint_core_micro"]["f1"],
            "record_exact_without_evidence": raw_score_b["record_exact_match"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/processed_v5")
    parser.add_argument("--seed42", type=Path,
                        default=ROOT / "outputs/e1/Qwen3-1.7B-v5-seed42/trained_predictions")
    parser.add_argument("--seed43", type=Path,
                        default=ROOT / "outputs/e1/Qwen3-1.7B-v5-seed43/trained_predictions")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "outputs/v5_analysis/seed_disagreement_1.7b_42_vs_43.json")
    args = parser.parse_args()
    report = {
        "purpose": "paired descriptive comparison; not a population-level training-seed confidence interval",
        "subsets": {},
    }
    for subset in eval_subsets(args.data):
        report["subsets"][subset] = summarize_pair(args.data, args.seed42, args.seed43, subset)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["subsets"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
