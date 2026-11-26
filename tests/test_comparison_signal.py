from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/research_followup'))
from audit_comparison_signal import vector_signal,summarize


def test_crossing_equal_count_vectors_have_no_pareto_supervision():
    # By the componentwise definition, neither [1,0] nor [0,1] dominates the other.
    x=vector_signal([[1,0],[0,1]])
    assert x['variable_but_no_dominance'] and x['dominance_edges']==0
    assert not x['all_pass_varies'] and not x['pass_rate_varies']


def test_all_pass_zero_can_still_have_verifiable_dominance():
    # Neither passes all checks, but the first strictly improves check 1 without harming check 2.
    x=vector_signal([[1,0],[0,0]])
    assert not x['all_pass_varies'] and x['pass_rate_varies'] and x['dominance_edges']==1


def test_invalid_and_none_do_not_count_as_constraint_information():
    records=[dict(sample_id=sid,arm='a',draw=i,signal=dict(valid=valid,components=vec,constraint_passes=cs))
             for sid,valid,vec,cs in [('invalid',False,[0,0,0],[0]),('N',True,[1,1],[])] for i in range(4)]
    result=summarize(records,4)
    assert result['arms']['a']['complete_prompt_groups']==2
    assert result['arms']['a']['all_valid_constrained_groups']==0
    assert result['cases'][1]['constraints_only'] is None
