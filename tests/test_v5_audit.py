import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from analyze_v5_main import noninferiority_decision
from analyze_v5_seed_disagreement import group_bootstrap_delta
from eval_exec import conservative_outcome
from trust_env import plan, plan_change_count
from build_v5_diagnostic_panel import paired_conditions, rename_roles


def test_noninferiority_requires_all_registered_seeds():
    # The preregistered H2 explicitly requires seeds 42/43/44.
    diagnostic = {"diff": 0.01, "ci95": [0.0, 0.02]}
    assert noninferiority_decision(diagnostic, [42, 43])["noninferior"] is None
    assert noninferiority_decision(diagnostic, [42, 43, 44])["noninferior"] is True
    assert noninferiority_decision({"ci95": [-.03, 0]}, [42, 43, 44])["noninferior"] is False


def test_pair_bootstrap_zero_when_every_group_is_tied():
    # Each E/I pair has zero A-B difference, so every possible resample is zero.
    assert group_bootstrap_delta({"a": (0, 2), "b": (0, 2)}, n_boot=100) == [0, 0, 0]


def test_equal_edit_alternatives_share_faithful_definition(monkeypatch):
    # a costs 10; b and c cost 0. Both b->z and c->z meet budget zero
    # with exactly one substitution. Lexicographic tie breaking chooses b.
    spec = {"cost_cny": 0, "duration_min": 1, "recipient": "local", "clears_pii": False}
    task = {"stages": [{"alternatives": ["a", "b", "c"], "default": "a"}],
            "finish": ["z"], "optional": {}, "data_class": None,
            "tools": {r: copy.deepcopy(spec) for r in ("a", "b", "c", "z")}}
    task["tools"]["a"]["cost_cny"] = 10
    gold = [{"type": "budget", "params": {"max_total_cost_cny": 0}}]
    assert plan(task, gold)[0] == ["b", "z"]
    assert plan_change_count(task, ["c", "z"]) == 1
    monkeypatch.setattr("eval_exec.conservative_plan", lambda _: ["c", "z"])
    row = {"sample_id": "x", "group_id": "g", "variant": "explicit", "task": task,
           "gold": {"constraints": gold}}
    assert conservative_outcome(row)["faithful_success"] is True
    with pytest.raises(ValueError, match="Duplicate"):
        plan_change_count(task, ["c", "c", "z"])


def test_role_renaming_is_reversible_and_preserves_readable_names():
    # A bijection must preserve the task when inverted, including scope/params.
    row = {"sample_id": "x", "group_id": "g", "catalog": [
        {"role": "pay", "name": "payment approval"}, {"role": "send", "name": "delivery"}],
        "task": {"tools": {"pay": {}, "send": {}}, "finish": ["send"]},
        "query": "Complete payment approval.",
        "gold": {"constraints": [{"scope": ["role:pay"], "params": {"before_role": "pay"}}]}}
    mapping = {"pay": "op_001", "send": "op_000"}
    renamed = rename_roles(row, mapping)
    assert rename_roles(renamed, {v: k for k, v in mapping.items()}) == row
    assert renamed["query"] == row["query"]
    assert renamed["catalog"][0]["name"] == "payment approval"
    assert renamed["gold"]["constraints"][0]["scope"] == ["role:op_001"]
    conditions = paired_conditions(row, mapping=mapping, seed=1)
    assert conditions["catalog_shuffled"]["gold"] == row["gold"]
    assert sorted(conditions["catalog_shuffled"]["catalog"], key=lambda x: x["role"]) == row["catalog"]
