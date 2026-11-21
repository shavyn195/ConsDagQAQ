import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_dataset_v4 import gen_group  # noqa: E402
from eval_exec import evaluate, mcnemar_p, paired_compare, reference_tiers  # noqa: E402
from run_e1 import chat_messages, score, target_json  # noqa: E402


@pytest.fixture(scope="module")
def rows():
    rng = random.Random(11)
    used: set[str] = set()
    out = []
    for k in range(12):
        group = gen_group(rng, f"dev-{k:05d}", "dev", used)
        used.add(group["records"][0]["task_goal"])
        out.extend(group["records"])
    return out


def raw_of(constraints, state):
    return json.dumps({"query_state": state, "constraints": constraints})


def test_gold_outputs_score_perfectly(rows):
    raw = [target_json(r) for r in rows]
    m = score(rows, [None] * len(rows), raw)
    assert m["metrics_version"] == "e1_score_v5"
    assert m["constraint_micro"]["f1"] == 1.0 and m["constraint_core_micro"]["f1"] == 1.0
    assert m["record_exact_match"] == 1.0
    summary, _ = evaluate(rows, raw)
    assert summary["safe_success"] == 1.0


def test_empty_outputs_fail_constrained_and_pass_none(rows):
    raw = [raw_of([], "none") for _ in rows]
    summary, _ = evaluate(rows, raw)
    assert summary["per_variant"]["explicit"]["safe_success"] == 0.0
    assert summary["per_variant"]["implicit"]["safe_success"] == 0.0
    assert summary["per_variant"]["none"]["safe_success"] == 1.0
    m = score(rows, [None] * len(rows), raw)
    assert m["per_variant"]["none"]["false_alarm_rate"] == 0.0


def test_core_key_ignores_severity_and_scope_wording(rows):
    row = next(r for r in rows if r["variant"] == "explicit")
    pred = [dict(c, severity="low", scope=["role:other"]) for c in row["gold"]["constraints"]]
    m = score([row], [None], [raw_of(pred, "explicit")])
    assert m["constraint_core_micro"]["f1"] == 1.0
    assert m["constraint_micro"]["f1"] == 0.0


def test_spurious_constraint_on_none_is_a_false_alarm(rows):
    row = next(r for r in rows if r["variant"] == "none")
    spurious = [{"type": "deadline", "state": "explicit", "severity": "high", "scope": ["role:*"],
                 "params": {"max_duration_hours": 0}, "evidence_span": "x"}]
    m = score([row], [None], [raw_of(spurious, "explicit")])
    assert m["per_variant"]["none"]["false_alarm_rate"] == 1.0
    summary, outcomes = evaluate([row], [raw_of(spurious, "explicit")])
    assert outcomes[0]["planned"] is False and summary["safe_success"] == 0.0


def test_malformed_output_falls_back_to_default_plan(rows):
    summary, outcomes = evaluate(rows, ["not json"] * len(rows))
    assert all(o["malformed"] for o in outcomes)
    assert summary["per_variant"]["none"]["safe_success"] == 1.0
    assert summary["per_variant"]["explicit"]["safe_success"] == 0.0


def test_reference_tiers_bracket_the_metric(rows):
    tiers = reference_tiers(rows)
    assert tiers["gold"]["safe_success"] == 1.0
    assert tiers["none"]["safe_success_constrained"] == 0.0


def test_paired_compare_and_mcnemar(rows):
    _, good = evaluate(rows, [target_json(r) for r in rows])
    _, bad = evaluate(rows, [raw_of([], "none") for _ in rows])
    cmp = paired_compare(good, bad)
    assert cmp["diff_a_minus_b"] > 0 and cmp["only_b_success"] == 0
    assert mcnemar_p(10, 0) < 0.01 and mcnemar_p(3, 3) == 1.0


def test_v4_prompt_exposes_policy_and_catalog_but_not_gold(rows):
    row = next(r for r in rows if r["variant"] == "implicit")
    prompt = chat_messages(row)[1]["content"]
    assert "max_total_cost_cny" in prompt and row["catalog"][0]["role"] in prompt
    for c in row["gold"]["constraints"]:
        if c["type"] == "budget":
            assert f"{c['params']['max_total_cost_cny']:,}" not in prompt.replace(row["query"], "")
