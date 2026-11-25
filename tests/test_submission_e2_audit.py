"""Regression for N plan errors: explicit counts, not extraction false alarms."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("e2_audit", ROOT / "scripts/submission/audit_e2_public_contract.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_invalid_and_valid_changed_plans_are_separate():
    # Hand-counted N cohort: one invalid, one default, two changed => 1/4, 1/4, 2/4.
    rows = [
        dict(variant="none", planned=False, faithful_success=False, deviates_from_default=None),
        dict(variant="none", planned=True, faithful_success=True, deviates_from_default=False),
        dict(variant="none", planned=True, faithful_success=False, deviates_from_default=True),
        dict(variant="none", planned=True, faithful_success=False, deviates_from_default=True),
        dict(variant="implicit", planned=False, faithful_success=False, deviates_from_default=None),
    ]
    result = audit.none_summary(rows)
    assert result["counts"] == {"invalid_plan": 1, "valid_default": 1, "valid_changed": 2}
    assert result["faithful_rate"] == 0.25
    assert result["invalid_plan_rate"] == 0.25
    assert result["valid_deviation_rate"] == 0.5
    assert "none_false_alarm_rate" not in result


def test_invalid_plan_does_not_supply_observed_deviation():
    with pytest.raises(ValueError, match="Invalid plans"):
        audit.none_summary([dict(variant="none", planned=False, faithful_success=False,
                                deviates_from_default=True)])


def test_changed_n_plan_cannot_be_faithful():
    with pytest.raises(ValueError, match="N faithful"):
        audit.none_summary([dict(variant="none", planned=True, faithful_success=True,
                                deviates_from_default=True)])


def test_alignment_rejects_missing_duplicate_or_reordered_predictions():
    rows = [{"sample_id": "a"}, {"sample_id": "b"}]
    for invalid in (rows[:1], rows[::-1], [rows[0], rows[0]], rows + [{"sample_id": "c"}]):
        with pytest.raises(ValueError, match="records"):
            audit.require_aligned(rows, invalid)


def test_empty_n_cohort_is_not_a_zero_error_rate():
    with pytest.raises(ValueError, match="No N cohort"):
        audit.none_summary([])
