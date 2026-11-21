from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_e1 import chat_messages, require_finite_loss, score, task_space_context  # noqa: E402


def constraint(kind: str, value: int, evidence: str) -> dict:
    return {
        "type": kind,
        "state": "implicit",
        "severity": "high",
        "scope": ["role:pay"],
        "params": {"limit": value},
        "evidence_span": evidence,
    }


def row(variant: str, constraints: list[dict], hint_meta: list[dict] | None = None) -> dict:
    state = "none" if variant == "none" else variant
    return {
        "sample_id": "sample-1",
        "variant": variant,
        "hint_meta": hint_meta or [],
        "gold": {"query_state": state, "constraints": constraints},
    }


def test_evidence_matching_is_constraint_aligned_and_order_independent():
    gold_a = constraint("budget", 10, "budget clue")
    gold_b = constraint("deadline", 5, "deadline clue")
    pred = {"query_state": "implicit", "constraints": [gold_b, gold_a]}

    metrics = score([row("implicit", [gold_a, gold_b])], [pred], [json.dumps(pred)])

    assert metrics["evidence_exact_rate"] == 1.0
    assert metrics["evidence_records"] == 2


def test_scope_role_order_does_not_change_constraint_match():
    gold = constraint("budget", 10, "budget clue")
    pred = {"query_state": "implicit", "constraints": [{**gold, "scope": list(reversed(gold["scope"]))}]}

    metrics = score([row("implicit", [gold])], [pred], [json.dumps(pred)])

    assert metrics["constraint_micro"]["f1"] == 1.0


def test_difficulty_bucket_counts_near_miss_false_positive_and_false_negative():
    gold = constraint("deadline", 5, "four hours from now")
    pred_constraint = constraint("deadline", 8, "four hours from now")
    pred = {"query_state": "implicit", "constraints": [pred_constraint]}

    metrics = score(
        [row("implicit", [gold], [{"difficulty": 2}])],
        [pred],
        [json.dumps(pred)],
    )

    assert metrics["per_difficulty_implicit"]["d2"]["tp"] == 0
    assert metrics["per_difficulty_implicit"]["d2"]["fp"] == 1
    assert metrics["per_difficulty_implicit"]["d2"]["fn"] == 1


def test_empty_constraint_set_has_undefined_prf_and_reports_exact_empty_rate():
    empty = row("none", [])
    pred = {"query_state": "none", "constraints": []}

    metrics = score([empty], [pred], [json.dumps(pred)])
    none = metrics["per_variant"]["none"]

    assert none["precision"] is None
    assert none["recall"] is None


def test_training_guard_rejects_non_finite_loss_before_backward():
    torch = pytest.importorskip("torch")

    with pytest.raises(FloatingPointError, match="epoch=2, example=7, optimizer_step=42"):
        require_finite_loss(
            torch.tensor(float("nan")), torch=torch,
            epoch=2, example_index=7, optimizer_step=42,
        )


def test_training_guard_accepts_finite_loss():
    torch = pytest.importorskip("torch")

    require_finite_loss(
        torch.tensor(0.25), torch=torch,
        epoch=1, example_index=0, optimizer_step=1,
    )


def test_scope_prompt_includes_task_space_metadata_without_gold_constraints():
    sample = {
        "available_roles": ["role:send", "role:finish"],
        "query": "Prepare the report.",
        "graph": {"nodes": [{
            "role": "send", "cost_cny": 12, "duration_min": 5,
            "recipient": "external", "data_classes": ["customer_records"],
            "terminal_output": True, "id": 3,
        }]},
        "gold": {"constraints": [{"type": "budget", "params": {"max_total_cost_cny": 12}}]},
    }

    metadata = task_space_context(sample)
    prompt = chat_messages(sample)[1]["content"]

    assert '"cost_cny":12' in metadata
    assert '"recipient":"external"' in metadata
    assert '"terminal":true' in metadata
    assert "Task-space node metadata for scope binding" in prompt
    assert "max_total_cost_cny" not in prompt


def test_score_rejects_misaligned_inputs_instead_of_truncating():
    with pytest.raises(ValueError, match="equal lengths"):
        score([row("none", [])], [], ['{"constraints": []}'])


def test_invalid_json_cannot_count_as_correct_none_state_or_empty_set():
    empty = row("none", [])
    normalised = {"query_state": "none", "abstain": True, "constraints": []}

    metrics = score([empty], [normalised], ["not json"])

    assert metrics["state_accuracy"] == 0.0
    assert metrics["per_variant"]["none"]["empty_set_accuracy"] == 0.0
    assert metrics["json_parse_rate"] == 0.0

