from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analyze_v6_main import independent_split_diff, verified_science_run  # noqa: E402
from run_e1 import eval_subsets


def test_independent_split_interval_uses_the_named_cohorts():
    # By construction every constrained task group succeeds in tool_ho and fails in struct_ho.
    tool = [[{"group_id": f"t{i}", "variant": "explicit", "faithful_success": True}
             for i in range(5)]]
    struct = [[{"group_id": f"s{i}", "variant": "implicit", "faithful_success": False}
               for i in range(7)]]
    result = independent_split_diff(tool, struct, n_boot=200)
    assert result["difference_tool_ho_minus_struct_ho"] == 1.0
    assert result["ci95"] == [1.0, 1.0]
    assert result["verdict"] == "does_not_transfer"
    assert result["tool_groups"] == 5
    assert result["struct_groups"] == 7


def test_science_run_requires_complete_matching_provenance_and_artifacts(tmp_path):
    data_dir = tmp_path / "data"
    run_dir = tmp_path / "run"
    predictions = run_dir / "trained_predictions"
    data_dir.mkdir()
    predictions.mkdir(parents=True)
    for subset in ("train", "dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho", "test_composition_ho"):
        (data_dir / f"{subset}.jsonl").write_text(
            json.dumps({"sample_id": subset}) + "\n", encoding="utf-8"
        )
    subsets = eval_subsets(data_dir)
    data_hashes = {
        name: hashlib.sha256((data_dir / f"{name}.jsonl").read_bytes()).hexdigest()
        for name in ["train", *eval_subsets(data_dir)]
    }
    metrics_path = run_dir / "metrics.json"
    source_hashes = {key: hashlib.sha256((ROOT / key).read_bytes()).hexdigest() for key in (
        "src/run_e1.py", "src/run_e1_v6.py", "src/eval_exec_v6.py", "src/dataset_v6_spec.py",
        "src/trust_env.py", "scripts/run_v6_queue.sh",
    )}
    config = {
        "model": "models/Qwen3-1.7B", "data_dir": "data/processed_v6", "precision": "bf16", "seed": 42,
        "epochs": 3, "learning_rate": 2e-4, "lora_rank": 16, "lora_alpha": 32,
        "gradient_accumulation_steps": 4, "max_seq_len": 1280, "max_new_tokens": 384,
        "eval_batch_size": 32, "skip_zeroshot": False, "skip_train": False,
    }
    environment = {"python": "3.12", "platform": "fixture", "packages": {"test": "1"}}
    gpu = {"name": "NVIDIA GeForce RTX 4080 SUPER", "memory_mib": "32768"}
    stable = {
        "schema_version": 1, "kind": "science", "config": config, "data_sha256": data_hashes,
        "source_sha256": source_hashes, "model_sha256": {"weights.safetensors": "a" * 64},
        "environment": environment, "gpu": gpu,
    }
    fingerprint = hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for tag in ("trained", "zeroshot"):
        tag_dir = run_dir / f"{tag}_predictions"
        tag_dir.mkdir(exist_ok=True)
        for subset in subsets:
            (tag_dir / f"{subset}.jsonl").write_text(
                json.dumps({"sample_id": subset, "raw": "{}"}) + "\n", encoding="utf-8"
            )
    metrics_path.write_text(json.dumps({
        "model_path": "models/Qwen3-1.7B",
        "seed": 42,
        "config": config,
        "data_sha256": data_hashes,
        "code_sha256": source_hashes["src/run_e1.py"],
        **{tag: {subset: {"records": 1, "exec": {"metrics_version": "e1_exec_v6_fail_closed"}}
                 for subset in subsets} for tag in ("trained", "zeroshot")},
    }), encoding="utf-8")
    artifacts = {"metrics.json": hashlib.sha256(metrics_path.read_bytes()).hexdigest()}
    for path in sorted(run_dir.glob("*_predictions/*.jsonl")):
        artifacts[path.relative_to(run_dir).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (run_dir / "adapter").mkdir()
    for name in ("adapter_config.json", "adapter_model.safetensors"):
        path = run_dir / "adapter" / name
        path.write_bytes(b"test artifact, never loaded")
        artifacts[path.relative_to(run_dir).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    provenance = {**stable, "fingerprint": fingerprint, "git": {"head": "fixture"}}
    (run_dir / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    (run_dir / "completion.json").write_text(json.dumps({
        "status": "complete",
        "kind": "science",
        "fingerprint": fingerprint,
        "data_sha256": data_hashes,
        "source_sha256": source_hashes,
        "model_path": "models/Qwen3-1.7B",
        "seed": 42,
        "precision": "bf16",
        "metrics_sha256": artifacts["metrics.json"],
        "artifact_sha256": artifacts,
    }), encoding="utf-8")

    assert verified_science_run(run_dir, data_dir, subsets, 42, "models/Qwen3-1.7B") == (True, "complete")
    assert not verified_science_run(run_dir, data_dir, subsets, 42, "models/Qwen3-4B")[0]
    with (run_dir / "zeroshot_predictions/dev.jsonl").open("a", encoding="utf-8") as stream:
        stream.write("{}\n")
    valid, reason = verified_science_run(run_dir, data_dir, subsets, 42, "models/Qwen3-1.7B")
    assert not valid
    assert reason.startswith("artifact_hash_mismatch:")
