"""Fail-closed execution metrics for v6; the legacy v5 evaluator is untouched."""

from __future__ import annotations

from typing import Any

from eval_exec import record_outcome as legacy_record_outcome
from eval_exec import summarise as legacy_summarise
from run_e1 import strict_parse


def record_outcome_v6(row: dict[str, Any], raw: str) -> dict[str, Any]:
    parsed = strict_parse(raw)
    outcome = legacy_record_outcome(row, parsed)
    outcome["compile_valid"] = parsed is not None
    if parsed is None:
        outcome["runtime_fallback_completed"] = bool(outcome["completed"])
        outcome["runtime_fallback_safe_success"] = bool(outcome["safe_success"])
        outcome.update({"planned": False, "completed": False, "safe_success": False,
                        "faithful_success": False, "unusable_constraints": None})
    else:
        outcome["runtime_fallback_completed"] = None
        outcome["runtime_fallback_safe_success"] = None
        if row["variant"] == "none" and (parsed["query_state"] != "none" or parsed["constraints"]):
            outcome["faithful_success"] = False
    return outcome


def evaluate_v6(rows: list[dict[str, Any]], raw_outputs: list[str]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if len(rows) != len(raw_outputs):
        raise ValueError(f"rows={len(rows)} raw={len(raw_outputs)}")
    outcomes = [record_outcome_v6(row, raw) for row, raw in zip(rows, raw_outputs)]
    summary = legacy_summarise(outcomes, rows)
    summary["metrics_version"] = "e1_exec_v6_fail_closed"
    summary["parse_rate"] = round(sum(o["compile_valid"] for o in outcomes) / len(outcomes), 4) if outcomes else None
    summary["runtime_fallback_completion"] = round(
        sum(bool(o["runtime_fallback_completed"]) for o in outcomes if o["malformed"])
        / max(sum(o["malformed"] for o in outcomes), 1), 4
    ) if any(o["malformed"] for o in outcomes) else None
    return summary, outcomes


def n_error_components(rows: list[dict[str, Any]], raw_outputs: list[str]) -> dict[str, Any]:
    if len(rows) != len(raw_outputs):
        raise ValueError(f"rows={len(rows)} raw={len(raw_outputs)}")
    none_rows = [(row, raw) for row, raw in zip(rows, raw_outputs) if row["variant"] == "none"]
    counts = {"n": len(none_rows), "parse_failure": 0, "nonempty_constraints": 0, "query_state_error": 0}
    for row, raw in none_rows:
        parsed = strict_parse(raw)
        if parsed is None:
            counts["parse_failure"] += 1
            continue
        counts["nonempty_constraints"] += int(bool(parsed["constraints"]))
        counts["query_state_error"] += int(parsed["query_state"] != "none")
    n = counts["n"]
    counts["any_contract_alarm"] = counts["parse_failure"] + sum(
        1 for row, raw in none_rows
        if (parsed := strict_parse(raw)) is not None
        and (bool(parsed["constraints"]) or parsed["query_state"] != "none")
    )
    counts["rates"] = {
        key: round(counts[key] / n, 4) if n else None
        for key in ("parse_failure", "nonempty_constraints", "query_state_error", "any_contract_alarm")
    }
    return counts


def n_error_subtypes(rows: list[dict[str, Any]], raw_outputs: list[str]) -> dict[str, Any]:
    """Attribute broad N-contract alarms to each distinct synthetic subtype on a row."""
    if len(rows) != len(raw_outputs):
        raise ValueError(f"rows={len(rows)} raw={len(raw_outputs)}")
    counts: dict[str, dict[str, int]] = {}
    for row, raw in zip(rows, raw_outputs):
        if row["variant"] != "none":
            continue
        subtypes = {item for item in row.get("near_miss_subtypes", []) if item}
        if not subtypes:
            continue
        parsed = strict_parse(raw)
        errors = {
            "parse_failure": parsed is None,
            "nonempty_constraints": bool(parsed and parsed["constraints"]),
            "query_state_error": bool(parsed and parsed["query_state"] != "none"),
        }
        for subtype in subtypes:
            stat = counts.setdefault(subtype, {"n": 0, **{key: 0 for key in errors}, "any_contract_alarm": 0})
            stat["n"] += 1
            for key, failed in errors.items():
                stat[key] += int(failed)
            stat["any_contract_alarm"] += int(any(errors.values()))
    return {
        subtype: {
            **stat,
            "rates": {
                key: round(stat[key] / stat["n"], 4) if stat["n"] else None
                for key in ("parse_failure", "nonempty_constraints", "query_state_error", "any_contract_alarm")
            },
        }
        for subtype, stat in sorted(counts.items())
    }


def aligned_raw(rows: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> list[str]:
    by_id = {item["sample_id"]: item["raw"] for item in predictions}
    ids = [row["sample_id"] for row in rows]
    if len(set(ids)) != len(ids) or len(by_id) != len(predictions) or set(ids) != set(by_id):
        raise ValueError("Missing, duplicate or unexpected sample IDs")
    return [by_id[sid] for sid in ids]

