"""Freeze dev-only paired input interventions, without changing v5 train/test data.

The panel tests catalog-order sensitivity and name-to-role binding. It does not
claim new reasoning depth, an unseen test set, or independent human validation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from run_e1 import load_jsonl
from trust_env import check, plan

ROOT = Path(__file__).resolve().parents[1]
SEED = 20261123
CONDITIONS = ("original", "catalog_shuffled", "opaque_roles")


def rename_roles(row: dict, mapping: dict[str, str]) -> dict:
    """Rename identifiers everywhere with a bijection, preserving readable names."""
    if len(mapping.values()) != len(set(mapping.values())):
        raise ValueError("Role mapping must be one-to-one")
    pattern = re.compile(r"(?<![A-Za-z0-9_])(" + "|".join(map(re.escape, sorted(mapping, key=len, reverse=True)))
                         + r")(?![A-Za-z0-9_])")

    def visit(value):
        if isinstance(value, str):
            return pattern.sub(lambda m: mapping[m.group(0)], value)
        if isinstance(value, list):
            return [visit(v) for v in value]
        if isinstance(value, dict):
            return {mapping.get(k, k): visit(v) for k, v in value.items()}
        return value
    return visit(row)


def paired_conditions(row: dict, *, mapping: dict[str, str], seed: int) -> dict[str, dict]:
    variants = {"original": copy.deepcopy(row), "catalog_shuffled": copy.deepcopy(row),
                "opaque_roles": rename_roles(row, mapping)}
    random.Random(seed).shuffle(variants["catalog_shuffled"]["catalog"])
    for condition, variant in variants.items():
        variant["source_sample_id"] = row["sample_id"]
        variant["source_group_id"] = row["group_id"]
        variant["diagnostic_condition"] = condition
        variant["sample_id"] = row["sample_id"] + "::" + condition
        variant["group_id"] = row["group_id"] + "::" + condition
    return variants


def build(source: Path, destination: Path, groups_per_count: int = 12) -> dict:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite frozen panel: {destination}")
    groups = defaultdict(list)
    for row in load_jsonl(source):
        groups[row["group_id"]].append(row)
    strata = defaultdict(list)
    for gid, group in groups.items():
        explicit = next(r for r in group if r["variant"] == "explicit")
        strata[len(explicit["gold"]["constraints"])].append(gid)
    selected = []
    for count in (1, 2, 3):
        candidates = sorted(strata[count], key=lambda gid: hashlib.sha256(f"{SEED}:{gid}".encode()).hexdigest())
        if len(candidates) < groups_per_count:
            raise ValueError(f"Not enough dev groups with {count} constraints")
        selected.extend(candidates[:groups_per_count])
    outputs = {condition: [] for condition in CONDITIONS}
    mappings = {}
    for index, gid in enumerate(selected):
        roles = sorted(groups[gid][0]["task"]["tools"])
        aliases = [f"op_{n:03d}" for n in range(len(roles))]
        random.Random(SEED + index).shuffle(aliases)
        mapping = dict(zip(roles, aliases))
        mappings[gid] = mapping
        for row in groups[gid]:
            original_plan, original_info = plan(row["task"], row["gold"]["constraints"])
            if original_plan is None:
                raise ValueError("Source gold has no feasible plan")
            for condition, variant in paired_conditions(row, mapping=mapping, seed=SEED + index).items():
                gold = variant["gold"]["constraints"]
                witness = [mapping.get(r, r) for r in original_plan] if condition == "opaque_roles" else original_plan
                if not check(variant["task"], witness, gold)["safe_success"]:
                    raise ValueError("Renamed original witness failed execution")
                _, info = plan(variant["task"], gold)
                if info["changes"] != original_info["changes"]:
                    raise ValueError("Intervention changed minimum edit count")
                if any(c["evidence_span"] not in variant["query"] for c in gold):
                    raise ValueError("Evidence lost during renaming")
                outputs[condition].append(variant)
    destination.mkdir(parents=True)
    hashes = {}
    for condition, rows in outputs.items():
        path = destination / f"{condition}.jsonl"
        path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8", newline="\n")
        hashes[condition] = hashlib.sha256(path.read_bytes()).hexdigest()
    protocol = {
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "source_split": "v5 dev",
        "selection_seed": SEED, "groups_per_constraint_count": groups_per_count,
        "selected_groups": selected, "records_per_condition": len(outputs["original"]),
        "conditions": list(CONDITIONS), "data_sha256": hashes, "role_maps": mappings,
        "purpose": "exploratory paired binding diagnostics; no new test or reasoning-depth claim",
        "primary": "paired faithful and core-exact changes; E/I/N grouped by source task",
        "secondary": "strict exact, N false positives, parse failures, generation tokens and wall time",
        "model_arms": ["Qwen3-1.7B-v5-seed42", "Qwen3-1.7B-v5-seed43", "Qwen3-4B-v5-seed42"],
        "generation": {"precision": "bf16", "do_sample": False, "max_new_tokens": 384, "batch_size": 8},
        "training": "none; frozen adapters only",
        "stop": "data/hash/witness failure, nonfinite model values, OOM, or another GPU process",
    }
    (destination / "protocol.json").write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return protocol


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=ROOT / "data/processed_v5/dev.jsonl")
    p.add_argument("--out", type=Path, default=ROOT / "data/diagnostic_v5_binding_20261123")
    p.add_argument("--groups-per-count", type=int, default=12)
    a = p.parse_args()
    protocol = build(a.source, a.out, a.groups_per_count)
    print(json.dumps({k: v for k, v in protocol.items() if k != "role_maps"}, ensure_ascii=False, indent=2))
