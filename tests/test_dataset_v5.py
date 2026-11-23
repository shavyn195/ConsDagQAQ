import copy
import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import dataset_v4_spec  # noqa: E402
from build_dataset_v5 import gen_group  # noqa: E402
from dataset_v5_spec import (  # noqa: E402
    NEAR_MISS, PII_CLASSES, POLICY_CARD, near_miss_gate, possible_signatures,
)
from eval_exec import conservative_outcome, evaluate, reference_tiers  # noqa: E402
from run_e1 import chat_messages, eval_subsets, target_json  # noqa: E402
from trust_env import _finish_orders, check, plan  # noqa: E402
from verify_dataset_v5 import spec_gates, task_signature, verify  # noqa: E402

SPLITS = (("train", 24), ("dev", 4), ("test_tpl_ho", 6), ("test_tool_ho", 6), ("test_struct_ho", 8))


@pytest.fixture(scope="module")
def rows():
    rng = random.Random(5)
    used: set[str] = set()
    out = []
    for subset, n in SPLITS:
        for k in range(n):
            group = gen_group(rng, f"{subset}-{k:05d}", subset, used)
            assert group is not None
            used.add(group["records"][0]["task_goal"])
            out.extend(group["records"])
    return out


def test_generated_rows_pass_v5_verifier(rows):
    report = verify(rows)
    assert report["verdict"] == "PASS", report["sample_errors"]


def test_spec_gates_hold():
    assert spec_gates() == {}


def test_v4_ambiguous_near_misses_fail_g1_and_v5_versions_pass():
    v4_test = dataset_v4_spec.NEAR_MISS
    assert not near_miss_gate(v4_test["tool_auth"]["test"][2])["G1"]
    assert not near_miss_gate(v4_test["deadline"]["test"][2])["G1"]
    assert all(near_miss_gate(t)["G1"] and near_miss_gate(t)["G2"]
               for pools in NEAR_MISS.values() for items in pools.values() for _, t in items)


def test_policy_card_lists_no_field_alias():
    low = POLICY_CARD.lower()
    assert not [f for info in PII_CLASSES.values() for fs in info["fields"].values() for f in fs if f.lower() in low]


def test_struct_split_is_structurally_disjoint(rows):
    from dataset_v5_spec import WORLDS
    train_sigs = possible_signatures("train")
    for r in rows:
        sig = task_signature(r["task"], WORLDS[r["world"]])
        if r["subset"] == "test_struct_ho":
            assert sig not in train_sigs
        elif r["subset"] == "test_tool_ho":
            assert sig in train_sigs


def test_finish_orders_match_v4_for_two_steps_and_count_inversions():
    assert _finish_orders(["a", "b"]) == [(["a", "b"], 0), (["b", "a"], 1)]
    moved = {tuple(p): m for p, m in _finish_orders(["a", "b", "c"])}
    assert moved[("a", "b", "c")] == 0 and moved[("c", "b", "a")] == 3 and len(moved) == 6


def test_struct_gold_plans_execute_and_none_plan_fails(rows):
    for r in rows:
        if r["subset"] != "test_struct_ho" or r["variant"] == "none":
            continue
        task, gold = r["task"], r["gold"]["constraints"]
        assert len(task["finish"]) == 3
        assert not check(task, plan(task, [])[0], gold)["safe_success"]
        assert check(task, plan(task, gold)[0], gold)["safe_success"]


def test_conservative_planner_cannot_reach_faithful_success(rows):
    constrained = [r for r in rows if r["gold"]["constraints"]]
    assert not any(conservative_outcome(r)["faithful_success"] for r in constrained)
    tiers = reference_tiers(constrained)
    assert tiers["gold"]["faithful_success"] == 1.0
    assert tiers["conservative"]["faithful_success"] == 0.0


def test_gold_outputs_are_faithful_and_empty_outputs_are_not(rows):
    summary, _ = evaluate(rows, [target_json(r) for r in rows])
    assert summary["faithful_success"] == 1.0
    empty, _ = evaluate(rows, [json.dumps({"query_state": "none", "constraints": []}) for _ in rows])
    assert empty["faithful_success_constrained"] == 0.0
    assert empty["per_variant"]["none"]["faithful_success"] == 1.0


def test_v5_prompt_uses_v5_card_and_v4_prompt_is_unchanged(rows):
    v5_row = next(r for r in rows if r["variant"] == "implicit")
    assert POLICY_CARD in chat_messages(v5_row)[1]["content"]
    v4_row = copy.deepcopy(v5_row)
    v4_row.pop("spec_version")
    content = chat_messages(v4_row)[1]["content"]
    assert dataset_v4_spec.POLICY_CARD in content and POLICY_CARD not in content


def test_eval_subsets_discovers_struct_split(tmp_path):
    for s in ("dev", "test_tpl_ho", "test_tool_ho"):
        (tmp_path / f"{s}.jsonl").write_text("", encoding="utf-8")
    assert eval_subsets(tmp_path) == ["dev", "test_tpl_ho", "test_tool_ho"]
    (tmp_path / "test_struct_ho.jsonl").write_text("", encoding="utf-8")
    assert eval_subsets(tmp_path)[-1] == "test_struct_ho"


def test_verifier_catches_struct_tool_leak(rows):
    bad = copy.deepcopy(rows)
    r = next(r for r in bad if r["subset"] == "train")
    r["query"] += " Then run the rented-cluster training."
    assert verify(bad)["failures"].get("V7_heldout_tool_seen")


def test_verifier_catches_wrong_subtype_label(rows):
    bad = copy.deepcopy(rows)
    r = next(r for r in bad if r["variant"] == "none")
    k = next(i for i, t in enumerate(r["template_ids"]) if ":N:" in t)
    r["near_miss_subtypes"][k] = "waiver" if r["near_miss_subtypes"][k] != "waiver" else "revoked"
    assert verify(bad)["failures"].get("V10_subtype_label")
