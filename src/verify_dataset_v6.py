"""Verify v6 files, triplets, hidden witnesses, composition isolation and hashes."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from build_dataset_v6 import SUBSETS
from dataset_v6_spec import HELDOUT_CONSTRAINT_COMBINATION, contains_heldout_pair
from verify_dataset_v5 import verify as verify_v5

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GROUPS = {
    "train": 4000,
    "dev": 300,
    "test_tpl_ho": 350,
    "test_tool_ho": 350,
    "test_struct_ho": 350,
    "test_composition_ho": 350,
}
PRECEDENCE_KEYS = {
    "tool_auth": ("approval_role", "required_role"),
    "order": ("before_role", "after_role"),
}


def load(data_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for subset in SUBSETS:
        path = data_dir / f"{subset}.jsonl"
        if not path.is_file():
            raise FileNotFoundError(f"Missing v6 split: {path}")
        part = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not part or any(row.get("subset") != subset for row in part):
            raise ValueError(f"Empty or mislabeled v6 split file: {path}")
        rows.extend(part)
    return rows


def cross_split_overlaps(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Count exact shared values across splits, allowing E/I/N sharing within a split.

    The generator reserves goals globally; goal/group sharing is intentional only
    inside a task triplet. Include the composition split, which verify_v5 omits.
    """
    values = {field: {subset: set() for subset in SUBSETS}
              for field in ("query", "task_goal", "group_id")}
    for row in rows:
        for field, by_subset in values.items():
            if row["subset"] in by_subset:
                by_subset[row["subset"]].add(row[field])
    return {
        f"{second}_{field}_overlap_with_{first}": len(by_subset[first] & by_subset[second])
        for field, by_subset in values.items()
        for first, second in combinations(SUBSETS, 2)
    }


def independent_replay(task: dict[str, Any], plan: list[str]) -> dict[str, Any]:
    """Replay task completion, cost, duration and privacy flow without trust_env."""
    tools = task["tools"]
    if not isinstance(plan, list) or any(not isinstance(role, str) or role not in tools for role in plan):
        return {"valid": False, "completed": False, "violations": [], "positions": {}}
    if len(plan) != len(set(plan)):
        return {"valid": False, "completed": False, "violations": [], "positions": {}}
    positions = {role: index for index, role in enumerate(plan)}
    previous = -1
    complete = True
    for stage in task["stages"]:
        hits = [positions[role] for role in stage["alternatives"] if role in positions]
        if len(hits) != 1 or hits[0] <= previous:
            complete = False
            break
        previous = hits[0]
    if complete and any(role not in positions or positions[role] <= previous for role in task["finish"]):
        complete = False

    active = False
    acquire_roles = set(task["stages"][0]["alternatives"])
    leaked_classes = []
    cost = minutes = 0
    for role in plan:
        tool = tools[role]
        cost += tool["cost_cny"]
        minutes += tool["duration_min"]
        if active and tool["recipient"] == "external" and task.get("data_class"):
            leaked_classes.append(task["data_class"])
        if role in acquire_roles and task.get("data_class"):
            active = True
        if tool["clears_pii"]:
            active = False
    return {
        "valid": True,
        "completed": complete,
        "positions": positions,
        "cost": cost,
        "minutes": minutes,
        "leaked_classes": leaked_classes,
    }


def independently_violates(task: dict[str, Any], plan: list[str], constraint: dict[str, Any]) -> bool:
    trace = independent_replay(task, plan)
    if not trace["valid"]:
        return True
    params = constraint["params"]
    ctype = constraint["type"]
    if ctype == "budget":
        return trace["cost"] > params["max_total_cost_cny"]
    if ctype == "deadline":
        return trace["minutes"] > params["max_duration_hours"] * 60
    if ctype == "privacy":
        return any(label in params["protected_data_classes"] for label in trace["leaked_classes"])
    first_key, second_key = PRECEDENCE_KEYS[ctype]
    first, second = params[first_key], params[second_key]
    positions = trace["positions"]
    return second in positions and (first not in positions or positions[first] > positions[second])


