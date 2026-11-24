"""Build the v6 paired E/I/N corpus with a dedicated composition holdout."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from build_dataset_v5 import gen_group
from dataset_v6_spec import (
    HELDOUT_CONSTRAINT_COMBINATION,
    SPEC_VERSION,
    WITNESS_CONTRACT,
    contains_heldout_pair,
    is_heldout_combination,
)

ROOT = Path(__file__).resolve().parents[1]
SUBSETS = ("train", "dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho", "test_composition_ho")
POSITIVE_VARIANTS = ("explicit", "implicit")


def add_witnesses(record: dict[str, Any]) -> None:
    constraints = record["gold"]["constraints"]
    if record["variant"] in POSITIVE_VARIANTS:
        from trust_env import plan

        witnesses = []
        for index, constraint in enumerate(constraints):
            relaxed, _ = plan(record["task"], constraints[:index] + constraints[index + 1 :])
            state_code = "E" if record["variant"] == "explicit" else "I"
            template_id = next(
                tid for tid in record["template_ids"]
                if tid.split(":")[1:3] == [constraint["type"], state_code]
            )
            witnesses.append({
                "constraint_index": index,
                "type": constraint["type"],
                "state": record["variant"],
                "evidence_span": constraint["evidence_span"],
                "template_id": template_id,
                "witness_plan": record["witness_plan"],
                "counterfactual_plan": relaxed,
            })
        record["generation_witness"] = {"constraints": witnesses}
        return

    record["generation_witness"] = {
        "constraints": [],
        "none_noop_plan": record["default_plan"],
        "negative_slots": [
            {"slot": index, "template_id": template_id, "subtype": subtype}
            for index, (template_id, subtype) in enumerate(
                zip(record["template_ids"], record["near_miss_subtypes"])
            )
        ],
    }


def combo_of(group: dict[str, Any]) -> tuple[str, ...]:
    explicit = next(record for record in group["records"] if record["variant"] == "explicit")
    return tuple(sorted(item["type"] for item in explicit["gold"]["constraints"]))


def build(config_path: Path = ROOT / "configs" / "dataset_v6.json") -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rng = random.Random(config["seed"])
    heldout = tuple(sorted(config["heldout_constraint_combination"]))
    if heldout != tuple(sorted(HELDOUT_CONSTRAINT_COMBINATION)):
        raise ValueError(f"heldout combination must match v6 spec: {HELDOUT_CONSTRAINT_COMBINATION}")

    out_dir = ROOT / config["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    used_goals: set[str] = set()
    rows_by_subset: dict[str, list[dict[str, Any]]] = {}
    generation_rejections = Counter()
    for subset in SUBSETS:
        target = int(config["groups"][subset])
        accepted: list[dict[str, Any]] = []
        candidate_index = 0
        attempts = 0
        while len(accepted) // 3 < target:
            attempts += 1
            if attempts > max(100_000, target * 500):
                raise RuntimeError(f"generation exhausted for {subset}: accepted={len(accepted)}/{target}")
            group = gen_group(rng, f"{subset}-{candidate_index:05d}", subset, used_goals)
            candidate_index += 1
            if group is None:
                generation_rejections["generator_returned_none"] += 1
                continue
            types = combo_of(group)
            if (subset == "test_composition_ho" and not is_heldout_combination(types)) or (
                subset != "test_composition_ho" and contains_heldout_pair(types)
            ):
                generation_rejections[f"{subset}_composition_filter"] += 1
                continue
            for record in group["records"]:
                record["spec_version"] = SPEC_VERSION
                add_witnesses(record)
                accepted.append(record)
            used_goals.add(group["records"][0]["task_goal"])
        rows_by_subset[subset] = accepted

    files: dict[str, Path] = {}
    for subset, rows in rows_by_subset.items():
        path = out_dir / f"{subset}.jsonl"
        path.write_text(
            "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
            newline="\n",
        )
        files[subset] = path

    all_rows = [row for rows in rows_by_subset.values() for row in rows]
    explicit = [r for r in all_rows if r["variant"] == "explicit"]
    report = {
        "dataset": "consdag_trusted_constraint_dataset_v6",
        "spec_version": SPEC_VERSION,
        "synthetic_only": True,
        "human_validation_status": "pending",
        "seed": config["seed"],
        "groups": {s: len(rows) // 3 for s, rows in rows_by_subset.items()},
        "records": {s: len(rows) for s, rows in rows_by_subset.items()},
        "heldout_constraint_combination": list(heldout),
        "constraint_type_distribution": {
            s: dict(Counter(c["type"] for r in rows if r["variant"] == "explicit"
                            for c in r["gold"]["constraints"]))
            for s, rows in rows_by_subset.items()
        },
        "constraints_per_group": dict(Counter(len(r["gold"]["constraints"]) for r in explicit)),
        "near_miss_subtype_distribution": dict(Counter(
            subtype for r in all_rows if r["variant"] == "none"
            for subtype in r["near_miss_subtypes"] if subtype
        )),
        "generation_rejections": dict(generation_rejections),
        "witness_contract": WITNESS_CONTRACT,
        "sha256": {s: hashlib.sha256(path.read_bytes()).hexdigest() for s, path in files.items()},
        "limitations": [
            "Synthetic, hand-templated labels; generated witnesses are not independent human semantic judgments.",
            "The blind human recoverability and N-control audit is pending.",
            "test_struct_ho remains a compound shift; test_composition_ho holds out the privacy + tool_auth pair and contains exactly that pair.",
            "Pair exclusion changes feasible task selection and constraint cardinality; this split is not a causal composition intervention.",
            "E/I/N encode generated surface conditions, not ambiguity or information insufficiency.",
        ],
    }
    (out_dir / "generation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return report


def main() -> None:
    print(json.dumps(build(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
