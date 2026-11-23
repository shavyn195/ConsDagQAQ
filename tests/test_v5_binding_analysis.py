"""Analytical pairing checks and an oracle wiring test, not model results."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from analyze_v5_binding import analyze, measure, paired_effect
from run_e1 import load_jsonl


def test_group_pairing_keeps_positive_and_negative_pair_together():
    # Each group has E/I: one improvement and one regression. Every complete
    # group contributes zero, so every possible group bootstrap is exactly zero.
    before = [{'sample_id': g+v, 'group_id': g, 'variant': v, 'constrained': True,
               'faithful': v == 'implicit'} for g in ('a', 'b') for v in ('explicit', 'implicit')]
    after = [{**r, 'faithful': not r['faithful']} for r in reversed(before)]
    effect = paired_effect(before, after, 'faithful', constrained=True, n_boot=100)
    assert effect['difference'] == 0
    assert effect['conditional_paired_group_ci95'] == [0, 0]
    assert effect['records_0_to_1'] == effect['records_1_to_0'] == 2
    with pytest.raises(ValueError, match='source IDs'):
        paired_effect(before, after[:-1], 'faithful', constrained=True, n_boot=100)
    wrong_group = copy.deepcopy(after)
    wrong_group[0]['group_id'] = 'another-task'
    with pytest.raises(ValueError, match='mismatch'):
        paired_effect(before, wrong_group, 'faithful', constrained=True, n_boot=100)


def test_gold_wiring_and_malformed_outputs_are_not_dropped():
    # Gold constraints have prevalidated feasible witnesses. Oracle compilations
    # must match every contract. This is a wiring test, never a model score.
    rows = load_jsonl(ROOT/'data/diagnostic_v5_binding_20261123/original.jsonl')[:3]
    oracle = [{'sample_id': r['sample_id'], 'raw': json.dumps(r['gold'])} for r in rows]
    measured = measure(rows, oracle)
    assert all(r['faithful'] and r['strict_exact'] and r['core_exact'] for r in measured)
    oracle[0]['raw'] = 'not JSON'
    measured = measure(rows, oracle)
    assert len(measured) == len(rows)
    assert measured[0]['parse_failure'] and not measured[0]['valid_faithful']
    assert not measured[0]['core_exact']


def test_completed_oracle_fixture_and_pending_arms(tmp_path):
    # Identical correct gold in each semantically preserved condition has
    # exactly zero paired differences. No trained outputs enter this test.
    panel = tmp_path/'panel'
    panel.mkdir()
    source = ROOT/'data/diagnostic_v5_binding_20261123'
    proto = json.loads((source/'protocol.json').read_text(encoding='utf-8'))
    for condition in proto['conditions']:
        rows = load_jsonl(source/f'{condition}.jsonl')[:3]
        path = panel/f'{condition}.jsonl'
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
        proto['data_sha256'][condition] = hashlib.sha256(path.read_bytes()).hexdigest()
    proto['records_per_condition'] = 3
    protocol_path = panel/'protocol.json'
    protocol_path.write_text(json.dumps(proto), encoding='utf-8')
    arm = proto['model_arms'][0]
    run = tmp_path/'runs'/arm
    (run/'diagnostic_predictions').mkdir(parents=True)
    (run/'manifest.json').write_text(json.dumps({'arm': arm,
        'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
        'generation': proto['generation'], 'adapter_sha256': {'test_fixture': 'oracle-only'}}), encoding='utf-8')
    (run/'metrics.json').write_text('{}', encoding='utf-8')
    for condition in proto['conditions']:
        rows = load_jsonl(panel/f'{condition}.jsonl')
        (run/'diagnostic_predictions'/f'{condition}.jsonl').write_text(''.join(
            json.dumps({'sample_id': r['sample_id'], 'raw': json.dumps(r['gold'])})+'\n'
            for r in reversed(rows)), encoding='utf-8')
    result = analyze(panel, tmp_path/'runs', n_boot=100)
    assert result['status'] == 'pending_or_partial'
    assert result['arms'][arm]['status'] == 'complete'
    for effects in result['arms'][arm]['effects'].values():
        assert effects['faithful_constrained']['difference'] == 0
        assert effects['core_exact_constrained']['conditional_paired_group_ci95'] == [0, 0]
    with (panel/'original.jsonl').open('a', encoding='utf-8') as f:
        f.write('\n')
    with pytest.raises(ValueError, match='hash mismatch'):
        analyze(panel, tmp_path/'runs', n_boot=100)
