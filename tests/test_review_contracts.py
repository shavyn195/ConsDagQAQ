import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/research_followup'))
from review_contracts import messages, project_fields, repair_slots
from review_contracts_format import messages as format_messages
from run_e1 import SCHEMA_HINT_V4


class ReviewContractsTest(unittest.TestCase):
    def setUp(self):
        self.task = {'tools': {'approval': {}, 'cloud': {}, 'local': {}}}
        self.before = {'query_state': 'explicit', 'constraints': [dict(type='tool_auth',state='explicit',severity='medium',scope=['role:local'],params={'approval_role':'bad_name','required_role':'local'})]}

    def test_field_only_keeps_valid_but_wrong_target(self):
        reviewed = copy.deepcopy(self.before)
        reviewed['constraints'][0]['params'] = {'approval_role':'approval','required_role':'cloud'}
        result = project_fields(self.before, reviewed, self.task)
        # Only bad_name is outside the catalogue. The valid local target is frozen by this control arm.
        self.assertEqual(result['constraints'][0]['params'], {'approval_role':'approval','required_role':'local'})
        self.assertEqual(self.before['constraints'][0]['params']['approval_role'], 'bad_name')

    def test_no_silent_empty_contract_on_failed_parse(self):
        # A failed parser cannot justify declaring that the request has no constraints.
        self.assertIsNone(project_fields(None, {'query_state':'none','constraints':[]}, self.task))
        self.assertIsNone(project_fields(self.before, None, self.task))
        self.assertIsNone(project_fields(self.before, {'query_state':'none','constraints':[]}, self.task))

    def test_prompt_does_not_expose_labels(self):
        row = dict(query='Get approval before cloud use.',catalog=[],task=self.task,spec_version='v5',
                   gold={'sentinel':'PRIVATE_GOLD'},witness='PRIVATE_WITNESS',variant='PRIVATE_VARIANT',group_id='PRIVATE_GROUP')
        for arm in ('invalid_fields','full_binding','fresh_compile'):
            prompt = json.dumps(messages(row,json.dumps(self.before),['local'],arm))
            for secret in ('PRIVATE_GOLD','PRIVATE_WITNESS','PRIVATE_VARIANT','PRIVATE_GROUP'):
                self.assertNotIn(secret,prompt)
            self.assertIn('Get approval before cloud use.',prompt)

    def test_format_reminder_preserves_shared_evidence(self):
        row = dict(query='Get approval before cloud use.',catalog=[],task=self.task,spec_version='v5',
                   gold={'sentinel':'PRIVATE_GOLD'},witness='PRIVATE_WITNESS',variant='PRIVATE_VARIANT',group_id='PRIVATE_GROUP')
        contexts=[]
        for arm in ('invalid_fields','full_binding','fresh_compile'):
            before=messages(row,json.dumps(self.before),['local'],arm)
            after=format_messages(row,json.dumps(self.before),['local'],arm)
            # Format smoke must append instructions without removing evidence or leaking labels.
            self.assertTrue(after[-1]['content'].startswith(before[-1]['content']))
            self.assertIn(SCHEMA_HINT_V4,after[-1]['content'])
            self.assertTrue(after[-1]['content'].endswith('Contract JSON:'))
            contexts.append(after[-1]['content'].split('Review context (draft can contain mistakes):\n')[1].split('\n')[0])
            for secret in ('PRIVATE_GOLD','PRIVATE_WITNESS','PRIVATE_VARIANT','PRIVATE_GROUP'):
                self.assertNotIn(secret,json.dumps(after))
        self.assertEqual(len(set(contexts)),1)


if __name__ == '__main__':
    unittest.main()
