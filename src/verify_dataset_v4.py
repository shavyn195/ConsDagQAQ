"""dataset_v4 独立验证器（发布包泄漏/可行性测试）。任何硬门槛失败 => verdict FAIL，非零退出。

V1 schema；V2 witness 计划经独立检查器完成目标且满足全部金标约束；
V3 咬合：默认计划违反每条金标约束；V4 必要性：去掉 c 后的最小改动计划违反 c；
V5 三元组：同组同任务同 goal、句槽数相同、E/I 金标约束（除 state/evidence）一致、N 金标为空、
   E/I/N 只在约束句槽上不同；V6 证据：evidence_span 是 query 子串，E 版句含参数原值，
   I 版句无指令词，budget/deadline 的 I 版 d2/d3 句不含金标数值；
V7 泄漏：跨 split query/goal/group 零重叠；held-out 工具名不出现在非 tool_ho 记录的任何输入中；
   test 池模板 id 不出现在 train/dev；V8 文本质量：无相邻重复词；
V9 下游刻度：无约束规划在 E/I 上安全成功率为 0、在 N 上为 1；金标规划处处为 1。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from dataset_v4_spec import HELDOUT_ROLES, PII_CLASSES, directive_hits, tool_name  # noqa: E402
from trust_env import check, plan  # noqa: E402

SUBSETS = ["train", "dev", "test_tpl_ho", "test_tool_ho"]
REPEAT = re.compile(r"\b(\w+) \1\b", re.IGNORECASE)


def load(data_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for subset in SUBSETS:
        part = [json.loads(line) for line in (data_dir / f"{subset}.jsonl").read_text(
            encoding="utf-8").splitlines() if line.strip()]
        if not part or any(r.get("subset") != subset for r in part):
            raise ValueError(f"Empty or mislabeled split file: {subset}")
        rows.extend(part)
    return rows


def model_input(row: dict[str, Any]) -> str:
    """编译器能看到的全部输入（query + 目录）。"""
    return row["query"] + " " + json.dumps(row["catalog"], ensure_ascii=False)


def core(c: dict[str, Any]) -> str:
    return json.dumps({k: c[k] for k in ("type", "severity", "scope", "params")}, sort_keys=True)


def verify(rows: list[dict[str, Any]], necessity_sample: int | None = None, *,
           subsets: list[str] = SUBSETS, unseen: dict[str, list[str]] | None = None,
           name: Any = None) -> dict[str, Any]:
    """unseen：{只能出现这些角色的 split: 角色表}；name：角色可读名函数。默认即 v4 口径。"""
    unseen = {"test_tool_ho": HELDOUT_ROLES} if unseen is None else unseen
    name = tool_name if name is None else name
    errors: dict[str, list[str]] = defaultdict(list)
    groups: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    seen_ids = set()
    for r in rows:
        if r["sample_id"] in seen_ids or r["variant"] in groups[r["group_id"]]:
            errors["V5_duplicate"].append(r["sample_id"])
        seen_ids.add(r["sample_id"])
        groups[r["group_id"]][r["variant"]] = r

    for gi, (gid, g) in enumerate(sorted(groups.items())):
        if set(g) != {"explicit", "implicit", "none"}:
            errors["V5_triplet"].append(gid)
            continue
        e, i, n = g["explicit"], g["implicit"], g["none"]
        task = e["task"]
        gold = e["gold"]["constraints"]
        # V1
        for r in (e, i, n):
            if r["gold"]["query_state"] != r["variant"] or not isinstance(r["gold"]["constraints"], list):
                errors["V1_schema"].append(r["sample_id"])
        # V5
        same = all(r["task"] == task and r["task_goal"] == e["task_goal"] for r in (i, n))
        slots = len(e["template_ids"]) == len(i["template_ids"]) == len(n["template_ids"])
        if not (same and slots and not n["gold"]["constraints"] and [core(c) for c in gold] == [core(c) for c in i["gold"]["constraints"]]):
            errors["V5_triplet"].append(gid)
        diff = [k for k, (a, b, c) in enumerate(zip(e["template_ids"], i["template_ids"], n["template_ids"])) if not (a == b == c)]
        if len(diff) != len(gold):
            errors["V5_minimal_pair"].append(gid)
        # V2-V4
        if not check(task, e["witness_plan"], gold)["safe_success"]:
            errors["V2_witness"].append(gid)
        if not all(check(task, e["default_plan"], [c])["violations"] for c in gold):
            errors["V3_binding"].append(gid)
        if necessity_sample is None or gi % max(1, len(groups) // necessity_sample) == 0:
            for k, c in enumerate(gold):
                relaxed, _ = plan(task, gold[:k] + gold[k + 1:])
                if relaxed is None or not check(task, relaxed, [c])["violations"]:
                    errors["V4_necessity"].append(gid)
                    break
        # V6
        for r in (e, i):
            hints = r["hint_meta"]
            if len(hints) != len(r["gold"]["constraints"]):
                errors["V6_hint_count"].append(r["sample_id"])
            for index, c in enumerate(r["gold"]["constraints"]):
                meta = hints[index] if index < len(hints) else {}
                span = c["evidence_span"]
                if not span.strip() or span not in r["query"]:
                    errors["V6_span"].append(r["sample_id"])
                if r["variant"] == "explicit" and not explicit_mentions(c, span, name):
                    errors["V6_explicit_value"].append(r["sample_id"])
                if r["variant"] == "implicit":
                    if directive_hits(span):
                        errors["V6_implicit_directive"].append(r["sample_id"])
                    value = numeric_value(c)
                    if value is not None and meta.get("difficulty", 1) >= 2 and re.search(rf"\b{re.escape(value)}\b", span):
                        errors["V6_implicit_value_leak"].append(r["sample_id"])
        # V8
        for r in (e, i, n):
            if REPEAT.search(r["query"]):
                errors["V8_repeat_word"].append(r["sample_id"])
        # V9
        none_plan, _ = plan(task, [])
        gold_plan, _ = plan(task, gold)
        if check(task, none_plan, gold)["safe_success"] or not check(task, gold_plan, gold)["safe_success"]:
            errors["V9_exec_scale"].append(gid)

    # V7
    by_subset: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_subset[r["subset"]].append(r)
    leak = {}
    for key in ("query", "task_goal", "group_id"):
        values = {s: {r[key] for r in by_subset[s]} for s in subsets}
        for first, s in combinations(subsets, 2):
            overlap = len(values[s] & values[first])
            leak[f"{s}_{key}_overlap_with_{first}"] = overlap
            if overlap:
                errors["V7_cross_split"].append(f"{first}:{s}:{key}:{overlap}")
    for own, roles in unseen.items():
        heldout_tokens = roles + [name(r) for r in roles]
        for r in rows:
            if r["subset"] != own:
                text = model_input(r)
                if any(t in text for t in heldout_tokens):
                    errors["V7_heldout_tool_seen"].append(r["sample_id"])
    for r in by_subset["train"] + by_subset["dev"]:
        if any(t.startswith("test:") for t in r["template_ids"]):
            errors["V7_template_pool"].append(r["sample_id"])

    hard = {k: len(v) for k, v in errors.items()}
    return {
        "records": len(rows),
        "groups": len(groups),
        "failures": hard,
        "leakage": leak,
        "sample_errors": {k: v[:5] for k, v in errors.items()},
        "verdict": "PASS" if not hard else "FAIL",
    }


def numeric_value(c: dict[str, Any]) -> str | None:
    p = c["params"]
    if c["type"] == "budget":
        return f"{p['max_total_cost_cny']:,}"
    if c["type"] == "deadline":
        return str(p["max_duration_hours"])
    return None


def explicit_mentions(c: dict[str, Any], span: str, name: Any = None) -> bool:
    name = tool_name if name is None else name
    p = c["params"]
    low = span.lower()
    if c["type"] in ("budget", "deadline"):
        return numeric_value(c) in span
    if c["type"] == "privacy":
        classes = p.get("protected_data_classes")
        named = {key for key, info in PII_CLASSES.items()
                 if re.search(r"(?<!\w)" + re.escape(info["name"]) + r"(?!\w)", low)}
        return isinstance(classes, list) and bool(classes) and set(classes) == named
    keys = ("approval_role", "required_role") if c["type"] == "tool_auth" else ("before_role", "after_role")
    return all(name(p[k]).lower() in low for k in keys)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=HERE.parent / "data" / "processed_v4")
    parser.add_argument("--out", type=Path, help="Write a separate audit result for a frozen dataset")
    parser.add_argument("--necessity-sample", type=int, default=None,
                        help="只对约 N 个组复核必要性（默认全量）")
    args = parser.parse_args()
    report = verify(load(args.data_dir), args.necessity_sample)
    output = args.out or args.data_dir / "verification_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["verdict"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
