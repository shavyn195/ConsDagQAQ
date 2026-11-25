"""Audit reference mismatches that collapse to identical frozen predicates.

This conservative sufficient-equivalence diagnostic does not replace any
registered metric. In this world, tool_auth and order call the same precedence
predicate. Equality here describes the frozen checker, not natural language.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


def predicate_signature(norm: dict) -> tuple:
    """Mirror only the fields read by the registered violated() function."""
    ctype = norm["type"]
    if ctype in ("tool_auth", "order"):
        return ("precedence", norm["first"], norm["second"])
    if ctype == "budget":
        return ("budget", norm["limit"])
    if ctype == "deadline":
        return ("deadline_minutes", norm["minutes"])
    if ctype == "privacy":
        return ("privacy", tuple(sorted(norm["classes"])))
    raise ValueError(f"Unknown normalized predicate: {ctype}")


def predicate_set(constraints: list[dict], task: dict, normalize) -> frozenset | None:
    norms = [normalize(item, task) for item in constraints]
    if any(norm is None for norm in norms):
        return None
    return frozenset(predicate_signature(norm) for norm in norms)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--diagnostic", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    root = args.project_root.resolve()
    sys.path.insert(0, str(root / "src"))
    from analyze_v6_main import current_data_hashes, file_sha256
    from eval_exec_v6 import aligned_raw, record_outcome_v6
    from run_e1 import core_key, constraint_key, eval_subsets, load_jsonl, strict_parse
    from run_v6_relay import check_release
    from trust_env import normalize_constraint

    seal = check_release(root)
    diagnostic = json.loads(args.diagnostic.read_text(encoding="utf-8"))
    data = root / "data/processed_v6"
    subsets = eval_subsets(data)
    if diagnostic["data_sha256"] != current_data_hashes(data, subsets):
        raise ValueError("Diagnostic data hash mismatch")
    paths = {"deepseek-few": root / "outputs/e1_v6_side/deepseek-v4-pro-0813-few"}
    paths.update({f"1.7B-seed{s}": root / f"outputs/e1_v6/Qwen3-1.7B-v6-seed{s}/trained_predictions"
                  for s in (42, 43, 44)})
    report = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "analysis_type": "post-hoc checker predicate equivalence audit",
        "source_sha256": file_sha256(Path(__file__)),
        "input_diagnostic_sha256": file_sha256(args.diagnostic),
        "release_files_verified": len(seal), "splits": {},
        "definition": "set equality of normalized predicates; order and tool_auth share precedence; repeated identical predicates are idempotent",
        "limitations": [
            "Identical predicates are a sufficient but incomplete equivalence criterion within this synthetic checker.",
            "No claim of human semantic equivalence or equivalence under another consumer.",
            "No label, source, prediction, scoring rule, or preregistered H1-H4 decision is changed.",
            "Predicate-equivalent records can still violate the typed output contract.",
        ],
    }
    for subset in subsets:
        rows = load_jsonl(data / f"{subset}.jsonl")
        split = {}
        for label, path in paths.items():
            prediction = path / f"{subset}.jsonl"
            reference = diagnostic["splits"][subset][label]
            if file_sha256(prediction) != reference["prediction_sha256"]:
                raise ValueError(f"Prediction changed: {label}/{subset}")
            raw = aligned_raw(rows, load_jsonl(prediction))
            stat = Counter()
            equivalent_ids = []
            mismatch_transitions = Counter()
            for row, text in zip(rows, raw):
                if row["variant"] == "none":
                    continue
                stat["constrained_n"] += 1
                parsed = strict_parse(text)
                if parsed is None:
                    stat["parse_failure"] += 1
                    continue
                gold, pred = row["gold"]["constraints"], parsed["constraints"]
                core_same = Counter(map(core_key, gold)) == Counter(map(core_key, pred))
                exact = (parsed["query_state"] == row["gold"]["query_state"]
                         and Counter(map(constraint_key, gold)) == Counter(map(constraint_key, pred)))
                gold_norm = predicate_set(gold, row["task"], normalize_constraint)
                pred_norm = predicate_set(pred, row["task"], normalize_constraint)
                if gold_norm is None:
                    raise ValueError("Unusable gold predicate")
                same = pred_norm is not None and gold_norm == pred_norm
                stat["predicate_set_equal"] += int(same)
                stat["strict_reference_exact"] += int(exact)
                stat["typed_core_mismatch"] += int(not core_same)
                if not core_same and same:
                    outcome = record_outcome_v6(row, text)
                    stat["core_mismatch_but_predicate_equal"] += 1
                    stat["core_mismatch_predicate_equal_and_faithful"] += int(outcome["faithful_success"])
                    equivalent_ids.append(row["sample_id"])
                    # Pair by exact normalized predicate, preserving multiplicity for type diagnostics.
                    available = list(range(len(pred)))
                    for g in gold:
                        key = predicate_signature(normalize_constraint(g, row["task"]))
                        pi = next((i for i in available if predicate_signature(normalize_constraint(pred[i], row["task"])) == key), None)
                        if pi is not None:
                            available.remove(pi)
                            if g["type"] != pred[pi]["type"]:
                                mismatch_transitions[f"{g['type']}->{pred[pi]['type']}"] += 1
                if same and not exact:
                    stat["strict_mismatch_but_predicate_equal"] += 1
            if (stat["strict_reference_exact"] != reference["strict_reference_exact"]
                    or stat["typed_core_mismatch"] != reference["categories"].get("core_reference_mismatch", 0)
                    or stat["constrained_n"] != reference["constrained_n"]):
                raise ValueError(f"Recount differs from verified diagnostic: {label}/{subset}")
            split[label] = {"counts": dict(stat), "equivalent_type_transitions": dict(mismatch_transitions),
                            "core_mismatch_but_predicate_equal_ids": equivalent_ids,
                            "predicate_set_equal_rate": stat["predicate_set_equal"] / stat["constrained_n"]}
        report["splits"][subset] = split
    report["status"] = "all_20_arm_split_recounts_match"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "out": str(args.out)}))


if __name__ == "__main__":
    main()
