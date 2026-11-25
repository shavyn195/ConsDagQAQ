from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/submission"))
sys.path.insert(0, str(ROOT / "src"))
from audit_v6_predicate_equivalence import predicate_set, predicate_signature
from trust_env import normalize_constraint, violated


def test_auth_and_order_have_identical_frozen_truth_tables():
    # violated() in the registered world checks both as the same conditional precedence.
    auth = {"type": "tool_auth", "first": "a", "second": "b"}
    order = dict(auth, type="order")
    reversed_order = {"type": "order", "first": "b", "second": "a"}
    assert predicate_signature(auth) == predicate_signature(order)
    assert predicate_signature(auth) != predicate_signature(reversed_order)
    for positions in ({}, {"a": 0}, {"b": 0}, {"a": 0, "b": 1}, {"b": 0, "a": 1}):
        assert violated(auth, {"positions": positions}) == violated(order, {"positions": positions})
    assert violated(auth, {"positions": {"a": 0, "b": 1}}) != violated(reversed_order, {"positions": {"a": 0, "b": 1}})


def test_parameter_changes_are_not_removed_by_canonicalization():
    assert predicate_signature({"type": "budget", "limit": 10}) != predicate_signature({"type": "budget", "limit": 20})
    assert predicate_signature({"type": "privacy", "classes": {"a"}}) != predicate_signature({"type": "privacy", "classes": {"a", "b"}})


def test_unusable_constraints_are_not_silently_dropped():
    # Invalid output is not equivalent to the empty conjunction.
    invalid = [{"type": "privacy", "params": {}}]
    assert predicate_set(invalid, {}, normalize_constraint) is None
    assert predicate_set([], {}, normalize_constraint) == frozenset()


def test_identical_repeated_constraints_are_logically_idempotent():
    # A AND A has the same truth values as A; this does not change typed record scoring.
    budget = {"type": "budget", "params": {"max_total_cost_cny": 10}}
    assert predicate_set([budget, budget], {}, normalize_constraint) == predicate_set([budget], {}, normalize_constraint)
