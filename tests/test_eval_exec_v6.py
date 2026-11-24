from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eval_exec_v6 import evaluate_v6, n_error_components, n_error_subtypes  # noqa: E402


def none_row(sample_id: str) -> dict:
    return {
        "sample_id": sample_id,
        "group_id": sample_id,
        "variant": "none",
        "task": {
            "tools": {"stage": {"cost_cny": 0, "duration_min": 1, "recipient": "local", "clears_pii": False}},
            "stages": [{"alternatives": ["stage"], "default": "stage"}],
            "finish": [],
            "optional": {},
            "data_class": None,
        },
        "default_plan": ["stage"],
        "gold": {"constraints": [], "query_state": "none"},
    }


def test_v6_malformed_none_fails_primary_metrics_but_retains_fallback_diagnostic():
    summary, outcomes = evaluate_v6([none_row("n1")], ["{"])
    assert summary["metrics_version"] == "e1_exec_v6_fail_closed"
    assert summary["safe_success"] == 0.0
    assert summary["faithful_success"] == 0.0
    assert outcomes[0]["malformed"]
    assert outcomes[0]["runtime_fallback_completed"]
    assert outcomes[0]["runtime_fallback_safe_success"]


def test_n_errors_are_reported_as_separate_channels():
    rows = [none_row("spurious"), none_row("state"), none_row("malformed")]
    nonempty = [{"type": "budget", "state": "none", "severity": "low", "scope": [],
                 "params": {"max_total_cost_cny": 0}}]
    raw = [
        json.dumps({"query_state": "none", "constraints": nonempty}),
        json.dumps({"query_state": "explicit", "constraints": []}),
        "{",
    ]
    counts = n_error_components(rows, raw)
    assert counts["parse_failure"] == 1
    assert counts["nonempty_constraints"] == 1
    assert counts["query_state_error"] == 1
    assert counts["any_contract_alarm"] == 3
    assert counts["rates"]["any_contract_alarm"] == 1.0


def test_v6_none_requires_valid_empty_none_state_even_if_plan_is_safe():
    # The v6 N contract is a valid empty/no-op compilation, not only unchanged execution.
    raw = json.dumps({"query_state": "explicit", "constraints": []})
    summary, outcomes = evaluate_v6([none_row("wrong-state")], [raw])
    assert outcomes[0]["safe_success"]
    assert not outcomes[0]["faithful_success"]
    assert summary["per_variant"]["none"]["faithful_success"] == 0.0


def test_n_subtype_alarm_is_union_per_row_and_keeps_separate_causes():
    rows = [
        {**none_row("a"), "near_miss_subtypes": ["waiver", "waiver", "revoked"]},
        {**none_row("b"), "near_miss_subtypes": ["waiver"]},
    ]
    raw = ["{", '{"query_state":"explicit","constraints":[]}']
    result = n_error_subtypes(rows, raw)
    assert result["waiver"]["n"] == 2
    assert result["waiver"]["parse_failure"] == 1
    assert result["waiver"]["query_state_error"] == 1
    assert result["waiver"]["any_contract_alarm"] == 2
    assert result["revoked"]["n"] == 1
    assert result["revoked"]["any_contract_alarm"] == 1
