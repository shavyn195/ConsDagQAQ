import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/research_followup'))
sys.path.insert(0, str(ROOT/'src'))
from common import evaluate_plan, intervene, public_row
from fixed_planner import planner_messages, select_groups
from waiter import ready


def toy():
    tools = {r: dict(cost_cny=c, duration_min=1, recipient='local', clears_pii=False)
             for r,c in [('a',10), ('cheap',1), ('b',0), ('f',0), ('g',0), ('approve',0)]}
    task = dict(data_class='', tools=tools, stages=[dict(default='a',alternatives=['a','cheap']),
                dict(default='b',alternatives=['b'])], finish=['f','g'], optional={'approve':['b']})
    budget = {'type':'budget','params':{'max_total_cost_cny':2}}
    row = dict(sample_id='x', group_id='g', variant='explicit', task=task, gold={'constraints':[budget]},
               witness_plan=['cheap','b','f','g'], query='Spend at most 2.', catalog=[])
    return row, ['a','b','f','g'], {'constraints':[budget]}


def test_budget_repair_is_correct_without_gold_access():
    row, original, parsed = toy()
    result = intervene(row['task'], original, parsed, row['sample_id'])
    # Hand calculation: original costs 10; substituting cheap costs 1 <= 2, exactly one edit.
    assert result['repaired'] == ['cheap','b','f','g']
    assert not evaluate_plan(row, original)['safe_success']
    assert evaluate_plan(row, result['repaired'])['faithful_success']
    assert row['task']['stages'][0]['default'] == 'a'


def test_invalid_compile_never_becomes_empty_constraint_plan():
    row, original, _ = toy()
    for parsed in (None, {'constraints':[{'type':'unknown','params':{}}]}):
        out = intervene(row['task'], original, parsed, 'x')
        assert out['repaired'] == original and out['symbolic'] is None and not out['usable']


def test_n_unchanged_and_invalid_are_distinct():
    row, original, _ = toy()
    row.update(variant='none', gold={'constraints':[]})
    assert evaluate_plan(row, original)['faithful_success']
    assert evaluate_plan(row, None)['deviates_from_default'] is None
    changed = evaluate_plan(row, ['cheap','b','f','g'])
    assert changed['safe_success'] and not changed['faithful_success']


def test_public_view_removes_all_labels():
    row, _, _ = toy()
    altered = copy.deepcopy(row)
    altered.update(gold='SECRET', witness_plan='SECRET', variant='SECRET', group_id='SECRET')
    assert public_row(row) == public_row(altered)


def test_queue_completion_gate_rejects_idle_gap_and_failed_queue():
    assert not ready({'status':'running', 'active':None})
    assert not ready({'status':'incomplete', 'active':None})
    assert not ready({'status':'complete', 'active':{'pid':1}})
    assert ready({'status':'complete', 'active':None})


def test_planner_prompt_gold_independent_and_group_sampling_balanced():
    import json
    with (ROOT/'data/processed_v6/dev.jsonl').open(encoding='utf-8') as f:
        rows=[json.loads(line) for line in f]
    row=rows[0]
    changed=copy.deepcopy(row)
    changed.update(gold='SECRET',witness_plan='SECRET',variant='SECRET')
    assert planner_messages(row) == planner_messages(changed)
    panel=select_groups(rows,3)
    assert len(panel)==9 and len({r['group_id'] for r in panel})==3
    assert {r['sample_id'] for r in panel}=={r['sample_id'] for r in select_groups(list(reversed(rows)),3)}


def test_compiler_prompt_keeps_frozen_policy_version():
    import json
    from run_e1 import chat_messages
    with (ROOT/'data/processed_v6/dev.jsonl').open(encoding='utf-8') as f:
        row=json.loads(next(f))
    assert chat_messages(public_row(row))==chat_messages(row)
