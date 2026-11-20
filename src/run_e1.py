"""E1 实验：约束编译器 trained vs zero-shot（T/Z 臂，本地 4060）。

数据：data/processed_v2（可信数据空间背景，E/I/N 三版，双 group-held-out）。
流程：token 统计 -> zero-shot 评测 -> LoRA 训练 -> 训练后评测。
指标：micro P/R/F1 + 三态分桶 + per-type + I 版难度分桶(d1/d2/d3) + evidence span + parse rate，
     按 subset（dev in-domain / test_tpl_ho / test_tool_ho）分列（E4 泛化主张）。
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

SUBSETS = ["dev", "test_tpl_ho", "test_tool_ho"]


def load_jsonl(path: Path | str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def target_json(row: dict[str, Any]) -> str:
    return json.dumps(row["gold"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))


SCHEMA_HINT = (
    '{"query_state":"explicit|implicit|none","abstain":false,'
    '"constraints":[{"type":"budget|deadline|privacy|tool_auth|order",'
    '"description":"...","evidence_span":"...","state":"explicit|implicit|none",'
    '"confidence":0.0,"severity":"high|medium|low","scope":["role:..."],"params":{}}]}'
)


def chat_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    prompt = (
        "You are a typed constraint compiler for tool-planning tasks in a trusted data space. "
        "Extract the user's constraints into typed objects; output an empty list when the query "
        "carries no constraint. Never invent a constraint that the query does not support.\n"
        "Output JSON only, matching this schema:\n" + SCHEMA_HINT + "\n"
        "Available role vocabulary: " + json.dumps(row["available_roles"], ensure_ascii=False) + "\n"
        "User query: " + row["query"] + "\n"
        "JSON:"
    )
    return [
        {"role": "system", "content": "Output JSON only."},
        {"role": "user", "content": prompt},
    ]


def render_chat(tokenizer: Any, messages: list[dict[str, str]], *, add_generation_prompt: bool) -> dict[str, Any]:
    try:
        rendered = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=add_generation_prompt,
            enable_thinking=False, return_tensors="pt",
        )
    except TypeError:
        rendered = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=add_generation_prompt,
            return_tensors="pt",
        )
    if hasattr(rendered, "items"):
        return dict(rendered)
    return {"input_ids": rendered, "attention_mask": rendered.new_ones(rendered.shape)}


def extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    candidates = [text]
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        candidates.insert(0, match.group(0))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict) and isinstance(value.get("constraints"), list):
                return value
        except json.JSONDecodeError:
            continue
    return None


def normalise_prediction(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {"query_state": "none", "abstain": True, "constraints": []}
    constraints = value.get("constraints")
    if not isinstance(constraints, list):
        constraints = []
    return {
        "query_state": value.get("query_state", "none"),
        "abstain": bool(value.get("abstain", False)),
        "constraints": constraints,
    }


def constraint_key(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item.get("type"), item.get("state"), item.get("severity"),
        tuple(item.get("scope", [])),
        json.dumps(item.get("params") or {}, sort_keys=True, separators=(",", ":")),
    )


def score(rows: list[dict[str, Any]], predictions: list[dict[str, Any]], raw: list[str]) -> dict[str, Any]:
    state_correct = 0
    state_correct_by_variant: dict[str, int] = {}
    count_by_variant: dict[str, int] = {}
    true_positive = false_positive = false_negative = 0
    per_variant: dict[str, dict[str, int]] = {}
    per_type: dict[str, dict[str, int]] = {}
    per_difficulty: dict[str, dict[str, int]] = {}
    evidence_exact = evidence_total = 0
    parse_ok = 0
    for row, pred, raw_text in zip(rows, predictions, raw):
        gold = row["gold"]
        state_correct += int(pred.get("query_state") == gold["query_state"])
        state_correct_by_variant[row["variant"]] = state_correct_by_variant.get(row["variant"], 0) + int(
            pred.get("query_state") == gold["query_state"]
        )
        count_by_variant[row["variant"]] = count_by_variant.get(row["variant"], 0) + 1
        parse_ok += int(extract_json(raw_text) is not None)
        v = per_variant.setdefault(row["variant"], {"n": 0, "tp": 0, "fp": 0, "fn": 0})
        v["n"] += 1
        got_keys = [constraint_key(c) for c in pred.get("constraints", [])]
        want_keys = [constraint_key(c) for c in gold.get("constraints", [])]
        matched = sum(min(got_keys.count(k), want_keys.count(k)) for k in set(got_keys) | set(want_keys))
        v["tp"] += matched
        v["fp"] += len(got_keys) - matched
        v["fn"] += len(want_keys) - matched
        true_positive += matched
        false_positive += len(got_keys) - matched
        false_negative += len(want_keys) - matched
        for gk, g in zip(want_keys, gold.get("constraints", [])):
            t = per_type.setdefault(g["type"], {"n": 0, "tp": 0, "fp": 0, "fn": 0})
            t["n"] += 1
            t["tp"] += int(gk in got_keys)
            t["fn"] += int(gk not in got_keys)
        for pk, p in zip(got_keys, pred.get("constraints", [])):
            if pk not in want_keys:
                t = per_type.setdefault(p.get("type", "?"), {"n": 0, "tp": 0, "fp": 0, "fn": 0})
                t["fp"] += 1
        if row["variant"] == "implicit" and row["hint_meta"]:
            for m, g in zip(row["hint_meta"], gold.get("constraints", [])):
                d = per_difficulty.setdefault(f"d{m['difficulty']}", {"n": 0, "tp": 0, "fp": 0, "fn": 0})
                d["n"] += 1
                gk = constraint_key(g)
                d["tp"] += int(gk in got_keys)
                d["fn"] += int(gk not in got_keys)
        if gold.get("constraints") and pred.get("constraints"):
            evidence_exact += int(
                pred["constraints"][0].get("evidence_span") == gold["constraints"][0].get("evidence_span")
            )
            evidence_total += 1
    n = max(len(rows), 1)

    def prf(tp: int, fp: int, fn: int) -> dict[str, Any]:
        p = tp / max(tp + fp, 1)
        r = tp / max(tp + fn, 1)
        return {"precision": p, "recall": r, "f1": 2 * p * r / max(p + r, 1e-12)}

    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(true_positive + false_negative, 1)
    return {
        "records": len(rows),
        "state_accuracy": state_correct / n,
        "state_accuracy_by_variant": {
            k: state_correct_by_variant[k] / max(count_by_variant[k], 1) for k in count_by_variant
        },
        "constraint_micro": prf(true_positive, false_positive, false_negative),
        "per_variant": {k: {**prf(v["tp"], v["fp"], v["fn"]), "records": v["n"]} for k, v in per_variant.items()},
        "per_type": {k: {**prf(v["tp"], v["fp"], v["fn"]), "gold_records": v["n"]} for k, v in per_type.items()},
        "per_difficulty_implicit": {k: {**prf(v["tp"], v["fp"], v["fn"]), "records": v["n"]} for k, v in per_difficulty.items()},
        "evidence_exact_rate": evidence_exact / max(evidence_total, 1),
        "evidence_records": evidence_total,
        "json_parse_rate": parse_ok / n,
    }


def generate_batched(model: Any, tokenizer: Any, rows: list[dict[str, Any]], max_new_tokens: int, batch_size: int) -> tuple[list[dict[str, Any]], list[str]]:
    """左 padding 批量贪心生成。"""
    import torch

    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    device = next(model.parameters()).device
    predictions: list[dict[str, Any]] = []
    raw_outputs: list[str] = []
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        encoded_list = [
            render_chat(tokenizer, chat_messages(row), add_generation_prompt=True)["input_ids"][0].tolist()
            for row in batch
        ]
        maxlen = max(len(ids) for ids in encoded_list)
        input_ids = torch.full((len(batch), maxlen), tokenizer.pad_token_id, dtype=torch.long)
        attention = torch.zeros((len(batch), maxlen), dtype=torch.long)
        for i, ids in enumerate(encoded_list):
            input_ids[i, maxlen - len(ids):] = torch.tensor(ids)
            attention[i, maxlen - len(ids):] = 1
        input_ids, attention = input_ids.to(device), attention.to(device)
        with torch.no_grad():
            output = model.generate(
                input_ids=input_ids, attention_mask=attention,
                do_sample=False, max_new_tokens=max_new_tokens,
                pad_token_id=tokenizer.eos_token_id,
            )
        for i in range(len(batch)):
            gen = output[i, maxlen:]
            raw = tokenizer.decode(gen, skip_special_tokens=True)
            raw_outputs.append(raw)
            predictions.append(normalise_prediction(extract_json(raw)))
    return predictions, raw_outputs


def load_model(model_path: str) -> tuple[Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch.float16, device_map="cuda", trust_remote_code=True,
    )
    model.eval()
    return model, tokenizer


def evaluate_all(model: Any, tokenizer: Any, data: dict[str, list[dict[str, Any]]], args: argparse.Namespace, tag: str, out_dir: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for subset in SUBSETS:
        rows = data[subset]
        t0 = time.time()
        predictions, raw = generate_batched(model, tokenizer, rows, args.max_new_tokens, args.eval_batch_size)
        results[subset] = score(rows, predictions, raw)
        results[subset]["eval_seconds"] = round(time.time() - t0, 1)
        pred_dir = out_dir / f"{tag}_predictions"
        pred_dir.mkdir(parents=True, exist_ok=True)
        (pred_dir / f"{subset}.jsonl").write_text(
            "".join(json.dumps({"sample_id": r["sample_id"], "prediction": p, "raw": t}, ensure_ascii=False) + "\n"
                    for r, p, t in zip(rows, predictions, raw)),
            encoding="utf-8",
        )
        print(json.dumps({"subset": subset, "tag": tag, "f1": results[subset]["constraint_micro"]["f1"],
                          "state_acc": results[subset]["state_accuracy"]}, ensure_ascii=False))
    return results


def train_lora(model: Any, tokenizer: Any, rows: list[dict[str, Any]], args: argparse.Namespace) -> Any:
    import torch
    from peft import LoraConfig, get_peft_model
    from peft.tuners.lora import model as peft_lora_model

    # 宿主镜像可能带旧 torchao：跳过 PEFT 的可选 dispatcher（沿 pilot 处理）
    if hasattr(peft_lora_model, "dispatch_torchao"):
        def skip_optional_torchao_dispatcher(*_a: Any, **_k: Any) -> None:
            return None
        peft_lora_model.dispatch_torchao = skip_optional_torchao_dispatcher

    config = LoraConfig(
        r=args.lora_rank, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, config)
    model.train()
    model.config.use_cache = False
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    device = next(model.parameters()).device

    examples = []
    for row in rows:
        prefix = render_chat(tokenizer, chat_messages(row), add_generation_prompt=True)["input_ids"][0].tolist()
        completion = tokenizer(target_json(row) + tokenizer.eos_token, add_special_tokens=False)["input_ids"]
        if len(prefix) + len(completion) > args.max_seq_len:
            continue
        examples.append((prefix + completion, [-100] * len(prefix) + completion))
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.learning_rate)
    rng = random.Random(args.seed)
    steps_per_epoch = len(examples) // args.gradient_accumulation_steps
    total_steps = steps_per_epoch * args.epochs
    done = 0
    print(json.dumps({"train_examples": len(examples), "planned_optimizer_steps": total_steps}))
    for _epoch in range(args.epochs):
        rng.shuffle(examples)
        accumulation = 0
        for ids_list, labels_list in examples:
            if done >= total_steps:
                break
            ids = torch.tensor([ids_list], dtype=torch.long, device=device)
            labels = torch.tensor([labels_list], dtype=torch.long, device=device)
            out = model(input_ids=ids, attention_mask=torch.ones_like(ids), labels=labels)
            (out.loss / args.gradient_accumulation_steps).backward()
            accumulation += 1
            if accumulation == args.gradient_accumulation_steps:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                accumulation = 0
                done += 1
                if done % 100 == 0 or done == 1:
                    print(json.dumps({"optimizer_step": done, "loss": float(out.loss.detach().cpu()),
                                      "elapsed_s": round(time.time() - args._t0, 1)}))
        if accumulation:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            done += 1
    model.eval()
    model.config.use_cache = True
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=str(ROOT / "models" / "Qwen3-0.6B"))
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "processed_v2")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--max-seq-len", type=int, default=1024)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument("--eval-batch-size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-zeroshot", action="store_true")
    parser.add_argument("--skip-train", action="store_true")
    args = parser.parse_args()

    model_name = Path(args.model).name
    args.out_dir = args.out_dir or ROOT / "outputs" / "e1" / model_name
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args._t0 = time.time()

    data = {subset: load_jsonl(args.data_dir / f"{subset}.jsonl") for subset in SUBSETS}
    train_rows = load_jsonl(args.data_dir / "train.jsonl")
    print(json.dumps({"model": args.model, "train": len(train_rows),
                      "eval": {k: len(v) for k, v in data.items()}}))

    import torch

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    model, tokenizer = load_model(args.model)

    results: dict[str, Any] = {"model_path": args.model, "seed": args.seed,
                               "config": {k: v for k, v in vars(args).items() if not k.startswith("_")}}

    if not args.skip_zeroshot:
        results["zeroshot"] = evaluate_all(model, tokenizer, data, args, "zeroshot", args.out_dir)
    if not args.skip_train:
        model = train_lora(model, tokenizer, train_rows, args)
        adapter_dir = args.out_dir / "adapter"
        model.save_pretrained(adapter_dir)
        results["trained"] = evaluate_all(model, tokenizer, data, args, "trained", args.out_dir)
        results["train_seconds"] = round(time.time() - args._t0, 1)

    (args.out_dir / "metrics.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps({"saved": str(args.out_dir / "metrics.json")}))


if __name__ == "__main__":
    main()
