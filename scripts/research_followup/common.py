"""Public-only decisions and gold-only scoring for the local planning pilot."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def align(rows, records):
    ids = [r['sample_id'] for r in rows]
    mapped = {r['sample_id']: r for r in records}
    if len(set(ids)) != len(ids) or len(mapped) != len(records) or set(ids) != set(mapped):
        raise ValueError('Missing, extra or duplicate sample IDs')
    return [mapped[sid] for sid in ids]


def public_row(row):
    # Training labels, variants, group IDs and witness are never passed to a model.
    return {k: row[k] for k in ('query', 'catalog', 'task', 'spec_version') if k in row}


def one_edits(task, original):
    """Existing probe_one_edit_repair operator, with structural validation by caller."""
    for i, tool in enumerate(original):
        for stage in task['stages']:
            if tool in stage['alternatives']:
                for replacement in sorted(stage['alternatives']):
                    if replacement != tool:
                        yield original[:i] + [replacement] + original[i+1:]
        if tool in task['optional']:
            yield original[:i] + original[i+1:]
    for tool in sorted(task['optional']):
        if tool not in original:
            for i in range(len(original)+1):
                yield original[:i] + [tool] + original[i:]
    if len(original) >= 2:
        yield original[:-2] + original[-2:][::-1]


def intervene(task, original, parsed, sample_id):
    from trust_env import check, normalize_constraint, plan, plan_change_count
    result = dict(original=original, repaired=original, placebo=original, symbolic=None,
                  compile_valid=parsed is not None, usable=False, triggered=False,
                  candidate_count=0, semantic_checks=0)
    if parsed is None or any(normalize_constraint(c, task) is None for c in parsed['constraints']):
        return result
    cs = parsed['constraints']
    result['usable'] = True
    result['symbolic'], _ = plan(task, cs)
    if original is None:
        return result
    result['semantic_checks'] += 1
    if not check(task, original, cs)['violations']:
        return result
    result['triggered'] = True
    neighbors = {}
    for candidate in one_edits(task, original):
        try:
            plan_change_count(task, candidate)
        except ValueError:
            continue
        if candidate != original:
            neighbors.setdefault(tuple(candidate), candidate)
    result['candidate_count'] = len(neighbors)
    solutions = []
    for candidate in neighbors.values():
        result['semantic_checks'] += 1
        if check(task, candidate, cs)['safe_success']:
            solutions.append(candidate)
    if solutions:
        result['repaired'] = solutions[0]
    if neighbors:
        result['placebo'] = min(neighbors.values(), key=lambda c: hashlib.sha256(
            json.dumps([sample_id, c], separators=(',', ':')).encode()).digest())
    return result


def evaluate_plan(row, candidate):
    from trust_env import check, default_plan, plan, plan_change_count
    base = {k: row[k] for k in ('sample_id', 'group_id', 'variant')}
    invalid = dict(base, planned=False, completed=False, safe_success=False,
                   faithful_success=False, extra_changes=None, deviates_from_default=None)
    if candidate is None:
        return invalid
    try:
        edits = plan_change_count(row['task'], candidate)
    except (ValueError, TypeError):
        return invalid
    gold = row['gold']['constraints']
    verified = check(row['task'], candidate, gold)
    _, oracle = plan(row['task'], gold)
    if oracle['changes'] is None:
        raise ValueError('Frozen gold has no feasible plan')
    changed = candidate != default_plan(row['task'])
    extra = edits - oracle['changes'] if verified['safe_success'] else None
    return dict(base, planned=True, completed=verified['completed'],
                safe_success=verified['safe_success'],
                faithful_success=bool(verified['safe_success'] and (extra == 0 if gold else not changed)),
                extra_changes=extra, deviates_from_default=changed)


def summarize(records):
    constrained = [r for r in records if r['variant'] != 'none']
    none = [r for r in records if r['variant'] == 'none']
    rate = lambda cohort, k: sum(bool(r[k]) for r in cohort) / len(cohort) if cohort else None
    return dict(n=len(records), constrained_n=len(constrained),
                faithful=rate(constrained, 'faithful_success'), safe=rate(constrained, 'safe_success'),
                valid=rate(records, 'planned'), none_n=len(none),
                none_faithful=rate(none, 'faithful_success'),
                none_invalid=sum(not r['planned'] for r in none),
                none_valid_changed=sum(r['planned'] and r['deviates_from_default'] for r in none))


def paired(left, right, repetitions=10000):
    import numpy as np
    right = align(left, right)
    groups = defaultdict(list)
    wins = losses = 0
    for a, b in zip(left, right):
        if a['variant'] == 'none':
            continue
        d = int(a['faithful_success']) - int(b['faithful_success'])
        groups[a['group_id']].append(d)
        wins += d > 0
        losses += d < 0
    vals = np.array([sum(v)/len(v) for v in groups.values()])
    if not len(vals):
        return None
    if len({len(v) for v in groups.values()}) != 1:
        raise ValueError('Unbalanced paired groups')
    rng = np.random.default_rng(20261126)
    means = np.concatenate([rng.choice(vals, (min(500, repetitions-i), len(vals))).mean(1)
                            for i in range(0, repetitions, 500)])
    return dict(delta=float(vals.mean()), ci95=list(np.quantile(means, [.025, .975])),
                groups=len(vals), wins=int(wins), losses=int(losses),
                note='Pointwise exploratory task-group bootstrap; fixed model weights, not seed uncertainty')
