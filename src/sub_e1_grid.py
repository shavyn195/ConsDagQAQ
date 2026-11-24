"""E1 插拔网格：编译器轴 × 规划器轴，纯 CPU 回放。

网格：编译器 {0.6B-SFT, 1.7B-SFT, 4B-SFT, prompted-compiler(skill-style, DeepSeek 10-shot)}
      × 规划器 {SFT-order42, SFT-order44, symbolic}

所有输入均为冻结缓存：编译器预测（v4 面板）、规划器四候选池、金标评测器。
不训练、不推理、不修改任何 v4/v5 冻结资产；产物落 outputs/submission/e1_grid/。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from probe_e2_format import parse
from probe_one_edit_repair import choose
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import aligned, digest, load_jsonl
from run_e1 import strict_parse
from trust_env import check, default_plan, normalize_constraint, plan as symbolic_plan, plan_change_count  # noqa: E402

SPLITS = ("test_tpl_ho", "test_tool_ho")
VARIANTS = ("explicit", "implicit", "none")

# 编译器轴：名称 -> (预测目录, 阵营标签)
COMPILERS: dict[str, dict[str, str]] = {
    "0.6B-SFT": {"dir": "outputs/e1/Qwen3-0.6B-v4/trained_predictions", "kind": "trained"},
    "1.7B-SFT": {"dir": "outputs/e1/Qwen3-1.7B-v4/trained_predictions", "kind": "trained"},
    "4B-SFT": {"dir": "outputs/e1/Qwen3-4B-v4/trained_predictions", "kind": "trained"},
    "prompted-compiler(skill-style)": {"dir": "outputs/e1_v4_side/deepseek-v4-pro-0813-few", "kind": "prompted"},
}

# 规划器轴：名称 -> 候选池目录（symbolic 无候选池）
PLANNERS: dict[str, str | None] = {
    "SFT-order42": "outputs/e2_v4/verified-one-edit-full-holdouts-v1",
    "SFT-order44": "outputs/e2_v4/verified-one-edit-full-order44-v1",
    "symbolic": None,
}

BOOT = 10_000


def panel_rows(root: Path) -> list[dict]:
    """冻结面板：v4 tpl_ho + tool_ho 全量 2100 条（含 N 对照）。"""
    rows: list[dict] = []
    for split in SPLITS:
        rows.extend(load_jsonl(root / "data/processed_v4" / f"{split}.jsonl"))
    return rows


def compiler_constraints(root: Path, compiler: str, rows: list[dict]) -> dict[str, list[dict]]:
    """读取冻结编译器预测，返回 sample_id -> 归一化约束列表（无金标可见性）。"""
    cfg = COMPILERS[compiler]
    out: dict[str, list[dict]] = {}
    for split in SPLITS:
        path = root / cfg["dir"] / f"{split}.jsonl"
        preds = load_jsonl(path)
        split_rows = [r for r in rows if r["subset"] == split]
        raw = aligned(split_rows, preds)
        for row, text in zip(split_rows, raw):
            parsed = strict_parse(text)
            got = parsed["constraints"] if parsed else []
            out[row["sample_id"]] = [c for c in got if normalize_constraint(c, row["task"]) is not None]
    return out


def planner_candidates(root: Path, planner: str) -> dict[str, list[str]] | None:
    """规划器四候选池（原始字符串，回放时按任务工具表解析，与 2×2 口径一致）。"""
    folder = PLANNERS[planner]
    if folder is None:
        return None
    path = root / folder / "raw.jsonl"
    return {x["id"]: x["raw"] for x in load_jsonl(path)}


def replay_cell(root: Path, rows: list[dict], constraints: dict[str, list[dict]],
                planner: str, candidates: dict[str, list[str]] | None) -> list[dict]:
    """单个网格单元：编译输出 -> 规划/修复 -> 金标评测（金标仅用于评测，修复过程不可见）。"""
    out: list[dict] = []
    for row in rows:
        task = row["task"]
        gold = row["gold"]["constraints"]
        pred = constraints[row["sample_id"]]
        gold_plan, gold_info = symbolic_plan(task, gold)
        if planner == "symbolic":
            fixed, info = symbolic_plan(task, pred)
            changes = info["changes"]
        else:
            tools = sorted(task["tools"])
            actions = [parse(v, tools, "names") for v in candidates[row["sample_id"]]]
            _, fixed, _, _, _ = choose(task, actions, pred, row["sample_id"])
            changes = None
            if fixed is not None:
                try:
                    changes = plan_change_count(task, fixed)
                except ValueError:
                    changes = None
        env = check(task, fixed, gold)
        deviates = fixed is not None and fixed != default_plan(task)
        extra = (changes - gold_info["changes"]) if (env["safe_success"] and changes is not None) else None
        faithful = bool(env["safe_success"]) and ((extra == 0) if gold else not deviates)
        out.append({
            "sample_id": row["sample_id"], "split": row["subset"], "variant": row["variant"],
            "group": row["group_id"], "gold_count": len(gold),
            "planned": fixed is not None, "completed": bool(env["completed"]),
            "safe_success": bool(env["safe_success"]), "faithful": faithful,
            "extra_changes": extra, "compiler_constraints": len(pred),
        })
    return out


def group_bootstrap_ci(records: list[dict], key: str = "faithful", n_boot: int = BOOT,
                       seed: int = 20261124) -> list[float] | None:
    """按任务组重采样（CGAP 惯例）：区间只覆盖组间抽样，不覆盖训练种子随机性。"""
    groups: dict[str, list[dict]] = {}
    for r in records:
        groups.setdefault(r["group"], []).append(r)
    if len(groups) < 2:
        return None
    keys = list(groups)
    rng = random.Random(seed)
    vals = []
    for _ in range(n_boot):
        picked = rng.choices(keys, k=len(keys))
        items = [r for g in picked for r in groups[g]]
        vals.append(sum(r[key] for r in items) / len(items))
    vals.sort()
    return [vals[int(0.025 * n_boot)], vals[int(0.975 * n_boot) - 1]]


def summarise(records: list[dict]) -> dict:
    n = len(records)
    if not n:
        return {"n": 0}
    out: dict = {"n": n, "planned": sum(r["planned"] for r in records) / n,
                 "safe_success": sum(r["safe_success"] for r in records) / n,
                 "faithful": sum(r["faithful"] for r in records) / n}
    ci = group_bootstrap_ci(records)
    if ci:
        out["faithful_ci95_group"] = ci
    by_variant = {}
    for v in VARIANTS:
        items = [r for r in records if r["variant"] == v]
        if items:
            by_variant[v] = {"n": len(items),
                             "faithful": sum(r["faithful"] for r in items) / len(items)}
    out["by_variant"] = by_variant
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "outputs/submission/e1_grid")
    ap.add_argument("--compilers", nargs="*", default=list(COMPILERS))
    ap.add_argument("--planners", nargs="*", default=list(PLANNERS))
    args = ap.parse_args()

    rows = panel_rows(ROOT)
    groups = {r["sample_id"]: r for r in rows}
    assert len(groups) == len(rows)

    results: dict = {"design": {
        "panel": "v4 tpl_ho+tool_ho (frozen)", "records": len(rows),
        "compiler_axis": args.compilers, "planner_axis": args.planners,
        "boot": BOOT, "boot_seed": 20261124,
        "note": "CPU replay of frozen caches; gold visible only to the evaluator, never to repair.",
    }, "cells": {}}

    for planner in args.planners:
        candidates = planner_candidates(ROOT, planner)
        for compiler in args.compilers:
            constraints = compiler_constraints(ROOT, compiler, rows)
            records = replay_cell(ROOT, rows, constraints, planner, candidates)
            cell: dict = {}
            for split in SPLITS:
                items = [r for r in records if r["split"] == split]
                cell[split] = summarise(items)
                constrained = [r for r in items if r["gold_count"]]
                cell[split]["faithful_constrained"] = (
                    sum(r["faithful"] for r in constrained) / len(constrained) if constrained else None)
            cell["overall"] = summarise(records)
            constrained = [r for r in records if r["gold_count"]]
            cell["overall"]["faithful_constrained"] = (
                sum(r["faithful"] for r in constrained) / len(constrained) if constrained else None)
            results["cells"][f"{compiler} | {planner}"] = cell
            print(json.dumps({"cell": f"{compiler} | {planner}",
                              "faithful_constrained": cell["overall"]["faithful_constrained"]}), flush=True)

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {args.out/'results.json'}")


if __name__ == "__main__":
    main()
