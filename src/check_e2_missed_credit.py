"""Check within-query reward differences on scripted frozen-v4 training plans."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean

from trust_env import check, plan


def centered(values):
    average = mean(values)
    return [x - average for x in values]


def diagnose(path):
    counts = Counter()
    types = Counter()
    seen = set()
    for line in path.open(encoding="utf8"):
        row = json.loads(line)
        if row["variant"] != "explicit":
            continue
        task, gold = row["task"], row["gold"]["constraints"]
        group = row["group_id"]
        if group in seen:
            raise ValueError(group)
        seen.add(group)
        for i, omitted in enumerate(gold):
            remaining = gold[:i] + gold[i+1:]
            relaxed, _ = plan(task, remaining)
            # Both candidate traces are feasible under the SAME predicted set.
            traces = [row["witness_plan"], relaxed]
            checks = [check(task, trace, gold) for trace in traces]
            if not all(check(task, trace, remaining)["safe_success"] for trace in traces):
                raise ValueError(f"{group}/{i}: invalid control")
            if [x["violations"] for x in checks] != [[], [i]]:
                raise ValueError(f"{group}/{i}: traces do not isolate the omission")
            fixed = centered([-1, -1])
            contingent = centered([-int(i in x["violations"]) for x in checks])
            counts["pairs"] += 1
            counts["fixed_zero_signal"] += fixed == [0, 0]
            counts["contingent_correct_ranking"] += contingent == [0.5, -0.5]
            types[omitted["type"]] += 1
    if not seen or len(types) != 5 or not counts["pairs"] == counts["fixed_zero_signal"] == counts["contingent_correct_ranking"]:
        raise AssertionError(counts)
    return {"groups":len(seen), "counts":counts, "types":types,
            "train_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "scope":"single synthetic omission; two scripted completed traces; unit penalty; within-group centering only"}


if __name__ == "__main__":
    print(json.dumps(diagnose(Path(__file__).resolve().parents[1]/"data/processed_v4/train.jsonl"), indent=2))
