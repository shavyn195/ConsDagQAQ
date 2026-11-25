"""Closed-form cases for paired group-bootstrap reporting."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts/architecture/analyze_pointer_pilot.py"
spec = importlib.util.spec_from_file_location("pointer_analysis", path)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def test_identical_outcomes_and_constant_effect():
    # Every resampled group has difference zero (or one), so these intervals
    # follow analytically and do not depend on the bootstrap random sequence.
    a = [{"group_id": str(i), "subset": "1", "n": False, "faithful": True} for i in range(3)]
    b = [dict(r, faithful=False) for r in a]
    assert analysis.compare(a, a)["descriptive_group_bootstrap_95ci_pp"] == [0, 0]
    assert analysis.compare(a, b)["descriptive_group_bootstrap_95ci_pp"] == [100, 100]


def test_unpaired_outcomes_cannot_be_compared():
    a = [{"group_id": "a", "subset": "1", "n": False, "faithful": True}]
    with unittest.TestCase().assertRaises(ValueError):
        analysis.compare(a, [])
