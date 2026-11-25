"""Analytic cases, including incompatible per-position marginals."""
from pathlib import Path
import sys

import unittest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constraint_set_learning import optimal_next_actions, positive_set_nll


def test_prefix_support_cannot_mix_two_correct_plans():
    # Only a,x and b,y are accepted. The product of marginals would invent a,y.
    plans = [["a", "x"], ["b", "y"]]
    assert optimal_next_actions(plans, []) == {"a", "b"}
    assert optimal_next_actions(plans, ["a"]) == {"x"}
    assert optimal_next_actions(plans, ["b", "y"]) == {None}
    with unittest.TestCase().assertRaises(ValueError):
        optimal_next_actions(plans, ["a", "y"])


def test_single_positive_is_cross_entropy():
    logits = torch.tensor([[1.0, -1.0, 0.5]], requires_grad=True)
    mask = torch.ones_like(logits, dtype=torch.bool)
    positive = torch.tensor([[False, True, False]])
    expected = torch.nn.functional.cross_entropy(logits, torch.tensor([1]))
    torch.testing.assert_close(positive_set_nll(logits, mask, positive), expected)


def test_two_equal_positives_receive_two_thirds_probability():
    logits = torch.zeros(1, 3, requires_grad=True)
    mask = torch.ones_like(logits, dtype=torch.bool)
    positive = torch.tensor([[True, True, False]])
    loss = positive_set_nll(logits, mask, positive)
    torch.testing.assert_close(loss, -torch.log(torch.tensor(2.0 / 3.0)))
    loss.backward()
    torch.testing.assert_close(logits.grad, torch.tensor([[-1/6, -1/6, 1/3]]))


def test_all_accepted_has_zero_loss_and_gradient():
    logits = torch.tensor([[2., -1., 10.]], requires_grad=True)
    mask = torch.tensor([[True, True, False]])
    loss = positive_set_nll(logits, mask, mask)
    loss.backward()
    torch.testing.assert_close(loss, torch.tensor(0.))
    torch.testing.assert_close(logits.grad, torch.zeros_like(logits))


def test_permuting_actions_preserves_loss():
    logits = torch.tensor([[0.5, 2., 1.]])
    allowed = torch.tensor([[True, True, False]])
    good = torch.tensor([[False, True, False]])
    permutation = [2, 0, 1]
    torch.testing.assert_close(positive_set_nll(logits, allowed, good),
                               positive_set_nll(logits[:, permutation], allowed[:, permutation], good[:, permutation]))


def test_invalid_target_and_nan_fail_before_training():
    with unittest.TestCase().assertRaises(ValueError):
        positive_set_nll(torch.zeros(1, 2), torch.tensor([[True, False]]), torch.tensor([[False, True]]))
    with unittest.TestCase().assertRaises(FloatingPointError):
        positive_set_nll(torch.tensor([[float('nan')]]), torch.ones(1, 1, dtype=torch.bool), torch.ones(1, 1, dtype=torch.bool))
