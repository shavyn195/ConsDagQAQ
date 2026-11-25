"""Replay the frozen public-input E2 control on CPU, without model calls.

N plan deviations are not constraint-extraction false alarms. Keep invalid
plans, valid default plans and valid changed plans separate. Never overwrite
the run, its predictions, its metrics, or an existing audit output.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def require_aligned(rows: list[dict[str, Any]], records: list[dict[str, Any]]) -> None:
    ids = [row["sample_id"] for row in rows]
    if len(set(ids)) != len(ids) or ids != [r["sample_id"] for r in records]:
        raise ValueError("Missing, reordered, extra or duplicate records")


def none_summary(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [o for o in outcomes if o["variant"] == "none"]
    if not rows:
        raise ValueError("No N cohort")
    counts = Counter()
    for row in rows:
        if not row["planned"]:
            if row["faithful_success"] or row["deviates_from_default"] is not None:
                raise ValueError("Invalid plans must not be counted as known deviations")
            counts["invalid_plan"] += 1
        else:
            changed = row["deviates_from_default"]
            if type(changed) is not bool or row["faithful_success"] != (not changed):
                raise ValueError("N faithful must equal valid and unchanged")
            counts["valid_changed" if changed else "valid_default"] += 1
    n = len(rows)
    return {"n": n, "counts": {k: counts[k] for k in ("invalid_plan", "valid_default", "valid_changed")},
            "faithful_rate": counts["valid_default"] / n,
            "invalid_plan_rate": counts["invalid_plan"] / n,
            "valid_deviation_rate": counts["valid_changed"] / n,
            "note": "All rates use all N rows. Plan deviation is not compiler false-alarm rate."}


def replay(row: dict[str, Any], raw: str, mono: Any) -> dict[str, Any]:
    # The frozen parser sees only public task information, never gold or witness.
    fixed = mono.parse_plan(raw, {"task": row["task"]})
    result = {k: row[k] for k in ("sample_id", "group_id", "variant")}
    if fixed is None:
        return dict(result, planned=False, completed=False, safe_success=False,
                    faithful_success=False, extra_changes=None,
                    deviates_from_default=None, violated_types=[])
    gold = row["gold"]["constraints"]
    checked = mono.check(row["task"], fixed, gold)
    _, info = mono.symbolic_plan(row["task"], gold)
    changed = fixed != mono.default_plan(row["task"])
    extra = mono.plan_change_count(row["task"], fixed) - info["changes"] if checked["safe_success"] else None
    return dict(result, planned=True, completed=bool(checked["completed"]),
                safe_success=bool(checked["safe_success"]),
                faithful_success=bool(checked["safe_success"] and (extra == 0 if gold else not changed)),
                extra_changes=extra, deviates_from_default=changed,
                violated_types=sorted({gold[i]["type"] for i in checked["violations"]}))


def audit(args: argparse.Namespace) -> dict[str, Any]:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    protocol_path = args.run_dir / "public_protocol.json"
    metric_path = args.run_dir / "metrics.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    metrics = json.loads(metric_path.read_text(encoding="utf-8"))
    baseline_path = args.pipeline_run / "metrics.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_source = args.source_dir / "sub_e2_monolithic.py"
    if (protocol["seed"] != 42 or metrics["seed"] != 42 or metrics["precision"] != "bf16"
            or metrics["prompt_mode"] != "public_contract" or baseline["config"]["seed"] != 42):
        raise ValueError("Unexpected arm configuration")
    if sha(protocol_path) != metrics["public_protocol_sha256"]:
        raise ValueError("Public protocol changed")
    if sha(baseline_source) != metrics["code_sha256"]:
        raise ValueError("Monolithic control source changed")
    for name, expected in protocol["source_sha256"].items():
        if sha(args.source_dir / name) != expected:
            raise ValueError(f"Public-control source changed: {name}")
    hashes = {}
    for split, expected in protocol["data_sha256"].items():
        value = sha(args.data_dir / f"{split}.jsonl")
        if not (value == expected == metrics["data_sha256"][split] == baseline["data_sha256"][split]):
            raise ValueError(f"Dataset hashes differ: {split}")
        hashes[split] = value
    sys.path.insert(0, str(args.source_dir))
    import torch
    torch.set_num_threads(1)
    import sub_e2_monolithic as mono
    token_audit = json.loads(args.token_budget.read_text(encoding="utf-8"))
    tokens = token_audit["arms"]["public_monolithic"]["planned_three_epoch_tokens"]
    if (metrics["budget"]["steps"] != 9000 or metrics["budget"]["dropped"] != 0
            or metrics["budget"]["tokens"] != {"prompt": tokens["prompt"],
                                                       "completion": tokens["supervised_target_including_eos"]}):
        raise ValueError("Observed training budget differs from the audited recipe")
    result: dict[str, Any] = {"revision": "20261125-e2-public-replay-v2",
        "created_utc": datetime.now(timezone.utc).isoformat(), "data_hashes": hashes,
        "splits": {}, "file_hashes": {"metrics.json": sha(metric_path),
        "public_protocol.json": sha(protocol_path), "baseline_metrics": sha(baseline_path),
        "training_token_budget": sha(args.token_budget), "audit_script": sha(Path(__file__))}}
    all_mono, all_pipe = [], []
    for split in mono.SPLITS:
        rows = load(args.data_dir / f"{split}.jsonl")
        raw_path = args.run_dir / "raw_predictions" / f"{split}.jsonl"
        saved_path = args.run_dir / "predictions" / f"{split}.jsonl"
        pipe_path = args.pipeline_run / "trained_predictions" / f"{split}.jsonl"
        raw, saved, pipe_raw = load(raw_path), load(saved_path), load(pipe_path)
        for records in (raw, saved, pipe_raw):
            require_aligned(rows, records)
        groups: dict[str, list[str]] = {}
        for row in rows:
            groups.setdefault(row["group_id"], []).append(row["variant"])
        if any(sorted(v) != ["explicit", "implicit", "none"] for v in groups.values()):
            raise ValueError("Incomplete E/I/N task group")
        outcomes = [replay(row, p["raw"], mono) for row, p in zip(rows, raw, strict=True)]
        for new, old in zip(outcomes, saved, strict=True):
            if any(new[k] != value for k, value in old.items()):
                raise ValueError(f"Saved outcome differs: {old['sample_id']}")
        pipeline = mono.pipeline_outcomes(args.data_dir, split, args.pipeline_run)
        require_aligned(rows, pipeline)
        constrained = [o for o in outcomes if o["variant"] != "none"]
        pipe = [o for o in pipeline if o["variant"] != "none"]
        paired = mono.paired_bootstrap(constrained, pipe)
        expected = metrics["paired_vs_pipeline"][split]
        if paired != {k: expected[k] for k in paired}:
            raise ValueError(f"Paired bootstrap does not reproduce: {split}")
        rate = lambda cohort, key: sum(bool(o[key]) for o in cohort) / len(cohort)
        failures = Counter()
        for outcome in constrained:
            if outcome["faithful_success"]:
                continue
            if not outcome["planned"]:
                failures["invalid_plan"] += 1
            elif not outcome["completed"]:
                failures["incomplete_plan"] += 1
            elif not outcome["safe_success"]:
                failures["constraint_violation"] += 1
            else:
                failures["safe_extra_changes"] += 1
        cell = {"records": len(rows), "groups": len(groups), "constrained_records": len(constrained),
            "valid_plan_rate": rate(outcomes, "planned"),
            "faithful_constrained": rate(constrained, "faithful_success"),
            "safe_success_constrained": rate(constrained, "safe_success"),
            "pipeline_faithful_constrained": rate(pipe, "faithful_success"),
            "none": none_summary(outcomes), "constrained_failure_counts": dict(failures),
            "paired_monolithic_minus_pipeline": paired, "replay_matches_saved_outcomes": True}
        for key in ("faithful_constrained",):
            if not math.isclose(cell[key], metrics["splits"][split][key], abs_tol=1e-12):
                raise ValueError("Saved summary differs")
        if not math.isclose(cell["none"]["faithful_rate"], metrics["splits"][split]["none_faithful"], abs_tol=1e-12):
            raise ValueError("N faithful summary differs")
        result["splits"][split] = cell
        for label, path in (("predictions", saved_path), ("raw_predictions", raw_path), ("pipeline", pipe_path)):
            result["file_hashes"][f"{label}/{split}.jsonl"] = sha(path)
        all_mono.extend(constrained)
        all_pipe.extend(pipe)
    result["overall_paired_monolithic_minus_pipeline"] = mono.paired_bootstrap(all_mono, all_pipe)
    if result["overall_paired_monolithic_minus_pipeline"] != metrics["paired_vs_pipeline"]["overall"]:
        raise ValueError("Overall paired bootstrap differs")
    result["cost"] = {"steps": metrics["budget"]["steps"], "prompt_tokens": tokens["prompt"],
        "completion_tokens": tokens["supervised_target_including_eos"], "elapsed_s": metrics["elapsed_s"],
        "evaluation": {s: {k: metrics["splits"][s][k] for k in ("gen_tokens", "elapsed_s")} for s in mono.SPLITS}}
    result["coverage_note"] = {"max_seq_len": protocol["max_seq_len"],
        "test_struct_ho_rows_over_max_seq_len": protocol["coverage"]["test_struct_ho"]["over_limit"],
        "eval_context_limit": protocol["evaluation_context_limit"], "training_examples_dropped": 0,
        "length_definition": "Prompt plus gold target, not input-only length; evaluation is untruncated."}
    result["limits"] = ["Exploratory fair-input correction, seed42 only; four pointwise CIs, no multiplicity correction.",
        "Task-group bootstrap conditions on fixed weights, not the training-seed population.",
        "Same rows and updates are not matched compute. Targets and source/target token counts differ.",
        "elapsed_s includes initialization, training and evaluation. No speed, price or FLOP advantage inferred.",
        "No compiler false-alarm rate is defined for a model that outputs plans rather than constraints."]
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source-dir", "data-dir", "run-dir", "pipeline-run", "token-budget", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise ValueError("Existing audit preserved; use a new output path")
    result = audit(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"out": str(args.out), "replay_matches_saved_outcomes": True}))


if __name__ == "__main__":
    main()
