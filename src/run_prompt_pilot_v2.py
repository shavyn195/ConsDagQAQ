"""Small, paired CPU prompt pilot on the frozen v2 E1 evaluation contract.

This is an explicitly labelled fallback when the external strong-model API is
unavailable. It is not a Qwen-Max baseline and is not comparable to the full
3,000-row E1 prompt run. Each selected group keeps its E/I/N triplet, and both
prompt variants use the v3 parser/scorer from ``run_e1``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def improved_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    from run_e1 import SCHEMA_HINT

    instruction = (
        "You are a conservative typed constraint compiler. Extract only constraints "
        "supported by the user query. Work field by field: first decide query_state "
        "(explicit, implicit, or none), then identify each constraint type and its "
        "numeric or categorical params, then bind scope only to roles in the supplied "
        "vocabulary. Copy an evidence_span from the query. If no supported constraint "
        "exists, return constraints=[] and query_state=none. Never infer a constraint "
        "from the role catalog alone. Return one JSON object and no prose.\n"
        "Schema:\n" + SCHEMA_HINT + "\n"
        "Available role vocabulary: " + json.dumps(row["available_roles"], ensure_ascii=False) + "\n"
        "User query: " + row["query"] + "\n"
        "JSON:"
    )
    return [{"role": "system", "content": "Output JSON only."}, {"role": "user", "content": instruction}]


def select_rows(data_dir: Path, groups_per_subset: int) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    for subset in ("dev", "test_tpl_ho", "test_tool_ho"):
        rows = load_jsonl(data_dir / f"{subset}.jsonl")
        by_group: dict[str, dict[str, dict[str, Any]]] = {}
        for row in rows:
            by_group.setdefault(row["group_id"], {})[row["variant"]] = row
        complete = [by_group[g] for g in sorted(by_group) if {"explicit", "implicit", "none"} <= set(by_group[g])]
        if groups_per_subset == 1:
            chosen = complete[:1]
        else:
            indices = [round(i * (len(complete) - 1) / (groups_per_subset - 1)) for i in range(groups_per_subset)]
            chosen = [complete[i] for i in indices]
        if len(chosen) != groups_per_subset:
            raise ValueError(f"{subset}: only {len(chosen)} complete groups, requested {groups_per_subset}")
        selected[subset] = [chosen_i[v] for chosen_i in chosen for v in ("explicit", "implicit", "none")]
    return selected


def run_variant(model: Any, tokenizer: Any, rows: list[dict[str, Any]], prompt_variant: str, max_new_tokens: int) -> tuple[list[dict[str, Any]], list[str]]:
    import torch
    from run_e1 import chat_messages, extract_json, generate_batched, normalise_prediction

    tokenizer.padding_side = "left"
    device = next(model.parameters()).device
    predictions: list[dict[str, Any]] = []
    raw_outputs: list[str] = []
    for index, row in enumerate(rows, start=1):
        messages = chat_messages(row) if prompt_variant == "baseline" else improved_messages(row)
        try:
            encoded = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                enable_thinking=False, return_tensors="pt",
            )
        except TypeError:
            encoded = tokenizer.apply_chat_template(
                messages, tokenize=True, add_generation_prompt=True,
                return_tensors="pt",
            )
        if hasattr(encoded, "items"):
            encoded = dict(encoded)
        else:
            encoded = {"input_ids": encoded, "attention_mask": encoded.new_ones(encoded.shape)}
        encoded = {key: value.to(device) for key, value in encoded.items()}
        with torch.no_grad():
            output = model.generate(
                **encoded, do_sample=False, max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.eos_token_id,
            )
        generated = output[0, encoded["input_ids"].shape[1]:]
        raw = tokenizer.decode(generated, skip_special_tokens=True)
        raw_outputs.append(raw)
        predictions.append(normalise_prediction(extract_json(raw)))
        if index % 5 == 0 or index == len(rows):
            print(json.dumps({"prompt_variant": prompt_variant, "completed": index, "total": len(rows)}), flush=True)
    return predictions, raw_outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=ROOT / "models" / "Qwen3-0.6B")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "processed_v2")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "prompt_pilot_v2_0.6B_cpu")
    parser.add_argument("--groups-per-subset", type=int, default=5)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument("--cpu-threads", type=int, default=2)
    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from run_e1 import score

    torch.set_num_threads(args.cpu_threads)
    device = torch.device("cpu")
    selected = select_rows(args.data_dir, args.groups_per_subset)
    rows = [row for subset in selected.values() for row in subset]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    model_hash = hashlib.sha256((args.model / "config.json").read_bytes()).hexdigest()
    metadata = {
        "experiment": "local_cpu_prompt_pilot_v2",
        "model": str(args.model),
        "model_config_sha256": model_hash,
        "device": str(device),
        "torch": torch.__version__,
        "transformers": __import__("transformers").__version__,
        "platform": platform.platform(),
        "groups_per_subset": args.groups_per_subset,
        "rows_per_subset": {key: len(value) for key, value in selected.items()},
        "records": len(rows),
        "max_new_tokens": args.max_new_tokens,
        "cpu_threads": args.cpu_threads,
        "temperature": 0,
        "api_status": "DashScope qwen-max unavailable: HTTP 401 Incorrect API key; no strong-model result",
        "limitation": "Fallback local 0.6B CPU pilot; not a Qwen-Max or strong-model baseline and not a full E1 run.",
        "sample_ids": [row["sample_id"] for row in rows],
    }
    (args.out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.float16, device_map=None,
        low_cpu_mem_usage=True, trust_remote_code=True,
    )
    model.to(device).eval()

    results: dict[str, Any] = {"metadata": metadata, "scores": {}}
    for prompt_variant in ("baseline", "improved"):
        t0 = time.time()
        predictions, raw = run_variant(model, tokenizer, rows, prompt_variant, args.max_new_tokens)
        results["scores"][prompt_variant] = score(rows, predictions, raw)
        results["scores"][prompt_variant]["seconds"] = round(time.time() - t0, 1)
        pred_dir = args.out_dir / "predictions"
        pred_dir.mkdir(exist_ok=True)
        (pred_dir / f"{prompt_variant}.jsonl").write_text(
            "".join(json.dumps({"sample_id": row["sample_id"], "prediction": pred, "raw": raw_text}, ensure_ascii=False) + "\n"
                    for row, pred, raw_text in zip(rows, predictions, raw)), encoding="utf-8"
        )
        print(json.dumps({"prompt_variant": prompt_variant, "seconds": results["scores"][prompt_variant]["seconds"], "score": results["scores"][prompt_variant]}, ensure_ascii=False))
    (args.out_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
