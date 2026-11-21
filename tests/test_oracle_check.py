from oracle_check import recovered_constraints


def test_oracle_recovery_requires_object_with_constraint_list():
    assert recovered_constraints(None) is None
    assert recovered_constraints({"constraints": "not-a-list"}) is None
    assert recovered_constraints({"constraints": [{"type": "budget"}]}) == [{"type": "budget"}]


def test_oracle_recovery_rejects_non_object_constraint_entries():
    assert recovered_constraints({"constraints": ["budget"]}) is None
