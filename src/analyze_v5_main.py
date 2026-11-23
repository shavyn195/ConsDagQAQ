"""v5 主表与预注册判定（design_v5_ccfb.md §6.3–§6.4）。只读预测文件，CPU 运行。

臂：训练臂 Qwen3-{0.6B,1.7B,4B} × seed {42,43,44}；零样本（seed 42）；PE 臂（outputs/e1_v5_side/<model>-<style>）。
主指标：受约束记录的 faithful_success（安全且改动数等于金标最小计划）。辅助：N 误报（按子类型）、
含证据整条全对、safe_success、保守规划器参考档。
统计：训练臂报逐种子值、均值与样本标准差；两臂差值用条件任务组 bootstrap —— 按任务组重采样（同组 E/I 一起），
每次重采样内先对训练臂的各种子取平均，再相减；10,000 次，固定种子 20261124。
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

from dataset_v5_spec import NEAR_MISS
from eval_exec import conservative_outcome
from rescore_v4_side import ROOT, aligned, outcome
from run_e1 import eval_subsets, load_jsonl, strict_parse

SIZES = ("0.6B", "1.7B", "4B")
SEEDS = (42, 43, 44)
PE_ARMS = ("deepseek-v4-pro-0813-few", "qwen-max-zero", "qwen-max-few")
NONINFERIORITY_MARGIN = 0.03
STRUCT_TRANSFER_MAX_DROP = 0.05
STRUCT_FAIL_MIN_DROP = 0.10
N_GATE_MAX_ALARM = 0.05
BOOT = 10_000


def alarm(raw: str) -> bool:
    parsed = strict_parse(raw)
    return parsed is None or bool(parsed["constraints"]) or parsed["query_state"] != "none"


def arm_dirs(root: Path, *, pe_root: Path | None = None) -> dict[str, list[Path]]:
    arms: dict[str, list[Path]] = {}
    for size in SIZES:
        runs = [root / f"outputs/e1/Qwen3-{size}-v5-seed{s}/trained_predictions" for s in SEEDS]
        runs = [r for r in runs if (r.parent / "metrics.json").is_file()
                and all((r / f"{s}.jsonl").is_file() for s in eval_subsets(root / "data/processed_v5"))]
        if runs:
            arms[f"Qwen3-{size}-LoRA"] = runs
        zs = root / f"outputs/e1/Qwen3-{size}-v5-seed42/zeroshot_predictions"
        if zs.is_dir():
            arms[f"Qwen3-{size}-zero"] = [zs]
    for name in PE_ARMS:
        d = (pe_root if pe_root is not None else root / "outputs/e1_v5_side") / name
        if (d / "full-scores.json").exists():
            arms[name] = [d]
    return arms


def per_record(rows: list[dict], folder: Path) -> dict[str, dict]:
    raw = aligned(rows, load_jsonl(folder / f"{rows[0]['subset']}.jsonl"))
    out = {}
    for r, t in zip(rows, raw):
        o = outcome(r, t)
        o["alarm"] = alarm(t) if r["variant"] == "none" else None
        out[r["sample_id"]] = o
    return out


def hier_diff(groups: list[str], a_runs: list[dict], b_runs: list[dict], key: str, ids_by_group: dict) -> dict:
    """重采样任务组，固定已观测种子；该区间不覆盖训练种子的总体随机性。"""
    def tally(runs):  # 每次运行、每个组的 (命中数, 记录数)，避免在重采样循环里逐条累加
        return [{g: (sum(run[i][key] for i in ids_by_group[g]), len(ids_by_group[g])) for g in groups} for run in runs]

    a_tally, b_tally = tally(a_runs), tally(b_runs)

    def value(tallies, sampled):
        vals = []
        for t in tallies:
            hits = sum(t[g][0] for g in sampled)
            vals.append(hits / sum(t[g][1] for g in sampled))
        return sum(vals) / len(vals)

    a_runs, b_runs = a_tally, b_tally
    rng = random.Random(20261124)
    point = value(a_runs, groups) - value(b_runs, groups)
    stats = sorted(value(a_runs, s) - value(b_runs, s)
                   for s in ([groups[rng.randrange(len(groups))] for _ in groups] for _ in range(BOOT)))
    return {"diff": round(point, 4), "ci95": [round(stats[int(0.025 * BOOT)], 4), round(stats[int(0.975 * BOOT) - 1], 4)],
            "uncertainty": "paired task-group bootstrap conditional on observed training seeds"}


def noninferiority_decision(difference: dict | None, observed_seeds: list[int]) -> dict | None:
    """Keep provisional diagnostics, but never confirm the three-seed H2 early."""
    if difference is None:
        return None
    complete = sorted(observed_seeds) == list(SEEDS)
    meets = difference["ci95"][0] > -NONINFERIORITY_MARGIN
    return {**difference, "observed_seeds": sorted(observed_seeds), "required_seeds": list(SEEDS),
            "conditional_interval_meets_margin": meets,
            "noninferior": meets if complete else None,
            "status": "complete_conditional_on_registered_seeds" if complete else "pending_required_seeds"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, default=ROOT / "data/processed_v5")
    p.add_argument("--runs-root", type=Path, default=ROOT,
                   help="Read frozen runs in another checkout without modifying that checkout.")
    p.add_argument("--pe-root", type=Path, default=None,
                   help="Optional directory of cached, already scored PE arms.")
    p.add_argument("--out", type=Path, default=ROOT / "outputs/v5_analysis/main.json")
    args = p.parse_args()
    arms = arm_dirs(args.runs_root, pe_root=args.pe_root)
    report: dict = {"arms": {k: [str(v) for v in vs] for k, vs in arms.items()}, "table": {}, "decisions": {},
                   "analysis_version": "v5-audit-20261123",
                   "notes": ["Task-group intervals are conditional on observed seeds, not seed-population intervals.",
                             "H3 compares confounded world slices; its preregistered label is not causal proof of structural transfer.",
                             "H4 is model agreement with synthetic labels, not independent human validity."]}
    records: dict = defaultdict(dict)
    groups_by_subset, ids_by_subset = {}, {}
    for subset in eval_subsets(args.data):
        rows = load_jsonl(args.data / f"{subset}.jsonl")
        constrained = [r for r in rows if r["gold"]["constraints"]]
        ids = defaultdict(list)
        for r in constrained:
            ids[r["group_id"]].append(r["sample_id"])
        groups_by_subset[subset], ids_by_subset[subset] = sorted(ids), ids
        cons = [conservative_outcome(r) for r in constrained]
        report["table"].setdefault("conservative_reference", {})[subset] = {
            "faithful": sum(o["faithful_success"] for o in cons) / len(cons),
            "safe": sum(o["safe_success"] for o in cons) / len(cons)}
        none_rows = [r for r in rows if r["variant"] == "none"]
        for arm, runs in arms.items():
            recs = [per_record(rows, run) for run in runs]
            records[arm][subset] = recs
            faithful = [sum(rec[r["sample_id"]]["faithful_success"] for r in constrained) / len(constrained)
                        for rec in recs]
            evidence = [sum(rec[r["sample_id"]]["exact_with_evidence"] for r in constrained) / len(constrained)
                        for rec in recs]
            alarms = defaultdict(lambda: [0, 0])
            for rec in recs:
                for r in none_rows:
                    for tid, st in zip(r["template_ids"], r.get("near_miss_subtypes", [])):
                        if st:
                            alarms[st][0] += int(rec[r["sample_id"]]["alarm"])
                            alarms[st][1] += 1
            report["table"].setdefault(arm, {})[subset] = {
                "faithful_constrained_per_seed": [round(v, 4) for v in faithful],
                "faithful_mean": round(statistics.mean(faithful), 4),
                "faithful_sd": round(statistics.stdev(faithful), 4) if len(faithful) > 1 else None,
                "exact_with_evidence_mean": round(statistics.mean(evidence), 4),
                "none_false_alarm": round(sum(rec[r["sample_id"]]["alarm"] for rec in recs for r in none_rows)
                                          / (len(none_rows) * len(recs)), 4),
                "none_false_alarm_by_subtype": {k: round(a / n, 4) for k, (a, n) in sorted(alarms.items())},
            }

    def diff(a: str, b: str, subset: str) -> dict | None:
        if a not in records or b not in records or subset not in records[a]:
            return None
        return hier_diff(groups_by_subset[subset], records[a][subset], records[b][subset],
                         "faithful_success", ids_by_subset[subset])

    subsets = list(groups_by_subset)
    dec = report["decisions"]
    for size in SIZES:
        lora, zero = f"Qwen3-{size}-LoRA", f"Qwen3-{size}-zero"
        dec[f"H1_training_gain_{size}"] = {s: diff(lora, zero, s) for s in subsets}
        observed_seeds = [int(run.parent.name.rsplit("seed", 1)[1]) for run in arms.get(lora, [])]
        dec[f"H1_training_gain_{size}_status"] = {
            "observed_seeds": observed_seeds,
            "status": "complete" if sorted(observed_seeds) == list(SEEDS) else "pending_required_seeds"}
        dec[f"H2_noninferiority_vs_deepseek_{size}"] = {
            s: noninferiority_decision(diff(lora, "deepseek-v4-pro-0813-few", s), observed_seeds)
            for s in subsets}
    # H3 结构迁移：同一臂 tool_ho 与 struct 的 faithful 均值之差（两个独立测试集，按组各自重采样）
    for arm in records:
        if "test_struct_ho" not in records[arm]:
            continue
        a = report["table"][arm]["test_tool_ho"]["faithful_mean"]
        b = report["table"][arm]["test_struct_ho"]["faithful_mean"]
        rng = random.Random(20261124)
        boots = []
        for _ in range(2000):
            vals = []
            for subset in ("test_tool_ho", "test_struct_ho"):
                g = groups_by_subset[subset]
                sampled = [g[rng.randrange(len(g))] for _ in g]
                recs = records[arm][subset]
                vals.append(statistics.mean(
                    sum(rec[i]["faithful_success"] for gg in sampled for i in ids_by_subset[subset][gg])
                    / sum(len(ids_by_subset[subset][gg]) for gg in sampled) for rec in recs))
            boots.append(vals[0] - vals[1])
        boots.sort()
        lo, hi = boots[int(0.025 * len(boots))], boots[int(0.975 * len(boots)) - 1]
        verdict = ("transfers" if hi <= STRUCT_TRANSFER_MAX_DROP else
                   "does_not_transfer" if lo >= STRUCT_FAIL_MIN_DROP else "inconclusive")
        dec.setdefault("H3_struct_drop", {})[arm] = {"drop": round(a - b, 4), "ci95": [round(lo, 4), round(hi, 4)],
                                                     "verdict": verdict}
    # H4 N 控制有效性：强模型在每个子类型上的误报率须 <= 5%，否则该子类型标为歧义并单列
    ds = report["table"].get("deepseek-v4-pro-0813-few", {})
    dec["H4_near_miss_validity"] = {
        s: {st: {"alarm": v, "valid": v <= N_GATE_MAX_ALARM}
            for st, v in ds.get(s, {}).get("none_false_alarm_by_subtype", {}).items()} for s in subsets}
    report["subtypes"] = sorted({st for pools in NEAR_MISS.values() for items in pools.values() for st, _ in items})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report["decisions"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
