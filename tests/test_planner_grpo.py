import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/research_followup'))
from planner_grpo_core import group_advantages,completion_ids


def test_binary_population_advantage():
    # Analytic population mean=.5 and std=.5 for [0,0,1,1].
    expected=.5/(.5+1e-4)
    assert group_advantages([0,0,1,1])==[-expected,-expected,expected,expected]
    assert group_advantages([1,1,1,1])==[0.,0.,0.,0.]


def test_advantage_shift_and_scale():
    # With epsilon zero, standardization is invariant under a positive affine transform.
    a=group_advantages([1,2,4,5],0)
    b=group_advantages([12,14,18,20],0)
    assert all(math.isclose(x,y,abs_tol=1e-12) for x,y in zip(a,b))
    assert abs(sum(a))<1e-12
    assert math.isclose(sum(x*x for x in a)/4,1.)


def test_completion_eos_and_cap():
    # Prompt tokens, even an EOS in the prompt, are never policy-gradient targets.
    assert completion_ids([9,2,7,8,2,2,2],2,2)==[7,8,2]
    assert completion_ids([9,2,7,8],2,2)==[7,8]
    try:completion_ids([9,2],2,2)
    except ValueError:pass
    else:raise AssertionError('Empty completion accepted')


def test_nonfinite_reward_rejected():
    for rewards in ([1.], [0.,float('nan')]):
        try:group_advantages(rewards)
        except ValueError:pass
        else:raise AssertionError('Invalid reward group accepted')
