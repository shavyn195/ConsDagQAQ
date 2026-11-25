"""Analytical contract tests, independent of the development experiment builder."""
import itertools
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/research_followup'))
from partial_contract import evaluate_policies, finite_completions, split_contract
from trust_env import violated


class PartialContractTests(unittest.TestCase):
    def test_kept_edit_requires_separate_release_evidence(self):
        tools = {r: dict(cost_cny=1, duration_min=1, recipient='external' if r == 'b' else 'local', clears_pii=r == 'c')
                 for r in 'abcde'}
        task = dict(data_class='pii', tools=tools,
                    stages=[dict(default=r, alternatives=[r]) for r in 'ab'], finish=['d'], optional={'c': ['@acquire'], 'e': ['d']})
        core = dict(type='privacy', state='explicit', severity='hard', scope='workflow',
                    params=dict(protected_data_classes=['pii'], forbidden_recipients=['external']))
        for target, expected_release in [('d', False), ('e', True)]:
            with self.subTest(target=target):
                unknown = dict(type='order', state='explicit', severity='hard', scope='workflow',
                               params=dict(before_role='missing', after_role=target))
                raw = json.dumps(dict(query_state='explicit', constraints=[core, unknown]))
                result = evaluate_policies(task, list('abd'), list('acbd'), [raw]*3)['decisions']
                # c removes the leak. If target=d, absent e may be its prerequisite: not releasable.
                # If target=e (unused), every possible prerequisite is vacuously satisfied.
                self.assertTrue(result['row_robust']['accepted'])
                self.assertEqual(result['row_robust']['released'], expected_release)
                self.assertFalse(result['row_defer']['released'])
                self.assertFalse(result['whole_record']['accepted'])

    def test_local_error_does_not_erase_other_evidence(self):
        raw = '{"query_state":"explicit","constraints":[{"type":"privacy","state":"explicit","severity":"hard","scope":"workflow","params":{"protected_data_classes":["patient_records"],"forbidden_recipients":["external"]}},{"type":"order","state":"explicit","severity":"hard","scope":"workflow","params":{"before_role":"missing","after_role":"b"}}]}'
        result = split_contract(raw, {'tools': {'a': {}, 'b': {}, 'c': {}}})
        # Direct inspection: the privacy object is intact, the nonexistent first role is unresolved.
        self.assertEqual([c['norm']['type'] for c in result['known']], ['privacy'])
        self.assertEqual(len(result['unknown']), 1)
        self.assertEqual(result['unknown'][0]['raw']['params']['before_role'], 'missing')

    def test_json_and_schema_failure_are_not_empty_truth(self):
        for raw in ('{', '{"constraints":[]}', '{"query_state":"explicit","constraints":[{}]}'):
            with self.subTest(raw=raw):
                value = split_contract(raw, {'tools': {}})
                # None of these three strings represents a valid empty contract.
                self.assertTrue(value['unknown'])
                self.assertIsNone(finite_completions(value['unknown'][0], {'tools': {}}))

    def test_complete_role_domain_without_gold(self):
        task = {'tools': {'a': {}, 'b': {}, 'c': {}}}
        unknown = dict(reason='unresolved_binding', raw=dict(type='order', params=dict(before_role='missing', after_role='b')))
        possibilities = finite_completions(unknown, task)
        # Finite domain {a,b,c}, second=b, and irreflexivity imply exactly {a,c}.
        self.assertEqual({n['first'] for n in possibilities}, {'a', 'c'})
        self.assertIsNone(finite_completions(unknown, task, cap=1))

    def test_quantification_matches_independent_precedence_truth_table(self):
        task = {'tools': {'a': {}, 'b': {}, 'c': {}}}
        unknown = dict(reason='unresolved_binding', raw=dict(type='order', params=dict(before_role='missing', after_role='b')))
        possibilities = finite_completions(unknown, task)
        for size in range(4):
            for seq in itertools.permutations('abc', size):
                actual = [violated(n, {'positions': {r: i for i, r in enumerate(seq)}}) for n in possibilities]
                # Independent semantics: when b occurs, every possible first must precede b.
                expected = 'b' not in seq or all(r in seq and seq.index(r) < seq.index('b') for r in ('a', 'c'))
                self.assertEqual(not any(actual), expected, seq)


if __name__ == '__main__':
    unittest.main()
