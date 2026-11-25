"""E3 A 系字段消融：0.6B 单 seed，每臂从表示中去掉一个组件后按同预算重训编译器。

A1 去 typed：target 退化为自由文本列表（"{type}: {params json}"）
A2 去 evidence_span：记录审计字段移除（规划器从不读它，预期下游 faithful 不变）
A3 去三态：constraints.state 与 query_state 三值 -> 二值（有/无约束）
A4 去 scope：角色绑定字段移除（规划器从不读它，预期下游 faithful 不变）

评测双轴（金标仅在评测阶段可见）：
  记录轴 = run_e1.score()（金标与预测按同一臂 schema 同步裁剪后复用官方评分器）
          + full-contract 解析率（部署成本：被 fail-closed 评测器拒绝的比例）
  下游轴 = 符号规划器（主管线同款）回放 faithful_constrained
预注册诚实预期：A1 下游崩（typed 必要性）；A2/A4 下游不变（字段消费方分层）；
A3 下游不变但隐式行 core F1 可能下滑（三态信号是否承载恢复能力由数据回答）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from pathlib import Path
from typing import Any

import torch

from dataset_v5_spec import POLICY_CARD
from eval_exec import record_outcome
from rescore_v4_side import load_jsonl
from run_e1 import (SCHEMA_HINT_V4, catalog_lines, chat_messages, core_key, eval_subsets,
                    load_model, render_chat, require_finite_loss, score, strict_parse)
from trust_env import check, default_plan, normalize_constraint, plan as symbolic_plan, plan_change_count

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho")
FIELDS = ("type", "state", "severity", "scope", "params", "evidence_span")


def ablate_schema_hint(arm: str) -> str:
    hint = SCHEMA_HINT_V4
    if arm == "A2":
        return re.sub(r',"evidence_span":"<copied query sentence>"', "", hint)
    if arm == "A3":
        hint = re.sub(r'"state":"explicit\|implicit",', "", hint)
        return hint.replace('"query_state":"explicit|implicit|none"', '"query_state":"explicit|none"')
    if arm == "A4":
        return re.sub(r',"scope":\["role:\.\.\."\]', "", hint)
    if arm == "A1":
        return '{"constraints":["<type>: <params json>", ...]}'
    raise ValueError(arm)


def ablate_policy_card(arm: str) -> str:
    card = POLICY_CARD
    if arm == "A4":
        card = re.sub(r"; scope = [^.\n]*", "", card)
        card = re.sub(r"scope = [^.\n]*\.", "", card)
    return card


def ablated_chat_messages(row: dict[str, Any], arm: str) -> list[dict[str, str]]:
    """与 run_e1.chat_messages 同构，仅替换 schema 提示与策略卡（ ablation 的 prompt 侧同步生效）。"""
    prompt = (
        "You are a typed constraint compiler for tool-planning tasks in a trusted data space. "
        "Extract every constraint the user's query places on the plan as typed objects; return an empty "
        "list when nothing restricts the plan. Never invent a constraint the query does not support.\n"
        + ablate_policy_card(arm) + "\n"
        "Tool catalog (role: name; paid|free; local|external):\n" + catalog_lines(row) + "\n"
        "Output JSON only, matching: " + ablate_schema_hint(arm) + "\n"
        "User query: " + row["query"] + "\n"
        "JSON:"
    )
    return [{"role": "system", "content": "Output JSON only."}, {"role": "user", "content": prompt}]


def ablated_target(row: dict[str, Any], arm: str) -> str:
    """训练 target：按臂裁剪金标约束（与 prompt 的 schema 一致）。"""
    gold = row["gold"]
    constraints = [dict(c) for c in gold["constraints"]]
    if arm == "A2":
        for c in constraints:
            c.pop("evidence_span", None)
    elif arm == "A3":
        for c in constraints:
            c.pop("state", None)
        state = "explicit" if gold["query_state"] in ("explicit", "implicit") else "none"
        return json.dumps({"query_state": state, "constraints": constraints},
                          ensure_ascii=False, separators=(",", ":"))
    elif arm == "A4":
        for c in constraints:
            c.pop("scope", None)
    elif arm == "A1":
        rendered = [f'{c["type"]}: {json.dumps(c["params"], ensure_ascii=False, separators=(",", ":"))}'
                    for c in constraints]
        return json.dumps({"constraints": rendered}, ensure_ascii=False, separators=(",", ":"))
    return json.dumps({"query_state": gold["query_state"], "constraints": constraints},
                      ensure_ascii=False, separators=(",", ":"))


def ablated_gold(row: dict[str, Any], arm: str) -> dict[str, Any]:
    """评测侧金标：与训练 target 同规则裁剪（A3 三态->二值，A4 去 scope，A2 去 evidence_span）。"""
    gold = json.loads(json.dumps(row["gold"]))
    constraints = [dict(c) for c in gold["constraints"]]
    if arm == "A2":
        for c in constraints:
            c.pop("evidence_span", None)
    elif arm == "A3":
        for c in constraints:
            c.pop("state", None)
        gold["query_state"] = "explicit" if gold["query_state"] in ("explicit", "implicit") else "none"
    elif arm == "A4":
        for c in constraints:
            c.pop("scope", None)
    gold["constraints"] = constraints
    return gold


def scoring_gold(row: dict[str, Any], arm: str) -> dict[str, Any]:
    """记录轴金标：在裁剪版基础上注入哨兵值，使被消融字段两侧恒等匹配（不参与区分），
    从而复用官方评分器比较其余字段。A3 哨兵 state=explicit；A4 哨兵 scope=[]。"""
    gold = ablated_gold(row, arm)
    for c in gold["constraints"]:
        if arm == "A3":
            c["state"] = "explicit"
        elif arm == "A4":
            c["scope"] = []
    return gold


def scoring_raw(text: str, arm: str) -> str:
    """记录轴预测：宽松解析后注入同样哨兵值；解析失败则原文返回（保持 malformed 计数）。"""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    for candidate in ([match.group(0)] if match else []) + [text.strip()]:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict) or not isinstance(value.get("constraints"), list):
            continue
        for c in value["constraints"]:
            if not isinstance(c, dict):
                continue
            if arm == "A3":
                c.setdefault("state", "explicit")
            elif arm == "A4":
                c.setdefault("scope", [])
        return json.dumps(value, ensure_ascii=False)
    return text


def train_ablated(model: Any, tokenizer: Any, rows: list[dict[str, Any]], arm: str,
                  args: argparse.Namespace) -> dict[str, Any]:
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
        prefix = render_chat(tokenizer, ablated_chat_messages(row, arm),
                             add_generation_prompt=True)["input_ids"][0].tolist()
        completion = tokenizer(ablated_target(row, arm) + tokenizer.eos_token,
                               add_special_tokens=False)["input_ids"]
        if len(prefix) + len(completion) > args.max_seq_len:
            dropped += 1
            continue
        examples.append((prefix + completion, [-100] * len(prefix) + completion))

    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.learning_rate)
    trainable = [p for p in model.parameters() if p.requires_grad]
    rng = random.Random(args.seed)
    steps_per_epoch = len(examples) // args.gradient_accumulation_steps
    total_steps = steps_per_epoch * args.epochs
    tokens = {"prompt": 0, "completion": 0}
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
            tokens["prompt"] += n_prompt
            tokens["completion"] += len(labels_list) - n_prompt
            accumulation += 1
            if accumulation == args.gradient_accumulation_steps:
                torch.nn.utils.clip_grad_norm_(trainable, 1.0, error_if_nonfinite=True)
                optimizer.step()
                if any(not torch.isfinite(p.detach()).all() for p in trainable):
                    raise FloatingPointError(f"non-finite parameter after optimizer_step={done + 1}")
                optimizer.zero_grad(set_to_none=True)
                accumulation = 0
                done += 1
        if accumulation:
            torch.nn.utils.clip_grad_norm_(trainable, 1.0, error_if_nonfinite=True)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            done += 1
    model.eval()
    model.config.use_cache = True
    return {"steps": done, "tokens": tokens, "examples": len(examples), "dropped": dropped}


def extract_constraints(text: str) -> list[Any] | None:
    """宽松抽取：只要 constraints 数组（供下游轴用；记录轴仍走 fail-closed strict_parse）。"""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    for candidate in ([match.group(0)] if match else []) + [text.strip()]:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and isinstance(value.get("constraints"), list):
            return value["constraints"]
    return None


def coerce_item(item: Any) -> dict[str, Any] | None:
    """把预测条目转成约束 dict。A1 臂的输出是自由文本 '<type>: <params json>'，必须可解析，
    否则下游轴会被 isinstance 过滤成空约束集，使 A1 的 faithful 恒为 0（不是测出来的）。"""
    if isinstance(item, dict):
        return item
    if isinstance(item, str):
        match = re.match(r"\s*([a-z_]+)\s*:\s*(\{.*\})\s*$", item, flags=re.DOTALL)
        if match:
            try:
                params = json.loads(match.group(2))
            except json.JSONDecodeError:
                return None
            if isinstance(params, dict):
                return {"type": match.group(1), "params": params}
    return None


def downstream_faithful(rows: list[dict[str, Any]], raw: list[str]) -> dict[str, Any]:
    """下游轴：宽松约束 -> 符号规划器（主管线同款）-> faithful（安全且改动数=金标最小）。"""
    out = []
    for row, text in zip(rows, raw):
        task = row["task"]
        gold = row["gold"]["constraints"]
        items = extract_constraints(text)
        coerced = [c for c in (coerce_item(i) for i in (items or [])) if c is not None]
        pred = [c for c in coerced if normalize_constraint(c, task) is not None]
        fixed, info = symbolic_plan(task, pred)
        env = check(task, fixed, gold)
        changes = info["changes"]
        _, gold_info = symbolic_plan(task, gold)
        deviates = fixed != default_plan(task)
        extra = (changes - gold_info["changes"]) if env["safe_success"] else None
        out.append({
            "sample_id": row["sample_id"], "variant": row["variant"], "gold_count": len(gold),
            "planned": fixed is not None, "safe_success": bool(env["safe_success"]),
            "faithful": bool(env["safe_success"]) and ((extra == 0) if gold else not deviates),
            "n_constraints_pred": len(coerced),
            "n_constraints_usable": len(pred),
            "n_constraints_unusable": len(coerced) - len(pred),
        })
    constrained = [o for o in out if o["gold_count"]]
    none_rows = [o for o in out if not o["gold_count"]]
    return {
        "n": len(out),
        "faithful_constrained": (sum(o["faithful"] for o in constrained) / len(constrained)) if constrained else None,
        "safe_constrained": (sum(o["safe_success"] for o in constrained) / len(constrained)) if constrained else None,
        "none_faithful": (sum(o["faithful"] for o in none_rows) / len(none_rows)) if none_rows else None,
        "none_false_alarm": (sum(o["n_constraints_usable"] > 0 for o in none_rows) / len(none_rows)) if none_rows else None,
        "none_planned_constraints_mean": (sum(o["n_constraints_pred"] for o in none_rows) / len(none_rows)) if none_rows else None,
        "implicit_faithful": (lambda items: sum(o["faithful"] for o in items) / len(items) if items else None)(
            [o for o in constrained if o["variant"] == "implicit"]),
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", choices=("A1", "A2", "A3", "A4"), required=True)
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data/processed_v5")
    ap.add_argument("--model", default=str(ROOT / "models" / "Qwen3-0.6B"))
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument("--baseline-run", type=Path, default=ROOT / "outputs/e1/Qwen3-0.6B-v5-seed42")
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
    ap.add_argument("--skip-train", action="store_true")
    args = ap.parse_args(argv)

    out_dir = args.out_dir or (ROOT / "outputs/submission/e3_ablation" / args.arm)
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    t0 = time.time()
    model, tokenizer = load_model(args.model, args.precision)

    data = {s: load_jsonl(args.data_dir / f"{s}.jsonl") for s in SPLITS}
    train_rows = load_jsonl(args.data_dir / "train.jsonl")
    budget: dict[str, Any] = {}
    if not args.skip_train:
        budget = train_ablated(model, tokenizer, train_rows, args.arm, args)
        model.save_pretrained(out_dir / "adapter")
    else:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, out_dir / "adapter")
        model.eval()

    from run_e1 import generate_batched

    report: dict[str, Any] = {"arm": args.arm, "dropped_fields": {
        "A1": "typed representation", "A2": "evidence_span", "A3": "three-state", "A4": "scope"}[args.arm]}
    for split in SPLITS:
        rows = data[split]
        _, raw = generate_batched(model, tokenizer, rows, args.max_new_tokens, args.eval_batch_size)
        (out_dir / "predictions").mkdir(parents=True, exist_ok=True)
        (out_dir / "predictions" / f"{split}.jsonl").write_text(
            "\n".join(json.dumps({"sample_id": r["sample_id"], "raw": t}, ensure_ascii=False)
                      for r, t in zip(rows, raw)) + "\n", encoding="utf-8")
        # 记录轴：金标与预测按同臂 schema 对齐（哨兵值使被消融字段恒等匹配），复用官方评分器
        if args.arm == "A1":
            predictions = []
            for text in raw:
                items = extract_constraints(text)
                predictions.append({"constraints": items} if items is not None else None)
            want = sum(len(r["gold"]["constraints"]) for r in rows)
            got = sum(len(p["constraints"]) for p in predictions if p)
            record = {"free_text_note": "set-size proxy only; typed F1 undefined by design",
                      "gold_items": want, "pred_items": got}
        else:
            scoring_rows = [dict(r, gold=scoring_gold(r, args.arm)) for r in rows]
            scoring_raws = [scoring_raw(t, args.arm) for t in raw]
            record = score(scoring_rows, [strict_parse(t) for t in scoring_raws], scoring_raws)
        full_contract = sum(strict_parse(t) is not None for t in raw) / len(raw)
        report[split] = {
            "record": record, "full_contract_parse_rate": full_contract,
            "downstream": downstream_faithful(rows, raw),
        }
        print(json.dumps({"arm": args.arm, "split": split,
                          "faithful_constrained": report[split]["downstream"]["faithful_constrained"]}), flush=True)

    metrics = {
        "arm": args.arm, "model": args.model, "seed": args.seed, "precision": args.precision,
        "data_sha256": hashlib.sha256((args.data_dir / "train.jsonl").read_bytes()).hexdigest(),
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "budget": budget, "train_rows": len(train_rows),
        "elapsed_s": round(time.time() - t0, 1), "splits": report,
        "note": "gold visible only at evaluation; prompt+target ablated symmetrically",
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps({"saved": str(out_dir / "metrics.json")}), flush=True)


if __name__ == "__main__":
    main()
