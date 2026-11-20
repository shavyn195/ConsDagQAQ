"""Schema and deterministic checks for the synthetic compiler pilot."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

VARIANTS = {"explicit", "implicit", "none"}
CONSTRAINT_TYPES = {"budget", "deadline", "privacy", "tool_auth", "order"}
SEVERITIES = {"high", "medium", "low"}


def _constraint_signature(items: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            item["type"],
            item["severity"],
            tuple(item["scope"]),
            tuple(sorted(item["params"].items())),
        )
        for item in items
    )


def check_witness(row: dict[str, Any]) -> list[str]:
    """Check that the stored witness is a topological, constraint-satisfying plan."""
    errors: list[str] = []
    nodes = row.get("graph", {}).get("nodes", [])
    edges = row.get("graph", {}).get("edges", [])
    node_by_id = {node.get("id"): node for node in nodes}
    if len(node_by_id) != len(nodes) or None in node_by_id:
        return ["graph node ids must be present and unique"]

    witness = row.get("witness", [])
    if len(witness) != len(nodes) or set(witness) != set(node_by_id):
        errors.append("witness must contain every graph node exactly once")
        return errors
    if len(set(witness)) != len(witness):
        errors.append("witness contains duplicate nodes")
        return errors

    position = {node_id: i for i, node_id in enumerate(witness)}
    adjacency: dict[Any, list[Any]] = defaultdict(list)
    indegree = {node_id: 0 for node_id in node_by_id}
    for edge in edges:
        source, target = edge.get("from"), edge.get("to")
        if source not in node_by_id or target not in node_by_id:
            errors.append("graph edge references an unknown node")
            continue
        adjacency[source].append(target)
        indegree[target] += 1
        if position[source] >= position[target]:
            errors.append("witness violates a DAG dependency")
    queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
    visited = 0
    while queue:
        node_id = queue.popleft()
        visited += 1
        for target in adjacency[node_id]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited != len(nodes):
        errors.append("graph contains a cycle")

    ordered_nodes = [node_by_id[node_id] for node_id in witness]
    for constraint in row.get("gold", {}).get("constraints", []):
        kind, params = constraint["type"], constraint["params"]
        roles = [node["role"] for node in ordered_nodes]
        if kind == "budget":
            total = sum(float(node.get("cost_cny", 0)) for node in ordered_nodes)
            if total > float(params["max_total_cost_cny"]):
                errors.append("witness exceeds the budget")
        elif kind == "deadline":
            total = sum(float(node.get("duration_min", 0)) for node in ordered_nodes)
            if total > float(params["max_duration_min"]):
                errors.append("witness misses the deadline")
        elif kind == "privacy":
            protected = set(params["protected_data_classes"])
            forbidden = set(params["forbidden_recipients"])
            for node in ordered_nodes:
                if node.get("recipient") in forbidden and protected.intersection(node.get("data_classes", [])):
                    errors.append("witness sends protected data to a forbidden recipient")
                    break
        elif kind == "tool_auth":
            approval_role = params["approval_role"]
            required_role = params["required_role"]
            approval_positions = [
                i for i, node in enumerate(ordered_nodes)
                if node["role"] == approval_role and node.get("approval_record") is True
            ]
            required_positions = [i for i, role in enumerate(roles) if role == required_role]
            if not required_positions or not approval_positions or max(approval_positions) >= min(required_positions):
                errors.append("witness uses a protected tool before recorded approval")
        elif kind == "order":
            before = params["before_role"]
            after = params["after_role"]
            before_positions = [i for i, role in enumerate(roles) if role == before]
            after_positions = [i for i, role in enumerate(roles) if role == after]
            if not before_positions or not after_positions or max(before_positions) >= min(after_positions):
                errors.append("witness violates the required role order")
    return errors


def validate_rows(rows: list[dict[str, Any]]) -> list[str]:
    """Validate record schema, evidence spans, pair integrity, and witness feasibility."""
    errors: list[str] = []
    required = {
        "sample_id", "group_id", "split", "variant", "task_goal", "query",
        "available_roles", "compiler_input", "graph", "witness", "gold",
    }
    by_group: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_samples: set[str] = set()

    for index, row in enumerate(rows):
        prefix = f"row {index}"
        missing = required - set(row)
        if missing:
            errors.append(f"{prefix} missing fields: {sorted(missing)}")
            continue
        if row["sample_id"] in seen_samples:
            errors.append(f"{prefix} duplicate sample_id")
        seen_samples.add(row["sample_id"])
        by_group[row["group_id"]].append(row)

        if row["variant"] not in VARIANTS:
            errors.append(f"{prefix} has unknown variant")
        gold = row["gold"]
        if gold.get("query_state") != row["variant"]:
            errors.append(f"{prefix} query_state does not match variant")
        if not isinstance(gold.get("abstain"), bool):
            errors.append(f"{prefix} abstain must be boolean")
        constraints = gold.get("constraints")
        if not isinstance(constraints, list):
            errors.append(f"{prefix} constraints must be a list")
            continue
        if row["variant"] == "none" and constraints:
            errors.append(f"{prefix} none variant must have an empty constraint list")
        if row["variant"] != "none" and not constraints:
            errors.append(f"{prefix} constrained variant must have at least one constraint")

        role_set = set(row["available_roles"])
        for constraint in constraints:
            for field in ("type", "description", "evidence_span", "state", "confidence", "severity", "scope", "params"):
                if field not in constraint:
                    errors.append(f"{prefix} constraint missing {field}")
            if constraint.get("type") not in CONSTRAINT_TYPES:
                errors.append(f"{prefix} constraint has unknown type")
            if constraint.get("state") != row["variant"]:
                errors.append(f"{prefix} constraint state disagrees with query state")
            if constraint.get("severity") not in SEVERITIES:
                errors.append(f"{prefix} constraint has unknown severity")
            confidence = constraint.get("confidence")
            if not isinstance(confidence, (float, int)) or not 0.0 <= confidence <= 1.0:
                errors.append(f"{prefix} confidence must be in [0, 1]")
            span = constraint.get("evidence_span")
            if not isinstance(span, str) or not span or span not in row["query"]:
                errors.append(f"{prefix} evidence_span must be a nonempty exact query substring")
            if not set(constraint.get("scope", [])) <= role_set:
                errors.append(f"{prefix} scope refers to a role outside available_roles")

        expected_input = {
            "query": row["query"],
            "available_roles": row["available_roles"],
        }
        if row["compiler_input"] != expected_input:
            errors.append(f"{prefix} compiler_input does not match query and role vocabulary")
        errors.extend(f"{prefix}: {error}" for error in check_witness(row))

    for group_id, group in by_group.items():
        if len(group) != 3 or {row["variant"] for row in group} != VARIANTS:
            errors.append(f"group {group_id} must contain exactly one E/I/N row")
            continue
        if len({row["split"] for row in group}) != 1:
            errors.append(f"group {group_id} crosses dataset splits")
        explicit = next(row for row in group if row["variant"] == "explicit")
        implicit = next(row for row in group if row["variant"] == "implicit")
        none = next(row for row in group if row["variant"] == "none")
        for field in ("task_goal", "available_roles", "graph", "witness"):
            if explicit[field] != implicit[field] or explicit[field] != none[field]:
                errors.append(f"group {group_id} changes {field} across E/I/N")
        if _constraint_signature(explicit["gold"]["constraints"]) != _constraint_signature(implicit["gold"]["constraints"]):
            errors.append(f"group {group_id} E/I gold constraint semantics differ")
        if explicit["query"] == implicit["query"]:
            errors.append(f"group {group_id} E/I query renderings must differ")
        if none["gold"]["constraints"]:
            errors.append(f"group {group_id} N variant must have no constraints")
    return errors
