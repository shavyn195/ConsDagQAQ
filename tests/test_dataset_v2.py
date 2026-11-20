"""dataset_v2 生成器与校验器的快速回归测试（内存中生成小样本，不依赖全量数据）。"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import build_dataset_v2 as builder  # noqa: E402
from dataset_v2_spec import E_TEMPLATES, I_TEMPLATES  # noqa: E402
from verify_dataset_v2 import check_constraint, validate_pairs, validate_record, witness_feasible  # noqa: E402


@pytest.fixture(scope="module")
def groups():
    rng = __import__("random").Random(7)
    out = {}
    for subset in ["train", "dev", "test_tpl_ho", "test_tool_ho"]:
        made = []
        idx = 0
        while len(made) < 8:
            g = builder.gen_group(rng, f"{subset}-{idx:03d}", subset)
            idx += 1
            if g:
                made.extend(g["records"])
        out[subset] = made
    return out


def test_groups_have_three_variants(groups):
    for subset, rows in groups.items():
        variants = {r["variant"] for r in rows}
        assert variants == {"explicit", "implicit", "none"}, subset


def test_ei_pairs_share_constraint_set(groups):
    for rows in groups.values():
        assert validate_pairs(rows) == []


def test_witness_satisfies_all_constraints(groups):
    for rows in groups.values():
        for r in rows:
            assert witness_feasible(r) == [], r["sample_id"]


def test_schema_and_evidence_span(groups):
    for rows in groups.values():
        for r in rows:
            assert validate_record(r) == [], r["sample_id"]


def test_template_pools_are_split():
    # 模板池 train/test 严格分池且每类每版每池 >=8 变体
    for ctype, pools in E_TEMPLATES.items():
        assert len(pools["train"]) >= 8 and len(pools["test"]) >= 8, ctype
        assert set(pools["train"]).isdisjoint(pools["test"]), ctype


def test_implicit_covers_hint_types_and_difficulties():
    for ctype, pools in I_TEMPLATES.items():
        for pool in ("train", "test"):
            combos = {(h, d) for h, d, _ in pools[pool]}
            for hint in ("consequence", "fact", "convention"):
                assert any(h == hint for h, _ in combos), (ctype, pool, hint)
            for diff in (1, 2, 3):
                assert any(d == diff for _, d in combos), (ctype, pool, diff)


def test_tool_ho_uses_heldout_roles(groups):
    from dataset_v2_spec import HELDOUT_SUBSYSTEMS, ROLES

    for r in groups["test_tool_ho"]:
        for node in r["graph"]["nodes"]:
            assert ROLES[node["role"]][0] in HELDOUT_SUBSYSTEMS, r["sample_id"]


def test_constraint_checker_negative_cases():
    witness = [
        {"step": 0, "role": "validate_workflow", "cost_cny": 0, "duration_min": 30,
         "recipient": "local", "data_classes": ["aggregate_metrics"]},
        {"step": 1, "role": "run_production_mode", "cost_cny": 0, "duration_min": 60,
         "recipient": "local", "data_classes": ["aggregate_metrics"]},
    ]
    ok_order = {"type": "order", "params": {"before_role": "validate_workflow", "after_role": "run_production_mode"}}
    bad_order = {"type": "order", "params": {"before_role": "run_production_mode", "after_role": "validate_workflow"}}
    assert check_constraint(ok_order, witness)
    assert not check_constraint(bad_order, witness)
    pii_external = [
        {"step": 0, "role": "call_external_api", "cost_cny": 50, "duration_min": 10,
         "recipient": "external", "data_classes": ["customer_pii"]},
    ]
    privacy = {"type": "privacy", "params": {"protected_data_classes": ["customer_pii"], "forbidden_recipients": ["external"]}}
    assert not check_constraint(privacy, pii_external)
