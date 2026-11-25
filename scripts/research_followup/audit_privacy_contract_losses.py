"""Inspect saved natural compiler failures; do not propose or rescore plans.

This is a gold-assisted descriptive audit of the eight previously exposed
privacy repair losses, not a deployment detector or independent evaluation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from run_e1 import prediction_is_well_formed, strict_parse
from trust_env import CONSTRAINT_TYPES, PRECEDENCE_KEYS, normalize_constraint
from common import align, read_rows, sha


def normalized_key(clause: dict, task: dict) -> str | None:
    norm = normalize_constraint(clause, task)
    if norm is None:
        return None
    return json.dumps(norm, sort_keys=True, default=lambda value: sorted(value))


def unresolved_details(clause: dict, task: dict, gold: list[dict]) -> dict:
    """Gold labels describe known failures; they must never select an edit."""
    kind = clause.get('type')
    params = clause.get('params', {})
    labels, fields = [], []
    if kind not in CONSTRAINT_TYPES:
        labels.append('unknown_constraint_type')
    elif kind in PRECEDENCE_KEYS:
        expected = [c for c in gold if c['type'] == kind]
        for key in PRECEDENCE_KEYS[kind]:
            value = params.get(key)
            role = value.removeprefix('role:').strip() if isinstance(value, str) else None
            if role is None:
                status = 'missing_or_nonstr_role'
            elif role not in task['tools']:
                status = 'out_of_catalog_role'
            elif len(expected) == 1 and role != expected[0]['params'][key]:
                status = 'valid_role_differs_from_gold'
            else:
                status = 'resolved_role'
            fields.append(dict(field=key, value=value, status=status))
            if status != 'resolved_role':
                labels.append(status)
    else:
        labels.append('invalid_nonprecedence_parameters')
    if not prediction_is_well_formed(dict(query_state='explicit', constraints=[clause])):
        labels.append('invalid_clause_schema')
    return dict(raw=clause, labels=sorted(set(labels)), fields=fields)


def run(out: Path) -> None:
    history_path = ROOT / 'outputs/history_audit_20261126/summary.json'
    family_dir = ROOT / 'outputs/edit_impact_family_audit_20261126_v2'
    cases_path = family_dir / 'privacy_authorization_changed_cases.jsonl'
    history = json.loads(history_path.read_text(encoding='utf-8'))
    family = json.loads((family_dir / 'summary.json').read_text(encoding='utf-8'))
    provenance = {str(p.relative_to(ROOT)): sha(p) for p in
                  (Path(__file__), history_path, cases_path, family_dir / 'summary.json')}

    def verify(path: Path, manifest: dict) -> None:
        rel = path.relative_to(ROOT).as_posix()
        matches = [h for name, h in manifest.items() if name.replace('\\', '/') == rel]
        if matches != [sha(path)]:
            raise ValueError('Historical input hash mismatch: ' + rel)
        provenance[rel] = matches[0]

    cases = []
    for case in read_rows(cases_path):
        replay = case['replay']
        if 'privacy' not in case['family'].split('+'):
            continue
        gated = replay['scores']['repaired' if replay['accept']['impact_with_cost_valid2'] else 'original']
        if replay['scores']['repaired']['faithful_success'] and not gated['faithful_success']:
            cases.append(case)
    # Source: frozen family audit, tool 7 losses + structure 1 loss (not a new rate).
    expected = sum(v['EI_contains_family_nonadditive'].get('privacy', {}).get('arms', {})
                   .get('impact_with_cost_valid2', {}).get('losses_vs_repaired', 0)
                   for v in family['splits'].values())
    if len(cases) != expected or len({c['sample_id'] for c in cases}) != len(cases):
        raise ValueError('Previously reported privacy losses do not reconcile')
    records = []
    for split in sorted({c['split'] for c in cases}):
        data_path = ROOT / 'data/processed_v5' / (split + '.jsonl')
        verify(data_path, history['provenance'])
        data = read_rows(data_path)
        rows = {r['sample_id']: r for r in data}
        predictions = {}
        for seed in (42, 43, 44):
            path = ROOT / f'outputs/e1/Qwen3-1.7B-v5-seed{seed}/trained_predictions/{split}.jsonl'
            verify(path, history['provenance'])
            predictions[seed] = {r['sample_id']: r for r in align(data, read_rows(path))}
        for case in (c for c in cases if c['split'] == split):
            row = rows[case['sample_id']]
            if case['gold'] != row['gold'] or case['query'] != row['query']:
                raise ValueError('Case differs from source task')
            gold = row['gold']['constraints']
            gold_privacy = {normalized_key(c, row['task']) for c in gold if c['type'] == 'privacy'}
            if not gold_privacy or None in gold_privacy:
                raise ValueError('Invalid privacy gold in saved case')
            views = []
            for index, seed in enumerate((42, 43, 44)):
                raw = predictions[seed][row['sample_id']]['raw']
                parsed = strict_parse(raw)
                if parsed is None:
                    raise ValueError('This audit expects the previously observed schema-valid records')
                clauses = parsed['constraints']
                keys = [normalized_key(c, row['task']) for c in clauses]
                usable = all(k is not None for k in keys)
                if usable != case['history']['usable_by_seed'][index]:
                    raise ValueError('Whole-record validity differs from saved history')
                privacy = {k for c, k in zip(clauses, keys) if c['type'] == 'privacy' and k is not None}
                unknowns = [unresolved_details(c, row['task'], gold)
                            for c, k in zip(clauses, keys) if k is None]
                views.append(dict(seed=seed, raw=raw, whole_record_usable=usable,
                                  usable_privacy_predicates_match_gold=privacy == gold_privacy,
                                  unknown_clauses=unknowns))
            records.append(dict(sample_id=row['sample_id'], group_id=row['group_id'], split=split,
                                variant=row['variant'], query=row['query'], gold=row['gold'],
                                family=case['family'], views=views,
                                original_score=case['replay']['scores']['original'],
                                repair_score=case['replay']['scores']['repaired']))
    invalid = [v for r in records for v in r['views'] if not v['whole_record_usable']]
    counts = Counter(label for v in invalid
                     for label in {label for c in v['unknown_clauses'] for label in c['labels']})
    summary = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                   scope='Gold-assisted analysis of selected historical losses; not a new model experiment or error rate.',
                   input_sha256=provenance, cases=len(records),
                   task_groups=len({r['group_id'] for r in records}),
                   compiler_records=sum(len(r['views']) for r in records),
                   unusable_records=len(invalid),
                   all_views_keep_matching_usable_privacy=all(v['usable_privacy_predicates_match_gold']
                                                             for r in records for v in r['views']),
                   unusable_record_error_labels_nonexclusive=dict(counts),
                   no_plan_generation=True, no_policy_changes=True, no_model_calls=True)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (out / 'cases.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'input_sha256'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
