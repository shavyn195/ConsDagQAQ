"""Hand-constructed checks for the frozen-consumer diagnostic definitions."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('audit_history', Path(__file__).resolve().parents[1]/'scripts/research_followup/audit_history.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
import probe_edit_impact as impact


class SignatureTests(unittest.TestCase):
    def test_invalid_is_not_empty_agreement(self):
        # Malformed output has no valid empty conjunction; three failures cannot vote.
        invalid = audit.strict_parse('{"constraints": []}')
        self.assertIsNone(invalid)
        self.assertEqual(audit.support_for_first([None,None,None]),0)
        empty = audit.strict_parse('{"query_state":"none","constraints":[]}')
        self.assertEqual(audit.predicate_signature(empty,{}),())
        self.assertEqual(audit.support_for_first([(),None,()]),2)

    def test_precedence_and_metadata(self):
        # trust_env.violated applies identical before/after logic to order and tool_auth.
        task = {'tools':{'approve':{},'run':{}}}
        auth = {'query_state':'explicit','constraints':[dict(type='tool_auth',state='explicit',severity='medium',scope=['role:run'],params=dict(approval_role='approve',required_role='run'))]}
        order = {'query_state':'implicit','constraints':[dict(type='order',state='implicit',severity='high',scope=['run'],params=dict(before_role='approve',after_role='run'))]}
        self.assertEqual(audit.predicate_signature(auth,task),audit.predicate_signature(order,task))
        self.assertNotEqual(audit.strict_signature(auth),audit.strict_signature(order))
        order['constraints'][0]['params'] = dict(before_role='run',after_role='approve')
        self.assertNotEqual(audit.predicate_signature(auth,task),audit.predicate_signature(order,task))

    def test_duplicate_conjunction_and_changed_threshold(self):
        # Logical idempotence: (cost <= 10 AND cost <= 10) == (cost <= 10).
        c = dict(type='budget',params=dict(max_total_cost_cny=10))
        single = audit.predicate_signature({'constraints':[c]}, {})
        self.assertEqual(single,audit.predicate_signature({'constraints':[c,c]},{}))
        self.assertNotEqual(single,audit.predicate_signature({'constraints':[dict(type='budget',params=dict(max_total_cost_cny=11))]},{}))

    def test_anchor_is_not_majority(self):
        # Two alternative seeds agreeing with each other do not support seed42.
        self.assertEqual(audit.support_for_first([('A',),('B',),('B',)]),1)

    def test_effect_gate_preserves_empty_view_objection(self):
        # View1 wants a new node; empty view2 sees only an unnecessary extra edit.
        old = [(0,0,1,0),(0,0,0,0),(0,0,1,0)]
        new = [(0,0,0,1),(0,0,0,1),(0,0,0,1)]
        self.assertTrue(impact.impact_accept(old,new,include_cost=False))
        self.assertFalse(impact.impact_accept(old,new,include_cost=True))
        self.assertFalse(impact.impact_accept(old,old,include_cost=True))
        self.assertFalse(impact.impact_accept(None,None,include_cost=True))

    def test_effect_gate_accepts_improvement_without_identity(self):
        # Three distinct constraints can all prefer the same legal correction.
        old = [(0,0,1,0),(0,0,2,0),(0,0,1,0)]
        new = [(0,0,0,1),(0,0,0,1),(0,0,0,1)]
        self.assertTrue(impact.impact_accept(old,new,include_cost=True))
        new[2] = (0,0,2,0)
        self.assertFalse(impact.impact_accept(old,new,include_cost=True))

    def test_missing_view_is_not_a_vote(self):
        before=[(0,0,1,0),None,(0,0,1,0)]
        after=[(0,0,0,1),None,(0,0,0,1)]
        self.assertTrue(impact.available_view_decisions([('a',),None,('b',)],before,after)['impact_with_cost_valid2'])
        self.assertFalse(impact.available_view_decisions([('a',),None,None],before,after)['impact_with_cost_valid2'])
        # A valid empty conjunction still objects to an unnecessary edit.
        before[2],after[2]=(0,0,0,0),(0,0,0,1)
        self.assertFalse(impact.available_view_decisions([('a',),None,()],before,after)['impact_with_cost_valid2'])


if __name__ == '__main__':
    unittest.main()
