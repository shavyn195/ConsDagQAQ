"""Exploratory public-name resolution on frozen outputs, never a new training run.

This baseline was motivated by inspected test failures. Its test numbers are
post-hoc sensitivity results, not a preregistered improvement or independent
evidence. Confirmation needs a frozen protocol and fresh name families.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from analyze_v5_binding import measure, paired_effect, sha256
from public_role_binding import bind_public_roles
from public_scope_binding import bind_public_scope
from rescore_v4_side import aligned
from run_e1 import eval_subsets, load_jsonl, score, strict_parse


def evaluate(data: Path, runs: Path, arms: list[str]) -> dict:
    result = {'checked_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
              'status': 'exploratory_posthoc_not_preregistered',
              'intervention': 'unique exact normalized public name to ID; no fuzzy match or gold',
              'metric_order': 'faithful primary; core/strict secondary; N errors retained',
              'code_sha256': {p.name: sha256(p) for p in (
                  Path(__file__), Path(__file__).with_name('public_role_binding.py'),
                  Path(__file__).with_name('public_scope_binding.py'))},
              'arms': {}}
    for arm in arms:
        result['arms'][arm] = {}
        for split in eval_subsets(data):
            source = data / (split + '.jsonl')
            path = runs / arm / 'trained_predictions' / (split + '.jsonl')
            if not path.exists():
                result['arms'][arm][split] = {'status': 'pending'}
                continue
            rows = [{**r, 'source_sample_id': r['sample_id'], 'source_group_id': r['group_id']}
                    for r in load_jsonl(source)]
            original = load_jsonl(path)
            raw = aligned(rows, original)
            changed, both, edited_records = [], [], 0
            for row, text in zip(rows, raw):
                parsed = strict_parse(text)
                if parsed is None:
                    alias_text = both_text = text
                else:
                    # Binding receives only publicly available catalog and predictions.
                    alias = bind_public_roles(parsed, row['catalog'])
                    edited_records += alias != parsed
                    alias_text = json.dumps(alias, ensure_ascii=False)
                    both_text = json.dumps(bind_public_scope(alias, row['catalog']), ensure_ascii=False)
                changed.append({'sample_id': row['sample_id'], 'raw': alias_text})
                both.append({'sample_id': row['sample_id'], 'raw': both_text})
            before_m, after_m = measure(rows, original), measure(rows, changed)
            both_m = measure(rows, both)
            if any(a['faithful'] != b['faithful'] for a, b in zip(after_m, both_m)):
                raise AssertionError('Scope changed faithful')
            scores = {}
            for name, preds in [('original', original), ('public_alias', changed), ('public_alias_and_scope', both)]:
                values = score(rows, [None]*len(rows), aligned(rows, preds))
                scores[name] = {k: values[k] for k in (
                    'constraint_micro', 'constraint_core_micro', 'record_exact_match')}
            result['arms'][arm][split] = {
                'status': 'complete_split', 'data_sha256': sha256(source), 'pred_sha256': sha256(path),
                'edited_records': edited_records, 'scores': scores,
                'faithful': paired_effect(before_m, after_m, 'faithful', constrained=True),
                'valid_faithful': paired_effect(before_m, after_m, 'valid_faithful', constrained=True),
                'none_false_positive': paired_effect(before_m, after_m, 'none_false_positive', constrained=False),
                'none_deviation': paired_effect(before_m, after_m, 'none_deviation', constrained=False),
                'parse_failures_before_after': [sum(r['parse_failure'] for r in m) for m in (before_m, after_m)],
            }
            print(json.dumps({'arm': arm, 'split': split, 'edited_records': edited_records,
                'faithful': result['arms'][arm][split]['faithful']}), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--runs', required=True, type=Path)
    parser.add_argument('--arm', action='append', required=True)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = evaluate(args.data, args.runs, args.arm)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
