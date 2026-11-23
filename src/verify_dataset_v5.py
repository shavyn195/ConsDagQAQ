"""dataset_v5 独立验证器。任何硬门槛失败 => verdict FAIL，非零退出。

V1–V9：沿用 verify_dataset_v4.verify（切分扩展为 5 个，V7 对 heldout 与 struct 两组未见角色分别检查）。
新增门槛（对应 design_v5_ccfb.md §3 的五个缺陷）：
V10 N 干扰句：规范层每条 N 模板通过 G1（提到他方规则必带"不适用于本任务"条款）与 G2（锚定本任务 + 豁免/
    否定/许可标记）；每类每池四个子类型各至少 2 条；数据中 N 渲染槽的子类型标签与模板一致。
V11 策略卡与别名泄漏：策略卡不含任何 PII 字段别名；test 池别名不出现在 train/dev/struct 的任何模型输入中。
V12 结构 OOD：test_struct_ho 每组任务的结构签名都不在 train 世界可能产生的签名集合内；
    test_tool_ho 的签名都在其中（如实标为名称级 held-out）。
V13 提及顺序：order/tool_auth 的 E、I 模板在每个池内"先提前一角色 / 先提后一角色"条数相等。
V14 保守规划器参考档：不看约束的保守规划器（每阶段选本地且最便宜、插入全部可选步骤）在受约束记录上的
    faithful_success（安全且改动数等于金标最小计划）须 <= 0.05，保证主指标不能被保守策略刷高。
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import verify_dataset_v4 as v4ver  # noqa: E402
from dataset_v5_spec import (  # noqa: E402
    E_TEMPLATES, HELDOUT_ROLES, I_TEMPLATES, NEAR_MISS, PII_CLASSES, POLICY_CARD, STRUCT_ROLES,
    first_mention, near_miss_gate, possible_signatures, tool_name,
)
from trust_env import canonical_insert, check, plan  # noqa: E402

SUBSETS = ["train", "dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho"]
SUBTYPES = ("waiver", "revoked", "other_party", "permission")
CONSERVATIVE_FAITHFUL_MAX = 0.05


def load(data_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for subset in SUBSETS:
        part = [json.loads(line) for line in (data_dir / f"{subset}.jsonl").read_text(
            encoding="utf-8").splitlines() if line.strip()]
        if not part or any(r.get("subset") != subset for r in part):
            raise ValueError(f"Empty or mislabeled split file: {subset}")
        rows.extend(part)
    return rows


def task_signature(task: dict[str, Any], world_spec: dict[str, Any]) -> tuple[int, int, int, bool]:
    fanout = max(len(s["alternatives"]) for s in task["stages"])
    anchor = any(req in task["finish"] for _, req in world_spec["auth_pairs"])
    return (len(task["stages"]), len(task["finish"]), fanout, anchor)


def conservative_plan(task: dict[str, Any]) -> list[str]:
    """不看约束：每阶段选本地且最便宜、最快的工具，finish 保持默认顺序，插入全部可选步骤。"""
    tools = task["tools"]
    best = [sorted(s["alternatives"], key=lambda r: (tools[r]["recipient"] == "external",
                                                    tools[r]["cost_cny"], tools[r]["duration_min"]))[0]
            for s in task["stages"]]
    return canonical_insert(task, best + list(task["finish"]), sorted(task["optional"]))


def spec_gates() -> dict[str, list[str]]:
    errors: dict[str, list[str]] = defaultdict(list)
    for ctype, pools in NEAR_MISS.items():
        for pool, items in pools.items():
            counts = Counter(st for st, _ in items)
            if any(counts[s] < 2 for s in SUBTYPES):
                errors["V10_subtype_coverage"].append(f"{pool}:{ctype}:{dict(counts)}")
            for i, (_, text) in enumerate(items):
                gate = near_miss_gate(text)
                if not (gate["G1"] and gate["G2"]):
                    errors["V10_near_miss_gate"].append(f"{pool}:{ctype}:N:{i}")
    low_card = POLICY_CARD.lower()
    for cls, info in PII_CLASSES.items():
        for pool, fields in info["fields"].items():
            for f in fields:
                if f.lower() in low_card:
                    errors["V11_card_alias"].append(f"{pool}:{f}")
    for ctype, (a, b) in {"order": ("before", "after"), "tool_auth": ("approval", "required")}.items():
        for table, name in ((E_TEMPLATES, "E"), (I_TEMPLATES, "I")):
            for pool, items in table[ctype].items():
                texts = [x if isinstance(x, str) else x[2] for x in items]
                c = Counter(first_mention(t, a, b) for t in texts)
                if c[a] != c[b]:
                    errors["V13_mention_balance"].append(f"{pool}:{ctype}:{name}:{dict(c)}")
    return errors


def verify(rows: list[dict[str, Any]], necessity_sample: int | None = None) -> dict[str, Any]:
    from dataset_v5_spec import WORLDS

    base = v4ver.verify(rows, necessity_sample, subsets=SUBSETS,
                        unseen={"test_tool_ho": HELDOUT_ROLES, "test_struct_ho": STRUCT_ROLES}, name=tool_name)
    errors = spec_gates()
    # V10 数据层：N 槽子类型与模板一致
    for r in rows:
        for tid, st in zip(r["template_ids"], r["near_miss_subtypes"]):
            if ":N:" in tid:
                pool, ctype, _, idx = tid.split(":")
                if NEAR_MISS[ctype][pool][int(idx)][0] != st:
                    errors["V10_subtype_label"].append(r["sample_id"])
            elif st is not None:
                errors["V10_subtype_label"].append(r["sample_id"])
    # V11 数据层：test 池别名不出现在非 tpl_ho 输入中
    test_aliases = [f for info in PII_CLASSES.values() for f in info["fields"]["test"]]
    for r in rows:
        if r["subset"] != "test_tpl_ho":
            text = v4ver.model_input(r)
            if any(a in text for a in test_aliases):
                errors["V11_alias_leak"].append(r["sample_id"])
    # V12 结构签名
    train_sigs = possible_signatures("train")
    sig_counts: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        if r["variant"] != "explicit":
            continue
        sig = task_signature(r["task"], WORLDS[r["world"]])
        sig_counts[r["subset"]][str(sig)] += 1
        if r["subset"] == "test_struct_ho" and sig in train_sigs:
            errors["V12_struct_signature"].append(r["group_id"])
        if r["subset"] == "test_tool_ho" and sig not in train_sigs:
            errors["V12_tool_ho_not_isomorphic"].append(r["group_id"])
    # V14 保守规划器参考档
    conservative: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        gold = r["gold"]["constraints"]
        if not gold:
            continue
        task = r["task"]
        cons = conservative_plan(task)
        result = check(task, cons, gold)
        gold_plan, gold_info = plan(task, gold)
        faithful = result["safe_success"] and cons == gold_plan
        stats = conservative[r["subset"]]
        stats[0] += 1
        stats[1] += int(result["safe_success"])
        stats[2] += int(faithful)
    conservative_rates = {s: {"records": n, "safe_success": round(safe / n, 4), "faithful_success": round(f / n, 4)}
                          for s, (n, safe, f) in conservative.items()}
    for s, rate in conservative_rates.items():
        if rate["faithful_success"] > CONSERVATIVE_FAITHFUL_MAX:
            errors["V14_conservative_faithful"].append(f"{s}:{rate['faithful_success']}")

    failures = dict(base["failures"])
    failures.update({k: len(v) for k, v in errors.items()})
    samples = dict(base["sample_errors"])
    samples.update({k: v[:5] for k, v in errors.items()})
    return {
        "records": base["records"],
        "groups": base["groups"],
        "failures": failures,
        "leakage": base["leakage"],
        "structural_signatures": {s: dict(c) for s, c in sig_counts.items()},
        "conservative_reference": conservative_rates,
        "sample_errors": samples,
        "verdict": "PASS" if not failures else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=HERE.parent / "data" / "processed_v5")
    parser.add_argument("--out", type=Path, help="Write a separate audit result for a frozen dataset")
    parser.add_argument("--necessity-sample", type=int, default=None, help="只对约 N 个组复核必要性（默认全量）")
    args = parser.parse_args()
    report = verify(load(args.data_dir), args.necessity_sample)
    output = args.out or args.data_dir / "verification_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["verdict"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
