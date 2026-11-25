"""Expected outcomes follow from explicitly enumerated two-choice toy tasks."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import trust_env as env

spec = importlib.util.spec_from_file_location("architecture_audit", ROOT / "scripts/architecture/audit_solver_supervision.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def task(tie=False):
    # Default costs 10; alternatives a,b cost 0. Replacing default costs one edit.
    tools = {r: {"cost_cny": cost, "duration_min": 1, "recipient": "local", "clears_pii": False}
             for r, cost in [("default", 10), ("a", 0), ("b", 0), ("finish", 0)]}
    return {"stages": [{"alternatives": ["default", "a", "b"] if tie else ["default", "a"],
                         "default": "default"}], "finish": ["finish"], "optional": {},
            "tools": tools, "data_class": None}


BUDGET = {"type": "budget", "params": {"max_total_cost_cny": 0}}


def test_minimum_set_does_not_treat_second_optimum_as_negative():
    t = task(tie=True)
    opts = audit.optimal_plans(t, [BUDGET], audit.enumerate_plans(t, env), env)
    assert {tuple(x[0]) for x in opts} == {("a", "finish"), ("b", "finish")}
    assert all(x[2] == 1 for x in opts)


def test_duplicate_constraints_have_zero_loo_but_require_edit():
    t = task()
    result = audit.duplicate_probe(t, BUDGET, audit.enumerate_plans(t, env), env)
    assert result == {"requires_edit": True, "duplicate_preserves_plan": True,
                      "both_leave_one_out_differences_empty": True}


def test_unknown_constraints_fail_closed():
    t = task()
    try:
        audit.optimal_plans(t, [{"type": "unknown"}], audit.enumerate_plans(t, env), env)
    except ValueError:
        pass
    else:
        raise AssertionError("Unusable constraint was silently ignored")


def test_precedence_is_conditional_on_target_presence():
    t = task()
    c = {"type": "order", "params": {"before_role": "b", "after_role": "a"}}
    opts = audit.optimal_plans(t, [c], audit.enumerate_plans(t, env), env)
    assert opts[0][0] == ["default", "finish"]
    assert opts[0][2] == 0
