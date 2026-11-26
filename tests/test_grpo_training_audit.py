from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/research_followup'))
from audit_grpo_training_readout import group_diagnostics


def item(draw, reward, passes, *, safe=False, valid=True):
    return dict(draw=draw, reward=reward,
        signal=dict(valid=valid, constraint_passes=passes),
        outcome=dict(planned=valid, safe_success=safe, faithful_success=bool(reward)))


def test_all_zero_can_have_partial_constraint_signal():
    # Both violate at least one of two constraints; only the second improves one.
    result = group_diagnostics([item(0, 0., [0, 0]), item(1, 0., [1, 0])])
    assert result['all_zero_reward_varying_constraints_all_valid'] == 1
    assert result['varying_reward'] == 0
    assert result['constant_reward_but_pass_fraction_varies'] == 1
    assert result['constant_reward_but_pareto_order_exists'] == 1


def test_tradeoff_is_not_mistaken_for_dominance():
    # [1,0] and [0,1] have equal pass count and neither Pareto-dominates the other.
    result = group_diagnostics([item(0, 0., [1, 0]), item(1, 0., [0, 1])])
    assert result['constant_reward_but_pass_fraction_varies'] == 0
    assert result['constant_reward_but_pareto_order_exists'] == 0
    assert result['varying_constraints_but_no_pareto_order'] == 1


def test_none_is_not_a_perfect_constraint_group():
    # An empty constraint vector supplies no constraint-credit learning signal.
    result = group_diagnostics([item(0, 1., [], safe=True), item(1, 1., [], safe=True)])
    assert result['all_reward_one'] == 1
    assert result['constant_reward_varying_constraints_all_valid'] == 0


def test_invalid_and_nonminimal_are_not_conflated():
    result = group_diagnostics([item(0, 0., [0, 0], valid=False), item(1, 0., [1, 1], safe=True)])
    assert result['all_zero_reward_varying_constraints_all_valid'] == 0
    assert result['safe_but_nonminimal_calls'] == 1
    assert result['valid_calls'] == 1


def test_duplicate_draw_rejected():
    try:
        group_diagnostics([item(0, 0., []), item(0, 0., [])])
    except ValueError:
        pass
    else:
        raise AssertionError('Duplicate draw accepted')
