"""Audit planner-teacher labels on train/dev before training a new architecture.

The candidate domain is stage choices, finish permutations, and canonical
insertions of ordered subsets of optional tools. It is independent of the
constraint record but is NOT the space of arbitrary DAGs. This diagnostic
reuses frozen execution semantics; it is not natural-language validation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def enumerate_plans(task: dict, env) -> list[tuple[list[str], dict, int]]:
    """Enumerate a constraint-independent canonical candidate domain."""
    result = {}
    extras = sorted(task["optional"])
    for assignment in itertools.product(*(s["alternatives"] for s in task["stages"])):
        for finish in itertools.permutations(task["finish"]):
            base = list(assignment) + list(finish)
            for n in range(len(extras) + 1):
                for optional in itertools.permutations(extras, n):
                    candidate = env.canonical_insert(task, base, list(optional))
                    key = tuple(candidate)
                    if key not in result:
                        trace = env.execute(task, candidate)
                        if trace["completed"]:
                            result[key] = (candidate, trace, env.plan_change_count(task, candidate))
    return list(result.values())


def optimal_plans(task: dict, constraints: list, candidates: list, env) -> list:
    norms = [env.normalize_constraint(c, task) for c in constraints]
    if any(n is None for n in norms):
        raise ValueError("Unusable constraint must not be interpreted as empty")
    feasible = [x for x in candidates if not any(env.violated(n, x[1]) for n in norms)]
    if not feasible:
        return []
    minimum = min(x[2] for x in feasible)
    return sorted((x for x in feasible if x[2] == minimum),
                  key=lambda x: (x[1]["cost"], x[1]["minutes"], tuple(x[0])))


def slots(task: dict, candidate: list[str]) -> dict:
    out = {f"stage:{i}": next(r for r in candidate if r in s["alternatives"])
           for i, s in enumerate(task["stages"])}
    out["finish"] = tuple(r for r in candidate if r in task["finish"])
    out.update({f"optional:{r}": r in candidate for r in sorted(task["optional"])})
    return out


def duplicate_probe(task: dict, constraint: dict, candidates: list, env) -> dict:
    """A duplicate constraint can make every leave-one-out effect vanish."""
    base = optimal_plans(task, [], candidates, env)[0][0]
    one = optimal_plans(task, [constraint], candidates, env)[0][0]
    two = optimal_plans(task, [constraint, constraint], candidates, env)[0][0]
    return {"requires_edit": slots(task, one) != slots(task, base),
            "duplicate_preserves_plan": one == two,
            "both_leave_one_out_differences_empty": one == two}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--train-groups", type=int, default=256)
    p.add_argument("--dev-groups", type=int, default=300)
    args = p.parse_args()
    root = args.project_root.resolve()
    sys.path.insert(0, str(root / "src"))
    import trust_env as env
    from run_v6_relay import check_release

    started = time.monotonic()
    seal = check_release(root)
    report = {"utc": datetime.now(timezone.utc).isoformat(),
              "source_sha256": sha(Path(__file__)), "release_files_verified": len(seal),
              "scope": "development diagnostic; train/dev only; no test selection",
              "candidate_domain": "stage assignments x finish permutations x canonical optional ordered subsets",
              "splits": {}}
    args.out.mkdir(parents=True, exist_ok=True)
    for split, limit in (("train", args.train_groups), ("dev", args.dev_groups)):
        path = root / "data/processed_v6" / f"{split}.jsonl"
        digest = sha(path)
        with path.open(encoding="utf-8") as f:
            rows = [r for line in f if (r := json.loads(line))["variant"] == "explicit"]
        rows.sort(key=lambda r: hashlib.sha256(r["group_id"].encode()).hexdigest())
        rows = rows[:limit]
        counts, totals = Counter(), Counter()
        examples = []
        with (args.out / f"{split}_lattice.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                task, cs = row["task"], row["gold"]["constraints"]
                candidates = enumerate_plans(task, env)
                totals["candidate_plans"] += len(candidates)
                counts["groups"] += 1
                lattice = {}
                for mask in range(1 << len(cs)):
                    subset = [c for i, c in enumerate(cs) if mask & (1 << i)]
                    opts = optimal_plans(task, subset, candidates, env)
                    original, info = env.plan(task, subset)
                    counts["subset_labels"] += 1
                    if not opts:
                        counts["unsolvable_subset"] += 1
                        raise ValueError("Originally feasible task has infeasible subset")
                    canonical = opts[0][0]
                    counts["multiple_min_edit_plans"] += len(opts) > 1
                    counts["solver_min_edit_disagreement"] += info["changes"] != opts[0][2]
                    counts["solver_not_in_canonical_domain"] += tuple(original) not in {tuple(x[0]) for x in candidates}
                    counts["representative_plan_changed"] += original != canonical
                    lattice[str(mask)] = {"constraints": subset, "plan": canonical,
                                          "min_changes": opts[0][2], "optimal_count": len(opts),
                                          "optimal_plans": [x[0] for x in opts]}
                full = str((1 << len(cs)) - 1)
                default_slots = slots(task, env.default_plan(task))
                full_slots = slots(task, lattice[full]["plan"])
                edits = {s for s in full_slots if full_slots[s] != default_slots[s]}
                attribution = {s: [] for s in edits}
                for i in range(len(cs)):
                    reduced = slots(task, lattice[str(int(full) ^ (1 << i))]["plan"])
                    for s in edits:
                        if reduced[s] != full_slots[s]:
                            attribution[s].append(i)
                counts["edited_slots"] += len(edits)
                counts["unattributed_edited_slots"] += sum(not v for v in attribution.values())
                counts["groups_with_multiple_full_optima"] += lattice[full]["optimal_count"] > 1
                # Test redundancy outside the generator's irredundancy filter.
                for c in cs:
                    probe = duplicate_probe(task, c, candidates, env)
                    if probe["requires_edit"]:
                        counts["duplicate_controls_requiring_edit"] += 1
                        counts["duplicate_controls_empty_loo"] += probe["both_leave_one_out_differences_empty"]
                if len(examples) < 3 and lattice[full]["optimal_count"] > 1:
                    examples.append({"sample_id": row["sample_id"], "types": [c["type"] for c in cs],
                                     "optimal_count": lattice[full]["optimal_count"],
                                     "first_plans": lattice[full]["optimal_plans"][:2]})
                stream.write(json.dumps({"sample_id": row["sample_id"], "group_id": row["group_id"],
                                         "task": task, "constraints": cs, "lattice": lattice,
                                         "representative_slot_loo": attribution}, ensure_ascii=False) + "\n")
        assert sha(path) == digest, "Source data changed during audit"
        target = args.out / f"{split}_lattice.jsonl"
        report["splits"][split] = {"data_sha256": digest, "selection": "sha256(group_id) ascending",
                                   "counts": dict(counts), "totals": dict(totals),
                                   "tie_examples": examples, "lattice_sha256": sha(target)}
        print(json.dumps({"split": split, "counts": dict(counts)}, ensure_ascii=False), flush=True)
    report["elapsed_seconds"] = time.monotonic() - started
    report["status"] = "completed"
    (args.out / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "seconds": report["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
