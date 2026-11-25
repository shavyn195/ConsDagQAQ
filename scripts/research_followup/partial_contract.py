"""Controlled partial-contract semantics; NOT a general NL safety certificate."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from run_e1 import prediction_is_well_formed
from trust_env import execute, normalize_constraint, plan_change_count, violated


def split_contract(raw: str, task: dict[str, Any]) -> dict[str, Any]:
    """Retain well-typed clauses and explicit unknowns; never repair invalid JSON."""
    result: dict[str, Any] = dict(known=[], unknown=[], envelope_valid=False)
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        result['unknown'].append(dict(index=None, raw=raw, reason='invalid_json'))
        return result
    if (not isinstance(value, dict) or value.get('query_state') not in ('explicit', 'implicit', 'none')
            or not isinstance(value.get('constraints'), list)):
        result['unknown'].append(dict(index=None, raw=value, reason='invalid_envelope'))
        return result
    result['envelope_valid'] = True
    for i, clause in enumerate(value['constraints']):
        schema_ok = prediction_is_well_formed(dict(query_state=value['query_state'], constraints=[clause]))
        norm = normalize_constraint(clause, task) if schema_ok else None
        if norm is None:
            result['unknown'].append(dict(index=i, raw=clause,
                                          reason='unresolved_binding' if schema_ok else 'invalid_clause_schema'))
        else:
            result['known'].append(dict(index=i, raw=clause, norm=norm))
    return result


def finite_completions(unknown: dict[str, Any], task: dict[str, Any], *, cap: int = 128) -> list[dict[str, Any]] | None:
    """Conditional domain: only the first role is corrupted; all other fields trusted.

    None means unsupported/unbounded, not an empty conjunction or a safe clause.
    The generic compiler cannot establish this single-field assumption by itself.
    """
    if unknown['reason'] != 'unresolved_binding':
        return None
    clause = unknown['raw']
    keys = {'order': ('before_role', 'after_role'), 'tool_auth': ('approval_role', 'required_role')}
    if clause['type'] not in keys:
        return None
    first_key, second_key = keys[clause['type']]
    params = clause['params']
    role = lambda v: v.removeprefix('role:').strip() if isinstance(v, str) else None
    first, second = role(params.get(first_key)), role(params.get(second_key))
    if first in task['tools'] or second not in task['tools']:
        return None
    possibilities = sorted(r for r in task['tools'] if r != second)
    if not possibilities or len(possibilities) > cap:
        return None
    results = []
    for r in possibilities:
        candidate = deepcopy(clause)
        candidate['params'][first_key] = r
        norm = normalize_constraint(candidate, task)
        if norm is None:
            return None
        results.append(norm)
    return results


def legal(task: dict[str, Any], candidate: list[str]) -> bool:
    try:
        plan_change_count(task, candidate)
        return True
    except (ValueError, TypeError):
        return False


def norm_key(norm: dict[str, Any]) -> str:
    return json.dumps({k: sorted(v) if isinstance(v, set) else v for k, v in norm.items()}, sort_keys=True)


def evaluate_policies(task: dict[str, Any], original: list[str], proposal: list[str], raws: list[str]) -> dict[str, Any]:
    """Decisions only receive public task, fixed plans, and compiler outputs."""
    views = [split_contract(raw, task) for raw in raws]
    full = [v for v in views if v['envelope_valid'] and not v['unknown']]
    partial = [v for v in views if v['envelope_valid']]
    old_trace, new_trace = execute(task, original), execute(task, proposal)
    calls = 0

    def bad(norm, trace):
        nonlocal calls
        calls += 1
        return violated(norm, trace)

    def rank(candidate, trace, view):
        if not legal(task, candidate):
            return (1, 1, 0, 0)
        return (0, int(not trace['completed']), sum(bad(c['norm'], trace) for c in view['known']),
                plan_change_count(task, candidate))

    def effect(vs):
        if len(vs) < 2:
            return False
        pairs = [(rank(original, old_trace, v), rank(proposal, new_trace, v)) for v in vs]
        return all(n <= o for o, n in pairs) and any(n < o for o, n in pairs)

    def satisfies(vs, candidate, trace):
        return len(vs) >= 2 and legal(task, candidate) and all(
            not bad(c['norm'], trace) for v in vs for c in v['known'])

    unknown_checks = []
    for i, view in enumerate(views):
        for unknown in view['unknown']:
            completions = finite_completions(unknown, task)
            pairs = [(bad(n, old_trace), bad(n, new_trace)) for n in completions] if completions is not None else None
            unknown_checks.append(dict(view=i, index=unknown['index'], raw=unknown['raw'], reason=unknown['reason'],
                completions=completions, before_after=pairs,
                nonregressing=pairs is not None and all(n <= o for o, n in pairs),
                original_all_satisfied=pairs is not None and all(not o for o, _ in pairs),
                proposal_all_satisfied=pairs is not None and all(not n for _, n in pairs)))
    signatures = [tuple(sorted({norm_key(c['norm']) for c in v['known']})) for v in full]
    accept_full = effect(full)
    accept_partial = effect(partial)
    accepted = dict(whole_record=accept_full,
                    whole_agreement=len(full) >= 2 and len(set(signatures)) == 1 and satisfies(full, proposal, new_trace),
                    row_drop_unknown=accept_partial, row_defer=accept_partial,
                    row_robust=accept_partial and all(u['nonregressing'] for u in unknown_checks))
    decisions = {}
    for name, accept in accepted.items():
        candidate, trace = (proposal, new_trace) if accept else (original, old_trace)
        vs = full if name.startswith('whole_') else partial
        released = satisfies(vs, candidate, trace)
        if name == 'row_defer':
            released = released and not unknown_checks
        elif name == 'row_robust':
            released = released and all(u['proposal_all_satisfied' if accept else 'original_all_satisfied'] for u in unknown_checks)
        decisions[name] = dict(accepted=bool(accept), edited=bool(accept and original != proposal),
                               released=bool(released), selected_plan=candidate)
    return dict(decisions=decisions, full_views=len(full), partial_views=len(partial),
                known_clause_counts=[len(v['known']) for v in views],
                unknown_checks=unknown_checks, predicate_checks=calls)
