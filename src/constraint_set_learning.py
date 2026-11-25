"""Set-valued supervision primitives for the architecture feasibility study.

These utilities do not define a new policy or change the frozen evaluator.
Targets come from training-only optimal-plan sets, never test-time gold rules.
"""
from __future__ import annotations

from collections.abc import Sequence

import torch


def optimal_next_actions(plans: Sequence[Sequence[str]], prefix: Sequence[str]) -> frozenset[str | None]:
    """Return supported next actions conditioned on the *whole* given prefix.

    None denotes EOS. Marginals from incompatible complete solutions must not
    be combined: the corresponding hybrid plan need not be feasible.
    An off-support prefix needs a separate recovery oracle, not a fake label.
    """
    position = len(prefix)
    result = set()
    for plan in plans:
        if len(plan) >= position and tuple(plan[:position]) == tuple(prefix):
            result.add(plan[position] if len(plan) > position else None)
    if not result:
        raise ValueError("Prefix has no optimal continuation in the supplied teacher set")
    return frozenset(result)


def positive_set_nll(logits: torch.Tensor, allowed: torch.Tensor, positive: torch.Tensor) -> torch.Tensor:
    """Mean -log probability mass on the accepted next-action set.

    For one positive this equals masked cross entropy; for every allowed
    action positive the loss is zero. The objective optimizes acceptance of
    any correct next action, not uniform coverage of all correct solutions.
    """
    if logits.ndim != 2 or logits.shape != allowed.shape or logits.shape != positive.shape:
        raise ValueError("Expected equal [batch, actions] tensor shapes")
    if allowed.dtype != torch.bool or positive.dtype != torch.bool:
        raise ValueError("Action masks must be boolean")
    if not allowed.any(dim=1).all() or not positive.any(dim=1).all():
        raise ValueError("Every row needs at least one allowed and one positive action")
    if (positive & ~allowed).any():
        raise ValueError("Positive action excluded by structural decoder mask")
    if not torch.isfinite(logits[allowed]).all():
        raise FloatingPointError("Non-finite allowed-action logits")
    full = logits.masked_fill(~allowed, -torch.inf)
    good = logits.masked_fill(~positive, -torch.inf)
    return (torch.logsumexp(full, dim=1) - torch.logsumexp(good, dim=1)).mean()
