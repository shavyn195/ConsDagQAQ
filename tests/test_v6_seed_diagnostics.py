from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "submission"))

from analyze_v6_seed_diagnostics import _binary_summary, _failure_overlap, record_diagnostic  # noqa: E402


def _constraint(*, scope="role:tool_a", state="explicit", severity="high", evidence="allowed"):
    return {
        "type": "privacy",
        "params": {"data_class": "patient_ids", "allowed_environment": "local"},
        "scope": [scope],
        "state": state,
        "severity": severity,
        "evidence_span": evidence,
    }


def test_exec_success_can_coexist_with_nonexact_constraint_record():
    # Constructed ground truth: params agree; all four audit fields are changed once.
    constraint = _constraint(scope="role:wrong_tool", state="implicit", severity="low", evidence="paraphrased")
    row = {
        "sample_id": "s1",
        "group_id": "g1",
        "variant": "explicit",
        "gold": {"query_state": "explicit", "constraints": [_constraint()]},
    }
    execution = {"faithful_success": True, "safe_success": True}

    diagnostic = record_diagnostic(row, json.dumps({"query_state": "explicit", "constraints": [constraint]}), execution)

    assert diagnostic["faithful"] is True
    assert diagnostic["strict_record_exact"] is False
    assert diagnostic["field_mismatches_among_core_matches"] == {
        "scope": 1,
        "constraint_state": 1,
        "severity": 1,
        "evidence_span": 1,
    }


def test_execution_and_record_confusion_counts_are_explicit():
    # Hand-counted truth table: one observation in each of three different cells.
    records = [
        {"faithful": True, "strict_record_exact": False},
        {"faithful": False, "strict_record_exact": True},
        {"faithful": True, "strict_record_exact": True},
    ]
    result = _binary_summary(records)
    assert result["faithful_but_not_strict_exact"] == 1
    assert result["strict_exact_but_not_faithful"] == 1
    assert result["faithful_and_strict_exact"] == 1


def test_seed_overlap_is_computed_on_task_groups_not_rows():
    # The E/I pair is one group, and only seed42 fails it; intersection is empty.
    seed42 = {
        "e1": {"group_id": "g1", "variant": "explicit", "faithful": False},
        "i1": {"group_id": "g1", "variant": "implicit", "faithful": True},
        "n1": {"group_id": "g1", "variant": "none", "faithful": True},
    }
    seed43 = {
        "e1": {"group_id": "g1", "variant": "explicit", "faithful": True},
        "i1": {"group_id": "g1", "variant": "implicit", "faithful": True},
        "n1": {"group_id": "g1", "variant": "none", "faithful": True},
    }
    result = _failure_overlap({"42": seed42, "43": seed43})
    pair = result["42_vs_43"]
    assert pair["seed_a_failed_groups"] == 1
    assert pair["seed_b_failed_groups"] == 0
    assert pair["intersection"] == 0
    assert pair["union"] == 1


def test_scope_order_has_the_frozen_scorer_set_semantics():
    # The registered strict key sorts scope roles; order alone is not an error.
    gold = _constraint()
    gold["scope"] = ["role:a", "role:b"]
    pred = dict(gold, scope=["role:b", "role:a"])
    row = {"sample_id": "x", "group_id": "g", "variant": "explicit",
           "gold": {"query_state": "explicit", "constraints": [gold]}}
    result = record_diagnostic(row, json.dumps({"query_state": "explicit", "constraints": [pred]}),
                               {"faithful_success": True, "safe_success": True})
    assert result["strict_record_exact"]
    assert result["field_mismatches_among_core_matches"] == {}


def test_core_matching_preserves_multiplicity_and_numeric_equivalence():
    # One prediction cannot cover two gold copies; 2 and 2.0 are equal by the frozen key.
    gold = dict(_constraint(), params={"max_cost": 2})
    pred = dict(gold, params={"max_cost": 2.0})
    row = {"sample_id": "x", "group_id": "g", "variant": "explicit",
           "gold": {"query_state": "explicit", "constraints": [gold, gold]}}
    result = record_diagnostic(row, json.dumps({"query_state": "explicit", "constraints": [pred]}),
                               {"faithful_success": False, "safe_success": False})
    assert result["core_matched_constraints"] == 1
    assert result["core_missing"] == 1
    assert not result["strict_record_exact"]
