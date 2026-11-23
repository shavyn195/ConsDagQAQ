"""Checks for audit counting and gold-free public binding, not model results."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from audit_v5_coverage import coverage, error_flags
from public_scope_binding import bind_public_scope


def fixture():
    catalog = [{'role': 'buy', 'paid': True, 'recipient': 'external'},
               {'role': 'approve', 'paid': False, 'recipient': 'local'}]
    c = {'type': 'tool_auth', 'state': 'explicit', 'severity': 'medium',
         'scope': ['role:buy'], 'params': {'approval_role': 'approve', 'required_role': 'buy'},
         'evidence_span': 'Get approval first.'}
    return catalog, c


def test_public_scope_changes_no_semantic_fields_or_input():
    catalog, c = fixture()
    items = [c, {**c, 'type': 'budget', 'params': {'max_total_cost_cny': 10}},
             {**c, 'type': 'privacy', 'params': {'local_only': True}},
             {**c, 'type': 'deadline', 'params': {'max_total_duration_min': 30}},
             {**c, 'type': 'order', 'params': {'before_role': 'approve', 'after_role': 'buy'}}]
    for item in items:
        item['scope'] = ['role:wrong']
    prediction = {'query_state': 'explicit', 'constraints': items}
    before = deepcopy(prediction)
    bound = bind_public_scope(prediction, catalog)
    assert prediction == before
    assert [c['scope'] for c in bound['constraints']] == [
        ['role:buy'], ['role:buy'], ['role:buy'], ['role:*'], ['role:approve', 'role:buy']]
    for old, new in zip(prediction['constraints'], bound['constraints']):
        assert {k: v for k, v in old.items() if k != 'scope'} == {
            k: v for k, v in new.items() if k != 'scope'}
    prediction['constraints'][0]['params']['required_role'] = 'unknown'
    assert bind_public_scope(prediction, catalog)['constraints'][0] == prediction['constraints'][0]
    with pytest.raises(ValueError, match='duplicate'):
        bind_public_scope(prediction, catalog + catalog[:1])


def test_coverage_counts_e_i_n_as_one_group():
    catalog, c = fixture()
    row = {'group_id': 'g', 'variant': 'explicit', 'catalog': catalog,
           'gold': {'constraints': [c]}}
    rows = [row, {**row, 'variant': 'implicit'},
            {**row, 'variant': 'none', 'gold': {'constraints': []}}]
    got = coverage(rows, rows)
    assert got['records'] == 3 and got['groups'] == 1
    assert got['directed_role_pairs'][0]['groups'] == 1
    assert got['groups_with_unseen_type_combination'] == 0
    with pytest.raises(ValueError, match='Duplicate'):
        coverage(rows + [row], rows)


def test_role_reversal_and_missing_type_are_separate_errors():
    catalog, c = fixture()
    row = {'variant': 'explicit', 'catalog': catalog, 'gold': {'constraints': [c]},
           'task': {'catalog': ['buy', 'approve'], 'tools': {'buy': {}, 'approve': {}}}}
    reversed_c = {**c, 'params': {'approval_role': 'buy', 'required_role': 'approve'}}
    flags = error_flags(row, {'query_state': 'explicit', 'constraints': [reversed_c]}, {'old_buy'})
    assert 'reversed_role_pair' in flags
    assert 'missing_constraint_type' not in flags
    assert 'parameter_role_absent_from_public_catalog' not in flags
    assert error_flags(row, None, set()) == {'parse_failure'}
    flags = error_flags(row, {'query_state': 'explicit', 'constraints': []}, set())
    assert 'missing_constraint_type' in flags
