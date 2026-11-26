import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/research_followup'))
from matched_planner_sft import select_additional

def test_new_training_excludes_whole_pretraining_groups():
    rows=[dict(sample_id=g+v,group_id=g,variant=v,subset='train')
          for g in ('a','b','c','d') for v in ('explicit','implicit','none')]
    selected=select_additional(rows,['aexplicit','bnone'],2,'fixed:',[])
    assert {r['group_id'] for r in selected}=={'c','d'}
    assert len(selected)==6

def test_new_training_still_rejects_evaluation_leakage():
    rows=[dict(sample_id='g'+v,group_id='g',variant=v,subset='train')
          for v in ('explicit','implicit','none')]
    try: select_additional(rows,[],1,'s:',[dict(sample_id='dev',group_id='g')])
    except ValueError: pass
    else: raise AssertionError('Evaluation group leaked into training')
