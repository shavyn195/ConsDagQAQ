"""Audit saved binding-panel generations; no model loading or training.

All deltas are intervention minus original, paired by source sample and task
group. Intervals describe this exploratory dev panel conditional on frozen
weights, not new-test performance or population uncertainty over training seeds.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from analyze_v5_seed_disagreement import group_bootstrap_delta
from rescore_v4_side import aligned, outcome
from run_e1 import constraint_key, core_key, load_jsonl, strict_parse


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(rows: list[dict], predictions: list[dict]) -> list[dict]:
    """Retain invalid predictions in every denominator, flagging parse failure."""
    outputs = []
    for row, raw in zip(rows, aligned(rows, predictions)):
        parsed = strict_parse(raw)
        got = parsed['constraints'] if parsed is not None else []
        gold = row['gold']['constraints']
        observed = outcome(row, raw)
        outputs.append({
            'sample_id': row['source_sample_id'], 'group_id': row['source_group_id'],
            'variant': row['variant'], 'constrained': bool(gold),
            'faithful': bool(observed['faithful_success']),
            'valid_faithful': bool(parsed is not None and observed['faithful_success']),
            'core_exact': bool(parsed is not None and Counter(map(core_key, got)) == Counter(map(core_key, gold))),
            'strict_exact': bool(parsed is not None and parsed['query_state'] == row['variant']
                                 and Counter(map(constraint_key, got)) == Counter(map(constraint_key, gold))),
            'evidence_exact': bool(observed['exact_with_evidence']),
            'parse_failure': parsed is None,
            'none_false_positive': bool(not gold and parsed is not None and got),
            'none_deviation': bool(not gold and observed['deviates_from_default']),
        })
    return outputs


def paired_effect(original: list[dict], intervention: list[dict], metric: str,
                  *, constrained: bool, n_boot: int = 10_000) -> dict[str, Any]:
    """Refuse incomplete pairs instead of silently selecting surviving outputs."""
    a = {r['sample_id']: r for r in original}
    b = {r['sample_id']: r for r in intervention}
    if len(a) != len(original) or len(b) != len(intervention) or set(a) != set(b):
        raise ValueError('Missing, duplicate or unexpected source IDs in paired comparison')
    groups: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    wins = losses = base_sum = changed_sum = 0
    for sid in sorted(a):
        before, after = a[sid], b[sid]
        if any(before[k] != after[k] for k in ('group_id', 'variant', 'constrained')):
            raise ValueError(f'Source task/variant mismatch: {sid}')
        if before['constrained'] != constrained:
            continue
        x, y = int(before[metric]), int(after[metric])
        base_sum += x
        changed_sum += y
        groups[before['group_id']][0] += y - x
        groups[before['group_id']][1] += 1
        wins += y > x
        losses += y < x
    if not groups:
        raise ValueError('No records in requested analysis stratum')
    n = sum(v[1] for v in groups.values())
    point, lo, hi = group_bootstrap_delta({k: tuple(v) for k, v in groups.items()}, n_boot=n_boot)
    return {'records': n, 'groups': len(groups), 'original_rate': base_sum/n,
            'intervention_rate': changed_sum/n, 'difference': point,
            'conditional_paired_group_ci95': [lo, hi],
            'records_0_to_1': wins, 'records_1_to_0': losses,
            'direction': 'intervention minus original; lower is better for error metrics'}


def analyze(panel: Path, runs: Path, *, n_boot: int = 10_000) -> dict[str, Any]:
    if n_boot < 100:
        raise ValueError('Use at least 100 bootstrap replicates')
    protocol_path = panel / 'protocol.json'
    proto = json.loads(protocol_path.read_text(encoding='utf-8'))
    data = {}
    for condition in proto['conditions']:
        path = panel / f'{condition}.jsonl'
        if sha256(path) != proto['data_sha256'][condition]:
            raise ValueError(f'Panel hash mismatch: {condition}')
        data[condition] = load_jsonl(path)
        if len(data[condition]) != proto['records_per_condition']:
            raise ValueError(f'Panel record count mismatch: {condition}')
    report: dict[str, Any] = {
        'purpose': 'exploratory dev intervention, conditional on frozen adapters',
        'interval_scope': 'source task-group bootstrap; not training-seed population or independent test',
        'faithful_policy': 'original v5 fallback retained; also report valid_faithful and parse failure',
        'protocol_sha256': sha256(protocol_path), 'n_bootstrap': n_boot, 'arms': {},
    }
    for arm in proto['model_arms']:
        root = runs / arm
        required = [root/'manifest.json', root/'metrics.json'] + [
            root/'diagnostic_predictions'/f'{c}.jsonl' for c in proto['conditions']]
        missing = [p.relative_to(root).as_posix() for p in required if not p.is_file()]
        if missing:
            report['arms'][arm] = {'status': 'pending_or_incomplete', 'missing': missing}
            continue
        manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        if (manifest['arm'] != arm or manifest['protocol_sha256'] != sha256(protocol_path)
                or manifest['generation'] != proto['generation']):
            raise ValueError(f'Run contract mismatch: {arm}')
        measurements, hashes = {}, {}
        for c, rows in data.items():
            pred_path = root/'diagnostic_predictions'/f'{c}.jsonl'
            hashes[c] = sha256(pred_path)
            measurements[c] = measure(rows, load_jsonl(pred_path))
        arm_report: dict[str, Any] = {'status': 'complete', 'prediction_sha256': hashes,
                                     'adapter_sha256': manifest['adapter_sha256'], 'effects': {}}
        for condition in proto['conditions']:
            if condition == 'original':
                continue
            before, after = measurements['original'], measurements[condition]
            effects = {}
            for metric in ('faithful', 'valid_faithful', 'core_exact', 'strict_exact', 'evidence_exact', 'parse_failure'):
                effects[metric+'_constrained'] = paired_effect(before, after, metric, constrained=True, n_boot=n_boot)
            for metric in ('none_false_positive', 'none_deviation', 'parse_failure', 'valid_faithful'):
                effects[metric+'_none'] = paired_effect(before, after, metric, constrained=False, n_boot=n_boot)
            by_id = {r['sample_id']: r for r in after}
            effects['changed_examples'] = [{'before': r, 'after': by_id[r['sample_id']]}
                for r in before if any(r[k] != by_id[r['sample_id']][k]
                                      for k in ('faithful', 'core_exact', 'strict_exact', 'parse_failure'))][:12]
            arm_report['effects'][condition] = effects
        report['arms'][arm] = arm_report
    report['status'] = 'complete' if all(a['status'] == 'complete' for a in report['arms'].values()) else 'pending_or_partial'
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panel', type=Path, required=True)
    parser.add_argument('--runs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--n-bootstrap', type=int, default=10_000)
    args = parser.parse_args()
    report = analyze(args.panel, args.runs, n_boot=args.n_bootstrap)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'status': report['status'], 'arms': {k: v['status'] for k, v in report['arms'].items()}}))


if __name__ == '__main__':
    main()
