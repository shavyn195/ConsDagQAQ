"""Versioned v6 data contract layered over the frozen v5 task world."""

from __future__ import annotations

from dataset_v5_spec import POLICY_CARD, SPEC_VERSION as V5_SPEC_VERSION

SPEC_VERSION = "v6"
BASE_SPEC_VERSION = V5_SPEC_VERSION
HELDOUT_CONSTRAINT_COMBINATION = ("privacy", "tool_auth")
HUMAN_VALIDATION_STATUS = "pending"

WITNESS_CONTRACT = {
    "positive": (
        "Each explicit or implicit gold constraint has a query evidence span, a feasible witness plan, "
        "and a counterfactual plan that violates that constraint when it is relaxed."
    ),
    "none": (
        "Each none record has empty gold and a default-plan no-op witness; negative near-miss labels "
        "remain synthetic and are not human-validated."
    ),
}


def is_heldout_combination(types: list[str] | tuple[str, ...]) -> bool:
    return tuple(sorted(types)) == tuple(sorted(HELDOUT_CONSTRAINT_COMBINATION))


def contains_heldout_pair(types: list[str] | tuple[str, ...]) -> bool:
    return set(HELDOUT_CONSTRAINT_COMBINATION).issubset(types)

