"""Checks for pending ablations, independent of model quality."""
import json
from pathlib import Path
import sys

import unittest
from unittest.mock import patch
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import sub_e3_ablation as ablation


def sample(variant="none"):
    with (ROOT / "data/processed_v5/dev.jsonl").open(encoding="utf-8") as stream:
        return next(row for row in map(json.loads, stream) if row["variant"] == variant)


def check_inference_uses_the_training_contract(arm):
    row = sample("implicit")
    seen = []

    def render(tokenizer, messages, **kwargs):
        seen.append(messages)
        return {"input_ids": torch.tensor([[1, 2]])}

    class Tokenizer:
        pad_token_id = 0
        eos_token_id = 3
        def decode(self, ids, **kwargs):
            return "result"

    class Model:
        def parameters(self):
            yield torch.tensor(1.0)
        def generate(self, input_ids, **kwargs):
            return torch.cat([input_ids, torch.tensor([[3]])], dim=1)

    with patch.object(ablation, "render_chat", render):
        assert ablation.generate_ablated(Model(), Tokenizer(), [row], arm, 384, 1) == ["result"]
    assert seen == [ablation.ablated_chat_messages(row, arm)]


def test_empty_constraints_and_malformed_output_are_distinguished():
    row = sample()
    good = ablation.downstream_faithful([row], ['{"constraints":[]}'])
    bad = ablation.downstream_faithful([row], ['not json'])
    assert good["none_valid_faithful"] == 1
    assert bad["none_valid_faithful"] == 0
    # Historical v5 fallback remains separately reported, never silently overwritten.
    assert bad["none_faithful"] == 1
    assert bad["invalid_output_rate"] == 1
    with unittest.TestCase().assertRaisesRegex(ValueError, "coverage"):
        ablation.downstream_faithful([row], [])


def test_string_representation_preserves_execution_semantics():
    row = sample("explicit")
    typed = json.dumps({"constraints": row["gold"]["constraints"]})
    strings = ablation.ablated_target(row, "A1")
    a = ablation.downstream_faithful([row], [typed])
    b = ablation.downstream_faithful([row], [strings])
    assert a["valid_faithful_constrained"] == b["valid_faithful_constrained"] == 1


class SubmissionChecks(unittest.TestCase):
    def test_training_inference_parity(self):
        for arm in ("A1", "A2", "A3", "A4"):
            with self.subTest(arm=arm):
                check_inference_uses_the_training_contract(arm)

    def test_invalid_none(self):
        test_empty_constraints_and_malformed_output_are_distinguished()

    def test_string_representation(self):
        test_string_representation_preserves_execution_semantics()


if __name__ == "__main__":
    unittest.main()
