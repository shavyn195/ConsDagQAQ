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
