from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import run_e1_v6


def test_v6_entry_point_defaults_are_isolated_without_importing_torch(monkeypatch):
    monkeypatch.setattr(run_e1_v6, "validate_v6_freeze", lambda _: None)
    args = run_e1_v6.v6_arguments(["--model", "models/Qwen3-4B", "--seed", "44"])
    assert args[args.index("--precision") + 1] == "bf16"
    assert args[args.index("--eval-batch-size") + 1] == "16"
    assert Path(args[args.index("--data-dir") + 1]) == ROOT / "data/processed_v6"
    assert Path(args[args.index("--out-dir") + 1]) == ROOT / "outputs/e1_v6/Qwen3-4B-v6-seed44"


def test_v6_entry_point_rejects_historical_output_and_wrong_precision(monkeypatch):
    monkeypatch.setattr(run_e1_v6, "validate_v6_freeze", lambda _: None)
    with pytest.raises(ValueError, match="historical"):
        run_e1_v6.v6_arguments(["--out-dir", str(ROOT / "outputs/e1/v5-results")])
    with pytest.raises(SystemExit):
        run_e1_v6.v6_arguments(["--precision", "fp16"])


def test_v6_protocol_is_fixed_to_registered_models_seeds_and_hyperparameters(monkeypatch):
    monkeypatch.setattr(run_e1_v6, "validate_v6_freeze", lambda _: None)
    for args, message in [
        (["--model", "models/Qwen3-7B"], "requires Qwen3"),
        (["--seed", "45"], "seed 42"),
        (["--epochs", "2"], "requires epochs=3"),
        (["--learning-rate", "0.0001"], "requires learning_rate=0.0002"),
    ]:
        with pytest.raises(ValueError, match=message):
            run_e1_v6.v6_arguments(args)


def test_token_coverage_rejects_training_truncation_and_oversized_gold(monkeypatch, tmp_path):
    class Tokenizer:
        eos_token = "<eos>"
        prefix_length = 5

        def apply_chat_template(self, *_args, **_kwargs):
            return [1] * self.prefix_length

        def __call__(self, text, **_kwargs):
            return {"input_ids": [1] * len(text)}

    rows = [{"sample_id": f"row-{i}", "target": "gold"} for i in range(4)]
    monkeypatch.setattr(run_e1_v6, "SUBSETS", ("train",))
    monkeypatch.setattr(run_e1_v6.run_e1, "load_jsonl", lambda _: rows)
    monkeypatch.setattr(run_e1_v6.run_e1, "chat_messages", lambda _row: [])
    monkeypatch.setattr(run_e1_v6.run_e1, "target_json", lambda row: row["target"])
    result = run_e1_v6.token_coverage(Tokenizer(), tmp_path)
    assert result["status"] == "PASS"
    assert result["splits"]["train"]["records"] == 4
    assert result["splits"]["train"]["dropped"] == 0

    # Fixed protocol: train total <=1280, gold (including EOS) <=384.
    tokenizer = Tokenizer()
    tokenizer.prefix_length = 1000
    rows[0]["target"] = "x" * 300
    with pytest.raises(ValueError, match=r"prompt\+gold=1305"):
        run_e1_v6.token_coverage(tokenizer, tmp_path)
    tokenizer.prefix_length = 5
    rows[0]["target"] = "x" * 380
    with pytest.raises(ValueError, match="token coverage failed"):
        run_e1_v6.token_coverage(tokenizer, tmp_path)
