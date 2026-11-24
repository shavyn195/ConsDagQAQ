"""Seed 方差机制分解（R3 必做项）：把跨 seed 的执行级波动归因到字段级错误。

回答的问题：三 seed 之间 faithful 的大幅波动（如 1.7B tool_ho 91.71/75.71/71.86）是
「系统性字段缺陷」（同样的样本被同样的字段错误击穿，低 seed 重叠度）还是
「训练噪声放大」（每个 seed 各错各的字段，高 seed 重叠度才系统性）？

字段级比对口径（对受约束行 E/I，金标仅在评测阶段可见）：
  对每个预测约束与金标约束做贪心最优匹配（同 type 优先），未匹配部分记为
  missed（金标未被覆盖）或 extra（无端多报）；已匹配对按字段比对：
  params / scope / state / severity / evidence_span 五类字段错误。
行为口径：编译器预测 -> normalize_constraint -> 符号规划器 plan() -> check()，
faithful = safe_success 且改动数 == 金标最小改动数（与 v5 主表 e1_exec_v2 口径一致）。

输出：outputs/v5_analysis/seed_variance_decomposition_20261125.json + stdout 摘要。
用法：python scripts/submission/seed_variance_decomposition.py [--models Qwen3-1.7B Qwen3-4B]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from trust_env import check, default_plan, normalize_constraint, plan  # noqa: E402

SPLITS = ["dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho"]
VARIANTS = ("explicit", "implicit")


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def field_errors(gold_list: list[dict], pred_list: list[dict]) -> dict:
    """贪心匹配同 type 约束后逐字段比对，返回字段错误计数与该对的错误字段集合。"""
    errors = Counter()
    used = set()
    matched_pairs = []
    for g in gold_list:
        best = None
        for j, p in enumerate(pred_list):
            if j in used or p.get("type") != g.get("type"):
                continue
            if best is None:
                best = j
        if best is None:
            errors["missed"] += 1
        else:
            used.add(best)
            matched_pairs.append((g, pred_list[best]))
    for j, p in enumerate(pred_list):
        if j not in used:
            errors["extra"] += 1
    for g, p in matched_pairs:
        if _canon(g.get("params")) != _canon(p.get("params")):
            errors["params"] += 1
        gs, ps = g.get("scope"), p.get("scope")
        if isinstance(gs, list) and isinstance(ps, list):
            same = sorted(gs) == sorted(ps)
        else:
            same = gs == ps
        if not same:
            errors["scope"] += 1
        if g.get("state") != p.get("state"):
            errors["state"] += 1
        if g.get("severity") != p.get("severity"):
            errors["severity"] += 1
        if (g.get("evidence_span") or "").strip() != (p.get("evidence_span") or "").strip():
            errors["evidence_span"] += 1
    return dict(errors)


def behavioural_faithful(row: dict, pred_constraints: list[dict]) -> dict:
    """主管线 faithful：符号规划器。返回 safe/faithful 与规划器诊断。"""
    task = row["task"]
    gold = row["gold"]["constraints"]
    # 规划器只看 type+params；与 v5 主表口径一致
    planned, info = plan(task, pred_constraints)
    res = check(task, planned, gold)
    min_changes = None
    gold_plan, gold_info = plan(task, gold)
    if gold_plan is not None:
        min_changes = gold_info.get("changes")
    safe = res["safe_success"]
    faithful = safe and planned is not None and gold_plan is not None and info.get("changes") == min_changes
    return {
        "safe": bool(safe),
        "faithful": bool(faithful),
        "planned": planned is not None,
        "usable": info.get("usable_constraints"),
        "unusable": info.get("unusable_constraints"),
        "changes": info.get("changes"),
        "gold_changes": min_changes,
    }


def analyse_split(rows: list[dict], preds: dict[str, dict]) -> dict:
    per_record = {}
    for row in rows:
        sid = row["sample_id"]
        if row["variant"] not in VARIANTS:
            continue
        pred = preds.get(sid)
        if pred is None:
            continue
        gold_list = row["gold"]["constraints"]
        pred_list = [c for c in (pred.get("constraints") or []) if isinstance(c, dict)]
        beh = behavioural_faithful(row, pred_list)
        rec_ok = beh["faithful"]
        field_err = field_errors(gold_list, pred_list)
        per_record[sid] = {
            "group": row["group_id"],
            "variant": row["variant"],
            "faithful": rec_ok,
            "safe": beh["safe"],
            "n_gold": len(gold_list),
            "n_pred": len(pred_list),
            "field_errors": field_err,
        }
    return per_record


def summarise(per_record: dict, seed: str) -> dict:
    n = len(per_record)
    failed = [r for r in per_record.values() if not r["faithful"]]
    field_totals = Counter()
    field_in_failures = Counter()
    for r in per_record.values():
        for k, v in r["field_errors"].items():
            field_totals[k] += v
    for r in failed:
        for k, v in r["field_errors"].items():
            field_in_failures[k] += v
    by_type_fail = Counter()
    for r in failed:
        for k, v in r["field_errors"].items():
            by_type_fail[(k,)] += v
    return {
        "seed": seed,
        "n": n,
        "n_failed": len(failed),
        "faithful_rate": (n - len(failed)) / n if n else None,
        "safe_rate": sum(1 for r in per_record.values() if r["safe"]) / n if n else None,
        "field_error_totals_all_records": dict(field_totals),
        "field_error_totals_in_failed_records": dict(field_in_failures),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["Qwen3-1.7B", "Qwen3-4B"])
    ap.add_argument("--seeds", nargs="+", default=["42", "43", "44"])
    ap.add_argument("--data-dir", default="data/processed_v5")
    ap.add_argument("--out", default="outputs/v5_analysis/seed_variance_decomposition_20261125.json")
    args = ap.parse_args()

    data = {s: {r["sample_id"]: r for r in load_jsonl(Path(args.data_dir) / f"{s}.jsonl")} for s in SPLITS}

    report: dict = {"purpose": "cross-seed variance decomposition: field-level attribution of behavioural swings",
                    "data_dir": args.data_dir,
                    "models": {}}
    for model in args.models:
        report["models"][model] = {}
        for split in SPLITS:
            rows = load_jsonl(Path(args.data_dir) / f"{split}.jsonl")
            per_seed: dict[str, dict] = {}
            for seed in args.seeds:
                pdir = ROOT / "outputs/e1" / f"{model}-v5-seed{seed}" / "trained_predictions"
                if not pdir.exists():
                    alt = ROOT / "outputs/e1" / f"{model}-v5-seed{seed}_trained_predictions"
                    if alt.exists():
                        pdir = alt
                pfile = pdir / f"{split}.jsonl"
                if not pfile.exists():
                    continue
                preds = {}
                for rec in load_jsonl(pfile):
                    p = rec.get("prediction")
                    preds[rec["sample_id"]] = p if isinstance(p, dict) else {}
                per_seed[seed] = analyse_split(rows, preds)
            if not per_seed:
                continue
            entry: dict = {"per_seed": {s: summarise(pr, s) for s, pr in per_seed.items()}}
            # 跨 seed 失败重叠（record 级）与字段级共现
            fail_sets = {s: {sid for sid, r in pr.items() if not r["faithful"]} for s, pr in per_seed.items()}
            seeds = sorted(fail_sets)
            overlap = {}
            for i, a in enumerate(seeds):
                for b in seeds[i + 1:]:
                    inter = fail_sets[a] & fail_sets[b]
                    union = fail_sets[a] | fail_sets[b]
                    overlap[f"{a}_vs_{b}"] = {
                        "intersection": len(inter), "union": len(union),
                        "jaccard": len(inter) / len(union) if union else None,
                        "universe": len(per_seed[a]),
                    }
            entry["record_failure_overlap"] = overlap
            entry["record_failure_count_by_number_of_seeds"] = dict(
                Counter(sum(sid in fs for fs in fail_sets.values()) for sid in per_seed[seeds[0]])
            )
            # 字段级：每种字段错误在失败记录中的 seed 间稳定性
            # 若某字段错误在不同 seed 命中同一批样本 => 系统性；若各 seed 各错各的 => 噪声放大
            field_stability: dict[str, dict] = {}
            field_keys = ["missed", "extra", "params", "scope", "state", "severity", "evidence_span"]
            for fk in field_keys:
                hits = {s: {sid for sid, r in pr.items() if r["field_errors"].get(fk)} for s, pr in per_seed.items()}
                tot = sum(len(h) for h in hits.values())
                inter_all = set.intersection(*hits.values()) if len(hits) > 1 else set()
                union_all = set.union(*hits.values()) if hits else set()
                field_stability[fk] = {
                    "records_with_error_per_seed": {s: len(h) for s, h in hits.items()},
                    "all_seed_intersection": len(inter_all),
                    "union": len(union_all),
                    "intersection_over_union": len(inter_all) / len(union_all) if union_all else None,
                    "mean_per_seed": tot / len(hits) if hits else None,
                }
            entry["field_stability"] = field_stability
            report["models"][model][split] = entry

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"written {out}")

    # stdout 摘要
    for model, splits in report["models"].items():
        print(f"\n===== {model} =====")
        for split, e in splits.items():
            print(f"--- {split} (n={e['per_seed'][list(e['per_seed'])[0]]['n']}) ---")
            for s, sm in e["per_seed"].items():
                print(f"  seed{s}: faithful={sm['faithful_rate']:.4f} failed={sm['n_failed']} "
                      f"fields(all)={sm['field_error_totals_all_records']}")
            print("  failure overlap:", {k: v['jaccard'] for k, v in e["record_failure_overlap"].items()})
            print("  by #seeds failing:", e["record_failure_count_by_number_of_seeds"])
            for fk, fs in e["field_stability"].items():
                if fs["mean_per_seed"]:
                    print(f"  field {fk:14s} per_seed={fs['records_with_error_per_seed']} "
                          f"all3inter={fs['all_seed_intersection']} iou={fs['intersection_over_union']:.3f}")


if __name__ == "__main__":
    main()
