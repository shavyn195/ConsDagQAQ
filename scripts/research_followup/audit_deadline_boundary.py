"""Offline one-edit reachability diagnostic; never repairs reported model outputs."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(Path(__file__).parent)]
from common import read_rows, one_edits, sha, evaluate_plan
from trust_env import check, plan_change_count


def main():
    folder = ROOT / 'outputs/matched_planner_sft_inputs_20261126/results'
    protocol = json.loads((folder / 'protocol.json').read_text())
    receipt = json.loads((folder.parent / 'receipt.json').read_text())
    for name, digest in receipt.items():
        assert sha(folder / name) == digest
    sources = {s: ROOT / ('data/processed_v6/' + s + '.jsonl') for s in ('train', 'dev')}
    for s, p in sources.items():
        assert sha(p) == protocol['data_sha256'][s]
    datasets = {s: {r['sample_id']: r for r in read_rows(p)} for s, p in sources.items()}
    parent = json.loads((ROOT / 'outputs/shared_planner_learning_20261126/results/protocol.json').read_text())
    cohorts = dict(continuation_train=('train', protocol['train_sample_ids']),
        shared_initial_train=('train', parent['train_sample_ids']), dev=('dev', protocol['eval_sample_ids']))
    coverage = {}
    for label, (split, ids) in cohorts.items():
        rows = [datasets[split][sid] for sid in ids]
        coverage[label] = dict(rows=len(rows), constrained_rows=sum(r['variant'] != 'none' for r in rows),
            instances=Counter(c['type'] for r in rows for c in r['gold']['constraints']))
    counts, examples = Counter(), []
    for decision in read_rows(folder / 'decisions.jsonl'):
        if decision['arm'] != 'contract_sft/contract' or not decision['outcome']['planned']:
            continue
        row = datasets['dev'][decision['sample_id']]
        constraints = row['gold']['constraints']
        deadlines = {i for i, c in enumerate(constraints) if c['type'] == 'deadline'}
        if not deadlines:
            continue
        before = check(row['task'], decision['plan'], constraints)
        if not deadlines.intersection(before['violations']):
            continue
        candidates = {}
        for plan in one_edits(row['task'], decision['plan']):
            try:
                plan_change_count(row['task'], plan)
            except ValueError:
                continue
            candidates[tuple(plan)] = check(row['task'], plan, constraints)
        values = list(candidates.values())
        flags = dict(deadline_failed_valid=True,
            some_one_edit_fixes_all=any(c['safe_success'] for c in values),
            some_one_edit_fixes_deadline=any(not deadlines.intersection(c['violations']) for c in values),
            some_one_edit_reduces_time=any(c['minutes'] < before['minutes'] for c in values),
            time_reduction_without_new_violations=any(c['minutes'] < before['minutes'] and set(c['violations']) <= set(before['violations']) for c in values),
            some_one_edit_reaches_faithful=any(evaluate_plan(row, list(plan))['faithful_success'] for plan in candidates))
        counts.update({k:int(v) for k,v in flags.items()})
        examples.append(dict(sample_id=row['sample_id'], variant=row['variant'], group_id=row['group_id'],
            constraint_types=[c['type'] for c in constraints], original_plan=decision['plan'],
            minutes=before['minutes'], limit_minutes=constraints[next(iter(deadlines))]['params']['max_duration_hours'] * 60,
            valid_one_edit_candidates=len(candidates), **flags))
    report = dict(coverage=coverage, counts=counts, cases=examples,
        source_decisions_sha256=sha(folder / 'decisions.jsonl'),
        scope='Oracle-label offline diagnostic of exposed dev errors. Existing one_edits neighborhood only; not a new repair algorithm, no changed model score, absence in this neighborhood is not a global impossibility proof.')
    dest = ROOT / 'outputs/planner_deadline_boundary_20261126'
    dest.mkdir(exist_ok=True)
    (dest / 'audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(coverage=coverage, counts=counts), indent=2))


if __name__ == '__main__':
    main()
