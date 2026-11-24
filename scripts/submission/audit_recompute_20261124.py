"""独立审计复算（2026-11-24，只读冻结资产，零 GPU）。

为论文草稿 v1 中「派生数字」提供可追溯来源，不改动任何既有脚本口径：
  1. E1 网格 12 格的 faithful_constrained（受约束 1400 行）组 bootstrap 95% 区间
     （results.json 中的 faithful_ci95_group 是对全 2100 行 faithful 算的，与表中报告列不一致）；
     以及 symbolic 列 DeepSeek vs 4B 的按组配对差。
  2. v5 train witness_plan 的安全性与最小改动性（E2 单体训练 target 的有效性）。
  3. seed 方差 JSON 的派生量：跨 seed 最大摆幅、三 seed 共杀的独立性基线期望、
     strict F1 与 faithful 的 seed 排序对照。
用法（仓库根目录）：python scripts/submission/audit_recompute_20261124.py
Windows 无 fcntl 时需在 PYTHONPATH 放一个空桩模块（仅 eval_repair_sft 的文件锁用到）。
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import sub_e1_grid as G  # noqa: E402
from trust_env import check, plan, plan_change_count  # noqa: E402

OUT = ROOT / "outputs/submission/audit_20261124/recompute.json"
BOOT = 10_000
SEED = 20261124


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def paired_group_diff(a: list[dict], b: list[dict]) -> dict:
    assert [x["sample_id"] for x in a] == [x["sample_id"] for x in b]
    groups: dict[str, list[int]] = {}
    for i, x in enumerate(a):
        groups.setdefault(x["group"], []).append(i)
    keys = list(groups)
    rng = random.Random(SEED)
    diffs = []
    for _ in range(BOOT):
        idx = [i for g in rng.choices(keys, k=len(keys)) for i in groups[g]]
        diffs.append(sum(a[i]["faithful"] - b[i]["faithful"] for i in idx) / len(idx))
    diffs.sort()
    point = sum(x["faithful"] for x in a) / len(a) - sum(x["faithful"] for x in b) / len(b)
    return {"diff": point, "ci95": [diffs[int(0.025 * BOOT)], diffs[int(0.975 * BOOT) - 1]], "n": len(a)}


def e1_constrained() -> dict:
    rows = G.panel_rows(G.ROOT)
    out: dict = {"cells": {}}
    symbolic: dict[str, list[dict]] = {}
    for planner in G.PLANNERS:
        cands = G.planner_candidates(G.ROOT, planner)
        for comp in G.COMPILERS:
            recs = G.replay_cell(G.ROOT, rows, G.compiler_constraints(G.ROOT, comp, rows), planner, cands)
            con = [r for r in recs if r["gold_count"]]
            out["cells"][f"{comp} | {planner}"] = {
                "n": len(con), "groups": len({r["group"] for r in con}),
                "faithful_constrained": sum(r["faithful"] for r in con) / len(con),
                "ci95_group_constrained": G.group_bootstrap_ci(con),
            }
            if planner == "symbolic":
                symbolic[comp] = con
    out["symbolic_deepseek_minus_4B"] = paired_group_diff(
        symbolic["prompted-compiler(skill-style)"], symbolic["4B-SFT"])
    out["note"] = "constrained rows only (E+I, 1400); group bootstrap 10000, seed 20261124"
    return out


def witness_minimality() -> dict:
    rows = load_jsonl(ROOT / "data/processed_v5/train.jsonl")
    n = safe = minimal = 0
    for r in rows:
        gold = r["gold"]["constraints"]
        if not gold:
            continue
        n += 1
        env = check(r["task"], r["witness_plan"], gold)
        _, info = plan(r["task"], gold)
        safe += bool(env["safe_success"])
        minimal += bool(env["safe_success"]) and plan_change_count(r["task"], r["witness_plan"]) == info["changes"]
    return {"constrained_train_rows": n, "witness_safe": safe, "witness_minimal_change": minimal}


def seed_derived() -> dict:
    d = json.loads((ROOT / "outputs/v5_analysis/seed_variance_decomposition_20261125.json").read_text(encoding="utf-8"))
    out: dict = {}
    for model, splits in d["models"].items():
        for split, e in splits.items():
            ps = e["per_seed"]
            seeds = sorted(ps)
            n = ps[seeds[0]]["n"]
            fails = [ps[s]["n_failed"] for s in seeds]
            faithful = [ps[s]["faithful_rate"] for s in seeds]
            expected3 = n
            for f in fails:
                expected3 *= f / n
            f1 = []
            for s in seeds:
                m = json.loads((ROOT / f"outputs/e1/{model}-v5-seed{s}/metrics.json").read_text(encoding="utf-8"))
                f1.append(m["trained"][split]["constraint_micro"]["f1"])
            out[f"{model} | {split}"] = {
                "seeds": seeds, "faithful": faithful, "strict_f1": f1,
                "faithful_swing_pp": round(100 * (max(faithful) - min(faithful)), 2),
                "failed": fails,
                "all_three_failed": e["record_failure_count_by_number_of_seeds"].get("3", 0),
                "all_three_expected_if_independent": round(expected3, 2),
                "seed_rank_by_faithful": sorted(seeds, key=lambda s: -faithful[seeds.index(s)]),
                "seed_rank_by_strict_f1": sorted(seeds, key=lambda s: -f1[seeds.index(s)]),
            }
    return out


def main() -> None:
    report = {
        "purpose": "independent audit recompute for paper_draft_v1 (read-only on frozen assets)",
        "e1_constrained": e1_constrained(),
        "v5_train_witness": witness_minimality(),
        "seed_variance_derived": seed_derived(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
