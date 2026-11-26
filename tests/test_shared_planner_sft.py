import copy
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts/research_followup'))
from shared_planner_sft import accumulation_batches, select_training, training_target
from format_recovery import explicit_messages
from wait_shared_planner_sft import dependency_action


def rejected(function):
    try: function()
    except ValueError: return
    raise AssertionError('Unsafe input accepted')


def test_group_selection_rejects_eval_and_is_target_independent():
    rows=[dict(sample_id=g+v,group_id=g,variant=v,subset='train',gold='unused')
          for g in ('a','b','c') for v in ('explicit','implicit','none')]
    chosen=select_training(rows,2,'salt:',[])
    changed=copy.deepcopy(list(reversed(rows)))
    for r in changed: r['gold']='different target'
    assert {r['sample_id'] for r in chosen}=={r['sample_id'] for r in select_training(changed,2,'salt:',[])}
    assert len(chosen)==6
    rejected(lambda:select_training(rows,2,'salt:',[dict(group_id='a',sample_id='dev')]))
    changed[0]['subset']='dev'
    rejected(lambda:select_training(changed,2,'salt:',[]))
    rejected(lambda:select_training(rows+rows[:1],2,'salt:',[]))


def toy():
    tools={r:dict(cost_cny=c,duration_min=1,recipient='local',clears_pii=False)
           for r,c in [('a',10),('cheap',1),('b',0),('f',0),('g',0),('approve',0)]}
    task=dict(data_class='',tools=tools,stages=[dict(default='a',alternatives=['a','cheap']),
         dict(default='b',alternatives=['b'])],finish=['f','g'],optional={'approve':['b']})
    return dict(sample_id='train-x',group_id='train-g',variant='explicit',subset='train',task=task,
        gold={'constraints':[{'type':'budget','params':{'max_total_cost_cny':2}}]},
        witness_plan=['cheap','b','f','g'],query='Spend at most 2.',
        catalog=[dict(role=r,name=r) for r in tools])


def test_targets_verified_but_never_in_prompt():
    row=toy()
    # Cost 1 <= 2 is feasible and needs exactly one substitution; cost 10 is infeasible.
    assert json.loads(training_target(row))==['cheap','b','f','g']
    altered=copy.deepcopy(row)
    altered.update(gold='PRIVATE-GOLD',witness_plan='PRIVATE-WITNESS',variant='PRIVATE-VARIANT')
    assert explicit_messages(row)==explicit_messages(altered)
    row['witness_plan']=['a','b','f','g']
    rejected(lambda:training_target(row))
    row['gold']={'constraints':[]}; row['variant']='none'
    row['witness_plan']=['cheap','b','f','g']
    # In N, the required target is the unchanged default even when a stale witness differs.
    assert json.loads(training_target(row))==['a','b','f','g']


def test_no_underweighted_or_dropped_accumulation_tail():
    assert accumulation_batches(list(range(8)),4)==[[0,1,2,3],[4,5,6,7]]
    rejected(lambda:accumulation_batches(list(range(7)),4))
    rejected(lambda:accumulation_batches([],4))


def test_conditional_launch_needs_completed_format_failure():
    assert dependency_action({'status':'running'},{'status':'smoke_gate_failed'})=='wait'
    assert dependency_action({'status':'complete'},{'status':'smoke_gate_failed'})=='train'
    assert dependency_action({'status':'complete'},{'status':'complete'})=='skip'
    assert dependency_action({'status':'incomplete'},{'status':'smoke_gate_failed'})=='skip'
    assert dependency_action({'status':'failed'}, {})=='skip'


def test_registered_new_followup_accepts_success_but_not_crash():
    assert dependency_action({'status':'complete'},{'status':'complete'},['complete'])=='train'
    assert dependency_action({'status':'failed'},{'status':'complete'},['complete'])=='skip'
    assert dependency_action({'status':'complete'},{'status':'budget_exhausted'},['complete'])=='skip'
    assert dependency_action({'status':'complete'},{'status':'smoke_gate_failed'},['complete'])=='skip'
