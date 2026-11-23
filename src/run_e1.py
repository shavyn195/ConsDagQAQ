"""E1 实验：约束编译器 trained vs zero-shot（T/Z 臂）。

数据：data/processed_v4（可执行任务世界，E/I/N 最小三元组，双 group-held-out）；v2/v3 旧数据走旧 prompt。
流程：zero-shot 评测 -> LoRA 训练 -> 训练后评测。
指标：e1_score_v5 = 严格键 micro P/R/F1 + 核心键（type+params）P/R/F1 + 三态分桶 + per-type
     + I 版难度分桶 + 记录级全对率 + N 版误报率 + evidence span + parse rate；
     v4 额外给执行级 e1_exec_v1（编译输出 -> 规划器 -> 独立检查器的约束安全成功率）。
     按 subset（dev in-domain / test_tpl_ho / test_tool_ho）分列。
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
OPTIONAL_SUBSETS = ["test_struct_ho"]  # v5 起新增；v4 数据目录没有该文件，行为不变


def eval_subsets(data_dir: Path) -> list[str]:
    return SUBSETS + [s for s in OPTIONAL_SUBSETS if (Path(data_dir) / f"{s}.jsonl").exists()]


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


def task_space_context(row: dict[str, Any]) -> str:
    """Expose the compiler's task-space interface needed for scope binding.

    Scope is defined over abstract roles, but role names alone do not reveal
    which roles are billable, external, terminal, or data-bearing. The graph
    metadata is part of the task-space input and is intentionally kept
    separate from the gold constraint object.
    """
    graph = row.get("graph") or {}
    nodes = graph.get("nodes") if isinstance(graph, dict) else []
    compact_nodes = []
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        compact_nodes.append({
            "role": f"role:{node.get('role', '')}",
            "cost_cny": node.get("cost_cny"),
            "duration_min": node.get("duration_min"),
            "recipient": node.get("recipient"),
            "data_classes": node.get("data_classes", []),
            "terminal": bool(node.get("terminal_output", False)),
        })
    return json.dumps(compact_nodes, ensure_ascii=False, separators=(",", ":"))


SCHEMA_HINT_V4 = (
    '{"query_state":"explicit|implicit|none","constraints":[{"type":"...","state":"explicit|implicit",'
    '"severity":"high|medium","scope":["role:..."],"params":{...},"evidence_span":"<copied query sentence>"}]}'
)


def catalog_lines(row: dict[str, Any]) -> str:
    return "\n".join(
        f"- {t['role']}: {t['name']}; {'paid' if t['paid'] else 'free'}; {t['recipient']}" for t in row["catalog"]
    )


def chat_messages_v4(row: dict[str, Any]) -> list[dict[str, str]]:
    if row.get("spec_version") == "v5":
        from dataset_v5_spec import POLICY_CARD
    else:
        from dataset_v4_spec import POLICY_CARD

    prompt = (
        "You are a typed constraint compiler for tool-planning tasks in a trusted data space. "
        "Extract every constraint the user's query places on the plan as typed objects; return an empty "
        "list when nothing restricts the plan. Never invent a constraint the query does not support.\n"
        + POLICY_CARD + "\n"
        "Tool catalog (role: name; paid|free; local|external):\n" + catalog_lines(row) + "\n"
        "Output JSON only, matching: " + SCHEMA_HINT_V4 + "\n"
        "User query: " + row["query"] + "\n"
        "JSON:"
    )
    return [
        {"role": "system", "content": "Output JSON only."},
        {"role": "user", "content": prompt},
    ]


def chat_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    if "catalog" in row:
        return chat_messages_v4(row)
    prompt = (
        "You are a typed constraint compiler for tool-planning tasks in a trusted data space. "
        "Extract the user's constraints into typed objects; output an empty list when the query "
        "carries no constraint. Never invent a constraint that the query does not support.\n"
        "Output JSON only, matching this schema:\n" + SCHEMA_HINT + "\n"
        "Available role vocabulary: " + json.dumps(row["available_roles"], ensure_ascii=False) + "\n"
        "Task-space node metadata for scope binding (do not invent nodes): "
        + task_space_context(row) + "\n"
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


VALID_QUERY_STATES = ("explicit", "implicit", "none")


def _stable_json(value: Any) -> str:
    # 任意非 str 值的稳定序列化，保证键可哈希、可比较
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def prediction_is_well_formed(value: Any) -> bool:
    """结构契约：顶层 dict；query_state 显式三态；constraints 为 list；
    每条约束为 dict 且含 type(str)/state(三态)/severity(str)/params(dict)/scope(str 或 list[str])。"""
    if not isinstance(value, dict):
        return False
    if value.get("query_state") not in VALID_QUERY_STATES:
        return False
    constraints = value.get("constraints")
    if not isinstance(constraints, list):
        return False
    for c in constraints:
        if not isinstance(c, dict):
            return False
        if not isinstance(c.get("type"), str):
            return False
        if c.get("state") not in VALID_QUERY_STATES:
            return False
        if not isinstance(c.get("severity"), str):
            return False
        if not isinstance(c.get("params"), dict):
            return False
        scope = c.get("scope")
        if isinstance(scope, list):
            if not all(isinstance(s, str) for s in scope):
                return False
        elif not isinstance(scope, str):
            return False
    return True


def strict_parse(text: str) -> dict[str, Any] | None:
    """严格解析：结构不完整的输出视为无效，不得参与任何得分（fail-closed）。"""
    text = text.strip()
    candidates = []
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        candidates.append(match.group(0))
    candidates.append(text)
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if prediction_is_well_formed(value):
            return value
    return None


def normalise_prediction(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {"query_state": "none", "abstain": True, "constraints": []}
    constraints = value.get("constraints")
    if not isinstance(constraints, list):
        constraints = []
    constraints = [c for c in constraints if isinstance(c, dict)]
    return {
        "query_state": value.get("query_state", "none"),
        "abstain": bool(value.get("abstain", False)),
        "constraints": constraints,
    }


def require_finite_loss(loss: Any, *, torch: Any, epoch: int, example_index: int, optimizer_step: int) -> None:
    if not torch.isfinite(loss.detach()).all():
        raise FloatingPointError(
            f"non-finite loss before backward at epoch={epoch}, example={example_index}, "
            f"optimizer_step={optimizer_step}: {loss.detach().item()}"
        )


def constraint_key(item: dict[str, Any]) -> tuple[Any, ...]:
    # Scope is a set of bound roles; model output order must not affect matching.
    # 兜底：非 str 元素稳定序列化，保证任何输入都不抛 TypeError: unhashable type
    def element_key(e: Any) -> Any:
        return e if isinstance(e, str) else _stable_json(e)

    scope = item.get("scope", [])
    if isinstance(scope, list):
        scope_key = tuple(sorted(element_key(e) for e in scope))
    elif isinstance(scope, str):
        scope_key = (scope,)
    else:
        scope_key = (_stable_json(scope),)
    return (
        element_key(item.get("type")), element_key(item.get("state")), element_key(item.get("severity")),
        scope_key,
        _stable_json(_canonical(item.get("params") or {})),
    )


def _canonical(value: Any) -> Any:
    # 整值浮点与整数等价（350.0 == 350），其余原样
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_canonical(v) for v in value]
    return value


def core_key(item: dict[str, Any]) -> tuple[Any, ...]:
    """核心键：只看决定执行行为的 type+params（与 state/severity/scope 的表述约定无关）。"""
    ctype = item.get("type")
    return (ctype if isinstance(ctype, str) else _stable_json(ctype), _stable_json(_canonical(item.get("params") or {})))


def _multiset_matches(got: list[tuple[Any, ...]], want: list[tuple[Any, ...]]) -> int:
    pool: dict[tuple[Any, ...], int] = {}
    for key in got:
        pool[key] = pool.get(key, 0) + 1
    matched = 0
    for key in want:
        if pool.get(key, 0):
            pool[key] -= 1
            matched += 1
    return matched


def score(rows: list[dict[str, Any]], predictions: list[dict[str, Any]], raw: list[str]) -> dict[str, Any]:
    if not (len(rows) == len(predictions) == len(raw)):
        raise ValueError(
            "score inputs must have equal lengths: "
            f"rows={len(rows)}, predictions={len(predictions)}, raw={len(raw)}"
        )

    state_correct = 0
    state_correct_by_variant: dict[str, int] = {}
    count_by_variant: dict[str, int] = {}
    true_positive = false_positive = false_negative = 0
    per_variant: dict[str, dict[str, int]] = {}
    per_type: dict[str, dict[str, int]] = {}
    per_difficulty: dict[str, dict[str, int]] = {}
    evidence_exact = evidence_total = 0
    difficulty_unattributed_fp = 0
    parse_ok = 0
    malformed_predictions = 0
    core_tp = core_fp = core_fn = 0
    exact_records = 0
    exact_by_variant: dict[str, int] = {}
    for row, pred, raw_text in zip(rows, predictions, raw):
        gold = row["gold"]
        # e1_score_v4：得分以严格解析的 raw 为唯一依据；结构不完整即无效（fail-closed），
        # 不给 state/empty_set 分，金标约束全部计 FN，且不产生 FP。
        strict = strict_parse(raw_text)
        valid_json = strict is not None
        if valid_json:
            parse_ok += 1
        else:
            malformed_predictions += 1
        state_value = strict.get("query_state") if valid_json else None
        state_correct += int(valid_json and state_value == gold["query_state"])
        state_correct_by_variant[row["variant"]] = state_correct_by_variant.get(row["variant"], 0) + int(
            valid_json and state_value == gold["query_state"]
        )
        count_by_variant[row["variant"]] = count_by_variant.get(row["variant"], 0) + 1
        v = per_variant.setdefault(
            row["variant"],
            {"n": 0, "tp": 0, "fp": 0, "fn": 0,
             "empty_gold": 0, "empty_pred": 0, "empty_correct": 0, "false_alarm": 0},
        )
        v["n"] += 1
        got = [c for c in strict.get("constraints", []) if isinstance(c, dict)] if valid_json else []
        want = [c for c in gold.get("constraints", []) if isinstance(c, dict)]
        got_keys = [constraint_key(c) for c in got]
        want_keys = [constraint_key(c) for c in want]
        pred_indices_by_key: dict[tuple[Any, ...], list[int]] = {}
        for pi, key in enumerate(got_keys):
            pred_indices_by_key.setdefault(key, []).append(pi)
        matched_pairs: list[tuple[int, int]] = []
        unmatched_gold: list[int] = []
        for gi, key in enumerate(want_keys):
            matches = pred_indices_by_key.get(key, [])
            if matches:
                matched_pairs.append((gi, matches.pop(0)))
            else:
                unmatched_gold.append(gi)
        matched_gold = {gi for gi, _ in matched_pairs}
        matched_pred = {pi for _, pi in matched_pairs}
        unmatched_pred = [pi for pi in range(len(got)) if pi not in matched_pred]
        matched = len(matched_pairs)
        row_fp = len(unmatched_pred)
        row_fn = len(unmatched_gold)
        v["tp"] += matched
        v["fp"] += row_fp
        v["fn"] += row_fn
        v["empty_gold"] += int(not want)
        v["empty_pred"] += int(not got)
        v["empty_correct"] += int(valid_json and not want and not got)
        v["false_alarm"] += int(valid_json and not want and bool(got))
        true_positive += matched
        false_positive += row_fp
        false_negative += row_fn
        core_matched = _multiset_matches([core_key(c) for c in got], [core_key(c) for c in want])
        core_tp += core_matched
        core_fp += len(got) - core_matched
        core_fn += len(want) - core_matched
        exact = int(valid_json and state_value == gold["query_state"] and row_fp == 0 and row_fn == 0)
        exact_records += exact
        exact_by_variant[row["variant"]] = exact_by_variant.get(row["variant"], 0) + exact

        for gi, g in enumerate(want):
            t = per_type.setdefault(g["type"], {"n": 0, "tp": 0, "fp": 0, "fn": 0})
            t["n"] += 1
            t["tp"] += int(gi in matched_gold)
            t["fn"] += int(gi not in matched_gold)
        for pi in unmatched_pred:
            p = got[pi]
            t = per_type.setdefault(p.get("type", "?"), {"n": 0, "tp": 0, "fp": 0, "fn": 0})
            t["fp"] += 1

        if row["variant"] == "implicit" and row["hint_meta"]:
            meta = row["hint_meta"]
            if len(meta) != len(want):
                raise ValueError(
                    f"hint_meta/gold constraint length mismatch for {row.get('sample_id')}: "
                    f"hint_meta={len(meta)}, gold_constraints={len(want)}"
                )
            for gi, (g, m) in enumerate(zip(want, meta)):
                d = per_difficulty.setdefault(
                    f"d{m['difficulty']}", {"n": 0, "tp": 0, "fp": 0, "fn": 0}
                )
                d["n"] += 1
                d["tp"] += int(gi in matched_gold)
                d["fn"] += int(gi not in matched_gold)

            # Attribute a near-miss FP to a same-type gold cue; truly extra types stay visible separately.
            available_gold = set(unmatched_gold)
            for pi in unmatched_pred:
                candidates = [gi for gi in sorted(available_gold) if want[gi].get("type") == got[pi].get("type")]
                if candidates:
                    gi = candidates[0]
                    available_gold.remove(gi)
                    d = per_difficulty[f"d{meta[gi]['difficulty']}"]
                    d["fp"] += 1
                else:
                    difficulty_unattributed_fp += 1

        for gi, pi in matched_pairs:
            evidence_total += 1
            evidence_exact += int(got[pi].get("evidence_span") == want[gi].get("evidence_span"))
    n = max(len(rows), 1)

    def prf(tp: int, fp: int, fn: int) -> dict[str, Any]:
        p = tp / (tp + fp) if tp + fp else None
        r = tp / (tp + fn) if tp + fn else None
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
        return {"precision": p, "recall": r, "f1": f1}

    return {
        "metrics_version": "e1_score_v5",
        "records": len(rows),
        "state_accuracy": state_correct / n,
        "state_accuracy_by_variant": {
            k: state_correct_by_variant[k] / max(count_by_variant[k], 1) for k in count_by_variant
        },
        "constraint_micro": prf(true_positive, false_positive, false_negative),
        "constraint_core_micro": prf(core_tp, core_fp, core_fn),
        "record_exact_match": exact_records / n,
        "record_exact_match_by_variant": {
            k: exact_by_variant[k] / max(count_by_variant[k], 1) for k in count_by_variant
        },
        "per_variant": {
            k: {
                **prf(v["tp"], v["fp"], v["fn"]),
                "records": v["n"],
                "empty_set_accuracy": v["empty_correct"] / max(v["n"], 1),
                "gold_empty_records": v["empty_gold"],
                "prediction_empty_records": v["empty_pred"],
                # 误报率：金标为空却输出了约束（结构无效的输出不计为误报，单独计入 malformed）
                "false_alarm_rate": v["false_alarm"] / v["empty_gold"] if v["empty_gold"] else None,
            }
            for k, v in per_variant.items()
        },
        "per_type": {k: {**prf(v["tp"], v["fp"], v["fn"]), "gold_records": v["n"]} for k, v in per_type.items()},
        "per_difficulty_implicit": {
            k: {
                "tp": v["tp"], "fp": v["fp"], "fn": v["fn"],
                **prf(v["tp"], v["fp"], v["fn"]),
                "gold_constraints": v["n"],
            }
            for k, v in per_difficulty.items()
        },
        "per_difficulty_unattributed_fp": difficulty_unattributed_fp,
        "evidence_exact_rate": evidence_exact / evidence_total if evidence_total else None,
        "evidence_records": evidence_total,
        "json_parse_rate": parse_ok / n,
        "malformed_prediction_count": malformed_predictions,
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


def load_model(model_path: str, precision: str) -> tuple[Any, Any]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    torch_dtype = torch.bfloat16 if precision == "bf16" else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch_dtype, device_map="cuda", trust_remote_code=True,
    )
    model.eval()
    return model, tokenizer


def evaluate_all(model: Any, tokenizer: Any, data: dict[str, list[dict[str, Any]]], args: argparse.Namespace, tag: str, out_dir: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for subset in data:
        rows = data[subset]
        t0 = time.time()
        predictions, raw = generate_batched(model, tokenizer, rows, args.max_new_tokens, args.eval_batch_size)
        results[subset] = score(rows, predictions, raw)
        if rows and "task" in rows[0]:
            from eval_exec import evaluate as evaluate_exec

            results[subset]["exec"] = evaluate_exec(rows, raw)[0]
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
    dropped = 0
    for row in rows:
        prefix = render_chat(tokenizer, chat_messages(row), add_generation_prompt=True)["input_ids"][0].tolist()
        completion = tokenizer(target_json(row) + tokenizer.eos_token, add_special_tokens=False)["input_ids"]
        if len(prefix) + len(completion) > args.max_seq_len:
            dropped += 1
            continue
        examples.append((prefix + completion, [-100] * len(prefix) + completion))
    if dropped:
        print(json.dumps({"warning": "examples dropped by max_seq_len", "dropped": dropped}))
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.learning_rate)
    trainable_parameters = [p for p in model.parameters() if p.requires_grad]
    rng = random.Random(args.seed)
    steps_per_epoch = len(examples) // args.gradient_accumulation_steps
    total_steps = steps_per_epoch * args.epochs
    target_steps = total_steps if args.smoke_train_steps is None else min(total_steps, args.smoke_train_steps)
    done = 0
    print(json.dumps({"train_examples": len(examples), "planned_optimizer_steps": total_steps,
                      "target_optimizer_steps": target_steps}))
    for epoch in range(args.epochs):
        rng.shuffle(examples)
        accumulation = 0
        for example_index, (ids_list, labels_list) in enumerate(examples):
            if done >= target_steps:
                break
            ids = torch.tensor([ids_list], dtype=torch.long, device=device)
            labels = torch.tensor([labels_list], dtype=torch.long, device=device)
            out = model(input_ids=ids, attention_mask=torch.ones_like(ids), labels=labels)
            require_finite_loss(
                out.loss, torch=torch, epoch=epoch + 1,
                example_index=example_index, optimizer_step=done + 1,
            )
            (out.loss / args.gradient_accumulation_steps).backward()
            accumulation += 1
            if accumulation == args.gradient_accumulation_steps:
                torch.nn.utils.clip_grad_norm_(trainable_parameters, 1.0, error_if_nonfinite=True)
                optimizer.step()
                if any(not torch.isfinite(parameter.detach()).all() for parameter in trainable_parameters):
                    raise FloatingPointError(
                        f"non-finite trainable parameter after optimizer_step={done + 1}"
                    )
                optimizer.zero_grad(set_to_none=True)
                accumulation = 0
                done += 1
                if done % 100 == 0 or done == 1:
                    print(json.dumps({"optimizer_step": done, "loss": float(out.loss.detach().cpu()),
                                      "elapsed_s": round(time.time() - args._t0, 1)}))
        if accumulation:
            torch.nn.utils.clip_grad_norm_(trainable_parameters, 1.0, error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(parameter.detach()).all() for parameter in trainable_parameters):
                raise FloatingPointError(
                    f"non-finite trainable parameter after optimizer_step={done + 1}"
                )
            optimizer.zero_grad(set_to_none=True)
            done += 1
    model.eval()
    model.config.use_cache = True
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=str(ROOT / "models" / "Qwen3-0.6B"))
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "processed_v4")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--max-seq-len", type=int, default=1280)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument("--eval-batch-size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--precision", choices=("fp16", "bf16"), default="bf16")
    parser.add_argument("--smoke-train-steps", type=int, default=None,
                        help="Run only this many optimizer steps and skip saving/evaluation; for launch checks.")
    parser.add_argument("--skip-zeroshot", action="store_true")
    parser.add_argument("--skip-train", action="store_true")
    args = parser.parse_args()
    if args.smoke_train_steps is not None and args.smoke_train_steps < 1:
        parser.error("--smoke-train-steps must be at least 1")

    model_name = Path(args.model).name
    args.out_dir = args.out_dir or ROOT / "outputs" / "e1" / model_name
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args._t0 = time.time()

    data = {subset: load_jsonl(args.data_dir / f"{subset}.jsonl") for subset in eval_subsets(args.data_dir)}
    train_rows = load_jsonl(args.data_dir / "train.jsonl")
    print(json.dumps({"model": args.model, "train": len(train_rows),
                      "eval": {k: len(v) for k, v in data.items()}}))

    import torch

    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    model, tokenizer = load_model(args.model, args.precision)

    import hashlib

    results: dict[str, Any] = {
        "model_path": args.model, "seed": args.seed,
        "config": {k: v for k, v in vars(args).items() if not k.startswith("_")},
        "data_sha256": {s: hashlib.sha256((args.data_dir / f"{s}.jsonl").read_bytes()).hexdigest()
                        for s in ["train"] + list(data)},
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }

    if not args.skip_zeroshot:
        results["zeroshot"] = evaluate_all(model, tokenizer, data, args, "zeroshot", args.out_dir)
    if not args.skip_train:
        try:
            model = train_lora(model, tokenizer, train_rows, args)
        except Exception as exc:
            failure = {
                "model_path": args.model,
                "seed": args.seed,
                "precision": args.precision,
                "failure_type": type(exc).__name__,
                "failure": str(exc),
                "failed_at_seconds": round(time.time() - args._t0, 1),
                "adapter_saved": False,
            }
            (args.out_dir / "training_failure.json").write_text(
                json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            raise
        if args.smoke_train_steps is not None:
            smoke = {
                "model_path": args.model,
                "seed": args.seed,
                "precision": args.precision,
                "optimizer_steps": args.smoke_train_steps,
                "requested_smoke_steps": args.smoke_train_steps,
                "config": {k: v for k, v in vars(args).items() if not k.startswith("_")},
            }
            (args.out_dir / "smoke.json").write_text(
                json.dumps(smoke, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
            )
            print(json.dumps({"smoke_complete": True, "saved": str(args.out_dir / "smoke.json")}))
            return
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
