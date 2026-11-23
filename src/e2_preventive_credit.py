"""A train-only intervention: credit an emitted action if removing/replacing it
preserves strict task completion but newly violates exactly one predicted rule."""
from collections import defaultdict
import statistics

from audit_warmup_rollouts import shape
from e2_credit import advantages as negative_credit, score_plan
from trust_env import check


def score_with_prevention(task, acts, constraints):
    s = score_plan(task, acts, constraints)
    traces = defaultdict(set)
    if s["done"] and constraints:
        base = set(s["bad"])
        for j, a in enumerate(acts):
            candidates = []
            if a in task["optional"]:
                candidates.append(acts[:j] + acts[j+1:])
            for stage in task["stages"]:
                if a in stage["alternatives"]:
                    candidates.extend(acts[:j]+[b]+acts[j+1:] for b in stage["alternatives"] if b != a)
            for other in candidates:
                if not shape(other,task):
                    continue
                cf = check(task,other,constraints)
                bad = set(cf["violations"])
                delta = bad-base
                if cf["completed"] and base <= bad and len(delta)==1:
                    traces[next(iter(delta))].add(j)
    # Multiple possible responsible positions are insufficient for unique binding.
    s["protect"] = {i:next(iter(js)) for i,js in traces.items() if len(js)==1}
    return s


def preventive_advantages(scores,lengths,maps,n_constraints,arm):
    if arm not in ("protect","protect_shifted"):
        raise ValueError(arm)
    rewards, av, negative_moves = negative_credit(scores,lengths,maps,n_constraints,"action")
    denom = max(statistics.pstdev(rewards),.25)*max(n_constraints,1)
    for s,length,mapping,v in zip(scores,lengths,maps,av,strict=True):
        for i,j in s["protect"].items():
            ix = mapping.get(j,[])
            # A sampled completed sibling must actually violate this same rule.
            hits = sum(t["done"] and i in t["bad"] for t in scores)
            if not hits or not ix:
                continue
            w = hits/len(scores)/denom
            before = sum(v)
            for k in range(length):
                v[k] -= w
            for k in ix:
                z = (k+max(1,length//2))%length if arm=="protect_shifted" else k
                v[z] += w*length/len(ix)
            if abs(sum(v)-before)>1e-6:
                raise ArithmeticError("preventive credit changed total trajectory credit")
    # Retain the existing driver's negative-relocations counter; positive moves are
    # reconstructed from its saved protect map, group outcomes, token maps and counts.
    return rewards,av,negative_moves
