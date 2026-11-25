"""Post-hoc field and behavior diagnostics for verified v6 compiler outputs.

No model calls or metric changes. This separates mismatched consumed fields
from mismatched unconsumed fields, without assuming every reference mismatch
is a semantic error. It is not an oracle repair or an additional H2 test.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys


def category(item: dict, *, valid: bool) -> str:
    """Partition records by parse validity and exact consumed/reference keys."""
    if not valid:
        return "parse_failure"
    if item["core_missing"] or item["core_extra"]:
        return "core_reference_mismatch"
    if not item["strict_record_exact"]:
        return "unconsumed_fields_or_query_state_mismatch"
    return "strict_reference_exact"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", required=True, type=Path)
    p.add_argument("--diagnostic-helper", required=True, type=Path)
    p.add_argument("--analysis", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    root = args.project_root.resolve()
    sys.path.insert(0, str(root / "src"))
    from run_v6_relay import check_release
    from analyze_v6_main import current_data_hashes, file_sha256, verified_pe_run, verified_science_run
    from eval_exec_v6 import aligned_raw, record_outcome_v6
    from run_e1 import eval_subsets, load_jsonl, strict_parse

    spec = importlib.util.spec_from_file_location("v6_diagnostic_helper", args.diagnostic_helper)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    seal = check_release(root)
    data = root / "data/processed_v6"
    subsets = eval_subsets(data)
    analysis = json.loads(args.analysis.read_text(encoding="utf-8"))
    if current_data_hashes(data, subsets) != analysis["data_sha256"]:
        raise ValueError("Analysis data fingerprint mismatch")
    paths = {"deepseek-few": root / "outputs/e1_v6_side/deepseek-v4-pro-0813-few"}
    for seed in (42, 43, 44):
        run = root / f"outputs/e1_v6/Qwen3-1.7B-v6-seed{seed}"
        valid, reason = verified_science_run(run, data, subsets, seed, "models/Qwen3-1.7B")
        if not valid:
            raise ValueError(f"Unverified seed {seed}: {reason}")
        paths[f"1.7B-seed{seed}"] = run / "trained_predictions"
    valid, reason = verified_pe_run(paths["deepseek-few"], data, subsets, "deepseek-v4-pro-0813")
    if not valid:
        raise ValueError(f"Unverified PE cache: {reason}")
    result = {
        "utc": datetime.now(timezone.utc).isoformat(), "analysis_type": "post-hoc descriptive",
        "release_files_verified": len(seal), "analysis_sha256": file_sha256(args.analysis),
        "source_sha256": file_sha256(Path(__file__)),
        "helper_sha256": file_sha256(args.diagnostic_helper),
        "data_sha256": analysis["data_sha256"], "splits": {},
        "limitations": [
            "Core means exact type+params keys, not semantic equivalence.",
            "Strict includes query_state/type/state/severity/scope/params; excludes evidence/confidence/description.",
            "Field counts are conditional on core-matched constraints and can overlap.",
            "Mismatch categories partition constrained records, but are not causal interventions.",
            "Shared fixed planner/predicates and synthetic reference labels; no new semantic validation.",
            "Illustrative cases are the first two records per category, not a representative sample.",
        ],
    }
    for subset in subsets:
        rows = load_jsonl(data / f"{subset}.jsonl")
        split = {}
        for label, path in paths.items():
            pred_path = path / f"{subset}.jsonl"
            raw = aligned_raw(rows, load_jsonl(pred_path))
            category_counts = Counter()
            faithful_categories = Counter()
            field_constraints = Counter()
            field_records = Counter()
            type_fields = defaultdict(Counter)
            examples = defaultdict(list)
            exact = 0
            faithful = 0
            matched_core = 0
            core_missing = 0
            core_extra = 0
            top_state_errors = 0
            variant_exact = Counter()
            n_constrained = 0
            for row, text in zip(rows, raw):
                outcome = record_outcome_v6(row, text)
                item = helper.record_diagnostic(row, text, outcome)
                variant_exact[row["variant"]] += int(item["strict_record_exact"])
                if row["variant"] == "none":
                    continue
                n_constrained += 1
                parsed = strict_parse(text)
                key = category(item, valid=parsed is not None)
                category_counts[key] += 1
                faithful_categories[key] += int(item["faithful"])
                faithful += int(item["faithful"])
                exact += int(item["strict_record_exact"])
                matched_core += item["core_matched_constraints"]
                core_missing += item["core_missing"]
                core_extra += item["core_extra"]
                top_state_errors += int(not item["top_state_correct"])
                field_constraints.update(item["field_mismatches_among_core_matches"])
                field_records.update(item["field_mismatches_among_core_matches"].keys())
                for ctype, counts in item["field_mismatches_by_type"].items():
                    type_fields[ctype].update(counts)
                if item["faithful"] and not item["strict_record_exact"] and len(examples[key]) < 2:
                    examples[key].append({"sample_id": row["sample_id"], "query": row["query"],
                                          "gold": row["gold"], "prediction": parsed, "diagnostic": item})
            arm = "PE-deepseek-v4-pro-0813-few" if label == "deepseek-few" else "Qwen3-1.7B-v6-trained"
            reference = analysis["arms"][arm]["splits"][subset]
            if label != "deepseek-few":
                reference = reference["per_run"][(42, 43, 44).index(int(label.rsplit("seed", 1)[1]))]
            if round(faithful / n_constrained, 4) != reference["faithful_success_constrained"]:
                raise ValueError(f"Execution recount disagrees: {label}/{subset}")
            for variant, count in variant_exact.items():
                denominator = sum(row["variant"] == variant for row in rows)
                if count / denominator != reference["record_exact_match_by_variant"][variant]:
                    raise ValueError(f"Strict recount disagrees: {label}/{subset}/{variant}")
            if sum(category_counts.values()) != n_constrained or sum(faithful_categories.values()) != faithful:
                raise ValueError("Categories do not partition the same denominator")
            split[label] = {
                "constrained_n": n_constrained, "faithful": faithful, "strict_reference_exact": exact,
                "categories": dict(category_counts), "faithful_by_category": dict(faithful_categories),
                "core_matched_constraint_n": matched_core,
                "core_unmatched_gold": core_missing, "core_unmatched_predictions": core_extra,
                "top_query_state_error_records": top_state_errors,
                "field_mismatch_constraint_n_on_core_matches": dict(field_constraints),
                "field_mismatch_record_n_on_core_matches": dict(field_records),
                "field_mismatch_types_on_core_matches": {k: dict(v) for k, v in type_fields.items()},
                "prediction_sha256": file_sha256(pred_path), "first_examples": dict(examples),
            }
        result["splits"][subset] = split
    result["status"] = "all_20_arm_split_recounts_match"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": result["status"], "out": str(args.out)}))


if __name__ == "__main__":
    main()
