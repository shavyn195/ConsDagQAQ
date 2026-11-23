"""dataset_v5 生成器：v4 流程 + 结构 OOD 世界（test_struct_ho）+ 子类型化 N 干扰句 + 无别名策略卡。

单组流程与 v4 相同（采样任务世界 -> 采样目标计划并定参 -> 规划器复核可行性与逐条必要性 -> 渲染 E/I/N），
差异只在规范层（dataset_v5_spec）与三处生成细节：
- test_struct_ho 使用 struct 世界（6 阶段、3 步 finish 块）与 train 模板池，只改变结构与工具名；
- 多于 2 步的 finish 块，目标计划随机取一个排列（2 步时与 v4 一样以 0.5 概率反转）；
- 每条记录带 spec_version 与 near_miss_subtypes（逐句槽，非 N 渲染的槽为 None），供评测分子类型报告。
确定性：全部随机性来自 seed，同一配置可复现。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from dataset_v5_spec import (  # noqa: E402
    BACKGROUND, CONSTRAINT_TYPES, DATASETS, DEFAULT_SEVERITY, E_TEMPLATES, GOAL_TEMPLATES,
    I_TEMPLATES, NEAR_MISS, PII_CLASSES, SPEC_VERSION, TEAMS, TOOLS, WORLDS, bare_name, fill_template,
    tool_name, with_article,
)
from trust_env import canonical_insert, check, default_plan, execute, plan  # noqa: E402

VARIANTS = ["explicit", "implicit", "none"]
WORLD_OF = {"test_tool_ho": "heldout", "test_struct_ho": "struct"}


# ---------------------------------------------------------------- 任务世界
def sample_attrs(rng: random.Random, role: str) -> dict[str, Any]:
    _, _, recipient, (clo, chi), (dlo, dhi), clears = TOOLS[role]
    return {
        "cost_cny": int(rng.randrange(clo, chi + 1) // 10 * 10) if chi > 0 else 0,
        "duration_min": int(rng.randrange(dlo, dhi + 1) // 5 * 5),
        "recipient": recipient,
        "clears_pii": clears,
    }


def sample_task(rng: random.Random, world: str) -> dict[str, Any]:
    spec = WORLDS[world]
    stages = []
    for name, alternatives, presence in spec["stages"]:
        if rng.random() < presence:
            stages.append({"stage": name, "alternatives": list(alternatives), "default": rng.choice(alternatives)})
    finish = rng.sample(spec["finish"], spec.get("finish_arity", 2))
    in_task = {r for s in stages for r in s["alternatives"]} | set(finish)
    optional = {
        role: targets for role, targets in spec["optional"].items()
        if targets == ["@acquire"] or any(t in in_task for t in targets)
    }
    distractors = rng.sample(spec["distractors"], rng.randint(2, min(4, len(spec["distractors"]))))
    roles = sorted(in_task | set(optional) | set(distractors))
    return {
        "world": world,
        "stages": stages,
        "finish": finish,
        "optional": optional,
        "tools": {r: sample_attrs(rng, r) for r in roles},
        "data_class": rng.choice(sorted(PII_CLASSES)) if rng.random() < 0.85 else None,
        "catalog": roles,
    }


def sample_target_plan(rng: random.Random, task: dict[str, Any]) -> list[str]:
    base = [rng.choice(s["alternatives"]) for s in task["stages"]]
    if len(task["finish"]) == 2:
        finish = list(task["finish"]) if rng.random() < 0.5 else list(reversed(task["finish"]))
    else:
        finish = rng.sample(task["finish"], len(task["finish"]))
    extras = [r for r in sorted(task["optional"]) if rng.random() < 0.35]
    return canonical_insert(task, base + finish, extras)


# ---------------------------------------------------------------- 定参（目标计划满足、默认计划违反）
def bind_params(
    rng: random.Random, ctype: str, task: dict[str, Any], default_trace: dict[str, Any],
    target: list[str], target_trace: dict[str, Any],
) -> dict[str, Any] | None:
    world = WORLDS[task["world"]]
    if ctype == "budget":
        limit = max(100, math.ceil(target_trace["cost"] / 50) * 50)
        return {"max_total_cost_cny": limit} if limit < default_trace["cost"] else None
    if ctype == "deadline":
        hours = math.ceil(target_trace["minutes"] / 60)
        return {"max_duration_hours": hours} if hours * 60 < default_trace["minutes"] else None
    if ctype == "privacy":
        if not task["data_class"] or not default_trace["leaks"] or target_trace["leaks"]:
            return None
        return {"protected_data_classes": [task["data_class"]], "forbidden_recipients": ["external"]}
    pairs = world["auth_pairs"] if ctype == "tool_auth" else world["order_pairs"]
    dpos, tpos = default_trace["positions"], target_trace["positions"]
    candidates = []
    for first, second in pairs:
        if first not in task["tools"] or second not in task["tools"]:
            continue
        default_violates = second in dpos and (first not in dpos or dpos[first] > dpos[second])
        target_ok = second not in tpos or (first in tpos and tpos[first] < tpos[second])
        if default_violates and target_ok:
            candidates.append((first, second))
    if not candidates:
        return None
    first, second = rng.choice(candidates)
    if ctype == "tool_auth":
        return {"approval_role": first, "required_role": second}
    return {"before_role": first, "after_role": second}


def scope_of(ctype: str, params: dict[str, Any], task: dict[str, Any]) -> list[str]:
    tools = task["tools"]
    if ctype == "budget":
        return sorted(f"role:{r}" for r in task["catalog"] if tools[r]["cost_cny"] > 0)
    if ctype == "deadline":
        return ["role:*"]
    if ctype == "privacy":
        return sorted(f"role:{r}" for r in task["catalog"] if tools[r]["recipient"] == "external")
    if ctype == "tool_auth":
        return [f"role:{params['required_role']}"]
    return sorted([f"role:{params['before_role']}", f"role:{params['after_role']}"])


# ---------------------------------------------------------------- 渲染
def render_mapping(
    rng: random.Random, ctype: str, params: dict[str, Any], team: str, dataset: str,
    data_class: str | None, field_pool: str,
) -> dict[str, Any]:
    mapping: dict[str, Any] = {"team": team, "dataset": dataset}
    if ctype == "budget":
        limit = params["max_total_cost_cny"]
        # d2/d3 的分量串不得含金标数值记号（防抄尾数捷径），同 v4
        gold = re.compile(rf"\b{re.escape(f'{limit:,}')}\b")
        b2 = rng.choice([b for b in range(100, 2001, 50)
                         if not gold.search(f"{limit + b:,} {b:,}")])
        a3 = rng.choice([a for a in range(50, limit, 50)
                         if not gold.search(f"{a:,} {limit - a:,}")] or [50])
        mapping.update({"limit": f"{limit:,}", "_d2": (f"{limit + b2:,}", f"{b2:,}"),
                        "_d3": (f"{a3:,}", f"{limit - a3:,}")})
    elif ctype == "deadline":
        hours = params["max_duration_hours"]
        now = rng.choice([h for h in range(6, max(7, 24 - hours)) if hours not in (h, h + hours)] or [6])
        used = rng.choice([u for u in range(1, 7) if u != hours])
        mapping.update({"hours": str(hours), "now": f"{now:02d}:00", "end": f"{now + hours:02d}:00",
                        "_d3": (str(hours + used), str(used))})
        if now + hours > 23:  # 跨日时刻无法无歧义相减，禁用 d2
            mapping["_no_d2"] = True
    elif ctype == "privacy":
        cls = params["protected_data_classes"][0] if params else (data_class or rng.choice(sorted(PII_CLASSES)))
        mapping.update({"pii": PII_CLASSES[cls]["name"], "field": rng.choice(PII_CLASSES[cls]["fields"][field_pool])})
    elif ctype == "tool_auth":
        approval, required = params["approval_role"], params["required_role"]
        mapping.update({"approval": tool_name(approval), "required": tool_name(required),
                        "required_bare": bare_name(required), "a_required": with_article(required)})
    else:
        mapping.update({"before": tool_name(params["before_role"]), "after": tool_name(params["after_role"])})
    return mapping


def render(
    rng: random.Random, ctype: str, variant: str, mapping: dict[str, Any], pool: str,
) -> tuple[str, str, dict[str, Any]]:
    """返回 (句子, 模板 id, 元数据)。variant=none 渲染近似干扰句，元数据带 near_miss 子类型。"""
    plain = {k: v for k, v in mapping.items() if not k.startswith("_")}
    if variant == "explicit":
        templates = E_TEMPLATES[ctype][pool]
        idx = rng.randrange(len(templates))
        return (fill_template(templates[idx], plain), f"{pool}:{ctype}:E:{idx}",
                {"hint_type": None, "difficulty": None})
    if variant == "none":
        templates = NEAR_MISS[ctype][pool]
        idx = rng.randrange(len(templates))
        subtype, text = templates[idx]
        return fill_template(text, plain), f"{pool}:{ctype}:N:{idx}", {"subtype": subtype}
    difficulty = rng.choices([1, 2, 3], weights=[0.3, 0.4, 0.3])[0]
    if difficulty == 2 and mapping.get("_no_d2"):
        difficulty = 3
    options = [(i, h, t) for i, (h, d, t) in enumerate(I_TEMPLATES[ctype][pool]) if d == difficulty]
    idx, hint, text = options[rng.randrange(len(options))]
    if f"_d{difficulty}" in mapping:
        plain["a"], plain["b"] = mapping[f"_d{difficulty}"]
    return fill_template(text, plain), f"{pool}:{ctype}:I:{idx}", {"hint_type": hint, "difficulty": difficulty}


def distractor_params(rng: random.Random, ctype: str, task: dict[str, Any]) -> dict[str, Any] | None:
    """干扰槽的伪参数：只用于渲染近似干扰句，不进金标。"""
    world = WORLDS[task["world"]]
    if ctype == "budget":
        return {"max_total_cost_cny": rng.randrange(300, 3001, 50)}
    if ctype == "deadline":
        return {"max_duration_hours": rng.randint(2, 12)}
    if ctype == "privacy":
        cls = task["data_class"] or rng.choice(sorted(PII_CLASSES))
        return {"protected_data_classes": [cls], "forbidden_recipients": ["external"]}
    pairs = [p for p in (world["auth_pairs"] if ctype == "tool_auth" else world["order_pairs"])
             if p[0] in task["tools"] and p[1] in task["tools"]]
    if not pairs:
        return None
    first, second = rng.choice(pairs)
    return ({"approval_role": first, "required_role": second} if ctype == "tool_auth"
            else {"before_role": first, "after_role": second})


# ---------------------------------------------------------------- 单组生成
def gen_group(rng: random.Random, group_id: str, subset: str, used_goals: set[str]) -> dict[str, Any] | None:
    world = WORLD_OF.get(subset, "train")
    pool = "test" if subset == "test_tpl_ho" else "train"
    for _attempt in range(80):
        task = sample_task(rng, world)
        base = default_plan(task)
        default_trace = execute(task, base)
        n_const = rng.choices([1, 2, 3], weights=[0.3, 0.4, 0.3])[0]
        types = rng.sample(CONSTRAINT_TYPES, n_const)
        bound: dict[str, dict[str, Any]] | None = None
        for _target_attempt in range(40):
            target = sample_target_plan(rng, task)
            target_trace = execute(task, target)
            if not target_trace["completed"]:
                continue
            params = {t: bind_params(rng, t, task, default_trace, target, target_trace) for t in types}
            if all(p is not None for p in params.values()):
                bound = params
                break
        if bound is None:
            continue
        constraints = [
            {"type": t, "severity": DEFAULT_SEVERITY[t], "scope": scope_of(t, bound[t], task), "params": bound[t]}
            for t in types
        ]
        witness, _ = plan(task, constraints)
        if witness is None or not check(task, witness, constraints)["safe_success"]:
            continue
        if not all(check(task, base, [c])["violations"] for c in constraints):
            continue
        necessary = True
        for i, c in enumerate(constraints):
            relaxed, _ = plan(task, constraints[:i] + constraints[i + 1:])
            if relaxed is None or not check(task, relaxed, [c])["violations"]:
                necessary = False
                break
        if not necessary:
            continue

        goal = None
        dataset, team = None, None
        for _g in range(80):
            dataset, team = rng.choice(DATASETS), rng.choice(TEAMS)
            cand = fill_template(rng.choice(GOAL_TEMPLATES[pool]), {"dataset": dataset, "team": team})
            if cand not in used_goals:
                goal = cand
                break
        if goal is None:
            return None

        field_pool = "test" if pool == "test" else "train"
        slots = [(c["type"], render_mapping(rng, c["type"], c["params"], team, dataset, task["data_class"], field_pool), True)
                 for c in constraints]
        if rng.random() < 0.4:
            spare = [t for t in CONSTRAINT_TYPES if t not in types]
            dtype = rng.choice(spare)
            dparams = distractor_params(rng, dtype, task)
            if dparams is not None:
                slots.append((dtype, render_mapping(rng, dtype, dparams, team, dataset, task["data_class"], field_pool), False))
        rng.shuffle(slots)
        background = (fill_template(rng.choice(BACKGROUND[pool]), {"team": team}) if rng.random() < 0.5 else None)
        distractor_text = {}
        for i, (dtype, mapping, is_constraint) in enumerate(slots):
            if not is_constraint:
                distractor_text[i] = render(rng, dtype, "none", mapping, pool)

        catalog = [
            {"role": r, "name": tool_name(r), "paid": task["tools"][r]["cost_cny"] > 0,
             "recipient": task["tools"][r]["recipient"]}
            for r in task["catalog"]
        ]
        by_type = {c["type"]: c for c in constraints}
        records = []
        for variant in VARIANTS:
            sentences, template_ids, hint_meta, gold_constraints, subtypes = [], [], [], [], []
            for i, (dtype, mapping, is_constraint) in enumerate(slots):
                if not is_constraint:
                    text, tid, meta = distractor_text[i]
                else:
                    text, tid, meta = render(rng, dtype, variant, mapping, pool)
                    if variant != "none":
                        hint_meta.append(meta)
                        gold_constraints.append({**by_type[dtype], "state": variant, "evidence_span": text})
                sentences.append(text)
                template_ids.append(tid)
                subtypes.append(meta.get("subtype"))
            parts = [goal] + ([background] if background else []) + sentences
            records.append({
                "sample_id": f"{group_id}-{variant[0].upper()}",
                "group_id": group_id,
                "split": "train" if subset == "train" else "dev" if subset == "dev" else "test",
                "subset": subset,
                "variant": variant,
                "world": world,
                "spec_version": SPEC_VERSION,
                "template_ids": template_ids,
                "near_miss_subtypes": subtypes,
                "hint_meta": hint_meta,
                "task_goal": goal,
                "query": " ".join(parts),
                "catalog": catalog,
                "task": task,
                "default_plan": base,
                "witness_plan": witness,
                "gold": {"query_state": variant, "constraints": gold_constraints},
            })
        return {"group_id": group_id, "subset": subset, "records": records}
    return None


# ---------------------------------------------------------------- 主流程
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "dataset_v5.yaml")
    args = parser.parse_args()
    import yaml

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    rng = random.Random(cfg["seed"])
    out_dir = ROOT / cfg["output_dir"]
    all_rows: list[dict[str, Any]] = []
    used_goals: set[str] = set()
    failures = 0
    for subset, n in cfg["groups"].items():
        made = idx = 0
        while made < n:
            group = gen_group(rng, f"{subset}-{idx:05d}", subset, used_goals)
            idx += 1
            if group is None:
                failures += 1
                if failures > 200:
                    raise SystemExit("生成失败次数过多，请检查任务世界配置")
                continue
            used_goals.add(group["records"][0]["task_goal"])
            all_rows.extend(group["records"])
            made += 1

    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for subset in cfg["groups"]:
        path = out_dir / f"{subset}.jsonl"
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in all_rows if r["subset"] == subset),
            encoding="utf-8", newline="\n",  # 固定 LF：哈希跨平台一致
        )
        files[subset] = path

    constrained = [r for r in all_rows if r["variant"] != "none"]
    report = {
        "dataset": "consdag_trusted_constraint_dataset_v5",
        "synthetic_only": True,
        "seed": cfg["seed"],
        "groups": dict(Counter(r["subset"] for r in all_rows if r["variant"] == "none")),
        "records": dict(Counter(r["subset"] for r in all_rows)),
        "constraint_type_distribution": {
            s: dict(Counter(c["type"] for r in all_rows if r["variant"] == "explicit" and r["subset"] == s
                            for c in r["gold"]["constraints"])) for s in cfg["groups"]},
        "constraints_per_group": dict(Counter(
            len(r["gold"]["constraints"]) for r in all_rows if r["variant"] == "explicit")),
        "implicit_difficulty_distribution": dict(Counter(
            f"d{m['difficulty']}" for r in all_rows if r["variant"] == "implicit" for m in r["hint_meta"])),
        "near_miss_subtype_distribution": dict(Counter(
            s for r in all_rows if r["variant"] == "none" for s in r["near_miss_subtypes"] if s)),
        "distractor_slot_rate": round(sum(
            len(r["template_ids"]) > len(r["gold"]["constraints"]) for r in constrained) / max(len(constrained), 1), 4),
        "generation_failures": failures,
        "sha256": {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()},
        "limitations": [
            "Synthetic, hand-templated corpus; not naturalistic user language.",
            "test_tool_ho is name-level held-out (same structure as train); test_struct_ho changes stage count, "
            "fan-out, finish-block arity and approval anchors, but keeps the five constraint types and train wording.",
            "No ambiguous/abstention-required examples; confidence is not a training target.",
            "Independent human recoverability audit of implicit cues and near-miss controls pending.",
        ],
    }
    (out_dir / "generation_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
