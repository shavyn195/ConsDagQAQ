import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oracle_check import recovered_constraints, render_recover_prompt  # noqa: E402


def test_oracle_recovery_requires_object_with_constraint_list():
    assert recovered_constraints(None) is None
    assert recovered_constraints({"constraints": "not-a-list"}) is None
    assert recovered_constraints({"constraints": [{"type": "budget"}]}) == [{"type": "budget"}]


def test_oracle_recovery_rejects_non_object_constraint_entries():
    assert recovered_constraints({"constraints": ["budget"]}) is None


def test_oracle_prompt_preserves_json_schema_and_query_braces():
    query = 'The task metadata is {"budget": 4}; do not infer a cap.'
    prompt = render_recover_prompt(query)
    assert 'Output JSON only: {"constraints":[{"type":"budget|deadline|privacy|tool_auth|order",' in prompt
    assert prompt.endswith("Query:\n" + query)
