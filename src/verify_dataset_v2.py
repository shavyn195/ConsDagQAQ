"""S5/S7 独立复查：witness 可行性(G⊨C) + 双 group-held-out 泄漏检查 + schema 校验。

独立于生成器实现（重新解析 JSONL 并重放约束检查器），避免生成器自证。
用法：python src/verify_dataset_v2.py [--data-dir data/processed_v2]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from dataset_v2_spec import AUTH_PAIRS, EXTERNAL_ROLES, ORDER_PAIRS  # noqa: E402

SUBSETS = ["train", "dev", "test_tpl_ho", "test_tool_ho"]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------- S5 约束检查器
def check_constraint(constraint: dict[str, Any], witness: list[dict[str, Any]]) -> bool:
    """重放 witness，检查单条约束是否被满足。"""
    ctype = constraint["type"]
    params = constraint["params"]
    if ctype == "budget":
        return sum(w["cost_cny"] for w in witness) <= params["max_total_cost_cny"]
    if ctype == "deadline":
        return sum(w["duration_min"] for w in witness) <= params["max_duration_hours"] * 60
    if ctype == "privacy":
        protected = set(params["protected_data_classes"])
        for w in witness:
            if w["recipient"] == "external" and protected & set(w["data_classes"]):
                return False
        return True
    if ctype == "tool_auth":
        pos = {w["role"]: i for i, w in enumerate(witness)}
        a, r = params["approval_role"], params["required_role"]
        return pos.get(a, 10**9) < pos.get(r, -1)
    if ctype == "order":
        pos = {w["role"]: i for i, w in enumerate(witness)}
        b, a = params["before_role"], params["after_role"]
        return pos.get(b, 10**9) < pos.get(a, -1)
    return False


def witness_feasible(record: dict[str, Any]) -> list[str]:
    """检查 witness 达成目标 + 满足全部金标约束；返回错误列表。"""
    errors: list[str] = []
    witness = record["witness"]
    graph_roles = {n["role"] for n in record["graph"]["nodes"]}
    if not witness:
        return ["witness 为空"]
    if {w["role"] for w in witness} != graph_roles:
        errors.append("witness 未覆盖全部 DAG 节点")
    # goal 达成：terminal_output 节点被执行
    terminal_roles = {n["role"] for n in record["graph"]["nodes"] if n.get("terminal_output")}
    if terminal_roles and not (terminal_roles & {w["role"] for w in witness}):
        errors.append("witness 未执行产出节点")
    for c in record["gold"]["constraints"]:
        if not check_constraint(c, witness):
            errors.append(f"约束 {c['type']} 不满足: {c['params']}")
    return errors


# ---------------------------------------------------------------- schema 校验
def validate_record(record: dict[str, Any]) -> list[str]:
    """结构校验：三态/证据子串/scope 词表/E-I 配对完整性（组级检查在 validate_pairs）。"""
    errors: list[str] = []
    gold = record["gold"]
    variant = record["variant"]
    if gold["query_state"] != variant:
        errors.append("gold.query_state 与 variant 不一致")
    if variant == "none":
        if gold["constraints"]:
            errors.append("none 版金标须为空集")
        return errors
    if not gold["constraints"]:
        errors.append(f"{variant} 版金标约束为空")
        return errors
    role_vocab = set(record["available_roles"])
    for c in gold["constraints"]:
        if c["state"] != variant:
            errors.append(f"约束 state={c['state']} 与 variant={variant} 不一致")
        if c["evidence_span"] not in record["query"]:
            errors.append("evidence_span 不是 query 的子串")
        if not c.get("severity"):
            errors.append("缺 severity（C-LOOP-2）")
        for s in c["scope"]:
            if s not in role_vocab:
                errors.append(f"scope 项 {s} 不在角色词表中")
        if c["type"] not in {"budget", "deadline", "privacy", "tool_auth", "order"}:
            errors.append(f"未知约束类型 {c['type']}")
    return errors


def validate_pairs(rows: list[dict[str, Any]]) -> list[str]:
    """组级配对完整性：E/I 同约束集（type+params+scope），N 空集，共享 goal 与目录。"""
    errors: list[str] = []
    groups: dict[str, dict[str, Any]] = {}
    for r in rows:
        groups.setdefault(r["group_id"], {})[r["variant"]] = r
    for gid, variants in groups.items():
        if set(variants) != {"explicit", "implicit", "none"}:
            errors.append(f"{gid}: 三版不完整 {sorted(variants)}")
            continue
        e, i = variants["explicit"], variants["implicit"]
        key = lambda r: sorted(  # noqa: E731
            (c["type"], json.dumps(c["params"], sort_keys=True), tuple(sorted(c["scope"])))
            for c in r["gold"]["constraints"]
        )
        if key(e) != key(i):
            errors.append(f"{gid}: E/I 约束集不一致")
        if e["task_goal"] != i["task_goal"] or e["available_roles"] != i["available_roles"]:
            errors.append(f"{gid}: E/I 信息面不一致")
        if variants["none"]["gold"]["constraints"]:
            errors.append(f"{gid}: N 版金标非空")
        if variants["none"]["task_goal"] != e["task_goal"]:
            errors.append(f"{gid}: N 版 goal 与 E 版不一致")
    return errors


# ---------------------------------------------------------------- S7 泄漏检查
def dag_pairs(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """每组的 DAG 角色使用集 -> 全部 2-子集。"""
    seen_groups: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    for r in rows:
        if r["group_id"] in seen_groups:
            continue
        seen_groups.add(r["group_id"])
        roles = sorted(n["role"] for n in r["graph"]["nodes"])
        pairs.update(combinations(roles, 2))
    return pairs


def template_ids_used(rows: list[dict[str, Any]]) -> set[str]:
    return {t for r in rows for t in r["template_ids"]}


def ngram_overlap(a: str, b: str, n: int = 3) -> float:
    """两模板池渲染文本的 3-gram Jaccard 重叠（QC 报告项，非硬断言）。"""
    def grams(texts: list[str]) -> set[str]:
        out: set[str] = set()
        for t in texts:
            tokens = t.lower().split()
            out.update(" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1))
        return out

    ga, gb = grams([a]), grams([b])
    return len(ga & gb) / max(len(ga | gb), 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "processed_v2")
    args = parser.parse_args()

    all_rows: list[dict[str, Any]] = []
    for subset in SUBSETS:
        path = args.data_dir / f"{subset}.jsonl"
        if path.exists():
            all_rows.extend(load_jsonl(path))

    errors: list[str] = []
    # S5：witness 复查（逐条）
    witness_fail = 0
    for r in all_rows:
        werr = witness_feasible(r)
        if werr:
            witness_fail += 1
            if len(errors) < 20:
                errors.append(f"[S5] {r['sample_id']}: {werr}")
    # schema：逐条
    schema_fail = 0
    for r in all_rows:
        serr = validate_record(r)
        if serr:
            schema_fail += 1
            if len(errors) < 40:
                errors.append(f"[schema] {r['sample_id']}: {serr}")
    # 配对完整性
    perr = validate_pairs(all_rows)
    errors.extend(perr[:20])

    # S7-1：工具 2-子集 held-out（train+dev+tpl_ho 的 DAG 2-子集 与 tool_ho 零交集）
    train_side = [r for r in all_rows if r["subset"] != "test_tool_ho"]
    tool_ho = [r for r in all_rows if r["subset"] == "test_tool_ho"]
    train_pairs = dag_pairs(train_side)
    ho_pairs = dag_pairs(tool_ho)
    leak_pairs = train_pairs & ho_pairs
    # S7-2：模板分池（tpl_ho 的模板 id 不在 train/dev/tool_ho 使用集）
    tpl_ho = [r for r in all_rows if r["subset"] == "test_tpl_ho"]
    others = [r for r in all_rows if r["subset"] != "test_tpl_ho"]
    leak_templates = template_ids_used(tpl_ho) & template_ids_used(others)
    # S7-3：n-gram 重叠（E 版渲染句，train 池 vs test 池；报告值）
    e_train = [s for r in others if r["variant"] == "explicit" for s in [c["evidence_span"] for c in r["gold"]["constraints"]]]
    e_test = [s for r in tpl_ho if r["variant"] == "explicit" for s in [c["evidence_span"] for c in r["gold"]["constraints"]]]
    ngram = ngram_overlap(" ".join(e_train[:500]), " ".join(e_test[:500]))

    verdict = {
        "records": len(all_rows),
        "witness_recheck_fail": witness_fail,
        "schema_fail": schema_fail,
        "pair_integrity_fail": len(perr),
        "s7_tool_pair_leak": sorted(leak_pairs),
        "s7_tool_pair_leak_count": len(leak_pairs),
        "s7_template_leak": sorted(leak_templates),
        "s7_template_leak_count": len(leak_templates),
        "s7_evidence_3gram_jaccard_train_vs_test": round(ngram, 4),
        "verdict": "PASS" if not (witness_fail or schema_fail or perr or leak_pairs or leak_templates) else "FAIL",
        "sample_errors": errors[:20],
    }
    out = args.data_dir / "verification_report.json"
    out.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    if verdict["verdict"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
