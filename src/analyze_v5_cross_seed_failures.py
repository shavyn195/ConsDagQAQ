"""Describe agreement of the three frozen 1.7B seeds on the same v5 tasks.

Group and E/I outcomes are kept paired. This is descriptive fixed-test analysis,
not inference over the population of training seeds, and it never selects a
checkpoint or removes a failed task.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from rescore_v4_side import aligned, outcome
from run_e1 import eval_subsets, load_jsonl, strict_parse


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(data: Path, runs: Path, seeds: tuple[int, ...] = (42, 43, 44)) -> dict[str, Any]:
    expected = json.loads((data / 'generation_report.json').read_text(encoding='utf-8'))['sha256']
    actual = {split: sha256(data / f'{split}.jsonl') for split in ['train', *eval_subsets(data)]}
    if actual != expected:
        raise ValueError('Frozen v5 dataset hashes do not match generation report')

    report: dict[str, Any] = {
        'purpose': 'descriptive cross-seed failure overlap on frozen v5 predictions',
        'inference_scope': 'fixed observed seeds and fixed task groups only; no seed-population CI',
        'counting': 'constrained E/I paired within group; N errors reported separately',
        'data_sha256': actual,
        'arms': {},
    }
    for split in eval_subsets(data):
        rows = load_jsonl(data / f'{split}.jsonl')
        constrained = [r for r in rows if r['gold']['constraints']]
        if len({(r['group_id'], r['variant']) for r in constrained}) != len(constrained):
            raise ValueError(f'Duplicate constrained group/variant in {split}')
        observations: dict[int, dict[str, dict[str, bool]]] = {}
        for seed in seeds:
            arm = f'Qwen3-1.7B-v5-seed{seed}'
            pred_path = runs / arm / 'trained_predictions' / f'{split}.jsonl'
            if not pred_path.is_file():
                raise FileNotFoundError(pred_path)
            pred = load_jsonl(pred_path)
            raw = aligned(rows, pred)
            scored = [outcome(row, text) for row, text in zip(rows, raw)]
            for item, text in zip(scored, raw):
                parsed = strict_parse(text)
                item['predicted_nonempty'] = bool(parsed and parsed['constraints'])
            by_id = {item['sample_id']: item for item in scored}
            if len(by_id) != len(rows):
                raise ValueError(f'Duplicate or missing scored sample IDs: {arm}/{split}')
            observations[seed] = by_id

        groups = sorted({r['group_id'] for r in constrained})
        variant_by_group = {gid: {} for gid in groups}
        row_by_key = {}
        for row in constrained:
            variant_by_group[row['group_id']][row['variant']] = row['sample_id']
            row_by_key[(row['group_id'], row['variant'])] = row
        if any(set(value) != {'explicit', 'implicit'} for value in variant_by_group.values()):
            raise ValueError(f'Expected one explicit and one implicit record per group in {split}')

        split_result: dict[str, Any] = {
            'task_groups': len(groups),
            'constrained_records': len(constrained),
            'seeds': {},
            'record_failure_count_by_number_of_seeds': {'0': 0, '1': 0, '2': 0, '3': 0},
            'group_failure_count_by_number_of_seeds': {'0': 0, '1': 0, '2': 0, '3': 0},
            'pairwise_failure_jaccard_by_record': {},
            'pairwise_failure_jaccard_by_group': {},
            'n_none_false_positive': {},
            'group_outcomes': {},
        }
        seed_record_fail: dict[int, set[tuple[str, str]]] = {}
        seed_group_fail: dict[int, set[str]] = {}
        for seed in seeds:
            record_fail = set()
            group_fail = set()
            variants = defaultdict(Counter)
            group_success_counts = Counter()
            for group in groups:
                success_n = 0
                for variant, sid in variant_by_group[group].items():
                    success = bool(observations[seed][sid]['faithful_success'])
                    variants[variant]['success' if success else 'failure'] += 1
                    if success:
                        success_n += 1
                    else:
                        record_fail.add((group, variant))
                group_success_counts[str(success_n)] += 1
                if success_n < 2:
                    group_fail.add(group)
            seed_record_fail[seed] = record_fail
            seed_group_fail[seed] = group_fail
            none_rows = [r for r in rows if not r['gold']['constraints']]
            none_false_positive = sum(bool(observations[seed][r['sample_id']]['predicted_nonempty'])
                                      for r in none_rows)
            split_result['seeds'][str(seed)] = {
                'variant_faithful_counts': {k: dict(v) for k, v in variants.items()},
                'groups_with_0_1_2_successful_EI_records': dict(group_success_counts),
                'group_failure_rate_any_EI': len(group_fail) / len(groups),
                'record_failure_count': len(record_fail),
            }
            split_result['n_none_false_positive'][str(seed)] = {
                'false_positive_records': none_false_positive,
                'denominator': len(none_rows),
                'rate': none_false_positive / max(len(none_rows), 1),
            }

        for nfailed in range(len(seeds) + 1):
            split_result['record_failure_count_by_number_of_seeds'][str(nfailed)] = sum(
                sum((group, variant) in seed_record_fail[s] for s in seeds) == nfailed
                for group, variant in row_by_key)
            split_result['group_failure_count_by_number_of_seeds'][str(nfailed)] = sum(
                sum(group in seed_group_fail[s] for s in seeds) == nfailed for group in groups)
        for i, a in enumerate(seeds):
            for b in seeds[i + 1:]:
                name = f'{a}_vs_{b}'
                for label, sets, universe in (
                    ('record', seed_record_fail, set(row_by_key)),
                    ('group', seed_group_fail, set(groups)),
                ):
                    left, right = sets[a], sets[b]
                    union = left | right
                    split_result[f'pairwise_failure_jaccard_by_{label}'][name] = {
                        'intersection': len(left & right), 'union': len(union),
                        'jaccard': len(left & right) / max(len(union), 1),
                        'universe': len(universe),
                    }
        group_outcomes = {}
        for group in groups:
            group_outcomes[group] = {
                'variants': {
                    variant: {
                        'sample_id': sid,
                        'per_seed_faithful': {str(seed): bool(observations[seed][sid]['faithful_success'])
                                              for seed in seeds},
                        'gold_types': sorted(c['type'] for c in row_by_key[(group, variant)]['gold']['constraints']),
                    }
                    for variant, sid in variant_by_group[group].items()
                }
            }
        split_result['group_outcomes'] = group_outcomes
        report['arms'][split] = split_result
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path('data/processed_v5'))
    parser.add_argument('--runs', type=Path, default=Path('outputs/e1'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = analyze(args.data, args.runs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({split: {
        'record_failure_by_seeds': values['record_failure_count_by_number_of_seeds'],
        'group_failure_by_seeds': values['group_failure_count_by_number_of_seeds'],
        'pairwise_group_jaccard': values['pairwise_failure_jaccard_by_group'],
    } for split, values in result['arms'].items()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
