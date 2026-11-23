"""Prospectively frozen public-binding analysis on the existing dev panel.

The repair was discovered on old v5 errors; this is a separate input intervention
diagnostic with frozen weights, not an independent benchmark or new seed claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_v5_binding import analyze, measure, paired_effect, sha256
from public_role_binding import bind_public_roles
from public_scope_binding import bind_public_scope
from rescore_v4_side import aligned
from run_e1 import load_jsonl, strict_parse


def repair_predictions(rows: list[dict], predictions: list[dict]) -> tuple[list[dict], int]:
    repaired, edited = [], 0
    for row, raw in zip(rows, aligned(rows, predictions)):
        parsed = strict_parse(raw)
        if parsed is not None:
            after = bind_public_scope(bind_public_roles(parsed, row['catalog']), row['catalog'])
            edited += after != parsed
            raw = json.dumps(after, ensure_ascii=False)
        repaired.append({'sample_id': row['sample_id'], 'raw': raw})
    return repaired, edited


def analyze_repair(panel: Path, runs: Path, protocol: Path, *, n_boot: int = 10_000) -> dict:
    frozen = json.loads(protocol.read_text(encoding='utf-8'))
    if sha256(panel/'protocol.json') != frozen['panel_protocol_sha256']:
        raise ValueError('Frozen panel protocol mismatch')
    for name, wanted in frozen['binder_sha256'].items():
        if sha256(Path(__file__).with_name(name)) != wanted:
            raise ValueError('Frozen binder code mismatch: ' + name)
    # Reuse original validation for data hashes, coverage, adapter and generation
    # manifest. 100 resamples suffice here because these outputs are not reported.
    validated = analyze(panel, runs, n_boot=100)
    proto = json.loads((panel/'protocol.json').read_text(encoding='utf-8'))
    result = {'status': validated['status'], 'protocol_sha256': sha256(protocol),
              'purpose': frozen['purpose'], 'n_bootstrap': n_boot,
              'interval_scope': 'task groups conditional on frozen weights, no seed-population inference',
              'arms': {}}
    for arm, validation in validated['arms'].items():
        if validation['status'] != 'complete':
            result['arms'][arm] = {'status': validation['status']}
            continue
        corrected, before, measurements, edits = {}, {}, {}, {}
        for condition in proto['conditions']:
            rows = load_jsonl(panel/(condition+'.jsonl'))
            pred = load_jsonl(runs/arm/'diagnostic_predictions'/(condition+'.jsonl'))
            new, edits[condition] = repair_predictions(rows, pred)
            before[condition] = measure(rows, pred)
            corrected[condition] = measure(rows, new)
            effects = {}
            for key in ('faithful', 'valid_faithful', 'core_exact', 'strict_exact', 'parse_failure'):
                effects[key+'_constrained'] = paired_effect(before[condition], corrected[condition], key,
                                                            constrained=True, n_boot=n_boot)
            for key in ('none_false_positive', 'none_deviation', 'parse_failure'):
                effects[key+'_none'] = paired_effect(before[condition], corrected[condition], key,
                                                     constrained=False, n_boot=n_boot)
            measurements[condition] = effects
        residual = {condition: paired_effect(corrected['original'], corrected[condition], 'faithful',
                                             constrained=True, n_boot=n_boot)
                    for condition in proto['conditions'] if condition != 'original'}
        result['arms'][arm] = {'status': 'complete', 'edited_records': edits,
                              'prediction_sha256': validation['prediction_sha256'],
                              'adapter_sha256': validation['adapter_sha256'],
                              'repair_effect_by_condition': measurements,
                              'input_intervention_effect_after_same_repair': residual}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--panel', required=True, type=Path)
    parser.add_argument('--runs', required=True, type=Path)
    parser.add_argument('--protocol', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = analyze_repair(args.panel, args.runs, args.protocol)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(json.dumps({'status': result['status']}))
