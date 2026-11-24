"""Full v6 training with a fixed bf16 protocol and frozen-data guards."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path

import run_e1
from build_dataset_v6 import SUBSETS

ROOT = Path(__file__).resolve().parents[1]
MODELS = ("Qwen3-0.6B", "Qwen3-1.7B", "Qwen3-4B")
EVAL_BATCH_SIZES = {"Qwen3-0.6B": 48, "Qwen3-1.7B": 32, "Qwen3-4B": 16}
FIXED_PROTOCOL = {
    "epochs": 3, "learning_rate": 2e-4, "lora_rank": 16, "lora_alpha": 32,
    "gradient_accumulation_steps": 4, "max_seq_len": 1280, "max_new_tokens": 384,
}


def validate_v6_freeze(data_dir: Path) -> None:
    generation = json.loads((data_dir / "generation_report.json").read_text(encoding="utf-8"))
    verification = json.loads((data_dir / "verification_report.json").read_text(encoding="utf-8"))
    if generation.get("spec_version") != "v6" or verification.get("verdict") != "PASS":
        raise ValueError("v6 requires a generated dataset with independent verification PASS")
    actual = {subset: hashlib.sha256((data_dir / f"{subset}.jsonl").read_bytes()).hexdigest()
              for subset in SUBSETS}
    if generation.get("sha256") != actual or verification.get("sha256") != actual:
        raise ValueError("v6 data differs from the frozen generation/verification hashes")


def protocol_parser() -> argparse.ArgumentParser:
    defaults = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    defaults.add_argument("--data-dir", type=Path, default=ROOT / "data/processed_v6")
    defaults.add_argument("--model", default=str(ROOT / "models/Qwen3-0.6B"))
    defaults.add_argument("--out-dir", type=Path)
    defaults.add_argument("--seed", type=int, default=42)
    defaults.add_argument("--precision", choices=("bf16",), default="bf16")
    for name, value in FIXED_PROTOCOL.items():
        defaults.add_argument("--" + name.replace("_", "-"), type=type(value), default=value)
    defaults.add_argument("--eval-batch-size", type=int)
    defaults.add_argument("--skip-zeroshot", action="store_true")
    return defaults


def v6_arguments(argv: list[str]) -> list[str]:
    args = protocol_parser().parse_args(argv)
    if Path(args.model).name not in MODELS or args.seed not in (42, 43, 44):
        raise ValueError("v6 requires Qwen3-0.6B/1.7B/4B and seed 42, 43 or 44")
    for name, value in FIXED_PROTOCOL.items():
        if getattr(args, name) != value:
            raise ValueError(f"the registered v6 protocol requires {name}={value}")
    expected_batch = EVAL_BATCH_SIZES[Path(args.model).name]
    if args.eval_batch_size is not None and args.eval_batch_size != expected_batch:
        raise ValueError(f"the registered v6 protocol requires eval_batch_size={expected_batch}")
    args.eval_batch_size = expected_batch
    validate_v6_freeze(args.data_dir)
    out_dir = args.out_dir or ROOT / "outputs/e1_v6" / f"{Path(args.model).name}-v6-seed{args.seed}"
    historical = (ROOT / "outputs/e1").resolve()
    if out_dir.resolve() == historical or historical in out_dir.resolve().parents:
        raise ValueError("v6 outputs must not overwrite historical outputs/e1")
    forwarded = ["--model", str(args.model), "--seed", str(args.seed), "--data-dir", str(args.data_dir),
                 "--out-dir", str(out_dir), "--precision", "bf16", "--eval-batch-size", str(expected_batch)]
    for name, value in FIXED_PROTOCOL.items():
        forwarded.extend(["--" + name.replace("_", "-"), str(value)])
    if args.skip_zeroshot:
        forwarded.append("--skip-zeroshot")
    return forwarded


def token_coverage(tokenizer: object, data_dir: Path) -> dict:
    """Reject any silent training truncation using the model's actual tokenizer."""
    result = {"status": "PASS", "max_seq_len": 1280, "max_new_tokens": 384, "splits": {}}
    for subset in SUBSETS:
        rows = run_e1.load_jsonl(data_dir / f"{subset}.jsonl")
        max_total = max_target = 0
        for row in rows:
            messages = run_e1.chat_messages(row)
            try:
                prefix = tokenizer.apply_chat_template(
                    messages, tokenize=True, add_generation_prompt=True, enable_thinking=False,
                )
            except TypeError:
                prefix = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
            if isinstance(prefix, Mapping):
                prefix = prefix["input_ids"]
            if hasattr(prefix, "tolist"):
                prefix = prefix.tolist()
            if prefix and isinstance(prefix[0], (list, tuple)):
                prefix = prefix[0]
            target = tokenizer(run_e1.target_json(row) + tokenizer.eos_token,
                               add_special_tokens=False)["input_ids"]
            if hasattr(target, "tolist"):
                target = target.tolist()
            if target and isinstance(target[0], (list, tuple)):
                target = target[0]
            total, generated = len(prefix) + len(target), len(target)
            max_total, max_target = max(max_total, total), max(max_target, generated)
            if (subset == "train" and total > 1280) or generated > 384:
                raise ValueError(f"v6 token coverage failed: {row['sample_id']} in {subset}: "
                                 f"prompt+gold={total}, gold_with_eos={generated}; dataset preserved")
        if subset == "train" and len(rows) % FIXED_PROTOCOL["gradient_accumulation_steps"]:
            raise ValueError("v6 train count must divide accumulation=4 for complete three-epoch coverage")
        result["splits"][subset] = {"records": len(rows), "max_prompt_plus_gold": max_total,
                                    "max_gold_with_eos": max_target, "dropped": 0}
    return result


def main() -> None:
    argv = sys.argv[1:]
    forwarded = v6_arguments(argv)
    args = protocol_parser().parse_args(forwarded)
    import torch
    from transformers import AutoTokenizer

    if not torch.cuda.is_available() or torch.cuda.device_count() != 1 or not torch.cuda.is_bf16_supported():
        raise RuntimeError("v6 requires one visible CUDA GPU with native bf16 support; no precision fallback")
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    coverage = token_coverage(tokenizer, args.data_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "token_coverage.json").write_text(
        json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    run_e1.main(forwarded)


if __name__ == "__main__":
    main()
