"""Matched sequence- and action-level relative credit for a small E2 pilot."""
import json
import math
import re
import statistics

from trust_env import check, execute, normalize_constraint
from audit_warmup_rollouts import shape


def score_plan(task, acts, constraints):
    done = bool(acts and shape(acts, task) and check(task, acts, [])["completed"])
    bad = check(task, acts, constraints)["violations"] if done else []
    loc = {}
    for i in bad:
        n = normalize_constraint(constraints[i], task)
        # Only bind a single, independently identifiable breach to a tool.
        if n["type"] in ("tool_auth", "order"):
            loc[i] = acts.index(n["second"])
        elif n["type"] == "privacy":
            hits = [j for j, cls in execute(task, acts)["leaks"] if cls in n["classes"]]
            if len(hits) == 1:
                loc[i] = hits[0]
    return {"done": done, "bad": bad, "loc": loc}


def role_tokens(tok, ids, acts):
    if not acts:
        return {}
    raw = tok.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    # Re-encoding can canonicalize generated token boundaries. Require exact replay.
    rendered = tok(raw, add_special_tokens=False, return_offsets_mapping=True)
    clean = [t for t in ids if t not in tok.all_special_ids]
    if rendered.input_ids != clean or ids[:len(clean)] != clean:
        return {}
    matches = list(re.finditer(r'"(?:[^"\\]|\\.)*"', raw))
    if [json.loads(m.group()) for m in matches] != acts:
        return {}
    return {i: [k for k,(lo,hi) in enumerate(rendered.offset_mapping)
                if lo < m.end()-1 and hi > m.start()+1] for i,m in enumerate(matches)}


def advantages(scores, lengths, maps, n_constraints, arm):
    # All non-vanilla arms use the same externally gated sequence score.
    nc = max(n_constraints, 1)
    rewards = [float(s["done"]) * (1 if arm == "function" else
               1 + (1 - len(s["bad"])/nc if n_constraints else 0)) for s in scores]
    center = statistics.mean(rewards)
    scale = max(statistics.pstdev(rewards), 0.25)
    vectors, moved = [], 0
    for s, length, mapping, reward in zip(scores, lengths, maps, rewards, strict=True):
        seq = (reward-center)/scale
        adv = [seq]*length
        if arm in ("action", "shifted"):
            for i, a in s["loc"].items():
                inds = mapping.get(a, [])
                if not inds:
                    continue
                # Move only the group-relative share of an incurred violation.
                rate = sum(i in obs["bad"] for obs in scores)/len(scores)
                penalty = -(1-rate)/(nc*scale)
                if not penalty:
                    continue
                if arm == "shifted":
                    inds = [(k+max(1,length//2))%length for k in inds]
                adv = [v-penalty for v in adv]
                for k in inds:
                    adv[k] += penalty*length/len(inds)
                moved += 1
        if not math.isclose(statistics.mean(adv), seq, abs_tol=1e-7):
            raise ArithmeticError("localization changed sequence credit")
        vectors.append(adv)
    return rewards, vectors, moved
