"""Rescore complete v6 prediction caches with field and fail-closed execution metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any

from eval_exec_v6 import aligned_raw, evaluate_v6, n_error_components, n_error_subtypes
from run_e1 import chat_messages_v4, eval_subsets, load_jsonl, score

ROOT = Path(__file__).resolve().parents[1]
SIZES = ("0.6B", "1.7B", "4B")
SEEDS = (42, 43, 44)
PE_ARMS = ("deepseek-v4-pro-0813-few", "qwen-max-zero", "qwen-max-few")
H4_DIAGNOSTIC_ARM = "PE-deepseek-v4-pro-0813-few"
N_GATE_MAX_ALARM = 0.05
STRUCT_TRANSFER_MAX_DROP = 0.05
STRUCT_FAIL_MIN_DROP = 0.10


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_data_hashes(data_dir: Path, subsets: list[str]) -> dict[str, str]:
    return {name: file_sha256(data_dir / f"{name}.jsonl") for name in ["train", *subsets]}


def verified_science_run(run_dir: Path, data_dir: Path, subsets: list[str], seed: int,
                         expected_model: str) -> tuple[bool, str]:
    """Only admit runs finalized by the queue against these exact data bytes."""
    completion_path, provenance_path, metrics_path = (
        run_dir / "completion.json", run_dir / "provenance.json", run_dir / "metrics.json"
    )
    if not all(path.is_file() for path in (completion_path, provenance_path, metrics_path)):
        return False, "missing_completion_provenance_or_metrics"
    completion = json.loads(completion_path.read_text(encoding="utf-8"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    stable_keys = ("schema_version", "kind", "config", "data_sha256", "source_sha256",
                   "model_sha256", "environment", "gpu")
    if any(key not in provenance for key in stable_keys):
        return False, "incomplete_provenance"
    stable_payload = {key: provenance[key] for key in stable_keys}
    stable_fingerprint = hashlib.sha256(
        json.dumps(stable_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if provenance.get("schema_version") != 1 or provenance.get("kind") != "science":
        return False, "provenance_schema_or_kind_mismatch"
    if provenance.get("fingerprint") != stable_fingerprint:
        return False, "provenance_fingerprint_invalid"
    if completion.get("status") != "complete" or completion.get("kind") != "science":
        return False, "completion_not_science_complete"
    if completion.get("fingerprint") != provenance.get("fingerprint"):
        return False, "provenance_fingerprint_mismatch"
    if not isinstance(completion.get("fingerprint"), str) or not completion["fingerprint"]:
        return False, "missing_provenance_fingerprint"
    if completion.get("source_sha256") != provenance.get("source_sha256"):
        return False, "source_fingerprint_mismatch"
    expected_data = current_data_hashes(data_dir, subsets)
    if completion.get("data_sha256") != expected_data or provenance.get("data_sha256") != expected_data:
        return False, "data_fingerprint_mismatch"
    if metrics.get("data_sha256") != expected_data or metrics.get("seed") != seed:
        return False, "metrics_seed_or_data_mismatch"
    batch_size = {"Qwen3-0.6B": 48, "Qwen3-1.7B": 32, "Qwen3-4B": 16}[Path(expected_model).name]
    expected_config = {
        "model": expected_model,
        "data_dir": "data/processed_v6",
        "precision": "bf16",
        "seed": seed,
        "epochs": 3,
        "learning_rate": 2e-4,
        "lora_rank": 16,
        "lora_alpha": 32,
        "gradient_accumulation_steps": 4,
        "max_seq_len": 1280,
        "max_new_tokens": 384,
        "eval_batch_size": batch_size,
        "skip_zeroshot": seed != 42,
        "skip_train": False,
    }
    if any(provenance["config"].get(key) != value for key, value in expected_config.items()):
        return False, "registered_config_mismatch"
    if any(metrics.get("config", {}).get(key) != value for key, value in expected_config.items()):
        return False, "metrics_config_mismatch"
    if (completion.get("seed") != seed or completion.get("precision") != "bf16"
            or completion.get("model_path") != expected_model or metrics.get("model_path") != expected_model):
        return False, "completion_model_seed_or_precision_mismatch"
    required_sources = {
        "src/run_e1.py", "src/run_e1_v6.py", "src/eval_exec_v6.py", "src/dataset_v6_spec.py",
        "src/trust_env.py", "scripts/run_v6_queue.sh",
    }
    if not required_sources.issubset(provenance["source_sha256"]):
        return False, "incomplete_source_fingerprint"
    if any(not isinstance(value, str) or len(value) != 64
           for value in provenance["source_sha256"].values()):
        return False, "invalid_source_hash"
    for relative, digest in provenance["source_sha256"].items():
        source_path = (ROOT / relative).resolve()
        if ROOT.resolve() not in source_path.parents or not source_path.is_file():
            return False, f"source_missing:{relative}"
        if file_sha256(source_path) != digest:
            return False, f"source_hash_mismatch:{relative}"
    if not isinstance(provenance["model_sha256"], dict) or not provenance["model_sha256"]:
        return False, "missing_model_hashes"
    if any(not isinstance(value, str) or len(value) != 64
           for value in provenance["model_sha256"].values()):
        return False, "invalid_model_hash"
    environment = provenance["environment"]
    gpu = provenance["gpu"]
    if not all(environment.get(key) for key in ("python", "platform", "packages")):
        return False, "incomplete_runtime_environment"
    try:
        gpu_memory = int(gpu["memory_mib"])
    except (KeyError, TypeError, ValueError):
        return False, "incomplete_gpu_provenance"
    if "RTX 4080 SUPER" not in gpu.get("name", "") or not 32000 <= gpu_memory <= 33792:
        return False, "gpu_provenance_mismatch"
    if not isinstance(provenance.get("git"), dict) or not provenance["git"].get("head"):
        return False, "incomplete_git_provenance"
    if metrics.get("code_sha256") != provenance.get("source_sha256", {}).get("src/run_e1.py"):
        return False, "metrics_source_fingerprint_mismatch"
    if completion.get("metrics_sha256") != file_sha256(metrics_path):
        return False, "metrics_hash_mismatch"
    artifacts = completion.get("artifact_sha256")
    if not isinstance(artifacts, dict) or not artifacts:
        return False, "missing_artifact_hashes"
    expected_artifacts = {"metrics.json", *(f"trained_predictions/{subset}.jsonl" for subset in subsets)}
    if seed == 42:
        expected_artifacts.update(f"zeroshot_predictions/{subset}.jsonl" for subset in subsets)
    if not expected_artifacts.issubset(artifacts):
        return False, "missing_required_artifact_hashes"
    if ("adapter/adapter_config.json" not in artifacts
            or not any(name.startswith("adapter/adapter_model.") for name in artifacts)):
        return False, "missing_adapter_artifact_hashes"
    root = run_dir.resolve()
    for relative, digest in artifacts.items():
        artifact = (run_dir / relative).resolve()
        if root not in artifact.parents or not artifact.is_file() or file_sha256(artifact) != digest:
            return False, f"artifact_hash_mismatch:{relative}"
    tags = ["trained"] + (["zeroshot"] if seed == 42 else [])
    try:
        for tag in tags:
            if set(metrics.get(tag, {})) != set(subsets):
                return False, f"metrics_split_set_mismatch:{tag}"
            for subset in subsets:
                rows = load_jsonl(data_dir / f"{subset}.jsonl")
                predictions = load_jsonl(run_dir / f"{tag}_predictions" / f"{subset}.jsonl")
                aligned_raw(rows, predictions)
                metric = metrics.get(tag, {}).get(subset, {})
                if (metric.get("records") != len(rows)
                        or metric.get("exec", {}).get("metrics_version") != "e1_exec_v6_fail_closed"):
                    return False, f"metrics_split_mismatch:{tag}:{subset}"
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return False, f"incomplete_predictions:{type(exc).__name__}"
    return True, "complete"


def verified_pe_run(path: Path, data_dir: Path, subsets: list[str], model: str) -> tuple[bool, str]:
    from pe_v4_side import DEFAULT_URL, demonstrations, fingerprint
    from run_pe_v6 import SOURCE_NAMES, prediction_hash, request_fingerprint, verify_completion

    config_path = path / "config.json"
    if not config_path.is_file():
        return False, "missing_pe_config"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    style = "few" if model == "deepseek-v4-pro-0813" or path.name.endswith("-few") else "zero"
    params = {"model": model, "temperature": 0, "max_tokens": 384}
    if model.startswith("deepseek"):
        params["enable_thinking"] = False
    demo = demonstrations(load_jsonl(data_dir / "train.jsonl")) if style == "few" else []
    if (config.get("params") != params or config.get("style") != style
            or config.get("url") != DEFAULT_URL or config.get("data") != current_data_hashes(data_dir, subsets)
            or config.get("demo_hash") != fingerprint(demo)):
        return False, "pe_config_mismatch"
    expected_sources = {
        name: file_sha256(ROOT / "src" / f"{name}.py")
        for name in SOURCE_NAMES
    }
    if config.get("source_hashes") != expected_sources:
        return False, "pe_source_fingerprint_mismatch"
    completion_path = path / "completion.json"
    if not completion_path.is_file():
        return False, "missing_pe_completion"
    try:
        verify_completion(path, config, subsets, model, style)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False, "pe_completion_or_artifact_hash_mismatch"
    for subset in subsets:
        rows = load_jsonl(data_dir / f"{subset}.jsonl")
        predictions = load_jsonl(path / f"{subset}.jsonl")
        expected: dict[str, str] = {}
        for row in rows:
            base = chat_messages_v4(row)
            messages = [base[0], *demo, base[1]] if style == "few" else base
            expected[row["sample_id"]] = request_fingerprint(config, params, messages)
        got = {item.get("sample_id"): item for item in predictions}
        if (len(got) != len(predictions) or set(got) != set(expected)
                or any(got[sid].get("request_hash") != digest or got[sid].get("model") != model
                       or not isinstance(got[sid].get("raw"), str)
                       or got[sid].get("prediction_sha256") != prediction_hash(got[sid])
                       for sid, digest in expected.items())):
            return False, f"pe_cache_fingerprint_mismatch:{subset}"
    return True, "complete"


def score_prediction_dir(data_dir: Path, prediction_dir: Path) -> dict[str, Any]:
    out = {}
    for subset in eval_subsets(data_dir):
        rows = load_jsonl(data_dir / f"{subset}.jsonl")
        predictions = load_jsonl(prediction_dir / f"{subset}.jsonl")
        raw = aligned_raw(rows, predictions)
        fields = score(rows, [None] * len(rows), raw)
        execution, outcomes = evaluate_v6(rows, raw)
        n_errors = n_error_components(rows, raw)
        n_by_subtype = n_error_subtypes(rows, raw)
        out[subset] = {
            "records": fields["records"],
            "constraint_strict_f1": fields["constraint_micro"]["f1"],
            "constraint_core_f1": fields["constraint_core_micro"]["f1"],
            "record_exact_match": fields["record_exact_match"],
            "record_exact_match_by_variant": fields["record_exact_match_by_variant"],
            "evidence_exact_rate": fields["evidence_exact_rate"],
            "json_parse_rate": fields["json_parse_rate"],
            "safe_success": execution["safe_success"],
            "faithful_success": execution["faithful_success"],
            "safe_success_constrained": execution["safe_success_constrained"],
            "faithful_success_constrained": execution["faithful_success_constrained"],
            "faithful_success_by_variant": {
                variant: entry["faithful_success"]
                for variant, entry in execution["per_variant"].items()
            },
            "n_errors": n_errors,
            "n_errors_by_subtype": n_by_subtype,
            "outcomes": outcomes,
        }
    return out


def mean_sd(values: list[float]) -> dict[str, float | None]:
    return {
        "mean": round(statistics.mean(values), 4) if values else None,
        "sample_sd": round(statistics.stdev(values), 4) if len(values) > 1 else None,
    }


def paired_group_diff(a_runs: list[list[dict[str, Any]]], b_runs: list[list[dict[str, Any]]],
                      *, subset: str, n_boot: int = 10_000, seed: int = 20261124) -> dict[str, Any] | None:
    if not a_runs or not b_runs:
        return None
    from collections import defaultdict
    import random

    def index_runs(runs: list[list[dict[str, Any]]]) -> list[dict[str, dict[str, Any]]]:
        return [{o["sample_id"]: o for o in run} for run in runs]

    def by_group(runs: list[list[dict[str, Any]]]) -> dict[str, list[float]]:
        all_runs = index_runs(runs)
        ids = set.intersection(*(set(run) for run in all_runs))
        group_values: dict[str, list[float]] = defaultdict(list)
        for sid in ids:
            outcomes = [run[sid] for run in all_runs]
            if outcomes[0]["variant"] == "none":
                continue
            group_values[outcomes[0]["group_id"]].append(
                statistics.mean(float(o["faithful_success"]) for o in outcomes)
            )
        return group_values

    a_by_group, b_by_group = by_group(a_runs), by_group(b_runs)
    groups = sorted(set(a_by_group) & set(b_by_group))
    if not groups:
        return None
    group_diff = {g: statistics.mean(a_by_group[g]) - statistics.mean(b_by_group[g]) for g in groups}
    point = statistics.mean(group_diff.values())
    rng = random.Random(seed)
    values = sorted(statistics.mean(group_diff[groups[rng.randrange(len(groups))]] for _ in groups)
                    for _ in range(n_boot))
    b_indexed = index_runs(b_runs)
    per_a_run = []
    for a_indexed in index_runs(a_runs):
        paired_ids = set.intersection(set(a_indexed), *(set(run) for run in b_indexed))
        per_group: dict[str, list[float]] = defaultdict(list)
        for sid in paired_ids:
            if a_indexed[sid]["variant"] == "none":
                continue
            baseline = statistics.mean(float(run[sid]["faithful_success"]) for run in b_indexed)
            per_group[a_indexed[sid]["group_id"]].append(float(a_indexed[sid]["faithful_success"]) - baseline)
        if per_group:
            per_a_run.append(round(statistics.mean(statistics.mean(v) for v in per_group.values()), 4))
    return {
        "subset": subset,
        "groups": len(groups),
        "difference_a_minus_b": round(point, 4),
        "paired_group_bootstrap_ci95": [values[int(.025 * n_boot)], values[int(.975 * n_boot) - 1]],
        "per_a_run_differences": per_a_run,
        "uncertainty": "paired task-group bootstrap conditional on observed model seeds",
    }


def independent_split_diff(tool_runs: list[list[dict[str, Any]]], struct_runs: list[list[dict[str, Any]]],
                           *, n_boot: int = 10_000, seed: int = 20261124) -> dict[str, Any] | None:
    """Compare named independent cohorts; bootstrap task groups within each split."""
    if not tool_runs or not struct_runs:
        return None
    from collections import defaultdict
    import random

    def by_group(runs: list[list[dict[str, Any]]]) -> dict[str, float]:
        values: dict[str, list[float]] = defaultdict(list)
        for run in runs:
            per_group: dict[str, list[float]] = defaultdict(list)
            for outcome in run:
                if outcome["variant"] != "none":
                    per_group[outcome["group_id"]].append(float(outcome["faithful_success"]))
            for group, group_values in per_group.items():
                values[group].append(statistics.mean(group_values))
        return {group: statistics.mean(group_values) for group, group_values in values.items()}

    tool, struct = by_group(tool_runs), by_group(struct_runs)
    if not tool or not struct:
        return None
    point = statistics.mean(tool.values()) - statistics.mean(struct.values())
    rng = random.Random(seed)
    tool_groups, struct_groups = list(tool), list(struct)
    samples = sorted(
        statistics.mean(tool[tool_groups[rng.randrange(len(tool_groups))]] for _ in tool_groups)
        - statistics.mean(struct[struct_groups[rng.randrange(len(struct_groups))]] for _ in struct_groups)
        for _ in range(n_boot)
    )
    ci = [samples[int(.025 * n_boot)], samples[int(.975 * n_boot) - 1]]
    verdict = ("transfers" if ci[1] <= STRUCT_TRANSFER_MAX_DROP else
               "does_not_transfer" if ci[0] >= STRUCT_FAIL_MIN_DROP else "inconclusive")
    return {
        "difference_tool_ho_minus_struct_ho": round(point, 4),
        "ci95": ci,
        "tool_groups": len(tool),
        "struct_groups": len(struct),
        "verdict": verdict,
        "interpretation": "association across independent cohorts; structure split is a compound shift, not a causal intervention",
    }


def collect(data_dir: Path, runs_root: Path) -> dict[str, Any]:
    subsets = eval_subsets(data_dir)
    data_hashes = current_data_hashes(data_dir, subsets)
    raw_arms: dict[str, list[Path]] = {}
    for size in SIZES:
        raw_arms[f"Qwen3-{size}-v6-trained"] = [
            runs_root / f"Qwen3-{size}-v6-seed{seed}" / "trained_predictions" for seed in SEEDS
        ]
    raw_arms.update({f"Qwen3-{size}-v6-zero": [
        runs_root / f"Qwen3-{size}-v6-seed42" / "zeroshot_predictions"
    ] for size in SIZES})
    arms: dict[str, Any] = {}
    parsed_runs: dict[str, dict[str, list[list[dict[str, Any]]]]] = {}
    for arm, dirs in raw_arms.items():
        trained_arm = arm.endswith("-trained")
        arms[arm] = {"observed_runs": [], "excluded_runs": [], "splits": {}}
        if trained_arm:
            arms[arm]["required_seeds"] = list(SEEDS)
        else:
            arms[arm]["required_seeds"] = [42]
        parsed_runs[arm] = {}
        for run_dir in dirs:
            root_dir = run_dir.parent
            try:
                run_seed = int(root_dir.name.rsplit("seed", 1)[1])
            except (IndexError, ValueError):
                arms[arm]["excluded_runs"].append({"run": str(root_dir), "reason": "unrecognized_run_name"})
                continue
            expected_model = "models/" + arm.removesuffix("-v6-trained").removesuffix("-v6-zero")
            try:
                valid, reason = verified_science_run(root_dir, data_dir, subsets, run_seed, expected_model)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                valid, reason = False, f"invalid_run_artifact:{type(exc).__name__}"
            if not valid or (not trained_arm and run_seed != 42):
                arms[arm]["excluded_runs"].append({
                    "run": str(root_dir), "reason": reason if not valid else "zero_shot_seed_must_be_42"
                })
                continue
            if not all((run_dir / f"{subset}.jsonl").is_file() for subset in subsets):
                arms[arm]["excluded_runs"].append({"run": str(root_dir), "reason": "missing_prediction_split"})
                continue
            metrics = score_prediction_dir(data_dir, run_dir)
            run_label = root_dir.name
            arms[arm]["observed_runs"].append(run_label)
            for subset, entry in metrics.items():
                parsed_runs[arm].setdefault(subset, []).append(entry.pop("outcomes"))
                arms[arm]["splits"].setdefault(subset, {}).setdefault("per_run", []).append(entry)
        for subset, split in arms[arm]["splits"].items():
            required = SEEDS if trained_arm else (42,)
            split_complete = len(arms[arm]["observed_runs"]) == len(required)
            split["aggregate_status"] = "complete" if split_complete else "provisional_incomplete_seed_set"
            for metric in ("constraint_strict_f1", "constraint_core_f1", "record_exact_match",
                           "evidence_exact_rate", "safe_success_constrained", "faithful_success_constrained"):
                values = [run[metric] for run in split["per_run"] if run[metric] is not None]
                split[metric + "_mean_sd"] = mean_sd(values) if split_complete else None
        if trained_arm:
            observed_seeds = sorted(int(name.rsplit("seed", 1)[1]) for name in arms[arm]["observed_runs"])
            arms[arm]["observed_seeds"] = observed_seeds
            arms[arm]["required_seeds_complete"] = observed_seeds == list(SEEDS)
        else:
            arms[arm]["baseline_complete"] = len(arms[arm]["observed_runs"]) == 1

    for model in PE_ARMS:
        arm = f"PE-{model}"
        path = ROOT / "outputs" / "e1_v6_side" / model
        try:
            pe_valid, pe_reason = verified_pe_run(path, data_dir, subsets, model.removesuffix("-few").removesuffix("-zero"))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            pe_valid, pe_reason = False, f"incomplete_pe_cache:{type(exc).__name__}"
        if pe_valid and all((path / f"{subset}.jsonl").is_file() for subset in subsets):
            metric = score_prediction_dir(data_dir, path)
            arms[arm] = {"observed_runs": [model], "splits": {}}
            parsed_runs[arm] = {}
            for subset, entry in metric.items():
                parsed_runs[arm][subset] = [entry.pop("outcomes")]
                arms[arm]["splits"][subset] = entry
        else:
            arms[arm] = {"observed_runs": [], "status": pe_reason, "splits": {}}

    decisions: dict[str, Any] = {
        "H1_training_gain": {},
        "H2_pe_noninferiority": {},
        "H3_struct_transfer": {},
    }
    for size in SIZES:
        trained = f"Qwen3-{size}-v6-trained"
        zero = f"Qwen3-{size}-v6-zero"
        complete = arms.get(trained, {}).get("required_seeds_complete", False)
        baseline_complete = arms.get(zero, {}).get("baseline_complete", False)
        for subset in subsets:
            train_outcomes = parsed_runs.get(trained, {}).get(subset, [])
            zero_outcomes = parsed_runs.get(zero, {}).get(subset, [])
            per_seed = [
                paired_group_diff([run], zero_outcomes, subset=subset, seed=20261124 + index)
                for index, run in enumerate(train_outcomes)
            ] if baseline_complete else []
            seed_results = [
                {"seed": arms[trained]["observed_seeds"][index], **result}
                for index, result in enumerate(per_seed) if result
            ]
            all_seed_ci_positive = len(seed_results) == len(SEEDS) and all(
                result["paired_group_bootstrap_ci95"][0] > 0 for result in seed_results
            )
            all_seed_points_positive = len(seed_results) == len(SEEDS) and all(
                result["difference_a_minus_b"] > 0 for result in seed_results
            )
            decisions["H1_training_gain"].setdefault(size, {})[subset] = {
                "status": "supported" if complete and baseline_complete and all_seed_ci_positive
                and all_seed_points_positive else
                "rejected_or_unresolved" if complete and baseline_complete and seed_results
                else "pending_required_seeds_or_baseline",
                "required_seeds_complete": complete,
                "baseline_complete": baseline_complete,
                "all_seed_ci_lower_bounds_positive": all_seed_ci_positive,
                "all_seed_points_positive": all_seed_points_positive,
                "per_seed_comparisons": seed_results,
            }
            pe_arm = "PE-deepseek-v4-pro-0813-few"
            if subset in parsed_runs.get(pe_arm, {}):
                comparison = paired_group_diff(
                    parsed_runs.get(trained, {}).get(subset, []), parsed_runs[pe_arm][subset], subset=subset,
                ) if complete else None
                lower = comparison["paired_group_bootstrap_ci95"][0] if comparison else None
                decisions["H2_pe_noninferiority"].setdefault(size, {})[subset] = {
                    "required_margin": -0.03,
                    "status": "noninferior" if complete and comparison and lower > -0.03 else
                    "not_established" if complete and comparison else "pending_required_seeds",
                    "noninferior": bool(complete and comparison and lower > -0.03),
                    "comparison": comparison,
                }
            else:
                decisions["H2_pe_noninferiority"].setdefault(size, {})[subset] = {
                    "required_margin": -0.03,
                    "status": "pending_pe_baseline",
                    "noninferior": False,
                    "comparison": None,
                }

        if complete:
            decisions["H3_struct_transfer"][trained] = independent_split_diff(
                parsed_runs.get(trained, {}).get("test_tool_ho", []),
                parsed_runs.get(trained, {}).get("test_struct_ho", []),
            )
        else:
            decisions["H3_struct_transfer"][trained] = {"status": "pending_required_seeds"}

    decisions["H4_n_diagnostic"] = {
        "diagnostic_arm": H4_DIAGNOSTIC_ARM,
        "threshold": N_GATE_MAX_ALARM,
        "interpretation": "model diagnostic only; this gate does not establish gold-label validity",
        "status": "complete" if arms.get(H4_DIAGNOSTIC_ARM, {}).get("observed_runs") else "pending_pe_baseline",
        "by_split": {},
    }
    diagnostic = arms.get(H4_DIAGNOSTIC_ARM, {})
    for subset, entry in diagnostic.get("splits", {}).items():
        decisions["H4_n_diagnostic"]["by_split"][subset] = {
            subtype: {
                "alarm": counts["rates"]["any_contract_alarm"],
                "status": "below_threshold" if counts["rates"]["any_contract_alarm"] < N_GATE_MAX_ALARM
                else "threshold_exceeded",
                "counts": counts,
            }
            for subtype, counts in entry["n_errors_by_subtype"].items()
        }

    h1_confirmatory = [
        decisions["H1_training_gain"][size][subset]["status"]
        for size in ("1.7B", "4B") for subset in ("dev", "test_composition_ho")
    ]
    decisions["H1_confirmatory_status"] = (
        "supported" if all(status == "supported" for status in h1_confirmatory) else
        "pending_required_seeds_or_baseline" if any(status.startswith("pending") for status in h1_confirmatory)
        else "rejected_or_unresolved"
    )

    return {
        "analysis_version": "v6-audit-20261124",
        "data_dir": str(data_dir),
        "subsets": subsets,
        "human_validation_status": "pending",
        "data_sha256": data_hashes,
        "arms": arms,
        "decisions": decisions,
        "notes": [
            "Confirmatory trained aggregates are emitted only for complete seed triplets; zero-shot baselines use the deterministic seed-42 cache.",
            "H1 uses a separate paired task-group bootstrap interval for each trained seed; intervals are conditional on the observed seeds.",
            "H3 compares independent named cohorts and does not establish a causal structure effect.",
            "H4 is a fixed DeepSeek PE model diagnostic and does not establish N gold-label validity.",
            "The strict F1, core F1, record exactness, evidence exactness, safe behavior and faithful behavior are separate metrics.",
            "Synthetic witness verification does not substitute for a blind human recoverability audit.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/processed_v6")
    parser.add_argument("--runs-root", type=Path, default=ROOT / "outputs/e1_v6")
    parser.add_argument("--out", type=Path, default=ROOT / "outputs/v6_analysis/main.json")
    args = parser.parse_args()
    report = collect(args.data, args.runs_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"saved": str(args.out), "arms": sorted(report["arms"]), "subsets": report["subsets"]}))


if __name__ == "__main__":
    main()