def verify(rows: list[dict[str, Any]], data_dir: Path) -> dict[str, Any]:
    failures: dict[str, list[str]] = defaultdict(list)
    leakage = cross_split_overlaps(rows)
    for name, count in leakage.items():
        if count:
            failures["cross_split_overlap"].append(f"{name}:{count}")
    counts = Counter(r.get("subset") for r in rows)
    groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    seen_ids = set()
    for row in rows:
        sid = row.get("sample_id", "<missing>")
        if sid in seen_ids:
            failures["duplicate_sample_id"].append(sid)
        seen_ids.add(sid)
        if row.get("spec_version") != "v6":
            failures["wrong_spec_version"].append(sid)
        if row.get("variant") in groups[row.get("group_id")]:
            failures["duplicate_variant"].append(sid)
        groups[row.get("group_id")][row.get("variant")] = row

    group_subset = {}
    combo_counts = Counter()
    for group_id, triplet in groups.items():
        if set(triplet) != {"explicit", "implicit", "none"}:
            failures["triplet_completeness"].append(group_id)
            continue
        e, i, n = (triplet[v] for v in ("explicit", "implicit", "none"))
        subset = e["subset"]
        group_subset[group_id] = subset
        if any(r["subset"] != subset or r["task"] != e["task"] or r["task_goal"] != e["task_goal"]
               for r in (i, n)):
            failures["triplet_task_alignment"].append(group_id)
        if [
            {k: c[k] for k in ("type", "severity", "scope", "params")}
            for c in e["gold"]["constraints"]
        ] != [
            {k: c[k] for k in ("type", "severity", "scope", "params")}
            for c in i["gold"]["constraints"]
        ]:
            failures["explicit_implicit_semantics"] .append(group_id)
        if (e["gold"]["query_state"] != "explicit" or i["gold"]["query_state"] != "implicit"
                or n["gold"]["query_state"] != "none" or n["gold"]["constraints"]):
            failures["e_in_consistency"].append(group_id)

        expected_combo = tuple(sorted(c["type"] for c in e["gold"]["constraints"]))
        if subset == "test_composition_ho":
            combo_counts["heldout"] += 1
            if expected_combo != tuple(sorted(HELDOUT_CONSTRAINT_COMBINATION)):
                failures["composition_test_mismatch"].append(group_id)
            if any(r["world"] != "train" or any(not tid.startswith("train:") for tid in r["template_ids"])
                   for r in (e, i, n)):
                failures["composition_train_world_or_template"] .append(group_id)
        elif contains_heldout_pair(expected_combo):
            failures["composition_leakage"] .append(group_id)
        else:
            combo_counts["seen"] += 1

        for positive in (e, i):
            witnesses = positive.get("generation_witness", {}).get("constraints", [])
            if len(witnesses) != len(positive["gold"]["constraints"]):
                failures["positive_witness_count"].append(positive["sample_id"])
                continue
            witness_trace = independent_replay(positive["task"], positive["witness_plan"])
            if not witness_trace["valid"] or not witness_trace["completed"] or any(
                independently_violates(positive["task"], positive["witness_plan"], c)
                for c in positive["gold"]["constraints"]
            ):
                failures["positive_witness_invalid"].append(positive["sample_id"])
            for index, (constraint, witness) in enumerate(zip(positive["gold"]["constraints"], witnesses)):
                span = constraint.get("evidence_span", "")
                if (witness.get("constraint_index") != index or witness.get("type") != constraint["type"]
                        or witness.get("state") != positive["variant"] or witness.get("evidence_span") != span
                        or witness.get("witness_plan") != positive["witness_plan"]
                        or not span or positive["query"].count(span) != 1):
                    failures["positive_evidence_witness"] .append(positive["sample_id"])
                cf = witness.get("counterfactual_plan")
                cf_trace = independent_replay(positive["task"], cf)
                remaining = positive["gold"]["constraints"][:index] + positive["gold"]["constraints"][index + 1:]
                if (not cf_trace["valid"] or not cf_trace["completed"]
                        or not independently_violates(positive["task"], cf, constraint)
                        or any(independently_violates(positive["task"], cf, other) for other in remaining)):
                    failures["counterfactual_necessity"] .append(positive["sample_id"])

        none_witness = n.get("generation_witness", {})
        replay = independent_replay(n["task"], none_witness.get("none_noop_plan"))
        if (none_witness.get("constraints") != [] or not replay["valid"] or not replay["completed"]
                or none_witness.get("none_noop_plan") != n["default_plan"]):
            failures["none_noop_witness"] .append(n["sample_id"])
        if len(none_witness.get("negative_slots", [])) != len(n["template_ids"]):
            failures["none_negative_slot_witness"] .append(n["sample_id"])

    count_errors = {s: {"expected_groups": EXPECTED_GROUPS[s], "observed_records": counts[s]}
                    for s in SUBSETS if counts[s] != EXPECTED_GROUPS[s] * 3}
    for subset, actual in count_errors.items():
        failures["split_record_count"].append(f"{subset}:{actual['observed_records']}")
    observed_groups = Counter(group_subset.values())
    for subset in SUBSETS:
        if observed_groups[subset] != EXPECTED_GROUPS[subset]:
            failures["split_group_count"].append(f"{subset}:{observed_groups[subset]}")

    # V5 schema/evidence/necessity, alias and held-out-tool checks apply to all
    # records. Its fixed five-split overlap loop is supplemented by leakage above.
    base = verify_v5(rows)
    for key, count in base["failures"].items():
        if count:
            failures[f"v5_{key}"].append(str(count))

    hashes = {}
    generation_path = data_dir / "generation_report.json"
    if not generation_path.is_file():
        failures["missing_generation_report"].append(str(generation_path))
    else:
        declared = json.loads(generation_path.read_text(encoding="utf-8")).get("sha256", {})
        for subset in SUBSETS:
            path = data_dir / f"{subset}.jsonl"
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes[subset] = actual
            if declared.get(subset) != actual:
                failures["sha256_mismatch"].append(subset)

    failure_counts = {key: len(values) for key, values in failures.items() if values}
    return {
        "dataset": "consdag_trusted_constraint_dataset_v6",
        "records": dict(counts),
        "groups": dict(observed_groups),
        "heldout_combination": list(HELDOUT_CONSTRAINT_COMBINATION),
        "combination_isolation": dict(combo_counts),
        "leakage": leakage,
        "leakage_comparison": "exact query, task_goal and group_id values across all six splits",
        "sha256": hashes,
        "independent_replay": True,
        "human_validation_status": "pending",
        "human_validation_included_in_verdict": False,
        "v5_base_verification": base["verdict"],
        "failures": failure_counts,
        "sample_errors": {key: values[:5] for key, values in failures.items() if values},
        "verdict": "PASS" if not failure_counts else "FAIL",
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "processed_v6")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = verify(load(args.data_dir), args.data_dir)
    out = args.out or args.data_dir / "verification_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["verdict"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
