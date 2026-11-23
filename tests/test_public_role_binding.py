from copy import deepcopy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from public_role_binding import bind_public_roles


def fixture():
    catalog = [{'role': 'check_lineage', 'name': 'the provenance verification'},
               {'role': 'run_local', 'name': 'the local training'}]
    prediction = {'query_state': 'implicit', 'constraints': [{'type': 'order',
        'params': {'before_role': 'provenance_verification', 'after_role': 'local_training'},
        'scope': ['role:wrong'], 'state': 'implicit', 'severity': 'medium', 'evidence_span': 'unchanged'}]}
    return catalog, prediction


def test_unique_alias_without_gold_and_without_mutation():
    catalog, prediction = fixture()
    saved = deepcopy(prediction)
    bound = bind_public_roles(prediction, catalog)
    assert prediction == saved
    assert bound['constraints'][0]['params'] == {'before_role': 'check_lineage', 'after_role': 'run_local'}
    assert bound['constraints'][0]['scope'] == ['role:wrong']
    assert bind_public_roles(bound, catalog) == bound
    assert bind_public_roles({'query_state': 'none', 'constraints': []}, catalog)['constraints'] == []


def test_ambiguous_partial_and_degenerate_bindings_are_not_guessed():
    catalog, prediction = fixture()
    ambiguous = catalog + [{'role': 'run_second', 'name': 'the local training'}]
    assert bind_public_roles(prediction, ambiguous) == prediction
    prediction['constraints'][0]['params']['after_role'] = 'local_training_new'
    assert bind_public_roles(prediction, catalog) == prediction
    prediction['constraints'][0]['params']['after_role'] = 'provenance_verification'
    assert bind_public_roles(prediction, catalog) == prediction


def test_valid_identifier_wins_over_conflicting_display_name():
    catalog, prediction = fixture()
    catalog[1]['name'] = 'the check lineage'
    prediction['constraints'][0]['params'] = {'before_role': 'check_lineage', 'after_role': 'run_local'}
    assert bind_public_roles(prediction, catalog) == prediction


def test_pe_and_training_cache_layouts_use_identical_measurement(tmp_path, monkeypatch):
    import json
    import evaluate_v5_public_binding as evaluator
    from run_e1 import load_jsonl
    root = Path(__file__).resolve().parents[1]
    rows = load_jsonl(root / 'data/diagnostic_v5_binding_20261123/original.jsonl')[:3]
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'dev.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    predictions = ''.join(json.dumps({'sample_id': r['sample_id'], 'raw': json.dumps(r['gold'])}) + '\n' for r in rows)
    for folder in (tmp_path / 'runs' / 'oracle', tmp_path / 'runs' / 'oracle' / 'trained_predictions'):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'dev.jsonl').write_text(predictions, encoding='utf-8')
    monkeypatch.setattr(evaluator, 'eval_subsets', lambda _: ['dev'])
    trained = evaluator.evaluate(data, tmp_path / 'runs', ['oracle'])
    pe = evaluator.evaluate(data, tmp_path / 'runs', ['oracle'], flat_predictions=True)
    assert pe['arms'] == trained['arms']
    assert pe['arms']['oracle']['dev']['faithful']['intervention_rate'] == 1
