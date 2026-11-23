"""可信数据空间任务世界：计划执行、独立约束检查器、约束感知规划器（dataset_v4 / E1-exec）。

- execute：按步骤累计费用/时长，跟踪 PII 数据流（获取阶段后激活，clears_pii 工具后解除），
  判定目标是否完成（各阶段按依赖顺序被某个备选工具覆盖，finish 两步在 report 之后）。
- check：对给定约束集逐条判定是否被计划违反；与生成器的 witness 构造代码相互独立。
- plan：最小改动规划器。给定（可能是编译器预测的）约束集，在"工具替换 × finish 顺序 × 脱敏插入
  × 前置步骤插入"空间里找满足全部可用约束、且相对默认计划改动最少的计划；无解返回 None。
  空约束集返回默认计划。它代表"完美服从约束的 planner"，使下游成功率只反映编译质量。
"""

from __future__ import annotations

import itertools
from typing import Any

CONSTRAINT_TYPES = ("budget", "deadline", "privacy", "tool_auth", "order")
PRECEDENCE_KEYS = {"tool_auth": ("approval_role", "required_role"), "order": ("before_role", "after_role")}


def _role(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value[5:] if value.startswith("role:") else value


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def normalize_constraint(item: Any, task: dict[str, Any]) -> dict[str, Any] | None:
    """把一条（可能来自模型的）约束转成可检查形式；类型/参数不合契约时返回 None（不可用）。"""
    if not isinstance(item, dict) or item.get("type") not in CONSTRAINT_TYPES:
        return None
    params = item.get("params")
    if not isinstance(params, dict):
        return None
    ctype = item["type"]
    if ctype == "budget":
        limit = _number(params.get("max_total_cost_cny"))
        return None if limit is None else {"type": ctype, "limit": limit}
    if ctype == "deadline":
        hours = _number(params.get("max_duration_hours"))
        return None if hours is None else {"type": ctype, "minutes": hours * 60}
    if ctype == "privacy":
        classes = params.get("protected_data_classes")
        recipients = params.get("forbidden_recipients")
        if not isinstance(classes, list) or not classes or not all(isinstance(c, str) for c in classes):
            return None
        if not isinstance(recipients, list) or "external" not in recipients:
            return None
        return {"type": ctype, "classes": set(classes)}
    first_key, second_key = PRECEDENCE_KEYS[ctype]
    first, second = _role(params.get(first_key)), _role(params.get(second_key))
    if first not in task["tools"] or second not in task["tools"] or first == second:
        return None
    return {"type": ctype, "first": first, "second": second}


def execute(task: dict[str, Any], plan: list[str]) -> dict[str, Any]:
    """执行计划，返回轨迹统计；未知角色使计划无效。"""
    tools = task["tools"]
    if not all(role in tools for role in plan):
        return {"valid": False, "completed": False, "cost": 0, "minutes": 0, "leaks": [], "positions": {}}
    acquire = set(task["stages"][0]["alternatives"])
    pii_active = False
    leaks: list[tuple[int, str]] = []
    positions: dict[str, int] = {}
    cost = minutes = 0
    for i, role in enumerate(plan):
        spec = tools[role]
        positions.setdefault(role, i)
        cost += spec["cost_cny"]
        minutes += spec["duration_min"]
        if pii_active and spec["recipient"] == "external":
            leaks.append((i, task["data_class"]))
        if role in acquire and task.get("data_class"):
            pii_active = True
        if spec["clears_pii"]:
            pii_active = False
    return {
        "valid": True, "completed": goal_completed(task, plan, positions),
        "cost": cost, "minutes": minutes, "leaks": leaks, "positions": positions,
    }


def goal_completed(task: dict[str, Any], plan: list[str], positions: dict[str, int]) -> bool:
    last = -1
    for stage in task["stages"]:
        hits = [positions[r] for r in stage["alternatives"] if r in positions]
        if not hits or min(hits) <= last:
            return False
        last = min(hits)
    return all(r in positions and positions[r] > last for r in task["finish"])


def violated(norm: dict[str, Any], trace: dict[str, Any]) -> bool:
    ctype = norm["type"]
    if ctype == "budget":
        return trace["cost"] > norm["limit"]
    if ctype == "deadline":
        return trace["minutes"] > norm["minutes"]
    if ctype == "privacy":
        return any(cls in norm["classes"] for _, cls in trace["leaks"])
    pos = trace["positions"]
    if norm["second"] not in pos:
        return False
    return norm["first"] not in pos or pos[norm["first"]] > pos[norm["second"]]


def check(task: dict[str, Any], plan: list[str] | None, constraints: list[dict[str, Any]]) -> dict[str, Any]:
    """独立检查器：计划是否完成目标、逐条金标约束是否违反。plan=None 视为未产出计划。"""
    if plan is None:
        return {"planned": False, "completed": False, "violations": [], "safe_success": False}
    trace = execute(task, plan)
    norms = [normalize_constraint(c, task) for c in constraints]
    if any(n is None for n in norms):
        raise ValueError("gold constraints must be well-formed")
    violations = [i for i, n in enumerate(norms) if violated(n, trace)]
    return {
        "planned": True, "completed": trace["completed"], "violations": violations,
        "safe_success": trace["completed"] and not violations,
        "cost": trace["cost"], "minutes": trace["minutes"],
    }


def _insert_before(plan: list[str], role: str, target: str) -> list[str]:
    i = plan.index(target)
    return plan[:i] + [role] + plan[i:]


def _close_precedence(plan: list[str], norms: list[dict[str, Any]], optional: dict[str, Any]) -> tuple[list[str], int]:
    """为前置类约束插入缺失的可选前置步骤（紧挨在目标之前）；返回 (计划, 插入数)。"""
    inserted = 0
    for _ in range(4):
        changed = False
        for n in norms:
            if n["type"] not in PRECEDENCE_KEYS:
                continue
            if n["second"] in plan and n["first"] not in plan and n["first"] in optional:
                plan = _insert_before(plan, n["first"], n["second"])
                inserted += 1
                changed = True
        if not changed:
            break
    return plan, inserted


def _finish_orders(finish: list[str]) -> list[tuple[list[str], int]]:
    """finish 块的全部排列及其相对默认顺序的逆序对数（改动数）。两步时即"原序 / 反转"，与 v4 一致。"""
    out = []
    for perm in itertools.permutations(range(len(finish))):
        moved = sum(perm[i] > perm[j] for i in range(len(perm)) for j in range(i + 1, len(perm)))
        out.append(([finish[k] for k in perm], moved))
    return out


def _anonymizer(task: dict[str, Any]) -> str | None:
    return next((r for r, targets in task["optional"].items() if targets == ["@acquire"]), None)


def plan(task: dict[str, Any], constraints: list[Any]) -> tuple[list[str] | None, dict[str, Any]]:
    """最小改动规划。返回 (计划或 None, 信息)；信息含可用/不可用约束数与改动数。"""
    norms = [n for n in (normalize_constraint(c, task) for c in constraints) if n is not None]
    info: dict[str, Any] = {"usable_constraints": len(norms), "unusable_constraints": len(constraints) - len(norms)}
    stages = task["stages"]
    defaults = [s["default"] for s in stages]
    anonymizer = _anonymizer(task)
    best: tuple[tuple[Any, ...], list[str]] | None = None
    for assignment in itertools.product(*[s["alternatives"] for s in stages]):
        swaps = sum(a != d for a, d in zip(assignment, defaults))
        for finish, moved in _finish_orders(task["finish"]):
            for anon in ((False, True) if anonymizer else (False,)):
                candidate = list(assignment) + finish
                if anon:
                    candidate = candidate[:1] + [anonymizer] + candidate[1:]
                candidate, inserted = _close_precedence(candidate, norms, task["optional"])
                trace = execute(task, candidate)
                if not trace["completed"] or any(violated(n, trace) for n in norms):
                    continue
                key = (swaps + moved + int(anon) + inserted, trace["cost"], trace["minutes"], tuple(candidate))
                if best is None or key < best[0]:
                    best = (key, candidate)
    if best is None:
        info["changes"] = None
        return None, info
    info["changes"] = best[0][0]
    return best[1], info


def default_plan(task: dict[str, Any]) -> list[str]:
    return [s["default"] for s in task["stages"]] + list(task["finish"])


def canonical_insert(task: dict[str, Any], base: list[str], extras: list[str]) -> list[str]:
    """按规范位置插入可选步骤（生成器采样目标计划用）；目标不在计划中则跳过。"""
    out = list(base)
    for role in extras:
        targets = task["optional"][role]
        if targets == ["@acquire"]:
            out = out[:1] + [role] + out[1:]
            continue
        present = [t for t in targets if t in out]
        if present:
            out = _insert_before(out, role, min(present, key=out.index))
    return out
