"""CPU-only replay of complete E3 arms, with paired task-group intervals.

Never edits a training process, prediction, or frozen score. Missing arms remain
pending. Both sides use the existing E3 execution reader and the same field
projection; intervals condition on seed42, not on the training-seed population.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_deepseek_planner import paired

SPLITS = ("dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho")
ARMS = ("A3", "A4", "A2", "A1")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def align(rows: list[dict[str, Any]], predictions: list[dict[str, Any]]) -> list[str]:
    ids = [r["sample_id"] for r in rows]
    pred_ids = [r["sample_id"] for r in predictions]
    if len(set(ids)) != len(ids) or len(set(pred_ids)) != len(pred_ids) or set(ids) != set(pred_ids):
        raise ValueError("Missing, extra, or duplicate prediction IDs; refusing aggregate")
    by_id = {r["sample_id"]: r["raw"] for r in predictions}
    if any(not isinstance(v, str) for v in by_id.values()):
        raise ValueError("Prediction raw field must be a string")
    groups: dict[str, list[str]] = {}
    for row in rows:
        groups.setdefault(row["group_id"], []).append(row["variant"])
    if any(sorted(v) != ["explicit", "implicit", "none"] for v in groups.values()):
        raise ValueError("Cohort does not contain complete E/I/N groups")
    return [by_id[i] for i in ids]


def replay(rows: list[dict[str, Any]], raw: list[str]) -> list[dict[str, Any]]:
    # Lazy import: pure coverage/statistics tests do not require torch.
    import sub_e3_ablation as e3
    from eval_exec import record_outcome
    from trust_env import normalize_constraint

    result = []
    for row, text in zip(rows, raw, strict=True):
        items = e3.extract_constraints(text)
        coerced = [c for c in (e3.coerce_item(i) for i in (items or [])) if c is not None]
        usable = [c for c in coerced if normalize_constraint(c, row["task"]) is not None]
        valid = items is not None and len(items) == len(coerced) == len(usable)
        outcome = record_outcome(row, {"constraints": usable})
        outcome["valid_faithful"] = valid and outcome["faithful_success"]
        outcome["valid_constraints"] = valid
        result.append(outcome)
    return result


def contrast(rows: list[dict[str, Any]], arm: list[dict[str, Any]], baseline: list[dict[str, Any]],
             reps: int = 10000) -> dict[str, Any]:
    if len(rows) != len(arm) or len(rows) != len(baseline):
        raise ValueError("Paired cohort lengths differ")
    for row, a, b in zip(rows, arm, baseline, strict=True):
        expected = tuple(row[k] for k in ("sample_id", "group_id", "variant"))
        if any(tuple(o[k] for k in ("sample_id", "group_id", "variant")) != expected for o in (a, b)):
            raise ValueError("Paired row identities differ")
    result = {}
    for cohort in ("constrained", "explicit", "implicit", "none"):
        indices = [i for i, r in enumerate(rows) if (
            r["variant"] != "none" if cohort == "constrained" else r["variant"] == cohort)]
        if not indices:
            raise ValueError(f"Empty cohort: {cohort}")
        cells = {}
        for name, outcomes in (("arm", arm), ("baseline", baseline)):
            cells[name] = {k: sum(bool(outcomes[i][k]) for i in indices) / len(indices) for k in (
                "faithful_success", "valid_faithful", "safe_success", "valid_constraints",
                "deviates_from_default")}
        cells["paired_arm_minus_baseline"] = {key: paired(
            [rows[i]["group_id"] for i in indices], [arm[i][key] for i in indices],
            [baseline[i][key] for i in indices], reps=reps) for key in (
                "faithful_success", "valid_faithful", "safe_success")}
        result[cohort] = cells
    return result


def audit_arm(root: Path, arm: str, reps: int) -> dict[str, Any]:
    import sub_e3_ablation as e3

    out = root / "outputs/submission" / f"e3_{arm}"
    metric_path = out / "metrics.json"
    metrics = json.loads(metric_path.read_text(encoding="utf-8"))
    if (metrics["arm"] != arm or metrics["seed"] != 42 or metrics["precision"] != "bf16"
            or metrics["protocol_revision"] != "20261125-arm-prompt-and-score-parity"):
        raise ValueError("Unexpected arm, seed, precision, or protocol revision")
    config = metrics["config"]
    resolve = lambda p: Path(p) if Path(p).is_absolute() else root / p
    data = resolve(config["data_dir"])
    baseline = resolve(config["baseline_run"]) / "trained_predictions"
    source = root / "src/sub_e3_ablation.py"
    if sha(source) != metrics["code_sha256"] or sha(data / "train.jsonl") != metrics["data_sha256"]:
        raise ValueError("Run source or training data hash mismatch")
    if metrics["budget"]["dropped"] or metrics["budget"]["examples"] != metrics["train_rows"]:
        raise ValueError("Run changed the training cohort")
    result: dict[str, Any] = {"seed": metrics["seed"], "budget": metrics["budget"],
        "elapsed_s_includes_eval": metrics["elapsed_s"], "source_sha256": metrics["code_sha256"],
        "metrics_sha256": sha(metric_path), "splits": {}}
    for split in SPLITS:
        paths = {"data": data / f"{split}.jsonl", "baseline": baseline / f"{split}.jsonl",
                 "arm": out / "predictions" / f"{split}.jsonl"}
        rows = read_jsonl(paths["data"])
        raw = {k: align(rows, read_jsonl(paths[k])) for k in ("arm", "baseline")}
        if sha(paths["baseline"]) != metrics["baseline_prediction_sha256"][split]:
            raise ValueError("Baseline hash differs from the run")
        replayed = {k: replay(rows, raw[k]) for k in raw}
        cell = contrast(rows, replayed["arm"], replayed["baseline"], reps)
        for name, saved in (("arm", metrics["splits"][split]), (
                "baseline", metrics["splits"][split]["baseline_same_projection"])):
            mapping = {"faithful_constrained": ("constrained", "faithful_success"),
                "valid_faithful_constrained": ("constrained", "valid_faithful"),
                "safe_constrained": ("constrained", "safe_success"),
                "none_faithful": ("none", "faithful_success"),
                "none_valid_faithful": ("none", "valid_faithful")}
            for key, (cohort, replay_key) in mapping.items():
                if not math.isclose(saved["downstream"][key], cell[cohort][name][replay_key], abs_tol=1e-12):
                    raise ValueError(f"Execution replay mismatch: {arm}/{split}/{name}/{key}")
            # Record axes reuse exactly the same projection as the completed run.
            record = e3.record_metrics(rows, raw[name], arm)
            if record["record"] != saved["record"] or record["arm_contract_parse_rate"] != saved["arm_contract_parse_rate"]:
                raise ValueError(f"Record replay mismatch: {arm}/{split}/{name}")
            cell[name + "_record_same_projection"] = record
        cell["input_sha256"] = {k: sha(p) for k, p in paths.items()}
        result["splits"][split] = cell
    return result


def process_identity(pid: int) -> str | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return fields[19] if fields[0] != "Z" else None
    except FileNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--watch-queue-pid", type=int)
    parser.add_argument("--reps", type=int, default=10000)
    args = parser.parse_args()
    if args.reps < 100:
        raise ValueError("At least 100 bootstrap replicates required")
    if args.watch_queue_pid:
        cmd = Path(f"/proc/{args.watch_queue_pid}/cmdline").read_bytes().split(b"\x00")
        if not any(x.endswith(b"/run_e2_informed_then_e3.sh") for x in cmd):
            raise ValueError("Watch PID is not the expected E3 supervisor")
    identity = process_identity(args.watch_queue_pid) if args.watch_queue_pid else None
    output = args.out or args.root / "outputs/submission/e3_analysis/paired_replay.json"
    completed: dict[str, Any] = {}
    hashes = {}
    while True:
        for arm in ARMS:
            path = args.root / "outputs/submission" / f"e3_{arm}" / "metrics.json"
            if not path.exists():
                continue
            current = sha(path)
            if arm in hashes and hashes[arm] != current:
                raise ValueError(f"Completed metrics changed during observation: {arm}")
            if arm not in completed:
                completed[arm] = audit_arm(args.root, arm, args.reps)
                hashes[arm] = current
                print(json.dumps({"event": "audited_arm", "arm": arm}), flush=True)
        pending = [arm for arm in ARMS if arm not in completed]
        alive = bool(identity and process_identity(args.watch_queue_pid) == identity)
        result = {"status": "pending" if not completed else "partial" if pending else "complete",
            "checked_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "arms": completed,
            "pending_arms": pending, "queue_alive": alive, "analysis_sha256": sha(Path(__file__)),
            "statistics_sha256": sha(Path(__file__).with_name("analyse_deepseek_planner.py")),
            "interpretation": "Exploratory pointwise task-group bootstrap; E/I siblings stay together. Conditional on seed42, not seed-population CIs; no multiplicity-adjusted significance or equivalence claim. Execution validity here checks usable type/params, not all record fields. Both sides use the frozen E3 lenient execution reader; frozen v5 scores are unchanged. Elapsed time includes evaluation; token counts do not imply matched compute."}
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
        os.replace(temporary, output)
        if not pending or not alive:
            print(json.dumps({"event": "finished_observing", "status": result["status"], "pending": pending}), flush=True)
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
