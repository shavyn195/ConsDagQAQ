"""dataset_v2 生成器（S2-S8 主流水线，可信数据空间背景）。

流程：目录采样 -> 分层 DAG -> 属性赋值 -> 约束采样(带支持度过滤) -> witness 构造
     -> E/I/N 三版渲染(模板分池) -> 双 group-held-out 切分 -> QC 报告。
确定性：全部随机性来自 seed，同一配置可复现。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from dataset_v2_spec import (  # noqa: E402
    ALL_ROLE_POOL, AUTH_PAIRS, DATASETS, DEFAULT_SEVERITY, DESCRIPTIONS,
    E_TEMPLATES, EXTERNAL_ROLES, GOAL_TEMPLATES, HELDOUT_ROLE_POOL,
    I_TEMPLATES, ORDER_PAIRS, PAID_ROLES, PII_CARRIER_ROLES, PII_CLASSES,
    ROLES, TEAMS, TRAIN_ROLE_POOL, fill_template, readable,
)

CONSTRAINT_TYPES = ["budget", "deadline", "privacy", "tool_auth", "order"]
VARIANTS = ["explicit", "implicit", "none"]


# ---------------------------------------------------------------- DAG 与属性
def gen_layers(rng: random.Random, n_nodes: int) -> list[list[int]]:
    """把 n 个节点分成 2-6 层，每层宽度 1-3。返回每层的节点数。"""
    if n_nodes < 3:
        raise ValueError("dag 需要至少 3 个节点")
    widths: list[int] = []
    remaining = n_nodes
    while remaining > 0:
        w = rng.randint(1, min(3, remaining))
        # 首层不能吃光全部节点：保证至少剩 1 个给下一层（层数 ≥ 2）
        if remaining - w == 0 and not widths:
            w = remaining - 1
        widths.append(w)
        remaining -= w
    # 层数压到 2-6：层数过多时合并
    while len(widths) > 6:
        widths[-2] += widths.pop()
    if len(widths) < 2:
        widths = [1, sum(widths) - 1]
    return widths


def build_dag(rng: random.Random, dag_roles: list[str]) -> dict[str, Any]:
    """分层随机 DAG：节点带角色，层间全连接保证连通。

    dag_roles 的传入顺序即层分配顺序（排前的角色层靠前）——
    调用方用此性质保证 tool_auth/order 配对的拓扑先后。
    """
    widths = gen_layers(rng, len(dag_roles))
    nodes: list[dict[str, Any]] = []
    layers: list[list[int]] = []
    idx = 0
    for width in widths:
        layer_ids = []
        for _ in range(width):
            role = dag_roles[idx]
            nodes.append({"id": idx, "role": role, "layer": len(layers)})
            layer_ids.append(idx)
            idx += 1
        layers.append(layer_ids)
    edges = []
    for li in range(len(layers) - 1):
        for a in layers[li]:
            for b in layers[li + 1]:
                # 0.85 概率连边；但保证每节点有入边/出边（全连接兜底）
                if rng.random() < 0.85 or len(layers[li]) == 1 or len(layers[li + 1]) == 1:
                    edges.append({"from": a, "to": b})
        # 兜底：保证下一层每节点有入边
        covered = {e["to"] for e in edges if e["to"] in layers[li + 1]}
        for b in layers[li + 1]:
            if b not in covered:
                edges.append({"from": rng.choice(layers[li]), "to": b})
    # 产出节点：最后层优先 terminal 类别角色
    last = layers[-1]
    terminal_id = next((i for i in last if ROLES[nodes[i]["role"]][1] == "terminal"), rng.choice(last))
    return {"nodes": nodes, "edges": edges, "layers": layers, "terminal_id": terminal_id}


def assign_attributes(rng: random.Random, graph: dict[str, Any], pii_class: str | None) -> None:
    """给节点赋 cost/duration/recipient/data_classes；保证 pii 只停在 local 节点。"""
    for node in graph["nodes"]:
        role = node["role"]
        lo, hi = PAID_ROLES.get(role, (0, 0))
        node["cost_cny"] = int(rng.randrange(lo, hi + 1) // 10 * 10) if hi > 0 else 0
        node["duration_min"] = int(rng.randrange(20, 125) // 5 * 5)
        node["recipient"] = "external" if role in EXTERNAL_ROLES else "local"
        if pii_class and role in PII_CARRIER_ROLES:
            node["data_classes"] = [pii_class]
        else:
            node["data_classes"] = ["aggregate_metrics"]
        node["terminal_output"] = node["id"] == graph["terminal_id"]


def topo_order(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """层序即拓扑序（层间边只从低层指向高层）。"""
    return sorted(graph["nodes"], key=lambda n: (n["layer"], n["id"]))


# ---------------------------------------------------------------- 约束采样
def pos_of(graph: dict[str, Any], role: str) -> int | None:
    """角色在 witness 拓扑序中的位置（层序+id 序；用于先后类约束的支持度判断）。"""
    order = topo_order(graph)
    for i, node in enumerate(order):
        if node["role"] == role:
            return i
    return None


def supported_types(graph: dict[str, Any], catalog: list[str]) -> list[str]:
    """按 DAG/目录支持度过滤约束类（位置比较与 witness 重放口径一致）。"""
    out = []
    roles_in_dag = {n["role"] for n in graph["nodes"]}
    if any(n["cost_cny"] > 0 for n in graph["nodes"]):
        out.append("budget")
    out.append("deadline")
    if any(r in EXTERNAL_ROLES for r in catalog):
        out.append("privacy")
    for approval, required in AUTH_PAIRS:
        if approval in roles_in_dag and required in roles_in_dag:
            pa, pr = pos_of(graph, approval), pos_of(graph, required)
            if pa is not None and pr is not None and pa < pr:
                out.append("tool_auth")
                break
    for before, after in ORDER_PAIRS:
        if before in roles_in_dag and after in roles_in_dag:
            pb, pa2 = pos_of(graph, before), pos_of(graph, after)
            if pb is not None and pa2 is not None and pb < pa2:
                out.append("order")
                break
    return out


def make_constraint(
    rng: random.Random, ctype: str, graph: dict[str, Any], catalog: list[str],
    pii_class: str | None,
) -> dict[str, Any] | None:
    """构造单条金标约束（type/params/scope/description）；不满足支持度返回 None。"""
    roles_in_dag = {n["role"] for n in graph["nodes"]}
    scope: list[str] = []
    params: dict[str, Any] = {}
    mapping: dict[str, str] = {}
    if ctype == "budget":
        total = sum(n["cost_cny"] for n in graph["nodes"])
        if total <= 0:
            return None
        margin = int(total * rng.uniform(0.15, 0.6) // 50 * 50) or 50
        limit = int((total + margin) // 50 * 50)
        params = {"max_total_cost_cny": limit}
        scope = sorted(f"role:{n['role']}" for n in graph["nodes"] if n["cost_cny"] > 0)
        mapping = {"limit": f"{limit:,}"}
    elif ctype == "deadline":
        total_min = sum(n["duration_min"] for n in graph["nodes"])
        hours = max(1, -(-total_min // 60) + rng.randint(1, 5))
        params = {"max_duration_hours": hours}
        terminal = next(n for n in graph["nodes"] if n["terminal_output"])
        scope = [f"role:{terminal['role']}"]
        mapping = {"hours": str(hours)}
    elif ctype == "privacy":
        ext = [r for r in catalog if r in EXTERNAL_ROLES]
        if not ext or not pii_class:
            return None
        params = {"protected_data_classes": [pii_class], "forbidden_recipients": ["external"]}
        scope = sorted(f"role:{r}" for r in ext)
        mapping = {"pii": PII_CLASSES[pii_class]}
    elif ctype == "tool_auth":
        candidates = [
            (a, r) for a, r in AUTH_PAIRS
            if a in roles_in_dag and r in roles_in_dag
            and (pos_of(graph, a) if pos_of(graph, a) is not None else 10**9) < (pos_of(graph, r) if pos_of(graph, r) is not None else -1)
        ]
        if not candidates:
            return None
        approval, required = rng.choice(candidates)
        params = {"approval_role": approval, "required_role": required}
        scope = [f"role:{required}"]
        mapping = {"approval": readable(approval), "required": readable(required)}
    elif ctype == "order":
        candidates = [
            (b, a) for b, a in ORDER_PAIRS
            if b in roles_in_dag and a in roles_in_dag
            and (pos_of(graph, b) if pos_of(graph, b) is not None else 10**9) < (pos_of(graph, a) if pos_of(graph, a) is not None else -1)
        ]
        if not candidates:
            return None
        before, after = rng.choice(candidates)
        params = {"before_role": before, "after_role": after}
        scope = sorted({f"role:{before}", f"role:{after}"})
        mapping = {"before": readable(before), "after": readable(after)}
    else:
        return None
    desc_pool = DESCRIPTIONS[ctype]
    description = fill_template(desc_pool[rng.randrange(len(desc_pool))], mapping)
    return {
        "type": ctype,
        "description": description,
        "evidence_span": "",  # 渲染期填充
        "state": "",  # 渲染期填充（explicit/implicit）
        "confidence": 1.0,  # 构造期常数（非校准目标，见 limitations）
        "severity": DEFAULT_SEVERITY[ctype],
        "scope": scope,
        "params": params,
        "_mapping": mapping,  # 渲染期用，写盘前移除
    }


# ---------------------------------------------------------------- 渲染
def render_sentences(
    rng: random.Random, constraints: list[dict[str, Any]], variant: str, pool: str,
) -> tuple[list[str], list[dict[str, Any]]]:
    """按 variant 渲染每条约束的句子；返回 (句子列表, 渲染元数据列表)。"""
    sentences: list[str] = []
    meta: list[dict[str, Any]] = []
    for c in constraints:
        mapping = c["_mapping"]
        if variant == "explicit":
            pool_list = E_TEMPLATES[c["type"]][pool]
            text = fill_template(pool_list[rng.randrange(len(pool_list))], mapping)
            template_id = f"{pool}:{c['type']}:E:{pool_list.index(next(t for t in pool_list if fill_template(t, mapping) == text))}"
            meta.append({"type": c["type"], "template_id": template_id, "hint_type": None, "difficulty": None})
        elif variant == "implicit":
            hint = rng.choice(["consequence", "fact", "convention"])
            difficulty = rng.choices([1, 2, 3], weights=[0.30, 0.45, 0.25])[0]
            pool_list = [
                (i, t) for i, (h, d, t) in enumerate(I_TEMPLATES[c["type"]][pool])
                if h == hint and d == difficulty
            ]
            if not pool_list:  # 该 (hint, difficulty) 组合缺模板时降级
                pool_list = [
                    (i, t) for i, (h, d, t) in enumerate(I_TEMPLATES[c["type"]][pool]) if h == hint
                ]
            idx, text = pool_list[rng.randrange(len(pool_list))]
            text = fill_template(text, mapping)
            template_id = f"{pool}:{c['type']}:I:{idx}"
            meta.append({"type": c["type"], "template_id": template_id, "hint_type": hint, "difficulty": difficulty})
        else:
            continue
        sentences.append(text)
    return sentences, meta


# ---------------------------------------------------------------- 单组生成
# 确保产生非零 cost 的付费角色（budget 注入用；create_purchase_order 采样可能为 0）
BUDGET_INJECT_ROLES = ["purchase_data_asset", "pay_with_wallet", "call_external_api"]


def gen_group(
    rng: random.Random, group_id: str, subset: str,
) -> dict[str, Any] | None:
    """生成一个任务组（E/I/N 三版共享 goal/DAG/约束集）。

    约束驱动构造：先采约束类型，再把支撑角色注入 DAG（保证五类均衡且支持度成立）。
    """
    # 池选择：tpl_ho 用 test 模板池；tool_ho 用 held-out 角色；其余 train
    tpl_pool = "test" if subset == "test_tpl_ho" else "train"
    dag_pool = HELDOUT_ROLE_POOL if subset == "test_tool_ho" else TRAIN_ROLE_POOL
    # tool_ho 子集无 tool_auth 配对（held-out 无授权惯例对），如实降级
    type_menu = [t for t in CONSTRAINT_TYPES if not (subset == "test_tool_ho" and t == "tool_auth")]

    for _attempt in range(30):
        # 1) 约束类型：五类均衡采 1-3 条
        n_const = rng.choices([1, 2, 3], weights=[0.4, 0.4, 0.2])[0]
        chosen_types = rng.sample(type_menu, min(n_const, len(type_menu)))
        # 2) 注入支撑角色（顺序即层序，pair 的 before/approval 必须排前）
        pinned: list[str] = []
        pair_hints: list[tuple[str, str]] = []

        def pin(role: str) -> None:
            if role not in pinned:
                pinned.append(role)

        for ctype in chosen_types:
            if ctype == "budget":
                # tool_ho 的 DAG 必须全 held-out 角色：用 FL 算力配额角色支撑 budget
                inject = ["create_fl_round"] if subset == "test_tool_ho" else BUDGET_INJECT_ROLES
                pin(rng.choice(inject))
            elif ctype == "tool_auth":
                pair = rng.choice(AUTH_PAIRS)
                pin(pair[0]); pin(pair[1])
                pair_hints.append(pair)
            elif ctype == "order":
                pool_pairs = [p for p in ORDER_PAIRS if all(r in dag_pool for r in p)]
                if not pool_pairs:
                    chosen_types = [t for t in chosen_types if t != "order"]
                    continue
                pair = rng.choice(pool_pairs)
                pin(pair[0]); pin(pair[1])
                pair_hints.append(pair)
        if not chosen_types:
            continue
        # pair 顺序重排：保证每个 hint 的 before 位于 after 前
        for before, after in pair_hints:
            if pinned.index(before) > pinned.index(after):
                pinned.remove(before)
                pinned.insert(pinned.index(after), before)
        # 3) 补随机角色到 3-6 个
        n_dag = rng.randint(max(3, len(pinned)), 6)
        filler = [r for r in rng.sample(dag_pool, len(dag_pool)) if r not in pinned]
        dag_roles = pinned + filler[: max(0, n_dag - len(pinned))]
        graph = build_dag(rng, list(dag_roles))
        pii_class = rng.choice(list(PII_CLASSES)) if rng.random() < 0.85 else None
        assign_attributes(rng, graph, pii_class)
        # 4) 目录：DAG 角色 + 干扰角色；privacy 被选时强制含 external 候选
        n_catalog = rng.randint(10, 16)
        distractors = [r for r in rng.sample(ALL_ROLE_POOL, len(ALL_ROLE_POOL)) if r not in dag_roles]
        if "privacy" in chosen_types:
            ext_extra = [r for r in distractors if r in EXTERNAL_ROLES]
            if not any(r in EXTERNAL_ROLES for r in dag_roles) and ext_extra:
                distractors.remove(ext_extra[0])
                distractors.insert(0, ext_extra[0])
        catalog = sorted(set(dag_roles) | set(distractors[: max(0, n_catalog - len(dag_roles))]))
        # 5) 生成约束（chosen_types 逐一尝试；失败的类型丢弃）
        constraints = []
        for ctype in chosen_types:
            c = make_constraint(rng, ctype, graph, catalog, pii_class)
            if c is not None:
                constraints.append(c)
        if not constraints:
            continue
        # goal 渲染
        goal = fill_template(
            GOAL_TEMPLATES[tpl_pool][rng.randrange(len(GOAL_TEMPLATES[tpl_pool]))],
            {"dataset": rng.choice(DATASETS), "team": rng.choice(TEAMS)},
        )
        available_roles = sorted(f"role:{r}" for r in catalog)
        tool_catalog = [
            {"role": r, "category": ROLES[r][1], "subsystem": ROLES[r][0]} for r in catalog
        ]
        # witness：拓扑序执行模拟
        witness = [
            {
                "step": i, "role": n["role"], "cost_cny": n["cost_cny"],
                "duration_min": n["duration_min"], "recipient": n["recipient"],
                "data_classes": list(n["data_classes"]),
            }
            for i, n in enumerate(topo_order(graph))
        ]
        records = []
        for variant in VARIANTS:
            if variant == "none":
                query = goal
                gold_constraints = []
                template_ids, hint_meta = [], []
            else:
                sentences, meta = render_sentences(rng, constraints, variant, tpl_pool)
                query = goal + " " + " ".join(sentences) if sentences else goal
                template_ids = [m["template_id"] for m in meta]
                hint_meta = [
                    {k: m[k] for k in ("hint_type", "difficulty")} for m in meta
                ]
                gold_constraints = []
                for c, m, sent in zip(constraints, meta, sentences):
                    gc = {k: v for k, v in c.items() if not k.startswith("_")}
                    gc["state"] = variant
                    gc["evidence_span"] = sent
                    gold_constraints.append(gc)
            if variant != "none" and not gold_constraints:
                continue
            record = {
                "sample_id": f"{group_id}-{variant[0].upper()}",
                "group_id": group_id,
                "split": "train" if subset == "train" else "dev" if subset == "dev" else "test",
                "subset": subset,
                "variant": variant,
                "template_ids": template_ids,
                "hint_meta": hint_meta,
                "task_goal": goal,
                "query": query,
                "available_roles": available_roles,
                "tool_catalog": tool_catalog,
                "graph": {
                    "nodes": [
                        {k: v for k, v in n.items()} for n in graph["nodes"]
                    ],
                    "edges": graph["edges"],
                },
                "witness": witness,
                "gold": {
                    "query_state": variant,
                    "abstain": False,
                    "constraints": gold_constraints,
                },
            }
            records.append(record)
        if len(records) == 3:
            return {"group_id": group_id, "subset": subset, "records": records}
    return None


# ---------------------------------------------------------------- 主流程
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "dataset_v2.yaml")
    args = parser.parse_args()
    import yaml  # 延迟导入，保持生成器无 yaml 依赖也可被测试

    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    seed = cfg["seed"]
    counts = cfg["groups"]  # {train, dev, test_tpl_ho, test_tool_ho}
    out_dir = ROOT / cfg["output_dir"]
    rng = random.Random(seed)

    all_rows: list[dict[str, Any]] = []
    groups_by_subset: dict[str, int] = Counter()
    failures = 0
    for subset, n in counts.items():
        made = 0
        idx = 0
        while made < n:
            group_id = f"{subset}-{idx:05d}"
            group = gen_group(rng, group_id, subset)
            idx += 1
            if group is None:
                failures += 1
                if failures > 200:
                    raise SystemExit("生成失败次数过多，请检查支持度配置")
                continue
            all_rows.extend(group["records"])
            groups_by_subset[subset] += 1
            made += 1

    # 写盘
    out_dir.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    for subset in counts:
        rows = [r for r in all_rows if r["subset"] == subset]
        path = out_dir / f"{subset}.jsonl"
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows),
            encoding="utf-8",
        )
        files[subset] = path

    # QC 统计（S8 初版；完整复查由 verify_dataset_v2.py 执行）
    def subset_rows(name: str) -> list[dict[str, Any]]:
        return [r for r in all_rows if r["subset"] == name]

    type_dist = Counter(
        c["type"] for r in all_rows for c in r["gold"]["constraints"]
    )
    hint_dist = Counter(
        (m["hint_type"], m["difficulty"])
        for r in all_rows if r["variant"] == "implicit" for m in r["hint_meta"]
    )
    report = {
        "dataset": "consdag_trusted_constraint_dataset_v2",
        "synthetic_only": True,
        "seed": seed,
        "groups": dict(groups_by_subset),
        "records": {k: len(subset_rows(k)) for k in counts},
        "constraint_type_distribution": dict(type_dist),
        "implicit_hint_distribution": {f"{h}-d{d}": n for (h, d), n in sorted(hint_dist.items())},
        "constraint_count_per_group": dict(Counter(
            len([r for r in all_rows if r["variant"] != "none" and r["group_id"] == g][0]["gold"]["constraints"])
            for g in {r["group_id"] for r in all_rows}
        )),
        "generation_failures": failures,
        "sha256": {
            k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in files.items()
        },
        "limitations": [
            "Synthetic, hand-templated corpus; not naturalistic user language.",
            "Oracle recoverability check (S6) not yet run; PE oracle pending API key.",
            "All gold confidence values are construction-time 1.0; no calibration target.",
            "No ambiguous or abstention-required examples by design (implicit red line).",
            "test_tool_ho subset contains no tool_auth constraints (no held-out auth pairs).",
        ],
    }
    (out_dir / "generation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
