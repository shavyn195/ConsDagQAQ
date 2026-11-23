"""Audit frozen v5 coverage, provenance, metric denominators, and metadata interventions."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path

from eval_exec import record_outcome
from rescore_v4_side import aligned, outcome
from run_e1 import constraint_key, core_key, load_jsonl, strict_parse
from trust_env import normalize_constraint
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
SPLITS = ("dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho")


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def executable_key(constraint: dict, task: dict) -> str:
    """Only equivalence under this executable world, not general semantic truth."""
    norm = normalize_constraint(constraint, task)
    if norm is None:
        return "UNUSABLE:" + json.dumps(constraint, sort_keys=True)
    if norm["type"] in ("tool_auth", "order"):
        norm["type"] = "conditional_precedence"
    norm = {k: sorted(v) if isinstance(v, set) else v for k, v in norm.items()}
    return json.dumps(norm, sort_keys=True)


def main() -> None:
    source = ROOT / "data/processed_v5"
    rows = {s: load_jsonl(source / f"{s}.jsonl") for s in SPLITS}
    expected = json.loads((source / "generation_report.json").read_text())["sha256"]
    actual = {s: digest(source / f"{s}.jsonl") for s in expected}
    if actual != expected:
        raise ValueError("Frozen source dataset hash mismatch")
    report = {"dataset_sha256": actual, "coverage": {}, "run_config_comparison": {},
              "joint_metrics": {}, "gold_metadata_intervention": {},
              "claims": ["Behavioral faithful success does not certify the full compilation record.",
                         "Metadata interventions are oracle diagnostics, not trained model improvements."]}
    arms = {
        "1.7B-seed42": ROOT / "outputs/e1/Qwen3-1.7B-v5-seed42/trained_predictions",
        "1.7B-seed43": ROOT / "outputs/e1/Qwen3-1.7B-v5-seed43/trained_predictions",
        "4B-seed42": ROOT / "outputs/e1/Qwen3-4B-v5-seed42/trained_predictions",
        "DeepSeek-ten-shot": ROOT / "outputs/e1_v5_side/deepseek-v4-pro-0813-few",
        "QwenMax-zero": ROOT / "outputs/e1_v5_side/qwen-max-zero",
        "QwenMax-ten-shot": ROOT / "outputs/e1_v5_side/qwen-max-few",
    }
    for arm, folder in arms.items():
        report["coverage"][arm] = {}
        for subset in SPLITS:
            path = folder / f"{subset}.jsonl"
            preds = load_jsonl(path) if path.exists() else []
            ids = [p["sample_id"] for p in preds]
            want = {r["sample_id"] for r in rows[subset]}
            report["coverage"][arm][subset] = {
                "expected": len(want), "present": len(preds), "duplicate_ids": len(ids) - len(set(ids)),
                "missing_ids": sorted(want - set(ids)), "unexpected_ids": sorted(set(ids) - want),
                "prediction_sha256": digest(path) if path.exists() else None}
    configs = []
    for seed in (42, 43):
        path = ROOT / f"outputs/e1/Qwen3-1.7B-v5-seed{seed}/metrics.json"
        m = json.loads(path.read_text())
        configs.append(m)
        report["run_config_comparison"][str(seed)] = {
            "metrics_sha256": digest(path), "config": m["config"],
            "source_code_sha256_recorded": m["code_sha256"], "data_sha256": m["data_sha256"]}
    report["run_config_comparison"]["differences"] = {
        k: [configs[0]["config"].get(k), configs[1]["config"].get(k)]
        for k in sorted(set(configs[0]["config"]) | set(configs[1]["config"]))
        if configs[0]["config"].get(k) != configs[1]["config"].get(k)}
    for arm in ("4B-seed42", "DeepSeek-ten-shot"):
        cohort = rows["test_struct_ho"]
        raw = aligned(cohort, load_jsonl(arms[arm] / "test_struct_ho.jsonl"))
        count = Counter()
        examples = []
        for row, text in zip(cohort, raw):
            if not row["gold"]["constraints"]:
                continue
            parsed = strict_parse(text)
            got = parsed["constraints"] if parsed else []
            gold = row["gold"]["constraints"]
            strict = bool(parsed and parsed["query_state"] == row["variant"] and
                          Counter(map(constraint_key, got)) == Counter(map(constraint_key, gold)))
            core = bool(parsed and Counter(map(core_key, got)) == Counter(map(core_key, gold)))
            world_equivalent = bool(parsed and
                Counter(executable_key(c, row["task"]) for c in got) ==
                Counter(executable_key(c, row["task"]) for c in gold))
            o = outcome(row, text)
            count["constrained_records"] += 1
            for key, value in {"faithful": o["faithful_success"], "strict_record": strict,
                               "core_record": core, "evidence_record": o["exact_with_evidence"],
                               "world_predicate_record": world_equivalent,
                               "core_wrong_but_same_world_predicates": not core and world_equivalent,
                               "faithful_but_strict_wrong": o["faithful_success"] and not strict,
                               "faithful_but_core_wrong": o["faithful_success"] and not core}.items():
                count[key] += int(value)
            if o["faithful_success"] and not strict and len(examples) < 5:
                examples.append({"sample_id": row["sample_id"], "gold": row["gold"], "predicted": parsed})
        report["joint_metrics"][arm] = {"subset": "test_struct_ho", "counts": dict(count), "examples": examples}

    # Edit only one metadata field at a time on the frozen development panel.
    panel = load_jsonl(ROOT / "data/diagnostic_v5_binding_20261123/original.jsonl")
    panel = [r for r in panel if r["gold"]["constraints"]]
    for field in ("scope", "state", "severity", "evidence_span"):
        faithful = 0
        for row in panel:
            corrupted = copy.deepcopy(row["gold"])
            for c in corrupted["constraints"]:
                c[field] = {"scope": ["role:unregistered"],
                            "state": "implicit" if c["state"] == "explicit" else "explicit",
                            "severity": "medium" if c["severity"] == "high" else "high",
                            "evidence_span": "This evidence does not occur in the request."}[field]
            if strict_parse(json.dumps(corrupted)) is None:
                raise ValueError("Metadata intervention accidentally invalidated the JSON schema")
            faithful += int(record_outcome(row, corrupted)["faithful_success"])
        report["gold_metadata_intervention"][field] = {"n": len(panel), "faithful": faithful}
    output = ROOT / "outputs/v5_analysis/measurement_audit_20261123.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"config_differences": report["run_config_comparison"]["differences"],
                      "joint_counts": {a: v["counts"] for a, v in report["joint_metrics"].items()},
                      "metadata_intervention": report["gold_metadata_intervention"]}, indent=2))


if __name__ == "__main__":
    main()
