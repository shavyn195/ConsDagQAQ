"""E2 / B1 单体对照：同底座、同数据、同预算，训「查询→计划」直出单体（跳过编译阶段）。

对比对象 = v5 主管线（编译器 LoRA + 符号规划器 plan()，即 e1_exec_v2 的 faithful 口径）。
预注册判定：
  - 单体 faithful_constrained >= 管线 - 1pp 且配对 bootstrap 95% 区间跨 0  => 架构主张死，如实报；
  - 否则管线显著赢 => 编译-规划分离成立。
预算匹配：训练行、LoRA 配置、lr、epoch、grad-accum、精度、种子与 run_e1.py 完全一致；
唯一差别是 target（约束 JSON -> 计划 JSON），两种 target 的 token 数都记账（成本列）。
金标仅在评测阶段可见；训练 target 的 witness_plan 是数据自带的构造条件（与编译器训练用同一批行）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import torch

from eval_exec import record_outcome
from rescore_v4_side import load_jsonl
from run_e1 import (chat_messages, eval_subsets, load_model, render_chat,
                    require_finite_loss, strict_parse)
from trust_env import check, default_plan, plan as symbolic_plan, plan_change_count

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho")
BOOT = 10_000


def monolithic_target(row: dict[str, Any]) -> str:
    """单体 target：受约束行用 witness_plan，N 行用默认计划（与管线规划器同口径）。"""
    gold = row["gold"]["constraints"]
    if gold:
        return json.dumps(row["witness_plan"], separators=(",", ":"))
    return json.dumps(default_plan(row["task"]), separators=(",", ":"))


def informed_chat_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    """信息对齐版提示：把任务结构（阶段/备选/默认/finish/可选前置/工具成本与时长）显式给出。

    旧版直接复用编译器提示，只给工具目录和 query，单体看不到任何计划结构，
    在未见结构切分上不可能产出合法计划（tool_ho 196 种、struct_ho 299 种结构 train 中未出现）。
    这一版让单体与"编译器 + 规划器"拿到同等信息，才是公平对照。
    """
    task = row["task"]
    contract = {
        "stages": [{"stage": s["stage"], "alternatives": s["alternatives"], "default": s["default"]}
                   for s in task["stages"]],
        "finish": task["finish"],
        "optional": task["optional"],
        "tools": {role: {"cost_cny": spec["cost_cny"], "duration_min": spec["duration_min"],
                         "recipient": spec["recipient"], "clears_pii": spec["clears_pii"]}
                  for role, spec in task["tools"].items()},
    }
    prompt = (
        "You are a tool planner for tasks in a trusted data space. Produce one executable plan that "
        "completes the task and satisfies every constraint stated in the user query. Return a JSON array "
        "of tool role names in execution order.\n"
        "Task contract (JSON): " + json.dumps(contract, ensure_ascii=False, separators=(",", ":")) + "\n"
        "Rules: exactly one tool per stage; include every finish tool after the last stage; insert an "
        "optional tool only when a constraint requires it; keep the plan as close to the defaults as "
        "possible while satisfying the constraints.\n"
        "User query: " + row["query"] + "\n"
        "JSON:"
    )
    return [{"role": "system", "content": "Output a JSON array only."},
            {"role": "user", "content": prompt}]


def train_monolithic(model: Any, tokenizer: Any, rows: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    """与 run_e1.train_lora 同构的训练循环，仅替换 target 与 prompt 后的 loss mask 规则。"""
    from peft import LoraConfig, get_peft_model
    from peft.tuners.lora import model as peft_lora_model

    if hasattr(peft_lora_model, "dispatch_torchao"):
        peft_lora_model.dispatch_torchao = lambda *_a, **_k: None

    model = get_peft_model(model, LoraConfig(
        r=args.lora_rank, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], task_type="CAUSAL_LM"))
    model.train()
    model.config.use_cache = False
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    device = next(model.parameters()).device

    examples = []
    dropped = 0
    for row in rows:
        prefix = render_chat(tokenizer, prompt_messages(row, args), add_generation_prompt=True)["input_ids"][0].tolist()
        completion = tokenizer(monolithic_target(row) + tokenizer.eos_token, add_special_tokens=False)["input_ids"]
        if len(prefix) + len(completion) > args.max_seq_len:
            dropped += 1
            continue
        examples.append((prefix + completion, [-100] * len(prefix) + completion))
    if dropped:
        print(json.dumps({"warning": "examples dropped by max_seq_len", "dropped": dropped}))

    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.learning_rate)
    trainable = [p for p in model.parameters() if p.requires_grad]
    rng = random.Random(args.seed)
    steps_per_epoch = len(examples) // args.gradient_accumulation_steps
    total_steps = steps_per_epoch * args.epochs
    print(json.dumps({"train_examples": len(examples), "planned_optimizer_steps": total_steps}))

    token_budget = {"prompt": 0, "completion": 0}
    done = 0
    for epoch in range(args.epochs):
        rng.shuffle(examples)
        accumulation = 0
        for ids_list, labels_list in examples:
            if done >= total_steps:
                break
            ids = torch.tensor([ids_list], dtype=torch.long, device=device)
            labels = torch.tensor([labels_list], dtype=torch.long, device=device)
            out = model(input_ids=ids, attention_mask=torch.ones_like(ids), labels=labels)
            require_finite_loss(out.loss, torch=torch, epoch=epoch + 1,
                                example_index=accumulation, optimizer_step=done + 1)
            (out.loss / args.gradient_accumulation_steps).backward()
            n_prompt = next(i for i, v in enumerate(labels_list) if v != -100)
            token_budget["prompt"] += n_prompt
            token_budget["completion"] += len(labels_list) - n_prompt
            accumulation += 1
            if accumulation == args.gradient_accumulation_steps:
                torch.nn.utils.clip_grad_norm_(trainable, 1.0, error_if_nonfinite=True)
                optimizer.step()
                if any(not torch.isfinite(p.detach()).all() for p in trainable):
                    raise FloatingPointError(f"non-finite trainable parameter after optimizer_step={done + 1}")
                optimizer.zero_grad(set_to_none=True)
                accumulation = 0
                done += 1
                if done % 100 == 0 or done == 1:
                    print(json.dumps({"optimizer_step": done, "loss": float(out.loss.detach().cpu())}), flush=True)
        if accumulation:
            torch.nn.utils.clip_grad_norm_(trainable, 1.0, error_if_nonfinite=True)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            done += 1
    model.eval()
    model.config.use_cache = True
    return {"steps": done, "tokens": token_budget, "examples": len(examples), "dropped": dropped}


def parse_plan(text: str, row: dict[str, Any]) -> list[str] | None:
    """fail-closed 计划解析：只接受 JSON 字符串数组，且每阶段恰一工具 + finish 全集，否则视作未产出。"""
    import re

    candidates = [text.strip()]
    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if match:
        candidates.insert(0, match.group(0))
    plan = None
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, list) and value and all(isinstance(x, str) for x in value):
            plan = value
            break
    if plan is None:
        return None
    task = row["task"]
    known = {a for s in task["stages"] for a in s["alternatives"]} | set(task["finish"]) | set(task["optional"])
    if any(x not in known for x in plan):
        return None
    try:
        plan_change_count(task, plan)
    except ValueError:
        return None
    return plan


def prompt_messages(row: dict[str, Any], args: argparse.Namespace) -> list[dict[str, str]]:
    return informed_chat_messages(row) if args.prompt_mode == "informed" else chat_messages(row)


def generate_batched_prompted(model: Any, tokenizer: Any, rows: list[dict[str, Any]], max_new_tokens: int,
                              batch_size: int, args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[str]]:
    """与 run_e1.generate_batched 同构，只是提示词由 prompt_messages 决定（支持 informed 臂）。"""
    from run_e1 import extract_json, normalise_prediction

    tokenizer.padding_side = "left"
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    device = next(model.parameters()).device
    predictions: list[dict[str, Any]] = []
    raw_outputs: list[str] = []
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        encoded_list = [
            render_chat(tokenizer, prompt_messages(row, args), add_generation_prompt=True)["input_ids"][0].tolist()
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
            raw = tokenizer.decode(output[i, maxlen:], skip_special_tokens=True)
            raw_outputs.append(raw)
            predictions.append(normalise_prediction(extract_json(raw)))
    return predictions, raw_outputs


def evaluate(model: Any, tokenizer: Any, data: dict[str, list[dict[str, Any]]], args: argparse.Namespace,
             out_dir: Path) -> dict[str, Any]:
    from run_e1 import generate_batched  # noqa: F401  (保留下游 import 兼容)

    report: dict[str, Any] = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        rows = data[split]
        t0 = time.time()
        predictions, raw = generate_batched_prompted(model, tokenizer, rows, args.max_new_tokens,
                                                     args.eval_batch_size, args)
        elapsed = round(time.time() - t0, 1)
        gen_tokens = sum(len(tokenizer(t, add_special_tokens=False)["input_ids"]) for t in raw)
        outcomes = []
        for row, text in zip(rows, raw):
            fixed = parse_plan(text, row)
            gold = row["gold"]["constraints"]
            if fixed is None:
                outcomes.append({"sample_id": row["sample_id"], "group_id": row["group_id"],
                                 "variant": row["variant"], "planned": False, "completed": False,
                                 "safe_success": False, "faithful_success": False, "extra_changes": None})
                continue
            env = check(row["task"], fixed, gold)
            changes = plan_change_count(row["task"], fixed)
            _, gold_info = symbolic_plan(row["task"], gold)
            deviates = fixed != default_plan(row["task"])
            extra = (changes - gold_info["changes"]) if env["safe_success"] else None
            outcomes.append({
                "sample_id": row["sample_id"], "group_id": row["group_id"], "variant": row["variant"],
                "planned": True, "completed": bool(env["completed"]),
                "safe_success": bool(env["safe_success"]),
                "faithful_success": bool(env["safe_success"]) and ((extra == 0) if gold else not deviates),
                "extra_changes": extra,
            })
        (out_dir / f"{split}.jsonl").write_text(
            "\n".join(json.dumps(o, ensure_ascii=False) for o in outcomes) + "\n", encoding="utf-8")
        report[split] = summarise(outcomes, elapsed, len(raw))
        report[split]["gen_tokens"] = gen_tokens
        print(json.dumps({"split": split, "faithful_constrained": report[split]["faithful_constrained"]}), flush=True)
    return report


def summarise(outcomes: list[dict[str, Any]], elapsed: float, n_raw: int) -> dict[str, Any]:
    constrained = [o for o in outcomes if o["variant"] in ("explicit", "implicit")]
    none_rows = [o for o in outcomes if o["variant"] == "none"]
    out: dict[str, Any] = {
        "n": len(outcomes), "elapsed_s": elapsed,
        "planned": sum(o["planned"] for o in outcomes) / len(outcomes),
        "safe_success": sum(o["safe_success"] for o in outcomes) / len(outcomes),
        "faithful": sum(o["faithful_success"] for o in outcomes) / len(outcomes),
        "faithful_constrained": (sum(o["faithful_success"] for o in constrained) / len(constrained)
                                 if constrained else None),
        "none_faithful": (sum(o["faithful_success"] for o in none_rows) / len(none_rows)) if none_rows else None,
    }
    by_variant = {}
    for v in ("explicit", "implicit", "none"):
        items = [o for o in outcomes if o["variant"] == v]
        if items:
            by_variant[v] = {"n": len(items), "faithful": sum(o["faithful_success"] for o in items) / len(items)}
    out["by_variant"] = by_variant
    return out


def pipeline_outcomes(data_dir: Path, split: str, run_dir: Path) -> list[dict[str, Any]]:
    """管线（1.7B seed42 编译器 + 符号规划器）逐记录 faithful，与单体同口径配对。"""
    rows = load_jsonl(data_dir / f"{split}.jsonl")
    preds = load_jsonl(run_dir / "trained_predictions" / f"{split}.jsonl")
    out = []
    for row, p in zip(rows, preds):
        o = record_outcome(row, strict_parse(p["raw"]))
        out.append({"sample_id": o["sample_id"], "group_id": o["group_id"], "variant": o["variant"],
                    "planned": o["planned"], "completed": o["completed"],
                    "safe_success": o["safe_success"], "faithful_success": o["faithful_success"],
                    "extra_changes": o["extra_changes"]})
    return out


def paired_bootstrap(a: list[dict[str, Any]], b: list[dict[str, Any]], key: str = "faithful_success",
                     n_boot: int = BOOT, seed: int = 20261124) -> dict[str, Any]:
    """按 group 配对 bootstrap：a - b 的差值与 95% 区间（两组预测同组一起重采样）。"""
    assert [x["sample_id"] for x in a] == [x["sample_id"] for x in b]
    groups: dict[str, list[int]] = defaultdict(list)
    for i, x in enumerate(a):
        groups[x["group_id"]].append(i)
    keys = list(groups)
    rng = random.Random(seed)
    diffs = []
    for _ in range(n_boot):
        picked = rng.choices(keys, k=len(keys))
        idx = [i for g in picked for i in groups[g]]
        diffs.append(sum(a[i][key] for i in idx) / len(idx) - sum(b[i][key] for i in idx) / len(idx))
    diffs.sort()
    mean = sum(a[i][key] for i in range(len(a))) / len(a) - sum(b[i][key] for i in range(len(b))) / len(b)
    return {"diff": mean, "ci95": [diffs[int(0.025 * n_boot)], diffs[int(0.975 * n_boot) - 1]],
            "n": len(a), "boot": n_boot}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data/processed_v5")
    ap.add_argument("--model", default=str(ROOT / "models" / "Qwen3-1.7B"))
    ap.add_argument("--out-dir", type=Path, default=ROOT / "outputs/submission/e2_monolithic")
    ap.add_argument("--pipeline-run", type=Path, default=ROOT / "outputs/e1/Qwen3-1.7B-v5-seed42")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--learning-rate", type=float, default=2e-4)
    ap.add_argument("--lora-rank", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--gradient-accumulation-steps", type=int, default=4)
    ap.add_argument("--max-seq-len", type=int, default=1280)
    ap.add_argument("--max-new-tokens", type=int, default=384)
    ap.add_argument("--eval-batch-size", type=int, default=32)
    ap.add_argument("--precision", choices=("fp16", "bf16"), default="bf16")
    ap.add_argument("--skip-train", action="store_true", help="仅用已存 adapter 复测")
    ap.add_argument("--prompt-mode", choices=("compiler", "informed"), default="compiler",
                    help="compiler=旧版（复用编译器提示，信息不对等）；informed=给出完整任务结构（公平对照）")
    args = ap.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    t0 = time.time()
    model, tokenizer = load_model(args.model, args.precision)

    data = {s: load_jsonl(args.data_dir / f"{s}.jsonl") for s in SPLITS}
    train_rows = load_jsonl(args.data_dir / "train.jsonl")

    budget: dict[str, Any] = {}
    if not args.skip_train:
        budget = train_monolithic(model, tokenizer, train_rows, args)
        model.save_pretrained(args.out_dir / "adapter")
    else:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.out_dir / "adapter")
        model.eval()

    report = evaluate(model, tokenizer, data, args, args.out_dir / "predictions")

    paired: dict[str, Any] = {}
    for split in SPLITS:
        pipe = pipeline_outcomes(args.data_dir, split, args.pipeline_run)
        mono = [json.loads(line) for line in
                (args.out_dir / "predictions" / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]
        constrained_pipe = [o for o in pipe if o["variant"] in ("explicit", "implicit")]
        constrained_mono = [o for o in mono if o["variant"] in ("explicit", "implicit")]
        if len(constrained_pipe) == len(constrained_mono):
            paired[split] = paired_bootstrap(constrained_mono, constrained_pipe)
            paired[split]["pipeline_faithful_constrained"] = (
                sum(o["faithful_success"] for o in constrained_pipe) / len(constrained_pipe))
            paired[split]["monolithic_faithful_constrained"] = (
                sum(o["faithful_success"] for o in constrained_mono) / len(constrained_mono))

    overall_constrained = []
    for split in SPLITS:
        pipe = pipeline_outcomes(args.data_dir, split, args.pipeline_run)
        mono = [json.loads(line) for line in
                (args.out_dir / "predictions" / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]
        overall_constrained.append((mono, pipe))
    flat_mono = [o for pair in overall_constrained for o in pair[0] if o["variant"] in ("explicit", "implicit")]
    flat_pipe = [o for pair in overall_constrained for o in pair[1] if o["variant"] in ("explicit", "implicit")]
    paired["overall"] = paired_bootstrap(flat_mono, flat_pipe)

    metrics = {
        "design": "B1 monolithic query->plan vs v5 pipeline (compiler + symbolic planner)",
        "prompt_mode": args.prompt_mode,
        "model": args.model, "seed": args.seed, "precision": args.precision,
        "data_sha256": {s: hashlib.sha256((args.data_dir / f"{s}.jsonl").read_bytes()).hexdigest()
                        for s in ["train"] + list(data)},
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "budget": budget, "train_rows": len(train_rows),
        "elapsed_s": round(time.time() - t0, 1),
        "splits": report, "paired_vs_pipeline": paired,
        "preregistered_rule": "mono >= pipe - 1pp and CI covers 0 => separation claim falsified (report as is)",
    }
    (args.out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"saved": str(args.out_dir / "metrics.json"),
                      "overall_paired": paired["overall"]}), flush=True)


if __name__ == "__main__":
    main()
