"""CPU replay of E2 training token lengths; no weights loaded or jobs changed.

The compiler source must match its saved run hash. Public-control sources must
match its frozen preflight. Counts describe the three-epoch recipe, not measured
FLOPs, training time, inference tokens, or completion of the queued control.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from statistics import median
from datetime import datetime, timezone


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stats(values):
    ordered = sorted(values)
    return {"sum": sum(values), "mean": sum(values) / len(values),
            "min": ordered[0], "median": median(ordered),
            "p95_nearest_rank": ordered[(95 * len(ordered) + 99) // 100 - 1],
            "max": ordered[-1]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-dir", type=Path, required=True)
    p.add_argument("--baseline-source", type=Path, required=True)
    p.add_argument("--baseline-metrics", type=Path, required=True)
    p.add_argument("--public-protocol", type=Path, required=True)
    p.add_argument("--train", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError("Existing audit preserved; use a new output path")
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["OMP_NUM_THREADS"] = "1"
    sys.path.insert(0, str(a.source_dir))
    baseline = json.loads(a.baseline_metrics.read_text())
    protocol = json.loads(a.public_protocol.read_text())
    if sha(a.baseline_source) != baseline["code_sha256"]:
        raise ValueError("Historical compiler source does not match its run")
    for name, expected in protocol["source_sha256"].items():
        if sha(a.source_dir / name) != expected:
            raise ValueError(f"Frozen public-control source drift: {name}")
    train_hash = sha(a.train)
    if not (train_hash == baseline["data_sha256"]["train"] == protocol["data_sha256"]["train"]):
        raise ValueError("Training data differ between arms")

    import torch
    from transformers import AutoTokenizer
    import run_e1
    import sub_e2_monolithic as mono
    from sub_e2_public_contract import public_messages
    torch.set_num_threads(1)
    spec = importlib.util.spec_from_file_location("historical_compiler", a.baseline_source)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    tok = AutoTokenizer.from_pretrained(str(a.model), local_files_only=True)
    if not tok.eos_token:
        raise ValueError("EOS token missing")
    recipe = {"epochs": 3, "learning_rate": 2e-4, "lora_rank": 16,
              "lora_alpha": 32, "gradient_accumulation_steps": 4,
              "max_seq_len": 1280, "seed": 42, "precision": "bf16"}
    if any(baseline["config"][k] != v for k, v in recipe.items()):
        raise ValueError("Baseline differs from the reviewed public-control recipe")
    if any(protocol[k] != recipe[k] for k in ("seed", "precision", "max_seq_len")):
        raise ValueError("Public preflight recipe differs")
    if baseline["config"].get("smoke_train_steps") is not None or baseline["config"].get("skip_train"):
        raise ValueError("Baseline is not a full training run")
    rows = run_e1.load_jsonl(a.train)
    if len(rows) != protocol["coverage"]["train"]["rows"]:
        raise ValueError("Preflight row count differs")
    if len(rows) % recipe["gradient_accumulation_steps"]:
        raise ValueError("Partial accumulation requires explicit training-loop replay")
    if len({r["sample_id"] for r in rows}) != len(rows):
        raise ValueError("Duplicate training sample IDs")
    modes = {
        "compiler": (old.chat_messages, old.target_json),
        "public_monolithic": (public_messages, mono.monolithic_target),
        "informed_monolithic_diagnostic": (mono.informed_chat_messages, mono.monolithic_target),
    }
    counts = {name: {"prompt": [], "supervised_target_including_eos": [], "sequence": []} for name in modes}
    for index, row in enumerate(rows):
        if row["spec_version"] != "v5":
            raise ValueError("Only the frozen v5 comparison is supported")
        if (old.chat_messages(row) != run_e1.chat_messages(row)
                or old.target_json(row) != run_e1.target_json(row)):
            raise ValueError(f"Historical and current compiler rendering differ at {row['sample_id']}")
        for name, (messages, target) in modes.items():
            prompt = old.render_chat(tok, messages(row), add_generation_prompt=True)["input_ids"][0].numel()
            answer = len(tok(target(row) + tok.eos_token, add_special_tokens=False)["input_ids"])
            if prompt + answer > recipe["max_seq_len"]:
                raise ValueError(f"Recipe would drop {row['sample_id']} in {name}; counts not comparable")
            counts[name]["prompt"].append(prompt)
            counts[name]["supervised_target_including_eos"].append(answer)
            counts[name]["sequence"].append(prompt + answer)
        if (index + 1) % 2000 == 0:
            print(json.dumps({"rows_counted": index + 1}), flush=True)
    arms = {}
    for name, values in counts.items():
        arms[name] = {"one_epoch": {k: stats(v) for k, v in values.items()},
                      "planned_three_epoch_tokens": {k: sum(v) * recipe["epochs"] for k, v in values.items()},
                      "rows": len(rows), "dropped": 0,
                      "planned_optimizer_steps": len(rows) // recipe["gradient_accumulation_steps"] * recipe["epochs"]}
    totals = {k: v["planned_three_epoch_tokens"] for k, v in arms.items()}
    ratios = {k: totals["compiler"][k] / totals["public_monolithic"][k] for k in totals["compiler"]}
    token_files = [f for f in a.model.iterdir() if f.is_file() and
                   (f.name in {"tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
                               "vocab.json", "merges.txt", "added_tokens.json"} or f.suffix == ".jinja")]
    result = {"revision": "20261125-training-token-replay-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "recipe": recipe, "arms": arms, "compiler_divided_by_public_monolithic": ratios,
              "verification": {"all_current_compiler_prompts_equal_historical": True,
                               "all_current_compiler_targets_equal_historical": True,
                               "frozen_public_sources_match": True, "train_data_match": True,
                               "historical_tokenizer_hash_available": False},
              "provenance": {"script_sha256": sha(__file__), "train_sha256": train_hash,
                             "baseline_metrics_sha256": sha(a.baseline_metrics),
                             "baseline_source_sha256": sha(a.baseline_source),
                             "public_protocol_sha256": sha(a.public_protocol),
                             "public_sources": protocol["source_sha256"],
                             "tokenizer_sha256": {f.name: sha(f) for f in token_files}},
              "limits": ["Tokenizer replay of the full planned recipe, not runtime GPU counters or proof the queued run completed.",
                         "Prompt tokens are loss-masked; targets include EOS. Sequence totals are not FLOPs.",
                         "Historical tokenizer hashes were not saved; this audit pins the currently deployed same-model tokenizer.",
                         "Compiler metrics.train_seconds includes initialization, zeroshot and trained evaluation; not pure training time.",
                         "Monolithic metrics.elapsed_s includes initialization, training, evaluation and analysis; not pure training time.",
                         "No latency, monetary saving, matched-compute or inference-token claim follows from these training lengths."]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({"saved": str(a.out), "ratios": ratios}), flush=True)


if __name__ == "__main__":
    main()
