"""Gold-candidate *development diagnostic*, never deployment candidate generation.

Public model features are request text and candidate predicates rendered with
public catalog names. Gold records construct candidates and labels only. E/I/N
share a pool, preventing candidate construction from revealing query state.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from typing import Callable


def predicate_key(constraints: list[dict], task: dict, normalize: Callable) -> tuple:
    result = set()
    for item in constraints:
        n = normalize(item, task)
        if n is None:
            raise ValueError("Unusable candidate predicate")
        t = n["type"]
        if t in ("order", "tool_auth"):
            key = ("precedence", n["first"], n["second"])
        elif t == "budget":
            key = (t, n["limit"])
        elif t == "deadline":
            key = (t, n["minutes"])
        elif t == "privacy":
            key = (t, tuple(sorted(n["classes"])))
        else:
            raise ValueError(t)
        result.add(key)
    return tuple(sorted(result))


def record_text(constraints: list[dict], catalog: list[dict]) -> str:
    """No evidence_span/state/severity, sample ID, label, witness or task costs."""
    names = {c["role"]: c["name"] for c in catalog}
    parts = []
    for c in constraints:
        t, p = c["type"], c["params"]
        if t == "budget":
            text = f"Total cost at most {p['max_total_cost_cny']:g} CNY."
        elif t == "deadline":
            text = f"Total duration at most {p['max_duration_hours']:g} hours."
        elif t == "privacy":
            text = "Do not send " + ", ".join(sorted(p["protected_data_classes"])) + " to external recipients."
        else:
            a, b = (("approval_role", "required_role") if t == "tool_auth" else ("before_role", "after_role"))
            text = f"If {names[p[b]]} is used, {names[p[a]]} must run before it."
        parts.append(text)
    return "Constraint record: " + (" ".join(parts) if parts else "No additional constraints.")


def proposals(base: list[dict], catalog: list[dict]) -> list[tuple[str, list[dict]]]:
    """One-local-change candidates. No claim each changes the optimal plan."""
    out = [("reference", copy.deepcopy(base)), ("empty", [])]
    roles = sorted(c["role"] for c in catalog)
    for i, c in enumerate(base):
        out.append(("omit_one", copy.deepcopy(base[:i] + base[i + 1:])))
        t, params = c["type"], c["params"]
        mutations = []
        if t in ("budget", "deadline"):
            key, delta = ("max_total_cost_cny", 100) if t == "budget" else ("max_duration_hours", 1)
            for value in (params[key] - delta, params[key] + delta):
                if value >= 0:
                    mutations.append(("numeric_bound", {**params, key: value}))
        elif t in ("order", "tool_auth"):
            a, b = (("approval_role", "required_role") if t == "tool_auth" else ("before_role", "after_role"))
            mutations.append(("reverse_binding", {a: params[b], b: params[a]}))
            alternatives = [r for r in roles if r not in (params[a], params[b])]
            for key in (a, b):
                for role in alternatives[:2]:
                    mutations.append(("replace_binding", {**params, key: role}))
        elif t == "privacy":
            for cls in ("customer_pii", "employee_pii", "patient_records"):
                if cls not in params["protected_data_classes"]:
                    mutations.append(("data_class", {**params, "protected_data_classes": [cls]}))
        for kind, p in mutations:
            new = copy.deepcopy(base)
            new[i]["params"] = p
            out.append((kind, new))
    return out


def selected_groups(rows: list[dict], limit: int) -> list[list[dict]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["group_id"]].append(row)
    ids = sorted(grouped, key=lambda s: hashlib.sha256(s.encode()).hexdigest())[:limit]
    result = []
    for gid in ids:
        group = sorted(grouped[gid], key=lambda r: r["variant"])
        if len(group) != 3 or {r["variant"] for r in group} != {"explicit", "implicit", "none"}:
            raise ValueError(f"Incomplete E/I/N group: {gid}")
        if any(r["task"] != group[0]["task"] or r["catalog"] != group[0]["catalog"] for r in group):
            raise ValueError(f"E/I/N public worlds differ: {gid}")
        result.append(group)
    return result


def make_group(rows: list[dict], env, enumerate_plans: Callable) -> dict:
    task, catalog = rows[0]["task"], rows[0]["catalog"]
    base = next(r["gold"]["constraints"] for r in rows if r["variant"] == "explicit")
    keys = [predicate_key(r["gold"]["constraints"], task, env.normalize_constraint) for r in rows]
    if keys[0] != keys[1] or keys[2] != ():
        raise ValueError("Expected E/I identical predicates and N empty")
    domain = enumerate_plans(task, env)

    def truth(record):
        norms = [env.normalize_constraint(c, task) for c in record]
        if any(n is None for n in norms):
            raise ValueError("Invalid candidate")
        return tuple(not any(env.violated(n, trace) for n in norms) for _, trace, _ in domain)

    refs = {k: truth(r["gold"]["constraints"]) for k, r in zip(keys, rows)}
    candidates, seen, excluded = [], set(), defaultdict(int)
    for kind, record in proposals(base, catalog):
        key = predicate_key(record, task, env.normalize_constraint)
        values = truth(record)
        if key not in refs and values in refs.values():
            excluded["different_predicate_but_same_domain_behavior"] += 1
            continue
        # Reordered serializations are added symmetrically to ALL records.
        for ordered in (record, list(reversed(record))):
            text = record_text(ordered, catalog)
            if text in seen:
                continue
            seen.add(text)
            witnesses = {}
            for ri, ref in enumerate(keys):
                if key != ref:
                    index = next((j for j, (a, b) in enumerate(zip(values, refs[ref])) if a != b), None)
                    if index is None:
                        raise ValueError("Negative has no distinguishing execution witness")
                    witnesses[str(ri)] = domain[index][0]
            candidates.append({"text": text, "constraints": ordered, "key": key, "kind": kind,
                               "distinguishing_plans": witnesses})
    # Candidate order must not expose which record was generated first.
    candidates.sort(key=lambda c: hashlib.sha256((rows[0]["group_id"] + c["text"]).encode()).hexdigest())
    positive = [[c["key"] == key for c in candidates] for key in keys]
    if not all(any(p) and not all(p) for p in positive):
        raise ValueError("Every query must have positives AND negatives")
    return {"group_id": rows[0]["group_id"], "rows": rows, "candidates": candidates,
            "queries": ["User request: " + r["query"] for r in rows], "positive": positive,
            "audit": {"domain_plans": len(domain), "excluded": dict(excluded)}}
