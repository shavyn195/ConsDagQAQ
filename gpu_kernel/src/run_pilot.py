"""Run the bounded 0.6B prompt-vs-LoRA compiler pilot on a remote GPU or locally.

The script deliberately keeps the evaluation contract small and auditable:
the frozen model is evaluated with two prompt templates, then the same base
model receives a short LoRA run and is evaluated with the identical parser.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pilot_schema import validate_rows  # noqa: E402


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def target_json(row: dict[str, Any]) -> str:
    # Keep target ordering stable so exact JSON comparisons are meaningful.
    return json.dumps(row["gold"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def prompt_for(row: dict[str, Any], style: str = "structured") -> str:
    schema = (
        '{"query_state":"explicit|implicit|none","abstain":false,'
        '"constraints":[{"type":"budget|deadline|privacy|tool_auth|order",'
        '"description":"...","evidence_span":"...","state":"explicit|implicit|none",'
        '"confidence":0.0,"severity":"high|medium|low","scope":["role:..."],"params":{}}]}'
    )
    return (
        "Output JSON only, matching this schema:\n" + schema + "\n"
        "Available role vocabulary: " + json.dumps(row["available_roles"], ensure_ascii=False) + "\n"
        "User query: " + row["query"] + "\n"
        "JSON:"
    )


def chat_messages(row: dict[str, Any], style: str) -> list[dict[str, str]]:
    instruction = "You are a typed constraint compiler. "
    if style == "abstaining":
        instruction += "Abstain only when the query does not provide enough evidence; never invent a constraint."
    else:
        instruction += "Return the best supported contract and use an empty list for no constraint."
    return [
        {"role": "system", "content": instruction + " Output JSON only."},
        {"role": "user", "content": prompt_for(row, style)},
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
    abstain_correct = 0
    constraint_exact = 0
    full_object_exact = 0
    schema_pass = 0
    evidence_exact = 0
    true_positive = false_positive = false_negative = 0
    per_state: dict[str, dict[str, int]] = {}
    per_variant: dict[str, dict[str, int]] = {}
    for row, pred, raw_text in zip(rows, predictions, raw):
        gold = row["gold"]
        state_match = pred.get("query_state") == gold["query_state"]
        state_correct += int(state_match)
        abstain_correct += int(pred.get("abstain", False) == gold["abstain"])
        bucket = per_state.setdefault(row["variant"], {"correct": 0, "total": 0})
        bucket["correct"] += int(state_match)
        bucket["total"] += 1
        variant_metrics = per_variant.setdefault(
            row["variant"],
            {"records": 0, "tp": 0, "fp": 0, "fn": 0, "exact": 0,
             "evidence_exact": 0, "evidence_total": 0},
        )
        variant_metrics["records"] += 1
        got = pred.get("constraints", [])
        want = gold.get("constraints", [])
        got_keys = [constraint_key(item) for item in got]
        want_keys = [constraint_key(item) for item in want]
        matched = sum(min(got_keys.count(key), want_keys.count(key)) for key in set(got_keys) | set(want_keys))
        row_fp = len(got_keys) - matched
        row_fn = len(want_keys) - matched
        true_positive += matched
        false_positive += row_fp
        false_negative += row_fn
        variant_metrics["tp"] += matched
        variant_metrics["fp"] += row_fp
        variant_metrics["fn"] += row_fn
        row_exact = int(sorted(got_keys) == sorted(want_keys))
        constraint_exact += row_exact
        variant_metrics["exact"] += row_exact
        full_object_exact += int(pred == gold)
        schema_pass += int(extract_json(raw_text) is not None)
        if want and got:
            evidence_match = int(got[0].get("evidence_span") == want[0].get("evidence_span"))
            evidence_exact += evidence_match
            variant_metrics["evidence_exact"] += evidence_match
            variant_metrics["evidence_total"] += 1
    n = max(len(rows), 1)
    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(true_positive + false_negative, 1)
    return {
        "records": len(rows),
        "state_accuracy": state_correct / n,
        "state_accuracy_by_variant": {key: value["correct"] / max(value["total"], 1) for key, value in per_state.items()},
        "constraint_metrics_by_variant": {
            key: {
                "records": value["records"],
                "precision": value["tp"] / (value["tp"] + value["fp"]) if value["tp"] + value["fp"] else None,
                "recall": value["tp"] / (value["tp"] + value["fn"]) if value["tp"] + value["fn"] else None,
                "f1": (2 * value["tp"] / (2 * value["tp"] + value["fp"] + value["fn"]))
                if 2 * value["tp"] + value["fp"] + value["fn"] else None,
                "exact_accuracy": value["exact"] / max(value["records"], 1),
                "evidence_exact_rate": value["evidence_exact"] / value["evidence_total"]
                if value["evidence_total"] else None,
                "evidence_records": value["evidence_total"],
            }
            for key, value in per_variant.items()
        },
        "abstain_accuracy": abstain_correct / n,
        "constraint_micro_precision": precision,
        "constraint_micro_recall": recall,
        "constraint_micro_f1": 2 * precision * recall / max(precision + recall, 1e-12),
        "constraint_exact_accuracy": constraint_exact / n,
        "full_object_exact_accuracy": full_object_exact / n,
        "evidence_exact_rate_constrained": evidence_exact / max(sum(bool(row["gold"].get("constraints")) for row in rows), 1),
        "json_parse_rate": schema_pass / n,
    }


def generate(model: Any, tokenizer: Any, rows: list[dict[str, Any]], style: str, max_new_tokens: int) -> tuple[list[dict[str, Any]], list[str]]:
    import torch

    predictions: list[dict[str, Any]] = []
    raw_outputs: list[str] = []
    device = next(model.parameters()).device
    for row in rows:
        encoded = {
            key: value.to(device)
            for key, value in render_chat(tokenizer, chat_messages(row, style), add_generation_prompt=True).items()
        }
        with torch.no_grad():
            output = model.generate(**encoded, do_sample=False, max_new_tokens=max_new_tokens, pad_token_id=tokenizer.eos_token_id)
        generated = output[0, encoded["input_ids"].shape[1]:]
        raw = tokenizer.decode(generated, skip_special_tokens=True)
        raw_outputs.append(raw)
        predictions.append(normalise_prediction(extract_json(raw)))
    return predictions, raw_outputs


def load_model(model_id: str, *, device_map: str = "auto") -> tuple[Any, Any]:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype="auto", device_map=device_map, trust_remote_code=True
    )
    model.eval()
    return model, tokenizer


def train_lora(model: Any, tokenizer: Any, rows: list[dict[str, Any]], args: argparse.Namespace) -> Any:
    import torch
    from peft import LoraConfig, get_peft_model

    # Some hosted GPU images may ship an old torchao distribution. PEFT's optional
    # dispatcher checks that package before falling through to its standard
    # nn.Linear implementation, so a stale install can break dense-model LoRA.
    # This pilot uses ordinary, unquantized Linear layers and does not need the
    # TorchAO backend.
    from peft.tuners.lora import model as peft_lora_model

    if hasattr(peft_lora_model, "dispatch_torchao"):
        def skip_optional_torchao_dispatcher(*_args: Any, **_kwargs: Any) -> None:
            return None

        peft_lora_model.dispatch_torchao = skip_optional_torchao_dispatcher

    config = LoraConfig(
        r=args.lora_rank, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, config)
    model.train()
    model.config.use_cache = False
    device = next(model.parameters()).device
    examples = []
    for row in rows[: args.max_train_examples]:
        prefix = render_chat(tokenizer, chat_messages(row, "structured"), add_generation_prompt=True)["input_ids"][0].tolist()
        completion = tokenizer(target_json(row) + tokenizer.eos_token, add_special_tokens=False)["input_ids"]
        examples.append(((prefix + completion)[: args.max_seq_len], ([-100] * len(prefix) + completion)[: args.max_seq_len]))
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.learning_rate)
    random.seed(args.seed)
    accumulation = 0
    optimizer_steps = 0
    while optimizer_steps < args.max_steps:
        random.shuffle(examples)
        for ids_list, labels_list in examples:
            if optimizer_steps >= args.max_steps:
                break
            ids = torch.tensor(ids_list, dtype=torch.long, device=device)
            labels = torch.tensor(labels_list, dtype=torch.long, device=device)
            out = model(input_ids=ids.unsqueeze(0), attention_mask=torch.ones_like(ids.unsqueeze(0)), labels=labels.unsqueeze(0))
            loss = out.loss / args.gradient_accumulation_steps
            loss.backward()
            accumulation += 1
            if accumulation == args.gradient_accumulation_steps:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                accumulation = 0
                optimizer_steps += 1
                if optimizer_steps % max(args.logging_steps, 1) == 0 or optimizer_steps == 1:
                    print(json.dumps({"optimizer_step": optimizer_steps, "loss": float(out.loss.detach().cpu())}))
        if accumulation and optimizer_steps < args.max_steps:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            accumulation = 0
            optimizer_steps += 1
    if accumulation:
        optimizer.zero_grad(set_to_none=True)
    args.actual_optimizer_steps = optimizer_steps
    model.eval()
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default=os.environ.get("MODEL_ID", "Qwen/Qwen3-0.6B"))
    parser.add_argument("--train", type=Path, default=ROOT / "data" / "processed" / "train.jsonl")
    parser.add_argument("--test", type=Path, default=ROOT / "data" / "processed" / "test.jsonl")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "pilot_run.json")
    parser.add_argument("--max-train-examples", type=int, default=500)
    parser.add_argument("--max-steps", type=int, default=75)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--max-seq-len", type=int, default=1024)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--adapter-output", type=Path, default=ROOT / "outputs" / "adapter")
    parser.add_argument("--prediction-dir", type=Path)
    args = parser.parse_args()
    random.seed(args.seed)
    train_rows, test_rows = load_jsonl(args.train), load_jsonl(args.test)
    errors = validate_rows(train_rows + test_rows)
    if errors:
        raise SystemExit("CPU preflight failed: " + " | ".join(errors[:10]))
    print(json.dumps({"preflight": "pass", "train": len(train_rows), "test": len(test_rows)}))

    import torch

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    model, tokenizer = load_model(args.model_id)
    results: dict[str, Any] = {
        "model_id": args.model_id,
        "train_records": len(train_rows),
        "test_records": len(test_rows),
        "seed": args.seed,
        "requested_max_steps": args.max_steps,
        "gradient_accumulation_steps": args.gradient_accumulation_steps,
        "max_train_examples": args.max_train_examples,
        "max_seq_len": args.max_seq_len,
        "max_new_tokens": args.max_new_tokens,
        "learning_rate": args.learning_rate,
        "lora_rank": args.lora_rank,
        "lora_alpha": args.lora_alpha,
    }
    prediction_dir = args.prediction_dir or args.output.parent / "predictions"
    prediction_dir.mkdir(parents=True, exist_ok=True)
    for style in ("structured", "abstaining"):
        predictions, raw = generate(model, tokenizer, test_rows, style, args.max_new_tokens)
        results[f"prompt_{style}"] = score(test_rows, predictions, raw)
        (prediction_dir / f"prompt_{style}.jsonl").write_text(
            "".join(json.dumps({"sample_id": row["sample_id"], "prediction": pred, "raw": output}, ensure_ascii=False) + "\n"
                    for row, pred, output in zip(test_rows, predictions, raw)), encoding="utf-8"
        )
    model = train_lora(model, tokenizer, train_rows, args)
    results["actual_optimizer_steps"] = args.actual_optimizer_steps
    predictions, raw = generate(model, tokenizer, test_rows, "structured", args.max_new_tokens)
    results["trained_lora"] = score(test_rows, predictions, raw)
    args.adapter_output.parent.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.adapter_output)
    (prediction_dir / "trained_lora.jsonl").write_text(
        "".join(json.dumps({"sample_id": row["sample_id"], "prediction": pred, "raw": output}, ensure_ascii=False) + "\n"
                for row, pred, output in zip(test_rows, predictions, raw)), encoding="utf-8"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
