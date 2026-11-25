"""Analytic objective and candidate-integrity tests; no fitted outputs as truth."""
from pathlib import Path
import copy
import math
import sys
import unittest

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from constraint_alignment import AlignmentHead, alignment_loss
from constraint_alignment_data import make_group, predicate_key, record_text, selected_groups
import trust_env as env


def test_zero_scores_analytic_losses():
    # E and I share record0; N matches record1. Direct softmax calculations.
    score = torch.zeros(3, 2, requires_grad=True)
    allowed = torch.ones_like(score, dtype=torch.bool)
    positive = torch.tensor([[True, False], [True, False], [False, True]])
    for arm in ("bce", "rank"):
        torch.testing.assert_close(alignment_loss(score, allowed, positive, arm), torch.tensor(math.log(2)))
    expected = 0.5 * (math.log(2) + (math.log(1.5) + math.log(3)) / 2)
    torch.testing.assert_close(alignment_loss(score, allowed, positive, "contrastive"), torch.tensor(expected))


def test_negative_only_columns_are_not_given_fake_reverse_positives():
    # Three choices, each query has one correct, last column is negative-only.
    score = torch.zeros(2, 3, requires_grad=True)
    allowed = torch.ones_like(score, dtype=torch.bool)
    positive = torch.tensor([[True, False, False], [False, True, False]])
    loss = alignment_loss(score, allowed, positive, "contrastive")
    torch.testing.assert_close(loss, torch.tensor((math.log(3) + math.log(2)) / 2))
    loss.backward()
    assert torch.isfinite(score.grad).all() and (score.grad[:, 2] > 0).all()


def test_other_task_scores_do_not_create_negatives_or_gradients():
    # Two 1-query tasks, each has one positive and one negative.
    scores = torch.tensor([[0., 1., 100., 200.], [300., 400., 0., 1.]], requires_grad=True)
    allowed = torch.tensor([[1, 1, 0, 0], [0, 0, 1, 1]], dtype=torch.bool)
    positive = torch.tensor([[1, 0, 0, 0], [0, 0, 1, 0]], dtype=torch.bool)
    for kind in ("bce", "rank", "contrastive"):
        loss = alignment_loss(scores, allowed, positive, kind)
        changed = scores.detach().clone()
        changed[~allowed] = -999
        torch.testing.assert_close(loss, alignment_loss(changed, allowed, positive, kind))
        grad, = torch.autograd.grad(loss, scores)
        assert (grad[~allowed] == 0).all()


def test_both_towers_receive_finite_gradients():
    torch.manual_seed(0)
    model = AlignmentHead(4, 6, 3)
    scores = model(torch.eye(4)[:2], torch.eye(4)[:3])
    p = torch.tensor([[1, 0, 0], [0, 1, 0]], dtype=torch.bool)
    alignment_loss(scores, torch.ones_like(p), p, "contrastive").backward()
    for tower in (model.query, model.record):
        assert all(v.grad is not None and torch.isfinite(v.grad).all() for v in tower.parameters())
        assert sum(float(v.grad.abs().sum()) for v in tower.parameters()) > 0


def test_invalid_and_nonfinite_fail_closed():
    s = torch.tensor([[float('nan'), 0.]])
    m = torch.ones_like(s, dtype=torch.bool)
    p = torch.tensor([[True, False]])
    with unittest.TestCase().assertRaises(FloatingPointError):
        alignment_loss(s, m, p, "contrastive")
    with unittest.TestCase().assertRaises(ValueError):
        alignment_loss(torch.zeros_like(s), m, torch.zeros_like(m), "bce")


def test_predicate_equivalence_not_string_equality():
    # Frozen checker implements both order and tool_auth as the same predicate.
    task = {"tools": {"a": {}, "b": {}}}
    a = {"type": "order", "params": {"before_role": "a", "after_role": "b"}}
    b = {"type": "tool_auth", "params": {"approval_role": "a", "required_role": "b"}}
    assert predicate_key([a, a], task, env.normalize_constraint) == predicate_key([b], task, env.normalize_constraint)
    reverse = {"type": "order", "params": {"before_role": "b", "after_role": "a"}}
    assert predicate_key([a], task, env.normalize_constraint) != predicate_key([reverse], task, env.normalize_constraint)


def test_features_cannot_read_gold_evidence_or_annotation_metadata():
    c = {"type": "budget", "params": {"max_total_cost_cny": 100}}
    text = record_text([c], [])
    dirty = copy.deepcopy(c)
    dirty.update(evidence_span="secret gold span", severity="high", state="implicit", witness_plan=["x"])
    assert text == record_text([dirty], [])
    assert text == "Constraint record: Total cost at most 100 CNY."


def test_group_selection_retains_all_three_variants():
    rows = [{"group_id": g, "variant": v, "task": {}, "catalog": []}
            for g in ("a", "b", "c") for v in ("explicit", "implicit", "none")]
    selected = selected_groups(rows, 2)
    assert len(selected) == 2 and all(len(g) == 3 for g in selected)
    assert selected_groups(list(reversed(rows)), 2) == selected
    with unittest.TestCase().assertRaises(ValueError):
        selected_groups(rows[:-1], 3)


def test_behaviorally_identical_numeric_mutations_are_not_false_negatives():
    # Independently enumerated costs {50,250}: caps100/200 agree everywhere;
    # cap0 differs. Gold cap100 and empty are distinct on the cost250 trace.
    task = {"tools": {}}
    budget = {"type": "budget", "params": {"max_total_cost_cny": 100}}
    rows = [{"variant": v, "group_id": "g", "query": "request", "catalog": [], "task": task,
             "gold": {"constraints": [] if v == "none" else [budget]}}
            for v in ("explicit", "implicit", "none")]
    domain = [(["cheap"], {"cost": 50}, 0), (["expensive"], {"cost": 250}, 1)]
    group = make_group(rows, env, lambda task, engine: domain)
    assert group["audit"]["excluded"]["different_predicate_but_same_domain_behavior"] == 1
    assert len(group["candidates"]) == 3
    for candidate in group["candidates"]:
        if candidate["kind"] == "numeric_bound":
            assert candidate["constraints"][0]["params"]["max_total_cost_cny"] == 0
            assert len(candidate["distinguishing_plans"]) == 3


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test()
    print(f"{len(tests)} alignment tests passed")
