"""冻结 v4 上的只重算分析（不训练、不改数据）：N 近似干扰句误报与保守规划器参考档。

输出 outputs/v4_reanalysis/nearmiss.json：
- 每条 N 模板在各系统上的误报率（误报 = 严格解析失败、输出任一约束、或 query_state != none）；
- G1 词法门槛（dataset_v5_spec.near_miss_gate）判定的模板；N 记录在"全部"与"剔除含 G1 失败模板的组"
  两种口径下的误报率与 faithful。后者是事后敏感性分析：门槛在看到结果后制定，不能替代冻结主表；
- 保守规划器（不看约束）在受约束记录上的 safe / faithful。
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from dataset_v4_spec import NEAR_MISS
from dataset_v5_spec import near_miss_gate
from eval_exec import conservative_outcome
from rescore_v4_side import ROOT, aligned, digest, outcome
from run_e1 import SUBSETS, load_jsonl, strict_parse

SYSTEMS = {
    "Qwen3-0.6B-LoRA": "outputs/e1/Qwen3-0.6B-v4/trained_predictions",
    "Qwen3-1.7B-LoRA": "outputs/e1/Qwen3-1.7B-v4/trained_predictions",
    "Qwen3-4B-LoRA": "outputs/e1/Qwen3-4B-v4/trained_predictions",
    "DeepSeek-10shot": "outputs/e1_v4_side/deepseek-v4-pro-0813-few",
}


def alarm(raw: str) -> bool:
    parsed = strict_parse(raw)
    return parsed is None or bool(parsed["constraints"]) or parsed["query_state"] != "none"


def template_text(tid: str) -> str:
    pool, ctype, _, idx = tid.split(":")
    return NEAR_MISS[ctype][pool][int(idx)]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "outputs/v4_reanalysis/nearmiss.json")
    args = p.parse_args()
    data = ROOT / "data/processed_v4"
    report: dict = {"data_sha256": {s: digest(data / f"{s}.jsonl") for s in SUBSETS}, "systems": {}}
    per_template: dict = defaultdict(lambda: {"records": 0})
    g1_fail = sorted(f"{pool}:{ctype}:N:{i}" for ctype, pools in NEAR_MISS.items() for pool, items in pools.items()
                     for i, text in enumerate(items) if not near_miss_gate(text)["G1"])
    report["g1_failing_templates"] = {t: template_text(t) for t in g1_fail}
    conservative = {}
    for subset in SUBSETS:
        rows = load_jsonl(data / f"{subset}.jsonl")
        constrained = [r for r in rows if r["gold"]["constraints"]]
        cons = [conservative_outcome(r) for r in constrained]
        conservative[subset] = {"records": len(cons),
                                "safe_success": round(sum(o["safe_success"] for o in cons) / len(cons), 4),
                                "faithful_success": round(sum(o["faithful_success"] for o in cons) / len(cons), 4)}
        none_rows = [r for r in rows if r["variant"] == "none"]
        for name, folder in SYSTEMS.items():
            raw = aligned(rows, load_jsonl(ROOT / folder / f"{subset}.jsonl"))
            raw_by = {r["sample_id"]: t for r, t in zip(rows, raw)}
            entry = report["systems"].setdefault(name, {}).setdefault(subset, {})
            for label, keep in (("all", lambda r: True),
                                ("excluding_g1_failures", lambda r: not set(r["template_ids"]) & set(g1_fail))):
                kept = [r for r in none_rows if keep(r)]
                obs = [outcome(r, raw_by[r["sample_id"]]) for r in kept]
                entry[label] = {
                    "none_records": len(kept),
                    "false_alarm": sum(alarm(raw_by[r["sample_id"]]) for r in kept),
                    "faithful": sum(o["faithful_success"] for o in obs),
                }
            for r in none_rows:
                hit = alarm(raw_by[r["sample_id"]])
                for tid in r["template_ids"]:
                    if ":N:" not in tid:
                        continue
                    slot = per_template[tid]
                    if name == next(iter(SYSTEMS)):
                        slot["records"] += 1
                    slot[name] = slot.get(name, 0) + int(hit)
    report["per_template"] = {
        tid: {"text": template_text(tid), "records": v["records"], "G1": near_miss_gate(template_text(tid))["G1"],
              "false_alarm_rate": {n: round(v.get(n, 0) / v["records"], 3) for n in SYSTEMS}}
        for tid, v in sorted(per_template.items())}
    report["conservative_reference"] = conservative
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("g1_failing_templates", "conservative_reference")},
                     ensure_ascii=False, indent=2))
    for name, subs in report["systems"].items():
        print(name, {s: (v["all"]["false_alarm"], v["all"]["none_records"],
                         v["excluding_g1_failures"]["false_alarm"], v["excluding_g1_failures"]["none_records"])
                     for s, v in subs.items()})


if __name__ == "__main__":
    main()
