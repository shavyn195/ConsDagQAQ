import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'scripts/research_followup'))
from planner_reward_probe import outcome_vector, select_panel, summarize_groups
from fixed_planner import planner_messages, select_groups
from wait_reward_probe import dependency_ready


def test_never_launch_before_both_dependencies_succeed():
    done = {'status':'complete'}
    queue = {'status':'complete', 'active':None}
    assert dependency_ready(queue,done,done)
    assert not dependency_ready(queue,{'status':'running'},done)
    assert not dependency_ready(queue,{'status':'incomplete'},done)
    assert not dependency_ready({'status':'running','active':None},done,done)
    assert not dependency_ready(queue,done,{})


def test_constant_failure_can_hide_different_constraint_results():
    # Four hand-built outcomes: all fail, but exactly one of two constraints passes.
    records = [dict(sample_id='s', arm='raw_request', draw=i,
                    signal=dict(scalar=0, components=[1,1,i%2,1-i%2],
                                constraint_passes=[i%2,1-i%2],valid=True)) for i in range(4)]
    result = summarize_groups(records,4)['raw_request']
    assert result['all_zero_groups'] == 1
    assert result['constant_scalar_variable_constraints_all_valid'] == 1
    assert summarize_groups(records[:3],4)['raw_request']['complete_prompt_groups'] == 0


def test_invalid_and_empty_output_never_get_safe_credit():
    row = {'gold':{'constraints':[{'type':'privacy'}]}}
    result = outcome_vector(row,None)
    assert result['scalar'] == 0 and result['components'] == [0,0,0]


def test_panel_excludes_prior_groups_and_does_not_use_labels():
    rows = [dict(group_id=f'g{i}',sample_id=f'g{i}-{v}',variant=v,gold='A')
            for i in range(7) for v in ('explicit','implicit','none')]
    config = dict(groups=2,exclude_fixed_planner_groups=3,selection_salt='salt:')
    panel = select_panel(rows,config)
    old = {r['group_id'] for r in select_groups(rows,3)}
    assert len(panel)==6 and not old.intersection(r['group_id'] for r in panel)
    changed = copy.deepcopy(rows)
    for row in changed:
        row['gold']='B'
    assert [r['sample_id'] for r in panel] == [r['sample_id'] for r in select_panel(list(reversed(changed)),config)]
