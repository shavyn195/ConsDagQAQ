import copy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts/research_followup'))
from matched_content_controls import require_same_recipe,first_messages,RECIPE_KEYS
from fixed_planner import summary_messages


def sample():
    return dict(query='Do the task.',catalog=[],spec_version='v6',gold={'secret':'DO_NOT_EXPOSE'},
        witness_plan=['secret'],variant='explicit',group_id='hidden',task=dict(data_class='normal',stages=[],finish=[],optional=[],tools={}))


def test_recipe_changes_fail_closed():
    cfg={k:1 for k in RECIPE_KEYS};require_same_recipe(cfg,dict(cfg))
    changed={**cfg,'learning_rate':2}
    try:require_same_recipe(changed,cfg)
    except ValueError as exc:assert 'learning_rate' in str(exc)
    else:raise AssertionError('Unmatched recipe accepted')


def test_generic_uses_exact_frozen_prompt():
    row=sample();before=copy.deepcopy(row)
    assert first_messages(row,'generic')==summary_messages(row)
    assert row==before
    assert 'DO_NOT_EXPOSE' not in str(first_messages(row,'generic'))


def test_pe_only_receives_public_fields():
    captured=[]
    def compiler(row):captured.append(row);return ['unchanged']
    assert first_messages(sample(),'pe',compiler)==['unchanged']
    assert set(captured[0])=={'query','catalog','task','spec_version'}
    try:first_messages(sample(),'oracle',compiler)
    except ValueError:pass
    else:raise AssertionError('Unregistered control accepted')
