import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dataset_v5_spec import POLICY_CARD
from sub_e2_public_contract import public_messages


def sample():
    with (ROOT / "data/processed_v5/train.jsonl").open(encoding="utf-8") as f:
        return json.loads(next(f))


def test_control_includes_all_public_input_information():
    row = sample()
    prompt = public_messages(row)[1]["content"]
    assert POLICY_CARD in prompt
    assert row["query"] in prompt
    assert row["task"]["data_class"] in prompt
    for tool in row["catalog"]:
        assert tool["name"] in prompt
        assert tool["role"] in prompt


def test_control_never_uses_gold_or_witness():
    row = sample()
    changed = copy.deepcopy(row)
    changed["gold"] = {"constraints": [{"hidden": "SECRET_GOLD"}]}
    changed["witness_plan"] = ["SECRET_WITNESS"]
    changed["variant"] = "SECRET_VARIANT"
    assert public_messages(row) == public_messages(changed)
