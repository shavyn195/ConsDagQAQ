import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/research_followup'))
from planner_learning_probe import policy_input
from planner_reward_probe import summarize_groups

def test_policy_and_information_are_separate_factors():
    assert policy_input('base_raw')==(False,False)
    assert policy_input('base_contract')==(False,True)
    assert policy_input('sft_raw')==(True,False)
    assert policy_input('sft_contract')==(True,True)
    try: policy_input('oracle_contract')
    except ValueError: pass
    else: raise AssertionError('Unknown arm accepted')

def test_summary_does_not_drop_new_arm_names_or_partial_calls():
    rows=[dict(sample_id='s',arm='sft_contract',draw=i,
        signal=dict(scalar=i%2,components=[1,1,i%2],constraint_passes=[i%2],valid=True)) for i in range(4)]
    r=summarize_groups(rows,4,['base_raw','sft_contract'])
    assert r['base_raw']['complete_prompt_groups']==0
    assert r['sft_contract']['complete_prompt_groups']==1
    assert r['sft_contract']['safe_calls']==2
    assert summarize_groups(rows[:3],4,['sft_contract'])['sft_contract']['partial_prompt_groups']==1
