import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/research_followup'))
from audit_record_metadata import describe


class MetadataAuditTest(unittest.TestCase):
    def setUp(self):
        self.gold={'query_state':'explicit','constraints':[dict(type='privacy',state='explicit',severity='high',
            scope=['role:a','role:b'],params={'forbidden_recipients':['external']},evidence_span='private')]}

    def test_scope_order_and_evidence_are_not_strict_errors(self):
        p=copy.deepcopy(self.gold)
        p['constraints'][0]['scope'].reverse()
        p['constraints'][0]['evidence_span']='different evidence'
        # Frozen constraint_key treats scope order as irrelevant and scores evidence separately.
        self.assertEqual(describe(self.gold,json.dumps(p))['category'],'record_exact')

    def test_scope_diff_preserves_core(self):
        p=copy.deepcopy(self.gold); p['constraints'][0]['scope']=['role:a']
        d=describe(self.gold,json.dumps(p))
        self.assertEqual(d['category'],'metadata_only')
        self.assertEqual(d['differences'][0]['fields'],['scope'])

    def test_param_error_and_invalid_are_not_metadata(self):
        p=copy.deepcopy(self.gold); p['constraints'][0]['params']['forbidden_recipients']=['local']
        self.assertEqual(describe(self.gold,json.dumps(p))['category'],'core_mismatch')
        self.assertEqual(describe(self.gold,'{')['category'],'invalid_output')

    def test_duplicate_core_alignment_not_guessed(self):
        g=copy.deepcopy(self.gold); g['constraints']*=2
        p=copy.deepcopy(g)
        for c in p['constraints']: c['scope']=['role:c']
        d=describe(g,json.dumps(p))
        self.assertEqual(d['ambiguous_clauses'],2)
        self.assertEqual(d['differences'],[])


if __name__=='__main__':
    unittest.main()
