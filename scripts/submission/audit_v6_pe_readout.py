"""Recount a completed v6 PE arm against a saved frozen-analysis snapshot.

Runs on server CPU with the frozen project supplied explicitly. No inference,
gold-label changes, or writes to the frozen project are performed. Integer
record counts provide a second aggregation path to the frozen main report;
execution predicates themselves remain the same registered predicates.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_equal(actual: object, expected: object, label: str) -> None:
    if actual != expected:
        raise ValueError(f"Recount mismatch for {label}: {actual!r} != {expected!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--model", choices=("deepseek-v4-pro-0813", "qwen-max"), required=True)
    parser.add_argument("--style", choices=("few", "zero"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    sys.path.insert(0, str(root / "src"))
    from analyze_v6_main import current_data_hashes, verified_pe_run
    from eval_exec_v6 import aligned_raw, evaluate_v6, n_error_components, n_error_subtypes
    from run_e1 import constraint_key, eval_subsets, load_jsonl, strict_parse
    from run_v6_relay import check_release

    seal = check_release(root)
    data = root / "data/processed_v6"
    subsets = eval_subsets(data)
    label = f"{args.model}-{args.style}"
    cache = root / "outputs/e1_v6_side" / label
    require_equal(verified_pe_run(cache, data, subsets, args.model), (True, "complete"), "PE integrity")
    analysis = json.loads(args.analysis.read_text(encoding="utf-8"))
    require_equal(analysis["data_sha256"], current_data_hashes(data, subsets), "analysis data")
    reference = analysis["arms"][f"PE-{label}"]
    require_equal(reference["observed_runs"], [label], "analysis accepted arm")
    report = {
        "utc": datetime.now(timezone.utc).isoformat(), "arm": label,
        "source_sha256": sha256(Path(__file__)), "release_files_verified": len(seal),
        "analysis_sha256": sha256(args.analysis),
        "completion_sha256": sha256(cache / "completion.json"),
        "interpretation": "independent integer aggregation; shared frozen execution predicates",
        "splits": {},
    }
    for subset in subsets:
        rows = load_jsonl(data / f"{subset}.jsonl")
        predictions = load_jsonl(cache / f"{subset}.jsonl")
        raw = aligned_raw(rows, predictions)
        execution, outcomes = evaluate_v6(rows, raw)
        counts = {variant: Counter() for variant in ("explicit", "implicit", "none")}
        n_alarm_cases = []
        for row, output, outcome in zip(rows, raw, outcomes):
            parsed = strict_parse(output)
            exact = bool(
                parsed is not None and parsed["query_state"] == row["gold"]["query_state"]
                and Counter(constraint_key(c) for c in parsed["constraints"])
                == Counter(constraint_key(c) for c in row["gold"]["constraints"])
            )
            faithful = bool(outcome["faithful_success"])
            stat = counts[row["variant"]]
            stat.update(records=1, faithful=int(faithful), strict_record_exact=int(exact),
                        faithful_but_record_wrong=int(faithful and not exact),
                        exact_but_not_faithful=int(exact and not faithful))
            if row["variant"] == "none" and (
                parsed is None or parsed["constraints"] or parsed["query_state"] != "none"
            ):
                n_alarm_cases.append({
                    "sample_id": row["sample_id"], "near_miss_subtypes": row.get("near_miss_subtypes", []),
                    "query": row["query"], "prediction": parsed,
                })
        expected = reference["splits"][subset]
        for metric in ("safe_success", "faithful_success", "safe_success_constrained", "faithful_success_constrained"):
            require_equal(execution[metric], expected[metric], f"{subset}:{metric}")
        for variant, stat in counts.items():
            require_equal(stat["strict_record_exact"] / stat["records"],
                          expected["record_exact_match_by_variant"][variant], f"{subset}:{variant}:record")
            require_equal(round(stat["faithful"] / stat["records"], 4),
                          expected["faithful_success_by_variant"][variant], f"{subset}:{variant}:faithful")
        require_equal(n_error_components(rows, raw), expected["n_errors"], f"{subset}:N counts")
        require_equal(n_error_subtypes(rows, raw), expected["n_errors_by_subtype"], f"{subset}:N subtypes")
        require_equal(len(n_alarm_cases), expected["n_errors"]["any_contract_alarm"], f"{subset}:N case count")
        constrained = counts["explicit"] + counts["implicit"]
        report["splits"][subset] = {
            "by_variant": {key: dict(value) for key, value in counts.items()},
            "constrained": dict(constrained),
            "constrained_faithful_rate": constrained["faithful"] / constrained["records"],
            "constrained_strict_record_rate": constrained["strict_record_exact"] / constrained["records"],
            "n_alarm_cases": n_alarm_cases,
            "subtype_note": "N subtype sets overlap; subtype counts must not be added",
        }
    report["status"] = "all_integer_recounts_match_frozen_analysis"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "out": str(args.out), "splits": len(subsets)}))


if __name__ == "__main__":
    main()
