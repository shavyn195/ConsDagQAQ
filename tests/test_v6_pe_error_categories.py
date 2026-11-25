from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/submission"))
from compare_v6_record_errors import category


def test_core_error_is_not_hidden_by_a_simultaneous_scope_error():
    # Constructed record has unmatched consumed params and unconsumed fields.
    assert category({"core_missing": 1, "core_extra": 1, "strict_record_exact": False}, valid=True) == "core_reference_mismatch"


def test_unconsumed_and_top_state_mismatches_require_exact_core_keys():
    # All consumed keys match, while strict record equality fails.
    assert category({"core_missing": 0, "core_extra": 0, "strict_record_exact": False}, valid=True) == "unconsumed_fields_or_query_state_mismatch"


def test_invalid_output_is_not_treated_as_an_empty_valid_reference():
    # A parse failure must take precedence even if an empty fallback key matches.
    assert category({"core_missing": 0, "core_extra": 0, "strict_record_exact": True}, valid=False) == "parse_failure"
    assert category({"core_missing": 0, "core_extra": 0, "strict_record_exact": True}, valid=True) == "strict_reference_exact"
