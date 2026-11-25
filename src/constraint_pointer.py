"""Small controlled graph/dense pointer policy for oracle-record experiments.

The graph and dense policies have identical parameters and inputs. They differ
only in whether attention to relation-free node pairs is masked. Neither the
graph nor the structural action mask calls a solver or receives future labels.
This is a pilot implementation, not a general DAG optimizer or safety proof.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import torch
from torch import nn

import trust_env as env

NUM_FEATURES = 24
NUM_RELATIONS = 10
PREDICATE_TEXT = {
    "budget": "Limit the total monetary cost of the workflow.",
    "deadline": "Limit the total sequential duration of the workflow.",
    "privacy": "Do not send protected data to external recipients.",
    "tool_auth": "If the target tool is used, its approval tool must precede it.",
    "order": "If the second tool is used, the first tool must precede it.",
}


@dataclass
class PolicyInput:
    texts: list[str]
    numbers: torch.Tensor
    relations: torch.Tensor
    allowed: torch.Tensor
    actions: list[str | None]


def structural_actions(task: dict, prefix: list[str]) -> set[str | None]:
    """Structure only: exactly one tool/stage, ordered stages, finish last.

    Optional tools remain possible irrespective of constraints. This admits
    unnecessary edits and unsafe choices, which evaluation must penalize.
    """
    if len(set(prefix)) != len(prefix) or any(r not in task["tools"] for r in prefix):
        raise ValueError("Duplicate or unknown tool in prefix")
    seen = set(prefix)
    completed_stages = 0
    previous_position = -1
    for stage in task["stages"]:
        hits = [r for r in stage["alternatives"] if r in seen]
        if len(hits) > 1:
            raise ValueError("More than one alternative from a stage")
        if hits:
            if completed_stages != task["stages"].index(stage):
                raise ValueError("Skipped an earlier stage")
            position = prefix.index(hits[0])
            if position <= previous_position:
                raise ValueError("Stages out of order")
            previous_position = position
            completed_stages += 1
    if any(r in seen for r in task["finish"]):
        if completed_stages != len(task["stages"]) or any(
            prefix.index(r) <= previous_position for r in task["finish"] if r in seen
        ):
            raise ValueError("Finish tools must follow all stages")
    allowed = set(task["optional"]) - seen
    if completed_stages < len(task["stages"]):
        allowed.update(task["stages"][completed_stages]["alternatives"])
    else:
        allowed.update(set(task["finish"]) - seen)
        if set(task["finish"]) <= seen:
            allowed.add(None)
    return allowed


def policy_input(task: dict, constraints: list[dict], prefix: list[str]) -> PolicyInput:
    norms = [env.normalize_constraint(c, task) for c in constraints]
    if any(n is None for n in norms):
        raise ValueError("Malformed record cannot become an empty record")
    roles = list(task["catalog"])
    if set(roles) != set(task["tools"]) or len(roles) != len(set(roles)):
        raise ValueError("Catalog and public tool specs disagree")
    descriptions = task.get("tool_descriptions", {})
    texts = ["Current execution state and end of workflow."]
    texts += [descriptions.get(r, r.replace("_", " ")) for r in roles]
    texts += ["Workflow stage " + s.get("stage", "unspecified") for s in task["stages"]]
    texts += [PREDICATE_TEXT[n["type"]] for n in norms]
    n = len(texts)
    numbers = torch.zeros(n, NUM_FEATURES)
    relations = torch.zeros(n, n, dtype=torch.long)
    relations.fill_diagonal_(1)
    relations[0, 1:] = 8
    relations[1:, 0] = 9
    numbers[0, 3] = 1
    trace = env.execute(task, prefix)
    numbers[0, 8:10] = torch.tensor([trace["cost"] / 1000, trace["minutes"] / 1000])
    numbers[0, 14] = len(prefix) / max(1, len(roles))
    # Reconstruct public data state; no gold plan is consulted.
    active = False
    for role in prefix:
        if role in task["stages"][0]["alternatives"] and task.get("data_class"):
            active = True
        if task["tools"][role]["clears_pii"]:
            active = False
    numbers[0, 10] = float(active)
    index = {r: i + 1 for i, r in enumerate(roles)}
    for r, i in index.items():
        spec = task["tools"][r]
        numbers[i, 0] = 1
        numbers[i, 5] = float(r in task["optional"])
        numbers[i, 6] = (task["finish"].index(r) + 1) / 10 if r in task["finish"] else 0
        numbers[i, 8:12] = torch.tensor([spec["cost_cny"] / 1000, spec["duration_min"] / 1000,
                                         float(spec["recipient"] == "external"), float(spec["clears_pii"])])
        numbers[i, 12] = float(r in prefix)
        numbers[i, 13] = (prefix.index(r) + 1) / len(roles) if r in prefix else 0
    for j, stage in enumerate(task["stages"]):
        si = 1 + len(roles) + j
        numbers[si, 2] = 1
        numbers[si, 7] = (j + 1) / 10
        for r in stage["alternatives"]:
            i = index[r]
            numbers[i, 7] = (j + 1) / 10
            numbers[i, 4] = float(r == stage["default"])
            relations[si, i] = 2
            relations[i, si] = 3
        if j:
            relations[si - 1, si] = 4
            relations[si, si - 1] = 5
    for r, targets in task["optional"].items():
        for target in (task["stages"][0]["alternatives"] if targets == ["@acquire"] else targets):
            relations[index[r], index[target]] = 4
            relations[index[target], index[r]] = 5
    for j, norm in enumerate(norms):
        ci = 1 + len(roles) + len(task["stages"]) + j
        numbers[ci, 1] = 1
        ctype = norm["type"]
        numbers[ci, 15 + env.CONSTRAINT_TYPES.index(ctype)] = 1
        if ctype in ("budget", "deadline"):
            limit = norm["limit"] if ctype == "budget" else norm["minutes"]
            spent = trace["cost"] if ctype == "budget" else trace["minutes"]
            numbers[ci, 20] = limit / 1000
            numbers[ci, 22] = (limit - spent) / 1000
            bound = roles
        elif ctype == "privacy":
            numbers[ci, 21] = float(task.get("data_class") in norm["classes"])
            bound = roles
        else:
            bound = [norm["first"], norm["second"]]
            numbers[ci, 22] = float(norm["first"] in prefix)
            numbers[ci, 23] = float(norm["second"] in prefix)
        for r in bound:
            relations[ci, index[r]] = 6
            relations[index[r], ci] = 7
        if ctype in ("tool_auth", "order"):
            # Directed binding distinguishes first from second, also visible
            # to the dense baseline as its identical relation-bias tensor.
            relations[ci, index[norm["first"]]] = 4
            relations[ci, index[norm["second"]]] = 5
    allowed_actions = structural_actions(task, prefix)
    actions = [None] + roles
    allowed = torch.tensor([a in allowed_actions for a in actions] + [False] * (n - len(actions)))
    if not torch.isfinite(numbers).all():
        raise FloatingPointError("Non-finite public numeric feature")
    return PolicyInput(texts, numbers, relations, allowed, actions)


class RelationAttention(nn.Module):
    def __init__(self, width: int, heads: int, *, graph: bool):
        super().__init__()
        if width % heads:
            raise ValueError("Width must be divisible by heads")
        self.heads, self.width, self.graph = heads, width, graph
        self.qkv = nn.Linear(width, width * 3)
        self.out = nn.Linear(width, width)
        self.bias = nn.Embedding(NUM_RELATIONS, heads)
        self.norm1 = nn.LayerNorm(width)
        self.norm2 = nn.LayerNorm(width)
        self.ff = nn.Sequential(nn.Linear(width, width * 4), nn.GELU(), nn.Linear(width * 4, width))

    def forward(self, x: torch.Tensor, relations: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        b, n, d = x.shape
        q, k, v = self.qkv(self.norm1(x)).reshape(b, n, 3, self.heads, d // self.heads).unbind(2)
        score = torch.einsum("bnhd,bmhd->bhnm", q, k) / math.sqrt(d // self.heads)
        score = score + self.bias(relations).permute(0, 3, 1, 2)
        attend = valid[:, None, :].expand(b, n, n).clone()
        if self.graph:
            attend &= relations != 0
        # Padded query nodes attend only to themselves, avoiding all -inf rows.
        attend = torch.where(valid[:, :, None], attend, torch.eye(n, dtype=torch.bool, device=x.device)[None])
        weights = score.masked_fill(~attend[:, None], -torch.inf).softmax(-1)
        message = torch.einsum("bhnm,bmhd->bnhd", weights, v).reshape(b, n, d)
        x = x + self.out(message)
        return x + self.ff(self.norm2(x))


class ConstraintPointer(nn.Module):
    def __init__(self, text_dim: int, *, width: int = 128, heads: int = 4, layers: int = 2, graph: bool = False):
        super().__init__()
        self.input = nn.Linear(text_dim + NUM_FEATURES, width)
        self.layers = nn.ModuleList(RelationAttention(width, heads, graph=graph) for _ in range(layers))
        self.query = nn.Linear(width, width)
        self.key = nn.Linear(width, width)

    def forward(self, text: torch.Tensor, numbers: torch.Tensor, relations: torch.Tensor, valid: torch.Tensor) -> torch.Tensor:
        x = self.input(torch.cat((text, numbers), dim=-1))
        for layer in self.layers:
            x = layer(x, relations, valid)
        return torch.einsum("bd,bnd->bn", self.query(x[:, 0]), self.key(x)) / math.sqrt(x.shape[-1])


def collate(inputs: list[PolicyInput], embeddings: dict[str, torch.Tensor], *, device: str = "cpu") -> dict:
    n = max(len(x.texts) for x in inputs)
    dim = next(iter(embeddings.values())).numel()
    b = len(inputs)
    text = torch.zeros(b, n, dim)
    numbers = torch.zeros(b, n, NUM_FEATURES)
    relations = torch.zeros(b, n, n, dtype=torch.long)
    valid = torch.zeros(b, n, dtype=torch.bool)
    allowed = torch.zeros(b, n, dtype=torch.bool)
    for j, item in enumerate(inputs):
        m = len(item.texts)
        text[j, :m] = torch.stack([embeddings[t] for t in item.texts])
        numbers[j, :m] = item.numbers
        relations[j, :m, :m] = item.relations
        valid[j, :m] = True
        allowed[j, :m] = item.allowed
    return {k: v.to(device) for k, v in dict(text=text, numbers=numbers, relations=relations,
                                            valid=valid, allowed=allowed).items()}
