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


def teacher_prefixes(plans: Sequence[Sequence[str]], representative: Sequence[str], *,
                     coverage: str = "representative") -> list[tuple[tuple[str, ...], str | None]]:
    """Shared input states and a valid deterministic single target per state.

    All-optimal coverage is a baseline for non-deterministic oracle learning,
    not a new objective. Preserve the representative next action wherever
    that representative supports the prefix. Else use the lexicographically
    first complete accepted continuation. Never splice independent marginals.
    """
    accepted = sorted({tuple(plan) for plan in plans})
    representative = tuple(representative)
    if representative not in accepted:
        raise ValueError("Representative must be a complete accepted plan")
    if coverage == "representative":
        prefixes = [representative[:k] for k in range(len(representative) + 1)]
    elif coverage == "all_optimal":
        prefixes = sorted({plan[:k] for plan in accepted for k in range(len(plan) + 1)},
                          key=lambda prefix: (len(prefix), prefix))
    else:
        raise ValueError(f"Unknown training prefix coverage: {coverage}")
    result = []
    for prefix in prefixes:
        k = len(prefix)
        if k <= len(representative) and representative[:k] == prefix:
            target_plan = representative
        else:
            target_plan = next(plan for plan in accepted if len(plan) >= k and plan[:k] == prefix)
        action = target_plan[k] if k < len(target_plan) else None
        result.append((prefix, action))
    return result


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
