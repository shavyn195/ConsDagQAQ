"""Analytical structural and equivariance cases; no empirical score goldens."""
from pathlib import Path
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constraint_pointer import ConstraintPointer, collate, policy_input, structural_actions


def task():
    # Two stages, one optional approval, no semantic filtering in action mask.
    roles = ["a", "b", "c", "approve", "finish"]
    return {"catalog": roles, "tools": {r: {"cost_cny": 5, "duration_min": 2,
             "recipient": "local", "clears_pii": False} for r in roles}, "data_class": None,
            "stages": [{"stage": "first", "alternatives": ["a", "b"], "default": "a"},
                       {"stage": "second", "alternatives": ["c"], "default": "c"}],
            "optional": {"approve": ["c"]}, "finish": ["finish"]}


def test_structural_mask_leaves_semantic_decision_to_policy():
    t = task()
    assert structural_actions(t, []) == {"a", "b", "approve"}
    assert structural_actions(t, ["a"]) == {"c", "approve"}
    assert structural_actions(t, ["a", "c", "finish"]) == {None, "approve"}
    with unittest.TestCase().assertRaises(ValueError):
        structural_actions(t, ["c", "a"])
    with unittest.TestCase().assertRaises(ValueError):
        structural_actions(t, ["a", "b"])


def test_invalid_record_is_not_an_unconstrained_input():
    with unittest.TestCase().assertRaises(ValueError):
        policy_input(task(), [{"type": "unknown", "params": {}}], [])


def test_tool_permutation_equivariance_and_padding():
    t = task()
    original = policy_input(t, [], ["a"])
    t["catalog"] = list(reversed(t["catalog"]))
    reordered = policy_input(t, [], ["a"])
    constrained = policy_input(t, [{"type": "budget", "params": {"max_total_cost_cny": 10}}], ["a"])
    texts = sorted(set(original.texts + constrained.texts))
    torch.manual_seed(3)
    vectors = {s: torch.randn(8) for s in texts}
    for graph in (False, True):
        net = ConstraintPointer(8, width=16, heads=4, graph=graph).eval()
        batch = collate([original, reordered, constrained], vectors)
        batch.pop("allowed")
        together = net(**batch)
        for i, action in enumerate(original.actions):
            j = reordered.actions.index(action)
            torch.testing.assert_close(together[0, i], together[1, j], atol=2e-6, rtol=2e-6)
        one = collate([original], vectors); one.pop("allowed")
        torch.testing.assert_close(net(**one)[0], together[0, :len(original.texts)], atol=2e-6, rtol=2e-6)
        together.sum().backward()
        assert all(torch.isfinite(p.grad).all() for p in net.parameters() if p.grad is not None)


def test_dense_and_graph_parameter_counts_match():
    dense = ConstraintPointer(8)
    graph = ConstraintPointer(8, graph=True)
    assert sum(p.numel() for p in dense.parameters()) == sum(p.numel() for p in graph.parameters())
    assert list(dense.state_dict()) == list(graph.state_dict())
