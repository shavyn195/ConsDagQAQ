"""Complete-cohort consumer contrasts and planner-only usage accounting.

No model calls. Intervals resample paired E/I task groups and condition on the
fixed compiler weights and cached API responses, not the training-seed population.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_coverage(config, records, responses):
    expected = config["requests"]
    ids = [r["id"] for r in records]
    hashes = [r["request_hash"] for r in responses]
    if len(set(ids)) != len(ids) or set(ids) != set(expected):
        raise ValueError("Incomplete or duplicated outcome cohort; no aggregate")
    if len(set(hashes)) != len(hashes) or set(hashes) != set(expected.values()):
        raise ValueError("Incomplete or duplicated response cache; no aggregate")
    for row in records:
        if row["request_hash"] != expected[row["id"]]:
            raise ValueError("Outcome request hash differs")
        for consumer in ("api", "symbolic"):
            if any(type(row[consumer][k]) is not bool for k in ("valid", "safe", "faithful", "deviates")):
                raise ValueError("Outcome is not a Boolean observation")
    if any(r["model"] != config["params"]["model"] for r in responses):
        raise ValueError("Returned model differs")


def paired(groups, left, right, reps=10000, seed=20261125):
    """left-minus-right percentage points; keep all siblings in each draw."""
    if not len(groups) or len(groups) != len(left) or len(left) != len(right):
        raise ValueError("Paired cohort length differs or is empty")
    indices = defaultdict(list)
    for i, group in enumerate(groups):
        indices[group].append(i)
    delta = np.asarray(left, dtype=float) - np.asarray(right, dtype=float)
    sums = np.array([delta[i].sum() for i in indices.values()])
    sizes = np.array([len(i) for i in indices.values()])
    rng = np.random.default_rng(seed)
    boot = []
    for start in range(0, reps, 256):
        draw = rng.integers(0, len(sizes), (min(256, reps - start), len(sizes)))
        boot.extend(sums[draw].sum(axis=1) / sizes[draw].sum(axis=1))
    return {"n": len(groups), "groups": len(indices), "difference_pp": float(delta.mean() * 100),
            "ci95_pp": (np.quantile(boot, [.025, .975]) * 100).tolist(),
            "positive_records": int((delta > 0).sum()), "negative_records": int((delta < 0).sum()),
            "bootstrap_replicates": reps}


def usage(rows):
    result = {"requests": len(rows)}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        values = [(r.get("usage") or {}).get(key) for r in rows]
        missing = sum(not isinstance(x, int) or isinstance(x, bool) for x in values)
        result[key] = {"total": sum(values) if not missing else None, "missing": missing}
    latencies = [r["latency_s"] for r in rows]
    result["request_latency_s"] = {"sum": sum(latencies), "median": float(np.median(latencies)),
                                   "p95": float(np.quantile(latencies, .95))}
    return result


def summarise(records, responses, reps=10000):
    table, contrasts = {}, {}
    splits = sorted({r["split"] for r in records})
    compilers = sorted({r["compiler"] for r in records})
    if compilers != ["1.7B-seed42", "DeepSeek-ten-shot"]:
        raise ValueError("Unexpected compiler arms")
    cache = {r["request_hash"]: r for r in responses}
    for split in splits:
        table[split], contrasts[split] = {}, {}
        arms = {}
        for compiler in compilers:
            rows = [r for r in records if r["split"] == split and r["compiler"] == compiler]
            constrained = sorted((r for r in rows if r["variant"] != "none"), key=lambda r: r["sample_id"])
            none = [r for r in rows if r["variant"] == "none"]
            arms[compiler] = constrained
            cells = {}
            for consumer in ("api", "symbolic"):
                rate = lambda cohort, key: sum(r[consumer][key] for r in cohort) / len(cohort)
                cells[consumer] = {"n": len(rows), "n_constrained": len(constrained), "n_none": len(none),
                                   "faithful_constrained": rate(constrained, "faithful"),
                                   "safe_constrained": rate(constrained, "safe"),
                                   "none_faithful": rate(none, "faithful"),
                                   "none_edit_rate": rate(none, "deviates"),
                                   "plan_valid_rate": rate(rows, "valid"),
                                   "compiler_malformed_rate": sum(r["compiler_malformed"] for r in rows) / len(rows),
                                   "valid_input_faithful_constrained": sum(r[consumer]["faithful"] and not r["compiler_malformed"] for r in constrained) / len(constrained),
                                   "valid_input_none_faithful": sum(r[consumer]["faithful"] and not r["compiler_malformed"] for r in none) / len(none)}
            cells["api_logical_usage"] = usage([cache[r["request_hash"]] for r in rows])
            table[split][compiler] = cells
            contrasts[split][compiler + ":api-minus-symbolic"] = paired(
                [r["group_id"] for r in constrained], [r["api"]["faithful"] for r in constrained],
                [r["symbolic"]["faithful"] for r in constrained], reps)
        weak, strong = (arms[c] for c in compilers)
        if [(r["sample_id"], r["group_id"], r["variant"]) for r in weak] != [
                (r["sample_id"], r["group_id"], r["variant"]) for r in strong]:
            raise ValueError("Compiler arms are not paired")
        for consumer in ("api", "symbolic"):
            contrasts[split][consumer + ":strong-minus-weak-compiler"] = paired(
                [r["group_id"] for r in weak], [r[consumer]["faithful"] for r in strong],
                [r[consumer]["faithful"] for r in weak], reps)
        contrasts[split]["consumer-by-compiler-interaction"] = paired(
            [r["group_id"] for r in weak],
            [int(s["api"]["faithful"]) - int(w["api"]["faithful"]) for w, s in zip(weak, strong)],
            [int(s["symbolic"]["faithful"]) - int(w["symbolic"]["faithful"]) for w, s in zip(weak, strong)], reps)
    return {"table": table, "paired_contrasts": contrasts,
            "actual_unique_api_usage": usage(responses),
            "logical_api_usage": usage([cache[r["request_hash"]] for r in records]),
            "interpretation": "Pointwise group-bootstrap intervals, conditional on fixed weights/cached responses; not training-seed CIs or multiplicity-adjusted hypothesis tests. N edit rate is not compiler false-alarm rate.",
            "cost_limit": "Planner stage only. Unique usage is actual completed cached requests; retries with no returned usage are not bill-audited. Logical usage is a no-dedup counterfactual. Latency sums include concurrency/retries and are not wall time. No price or speed advantage inferred."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "outputs/submission/deepseek_planner_v5")
    p.add_argument("--after-pid", type=int)
    a = p.parse_args()
    if a.after_pid:
        proc = Path(f"/proc/{a.after_pid}")
        if proc.exists():
            args = (proc / "cmdline").read_bytes().split(bytes([0]))
            if not any(x.endswith(b"/deepseek_planner.py") for x in args):
                raise ValueError("Wait PID is not the intended planner worker")
            initial = (proc / "stat").read_text().rsplit(")", 1)[1].split()[19]
            print(json.dumps({"event": "waiting_for_planner", "pid": a.after_pid}), flush=True)
            while proc.exists():
                try:
                    fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
                except FileNotFoundError:
                    break
                if fields[19] != initial or fields[0] == "Z":
                    break
                time.sleep(30)
    paths = {n: a.out / n for n in ("config.json", "outcomes.jsonl", "responses.jsonl")}
    config = json.loads(paths["config.json"].read_text(encoding="utf-8"))
    records, responses = load(paths["outcomes.jsonl"]), load(paths["responses.jsonl"])
    check_coverage(config, records, responses)
    result = summarise(records, responses)
    result["provenance"] = {"source_sha256": sha(Path(__file__)), "inputs_sha256": {n: sha(v) for n, v in paths.items()},
                            "data_version": config["data_version"], "planner_params": config["params"]}
    dest = a.out / "paired_analysis.json"
    with dest.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({"event": "complete", "records": len(records), "result": str(dest)}), flush=True)


if __name__ == "__main__":
    main()
