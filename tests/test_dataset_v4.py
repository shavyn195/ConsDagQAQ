import copy
import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_dataset_v4 import gen_group  # noqa: E402
from dataset_v4_spec import E_TEMPLATES, directive_hits, I_TEMPLATES, NEAR_MISS  # noqa: E402
from trust_env import check, default_plan, execute, plan  # noqa: E402
from verify_dataset_v4 import verify  # noqa: E402


@pytest.fixture(scope="module")
def rows():
    rng = random.Random(3)
    used: set[str] = set()
    out = []
    for subset, n in (("train", 24), ("dev", 4), ("test_tpl_ho", 6), ("test_tool_ho", 6)):
        for k in range(n):
            group = gen_group(rng, f"{subset}-{k:05d}", subset, used)
            assert group is not None
            used.add(group["records"][0]["task_goal"])
            out.extend(group["records"])
    return out


def test_implicit_templates_carry_no_directive():
    for ctype, pools in I_TEMPLATES.items():
        for pool, items in pools.items():
            for _, _, text in items:
                assert not directive_hits(text), (ctype, pool, text)


def test_template_pools_are_disjoint():
    for table in (E_TEMPLATES, NEAR_MISS):
        for ctype, pools in table.items():
            assert not set(pools["train"]) & set(pools["test"]), ctype


def test_generated_rows_pass_verifier(rows):
    report = verify(rows)
    assert report["verdict"] == "PASS", report["sample_errors"]


def test_verifier_catches_tampered_witness(rows):
    bad = copy.deepcopy(rows)
    for r in bad:
        if r["variant"] == "explicit":
            r["witness_plan"] = r["default_plan"]
            break
    assert verify(bad)["failures"].get("V2_witness")


def test_verifier_catches_constraint_left_in_none(rows):
    bad = copy.deepcopy(rows)
    e = next(r for r in bad if r["variant"] == "explicit")
    n = next(r for r in bad if r["group_id"] == e["group_id"] and r["variant"] == "none")
    n["gold"]["constraints"] = copy.deepcopy(e["gold"]["constraints"])
    assert verify(bad)["failures"].get("V5_triplet")


def test_verifier_catches_heldout_tool_in_train(rows):
    bad = copy.deepcopy(rows)
    r = next(r for r in bad if r["subset"] == "train")
    r["query"] += " Then run the federated training."
    assert verify(bad)["failures"].get("V7_heldout_tool_seen")


def test_none_variant_is_not_shorter_than_explicit(rows):
    by_group = {}
    for r in rows:
        by_group.setdefault(r["group_id"], {})[r["variant"]] = r
    for g in by_group.values():
        assert g["none"]["query"] != g["none"]["task_goal"]
        assert len(g["none"]["template_ids"]) == len(g["explicit"]["template_ids"])


def test_planner_empty_constraints_returns_default(rows):
    task = rows[0]["task"]
    got, info = plan(task, [])
    assert got == default_plan(task) and info["changes"] == 0


def test_planner_ignores_unusable_and_fails_on_impossible(rows):
    task = rows[0]["task"]
    got, info = plan(task, [{"type": "budget", "params": {"max_total_cost_cny": "cheap"}}])
    assert got == default_plan(task) and info["unusable_constraints"] == 1
    impossible, _ = plan(task, [{"type": "deadline", "params": {"max_duration_hours": 0}}])
    assert impossible is None
    assert check(task, impossible, [])["safe_success"] is False


def test_precedence_is_vacuous_when_second_role_absent(rows):
    task = rows[0]["task"]
    base = default_plan(task)
    absent = next(r for r in task["tools"] if r not in base)
    first = next(r for r in task["tools"] if r != absent)
    c = {"type": "order", "params": {"before_role": first, "after_role": absent}}
    assert check(task, base, [c])["violations"] == []


def test_gold_constraints_bind_and_none_plan_fails(rows):
    for r in rows:
        if r["variant"] == "none":
            continue
        task, gold = r["task"], r["gold"]["constraints"]
        assert not check(task, plan(task, [])[0], gold)["safe_success"]
        assert check(task, plan(task, gold)[0], gold)["safe_success"]
        assert execute(task, r["witness_plan"])["completed"]


def test_rows_are_json_serialisable(rows):
    json.dumps(rows)
