"""Gold isolation and strict execution checks for the external consumer arm."""
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("deepseek_planner", ROOT / "scripts/submission/deepseek_planner.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row():
    with (ROOT / "data/processed_v5/dev.jsonl").open(encoding="utf-8") as stream:
        return json.loads(next(stream))


def test_gold_and_witness_cannot_change_the_request():
    first = row()
    second = copy.deepcopy(first)
    second.update(gold={"hidden": "SECRET_GOLD"}, witness_plan=["SECRET_WITNESS"], query="SECRET_QUERY")
    assert module.messages(first, []) == module.messages(second, [])
    assert "SECRET" not in json.dumps(module.messages(second, []))


def test_executor_accepts_witness_and_rejects_duplicate_and_missing_plans():
    r = row()
    assert module.outcome(r, r["witness_plan"])["safe"]
    assert not module.outcome(r, None)["faithful"]
    assert not module.outcome(r, r["witness_plan"] * 2)["valid"]
    assert not module.outcome(r, ["unknown_role"])["valid"]
