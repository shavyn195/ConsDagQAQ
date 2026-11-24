"""论文草稿 v1 的派生数字（2026-11-24，只读冻结资产，零 GPU，不重复 audit_recompute 的回放）。

  1. v5/v6 各切分规模（行数、组数、E/I/N）；
  2. v5 各切分的任务结构签名（阶段/默认/备选/finish）与 train 的重叠——E2 单体 prompt 不含任务结构时的信息缺口；
  3. 同一工具角色的 cost_cny / duration_min 是否随任务变化——单体能否靠记忆补上 prompt 中缺失的数值；
  4. v5 三 seed faithful_constrained 均值±样本标准差（取自 seed 方差 JSON 的 per_seed）；
  5. 三 seed 共杀：观测 / 独立假设期望（取自 recompute.json）。
用法（仓库根目录）：python scripts/submission/draft_numbers_20261124.py
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/submission/audit_20261124/draft_numbers.json"
AUDIT = ROOT / "outputs/submission/audit_20261124/recompute.json"
SEEDVAR = ROOT / "outputs/v5_analysis/seed_variance_decomposition_20261125.json"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def signature(task: dict) -> str:
    stages = [[s["stage"], s["default"], sorted(s["alternatives"])] for s in task["stages"]]
    return json.dumps([stages, task["finish"], sorted(task["optional"])])


def dataset_sizes(version: str) -> dict:
    out = {}
    for path in sorted((ROOT / "data" / version).glob("*.jsonl")):
        rows = load_jsonl(path)
        out[path.stem] = {"rows": len(rows), "groups": len({r["group_id"] for r in rows}),
                          "variants": dict(Counter(r["variant"] for r in rows))}
    out["total_rows"] = sum(v["rows"] for v in out.values())
    return out


def structure_overlap() -> dict:
    data = {p.stem: load_jsonl(p) for p in sorted((ROOT / "data/processed_v5").glob("*.jsonl"))}
    train_sigs = {signature(r["task"]) for r in data["train"]}
    out = {"train_distinct_signatures": len(train_sigs)}
    for split, rows in data.items():
        if split == "train":
            continue
        sigs = {signature(r["task"]) for r in rows}
        out[split] = {"distinct_signatures": len(sigs), "unseen_in_train": len(sigs - train_sigs)}
    values: dict[str, dict[str, set]] = defaultdict(lambda: {"cost_cny": set(), "duration_min": set()})
    for r in data["train"]:
        for role, spec in r["task"]["tools"].items():
            values[role]["cost_cny"].add(spec["cost_cny"])
            values[role]["duration_min"].add(spec["duration_min"])
    out["train_roles"] = len(values)
    out["roles_with_varying_cost"] = sum(len(v["cost_cny"]) > 1 for v in values.values())
    out["roles_with_varying_duration"] = sum(len(v["duration_min"]) > 1 for v in values.values())
    return out


def seed_means() -> dict:
    d = json.loads(SEEDVAR.read_text(encoding="utf-8"))
    out = {}
    for model, splits in d["models"].items():
        for split, e in splits.items():
            vals = [100 * e["per_seed"][s]["faithful_rate"] for s in sorted(e["per_seed"])]
            out[f"{model} | {split}"] = {"per_seed_pct": [round(v, 2) for v in vals],
                                          "mean_pct": round(statistics.mean(vals), 2),
                                          "sd_pct": round(statistics.stdev(vals), 2)}
    return out


def cofail_ratio() -> dict:
    d = json.loads(AUDIT.read_text(encoding="utf-8"))["seed_variance_derived"]
    out = {}
    for key, v in d.items():
        exp = v["all_three_expected_if_independent"]
        if v["all_three_failed"] or exp >= 0.5:
            out[key] = {"observed": v["all_three_failed"], "expected_if_independent": exp,
                        "ratio": round(v["all_three_failed"] / exp, 2) if exp else None}
    return out


def main() -> None:
    report = {
        "purpose": "derived numbers for reports/paper_draft_v1.md (read-only on frozen assets)",
        "dataset_v5": dataset_sizes("processed_v5"),
        "dataset_v6": dataset_sizes("processed_v6"),
        "v5_structure_and_tool_values": structure_overlap(),
        "v5_three_seed_faithful": seed_means(),
        "three_seed_cofail": cofail_ratio(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
