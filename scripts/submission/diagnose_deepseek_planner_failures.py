"""Offline diagnostic of cached consumer errors; no model calls or plan repair."""
import argparse
from collections import Counter, defaultdict
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--replay", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError("Existing diagnostic preserved")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    sys.path.insert(0, str(a.root / "src"))
    sys.path.insert(0, str(a.root / "scripts/submission"))
    import deepseek_planner as original
    from trust_env import check, default_plan, execute, normalize_constraint, violated
    jobs, hashes = original.panel(a.root)
    cache_root = a.root / "outputs/submission/deepseek_planner_v5"
    config = json.loads((cache_root / "config.json").read_text())
    if hashes != config["input_sha256"] or {j["id"]: j["request_hash"] for j in jobs} != config["requests"]:
        raise ValueError("Frozen input/request identity changed")
    rows = original.load(a.replay / "outcomes.jsonl")
    index = {r["id"]: r for r in rows}
    if len(index) != len(rows) or set(index) != {j["id"] for j in jobs}:
        raise ValueError("Incomplete or duplicate replay cohort")
    totals = defaultdict(Counter)
    types = defaultdict(Counter)
    examples = {}
    for job in jobs:
        r, scored = job["row"], index[job["id"]]
        if r["variant"] == "none":
            continue
        key = job["split"] + ":" + job["compiler"]
        t = totals[key]
        t["n"] += 1
        actions, result = scored["shared_actions"], scored["api"]
        compiled = job["parsed"]["constraints"] if job["parsed"] is not None else []
        norms = [normalize_constraint(c, r["task"]) for c in compiled]
        unusable = sum(n is None for n in norms)
        t["records_with_unusable_supplied_constraint"] += unusable > 0
        if not result["valid"]:
            category = "invalid_plan"
        else:
            trace = execute(r["task"], actions)
            supplied_violations = [n["type"] for n in norms if n is not None and violated(n, trace)]
            checked = check(r["task"], actions, r["gold"]["constraints"])
            if bool(checked["safe_success"]) != result["safe"]:
                raise ValueError("Replay safety score disagrees with checker")
            t["valid_plan"] += 1
            t["default_plan"] += actions == default_plan(r["task"])
            t["valid_plan_violates_supplied_constraints"] += bool(supplied_violations)
            for ctype in {n["type"] for n in norms if n is not None}:
                types[key][ctype + "_valid_plan_with_supplied_type"] += 1
            for ctype in set(supplied_violations):
                types[key][ctype + "_violating_supplied_type"] += 1
            if result["faithful"]:
                category = "faithful"
            elif not result["safe"]:
                category = ("unsafe_violates_supplied_constraint" if supplied_violations else
                            "unsafe_without_detected_supplied_violation")
            else:
                category = "safe_nonminimal"
            if category != "faithful" and (key, category) not in examples:
                examples[key, category] = {"id": job["id"], "category": category,
                    "supplied_constraints": compiled, "actions": actions,
                    "cost": trace["cost"], "minutes": trace["minutes"],
                    "supplied_violated_types": supplied_violations,
                    "gold_violated_types": [r["gold"]["constraints"][i]["type"] for i in checked["violations"]]}
        t[category] += 1
    categories = ("faithful", "invalid_plan", "unsafe_violates_supplied_constraint",
                  "unsafe_without_detected_supplied_violation", "safe_nonminimal")
    for key, t in totals.items():
        if sum(t[c] for c in categories) != t["n"]:
            raise ValueError("Failure categories do not partition the cohort")
    report = {"revision": "20261125-consumer-failure-diagnostic-v1",
              "constrained_cells": {k: dict(v) for k, v in sorted(totals.items())},
              "supplied_type_violations": {k: dict(v) for k, v in sorted(types.items())},
              "first_example_per_cell_category": list(examples.values()),
              "provenance": {"script_sha256": original.file_hash(Path(__file__)),
                  "replay_outcomes_sha256": original.file_hash(a.replay / "outcomes.jsonl"),
                  "original_config_sha256": original.file_hash(cache_root / "config.json"),
                  "checker_sha256": original.file_hash(a.root / "src/trust_env.py")},
              "limits": "Descriptive post-hoc diagnostic on the fixed zero-shot, thinking-disabled, 384-token API consumer. Supplied-type violation denominators include only valid plans with that usable supplied type. Types overlap. Unusable/missing compiler constraints are not inferred correct; no human semantic validation. No new API requests or training."}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps({"saved": str(a.out), "constrained_cells": report["constrained_cells"]}), flush=True)


if __name__ == "__main__":
    main()
