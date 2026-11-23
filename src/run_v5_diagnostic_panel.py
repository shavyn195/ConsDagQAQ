"""Frozen-adapter inference on the registered v5 dev intervention panel (GPU server only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import time

from run_e1 import chat_messages, evaluate_all, load_jsonl, load_model, render_chat


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--adapter", required=True, type=Path)
    p.add_argument("--panel", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if platform.system() != "Linux":
        raise RuntimeError("This experiment is registered for the Linux GPU server")
    if args.out.exists():
        raise FileExistsError("Use a fresh output directory; do not overwrite a previous run")
    if not (args.adapter / "adapter_config.json").is_file():
        raise FileNotFoundError(args.adapter)
    proto = json.loads((args.panel / "protocol.json").read_text(encoding="utf-8"))
    arm = args.adapter.parent.name
    if arm not in proto["model_arms"]:
        raise ValueError(f"Unregistered model arm: {arm}")
    data = {}
    for condition in proto["conditions"]:
        path = args.panel / f"{condition}.jsonl"
        if hashlib.sha256(path.read_bytes()).hexdigest() != proto["data_sha256"][condition]:
            raise ValueError(f"Panel hash mismatch: {condition}")
        data[condition] = load_jsonl(path)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    import torch
    import peft
    import transformers
    torch.manual_seed(20261123)
    model, tokenizer = load_model(str(args.model), "bf16")
    model = peft.PeftModel.from_pretrained(model, args.adapter).eval()
    if any(not torch.isfinite(param).all() for param in model.parameters()):
        raise FloatingPointError("Nonfinite frozen model weights")
    input_lengths = {c: [int(render_chat(tokenizer, chat_messages(r), add_generation_prompt=True)["input_ids"].shape[-1])
                         for r in rows] for c, rows in data.items()}
    if max(max(v) for v in input_lengths.values()) + proto["generation"]["max_new_tokens"] > model.config.max_position_embeddings:
        raise ValueError("Panel exceeds model context; no truncation allowed")
    args.out.mkdir(parents=True)
    hashes = {str(path.name): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(args.adapter.glob("*.safetensors"))}
    manifest = {"arm": arm, "protocol_sha256": hashlib.sha256((args.panel / "protocol.json").read_bytes()).hexdigest(),
                "adapter_sha256": hashes, "torch": torch.__version__, "peft": peft.__version__,
                "transformers": transformers.__version__, "gpu": torch.cuda.get_device_name(),
                "input_lengths": input_lengths, "generation": proto["generation"]}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    settings = argparse.Namespace(max_new_tokens=proto["generation"]["max_new_tokens"],
                                  eval_batch_size=proto["generation"]["batch_size"])
    started = time.monotonic()
    scores = evaluate_all(model, tokenizer, data, settings, "diagnostic", args.out)
    for condition in scores:
        preds = load_jsonl(args.out / "diagnostic_predictions" / f"{condition}.jsonl")
        scores[condition]["decoded_text_tokens"] = sum(len(tokenizer(p["raw"], add_special_tokens=False)["input_ids"]) for p in preds)
    (args.out / "metrics.json").write_text(json.dumps({"scores": scores, "seconds": time.monotonic() - started}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
