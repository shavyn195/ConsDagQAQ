"""Matched objectives for a frozen-encoder alignment feasibility experiment.

CLIP-inspired symmetric mass-on-positives objective; not a CLIP reproduction.
Cross-task pairs are masked. Candidate-only negatives participate in query to
record, but cannot invent a positive query for the reverse direction.
"""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class AlignmentHead(nn.Module):
    def __init__(self, dim: int, hidden: int = 256, projection: int = 128, temperature: float = 0.1):
        super().__init__()
        if temperature <= 0:
            raise ValueError("Temperature must be positive")
        self.query = nn.Sequential(nn.Linear(dim, hidden), nn.GELU(), nn.Linear(hidden, projection))
        self.record = nn.Sequential(nn.Linear(dim, hidden), nn.GELU(), nn.Linear(hidden, projection))
        self.temperature = temperature

    def forward(self, queries: torch.Tensor, records: torch.Tensor) -> torch.Tensor:
        q = F.normalize(self.query(queries), dim=-1)
        r = F.normalize(self.record(records), dim=-1)
        return q @ r.T / self.temperature


def alignment_loss(scores: torch.Tensor, allowed: torch.Tensor, positive: torch.Tensor, kind: str) -> torch.Tensor:
    if scores.ndim != 2 or scores.shape != allowed.shape or scores.shape != positive.shape:
        raise ValueError("Expected matching matrix shapes")
    if allowed.dtype != torch.bool or positive.dtype != torch.bool:
        raise ValueError("Masks must be boolean")
    if (positive & ~allowed).any() or not positive.any(1).all():
        raise ValueError("Positive missing or outside allowed set")
    negative = allowed & ~positive
    if not negative.any(1).all():
        raise ValueError("Every query requires a negative")
    if not torch.isfinite(scores[allowed]).all():
        raise FloatingPointError("Non-finite alignment score")

    def mean_mask(values, mask):
        return (values.masked_fill(~mask, 0).sum(1) / mask.sum(1)).mean()

    if kind == "bce":
        return 0.5 * (mean_mask(F.softplus(-scores), positive) + mean_mask(F.softplus(scores), negative))
    if kind == "rank":
        losses = [F.softplus(row[n][:, None] - row[p][None, :]).mean()
                  for row, p, n in zip(scores, positive, negative)]
        return torch.stack(losses).mean()
    if kind == "contrastive":
        full = scores.masked_fill(~allowed, -torch.inf)
        good = scores.masked_fill(~positive, -torch.inf)
        forward = (full.logsumexp(1) - good.logsumexp(1)).mean()
        columns = positive.any(0)
        backward = (full[:, columns].logsumexp(0) - good[:, columns].logsumexp(0)).mean()
        return (forward + backward) / 2
    raise ValueError(f"Unknown objective: {kind}")
