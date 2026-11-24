"""CPU-only safety tests for the v6 GPU handoff supervisor."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_v6_relay import (
    DATA, OUT, PLAN, SEAL, checked_plan, check_release, event, gpu_state,
    idle, load_state, run_guarded, seal_release,
)


def test_fixed_release_seal_detects_data_tampering(tmp_path: Path) -> None:
    required = [
        tmp_path / PLAN, tmp_path / "src/run_v6_relay.py", tmp_path / "scripts/run_v6_queue.sh",
        tmp_path / "reports/design_v6_ccfb.md",
    ]
    for split in ("train", "dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho", "test_composition_ho"):
        required.append(tmp_path / DATA / f"{split}.jsonl")
    for path in required:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixed reviewed fixture\n")
    seal_release(tmp_path)
    manifest = json.loads((tmp_path / SEAL).read_text(encoding="utf-8"))
    assert manifest["sha256"]["data/processed_v6/train.jsonl"] == hashlib.sha256(
        b"fixed reviewed fixture\n"
    ).hexdigest()
    assert check_release(tmp_path)
    (tmp_path / DATA / "train.jsonl").write_text("mutated\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        check_release(tmp_path)


def test_registered_plan_prioritizes_complete_primary_triplets() -> None:
    plan = checked_plan(Path.cwd())
    assert [(job["model"], job["seed"]) for job in plan["jobs"]] == [
        ("Qwen3-1.7B", 42), ("Qwen3-1.7B", 43), ("Qwen3-1.7B", 44),
        ("Qwen3-4B", 42), ("Qwen3-4B", 43), ("Qwen3-4B", 44),
        ("Qwen3-0.6B", 42), ("Qwen3-0.6B", 43), ("Qwen3-0.6B", 44),
    ]
    assert plan["precision"] == "bf16"
    assert plan["recipe"]["lora_dropout"] == 0.05


@pytest.mark.parametrize(
    ("memory", "compute", "training", "expected"),
    [(0, [], [], True), (5120, [], [], False), (10, ["pid, python"], [], False),
     (10, [], ["123 python src/run_e1.py"], False)],
)
def test_idle_gate_requires_low_memory_and_no_processes(memory, compute, training, expected) -> None:
    assert idle({"memory_used_mib": memory, "compute_processes": compute, "training_processes": training}) is expected


def test_gpu_state_uses_fake_nvidia_smi_and_python_process_listing(monkeypatch) -> None:
    responses = iter([
        "0, NVIDIA GeForce RTX 4080 SUPER, GPU-test, 1024, 32768, 550.1",
        "",
        "10 python src/run_e1.py --seed 44\n11 python -c harmless",
    ])

    def fake_capture(command, *, root=None):
        if command[0] == "ps":
            return next(responses)
        if "--query-compute-apps" in command:
            return next(responses)
        return next(responses)

    monkeypatch.setattr("run_v6_relay.capture", fake_capture)
    found = gpu_state("0", nvidia_smi="fake-nvidia-smi")
    assert found["name"] == "NVIDIA GeForce RTX 4080 SUPER"
    assert found["memory_used_mib"] == 1024
    assert found["training_processes"] == ["10 python src/run_e1.py --seed 44"]
    assert not idle(found)


def test_wall_budget_kills_only_the_supervised_process_group(tmp_path: Path) -> None:
    log = tmp_path / "budget.log"
    code, reason, elapsed = run_guarded(
        [sys.executable, "-u", "-c", "import time; print('started', flush=True); time.sleep(10)"],
        root=tmp_path, log=log, seconds=0.3,
    )
    assert (code, reason) == (124, "budget_exhausted")
    assert elapsed < 2
    assert "started" in log.read_text(encoding="utf-8")


@pytest.mark.parametrize("raw_exit", [124, 137, -9])
@pytest.mark.parametrize("elapsed", [1.0, 30.0])
def test_linux_timeout_exit_is_normalized_only_at_budget_deadline(tmp_path: Path, monkeypatch, raw_exit, elapsed) -> None:
    import types
    import run_v6_relay as relay

    # Exercise the actual POSIX wrapper/classification branch without requiring
    # Linux or launching a GPU process on the Windows preparation machine.
    monkeypatch.setattr(relay, "os", types.SimpleNamespace(name="posix"))
    monkeypatch.setattr(relay, "signal", types.SimpleNamespace(SIGKILL=9))
    monkeypatch.setattr(relay.shutil, "which", lambda _: "/usr/bin/timeout")
    clock = iter([100.0, 100.01, 100.0 + elapsed])
    monkeypatch.setattr(relay.time, "monotonic", lambda: next(clock))
    launched = []

    def fake_popen(command, **kwargs):
        launched.append(command)
        return types.SimpleNamespace(wait=lambda **_kwargs: raw_exit)

    monkeypatch.setattr(relay.subprocess, "Popen", fake_popen)
    log = tmp_path / "timeout.log"
    code, reason, measured = relay.run_guarded(["python", "training-fixture.py"], root=tmp_path, log=log, seconds=30)
    assert launched == [["/usr/bin/timeout", "--signal=KILL", "30.000000s", "python", "training-fixture.py"]]
    assert measured == elapsed
    if elapsed == 30.0:
        assert (code, reason) == (124, "budget_exhausted")
        assert json.loads(log.read_text(encoding="utf-8"))["watchdog_exit_code"] == raw_exit
    else:
        assert (code, reason) == (raw_exit, "subprocess_failed")


def test_nonfinite_log_stops_child_and_records_fail_stop_manifest(tmp_path: Path) -> None:
    log = tmp_path / "nan.log"
    code, reason, elapsed = run_guarded(
        [sys.executable, "-u", "-c", "import time; print('non-finite loss: nan', flush=True); time.sleep(10)"],
        root=tmp_path, log=log, seconds=10,
    )
    assert code != 0 and reason == "oom_or_nonfinite" and elapsed < 3
    event(tmp_path, "science_failed", model="Qwen3-1.7B", seed=42, reason=reason)
    rows = [json.loads(line) for line in (tmp_path / OUT / "queue_manifest.jsonl").read_text().splitlines()]
    assert len(rows) == 1 and rows[0]["event"] == "science_failed"
    assert rows[0]["reason"] == "oom_or_nonfinite"


def test_active_queue_cannot_be_restarted_with_fresh_budget(tmp_path: Path) -> None:
    path = tmp_path / OUT / "queue_state.json"
    state = {"schema_version": 2, "budget_seconds": 108000, "gpu_seconds_used": 30,
             "active": {"model": "Qwen3-4B", "seed": 44, "reserved_seconds": 107970}, "status": "running"}
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ValueError, match="Unclean prior queue termination"):
        load_state(tmp_path, 108000)
    stopped = json.loads(path.read_text(encoding="utf-8"))
    assert stopped["gpu_seconds_used"] == 108000
    assert stopped["status"] == "incomplete"


def test_relay_provenance_and_artifacts_are_accepted_by_analysis(tmp_path: Path, monkeypatch) -> None:
    import analyze_v6_main as analysis
    import run_v6_relay as relay

    monkeypatch.setattr(analysis, "ROOT", tmp_path)
    data_hashes = {}
    for split in relay.SPLITS:
        path = tmp_path / DATA / f"{split}.jsonl"
        relay.write(path, {"sample_id": f"{split}-record"})
        # JSONL has one object on one line, independently of the JSON writer.
        path.write_text(json.dumps({"sample_id": f"{split}-record"}) + "\n", encoding="utf-8")
        data_hashes[split] = relay.digest(path)
    sources = {}
    for name in ("src/run_e1.py", "src/run_e1_v6.py", "src/eval_exec_v6.py", "src/dataset_v6_spec.py",
                 "src/trust_env.py", "scripts/run_v6_queue.sh"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# source fixture, never executed", encoding="utf-8")
        sources[name] = relay.digest(path)
    plan = checked_plan(ROOT)
    job = {"model": "Qwen3-1.7B", "seed": 43, "eval_batch_size": 32}
    relative = OUT / "Qwen3-1.7B-v6-seed43"
    config = relay.job_config(job, plan, relative)
    expected = {"config": config, "data_sha256": data_hashes, "source_sha256": sources,
                "model_sha256": {"model.safetensors": "a" * 64},
                "environment": {"python": "test", "platform": "test", "packages": {"pytest": "test"}},
                "gpu": {"name": "NVIDIA GeForce RTX 4080 SUPER", "memory_mib": "32768"},
                "git": {"head": "test-existing-revision", "status": " M test"}}
    run = tmp_path / relative
    relay.write(run / "provenance.json", relay.provenance_record(expected))
    metrics = {"config": {k: v for k, v in config.items() if k != "lora_dropout"},
               "model_path": config["model"], "seed": job["seed"], "data_sha256": data_hashes,
               "code_sha256": sources["src/run_e1.py"],
               "trained": {split: {"records": 1, "exec": {"metrics_version": "e1_exec_v6_fail_closed"}}
                           for split in relay.SPLITS[1:]}}
    relay.write(run / "metrics.json", metrics)
    for split in relay.SPLITS[1:]:
        path = run / "trained_predictions" / f"{split}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"sample_id": f"{split}-record", "raw": "{}"}) + "\n", encoding="utf-8")
    relay.write(run / "adapter/adapter_config.json", {"r": 16, "lora_alpha": 32, "lora_dropout": .05})
    (run / "adapter/adapter_model.safetensors").write_bytes(b"CPU provenance fixture, never loaded")
    relay.write(run / "token_coverage.json", {"status": "PASS", "max_seq_len": 1280, "max_new_tokens": 384,
                "splits": {s: {"records": 12000 if s == "train" else 900 if s == "dev" else 1050,
                               "dropped": 0, "max_gold_with_eos": 200, "max_prompt_plus_gold": 1000}
                           for s in relay.SPLITS}})
    artifacts = relay.validate_artifacts(tmp_path, run, expected)
    relay.write(run / "completion.json", relay.completion_record(expected, artifacts))
    accepted, reason = analysis.verified_science_run(run, tmp_path / DATA, list(relay.SPLITS[1:]), 43, config["model"])
    assert accepted, reason
    # Git worktree status is evidence but cannot change run identity on resume.
    changed = {**expected, "git": {"head": "test-existing-revision", "status": "?? new-output"}}
    assert relay.provenance_record(expected)["fingerprint"] == relay.provenance_record(changed)["fingerprint"]
    (run / "trained_predictions/dev.jsonl").write_text('{"sample_id":"wrong", "raw":"{}"}\n')
    accepted, reason = analysis.verified_science_run(run, tmp_path / DATA, list(relay.SPLITS[1:]), 43, config["model"])
    assert not accepted and reason.startswith("artifact_hash_mismatch")


@pytest.mark.parametrize("exit_code,outcome", [(0, "complete"), (1, "subprocess_failed"), (124, "budget_exhausted")])
def test_queue_never_starts_next_job_after_failure_or_budget_stop(tmp_path: Path, monkeypatch, exit_code, outcome) -> None:
    import argparse
    import types
    import run_v6_relay as relay

    plan = checked_plan(ROOT)
    plan["jobs"] = plan["jobs"][:2]
    sources = {f"data/processed_v6/{split}.jsonl": "a" * 64 for split in relay.SPLITS}
    sources["src/run_e1.py"] = "b" * 64
    monkeypatch.setattr(relay, "check_release", lambda _: sources)
    monkeypatch.setattr(relay, "checked_plan", lambda _: plan)
    monkeypatch.setattr(relay, "model_hashes", lambda *_: {"model.safetensors": "c" * 64})
    monkeypatch.setattr(relay, "environment", lambda: {"python": "CPU test"})
    monkeypatch.setattr(relay, "digest", lambda _: "d" * 64)
    monkeypatch.setattr(relay, "capture", lambda *_args, **_kwargs: "test-existing-revision")
    gpu = {"index": "0", "name": "NVIDIA GeForce RTX 4080 SUPER", "uuid": "GPU-test", "memory_mib": "32768",
           "driver": "test", "memory_used_mib": 0, "compute_processes": [], "training_processes": []}
    monkeypatch.setattr(relay, "gpu_state", lambda *_: gpu)

    def verify(command, **kwargs):
        relay.write(tmp_path / OUT / "preflight_verification.json",
                    {"verdict": "PASS", "sha256": {split: "a" * 64 for split in relay.SPLITS}})
        return types.SimpleNamespace(returncode=0)

    calls = []

    def fail_job(command, **kwargs):
        calls.append(command)
        return exit_code, outcome, 12.0

    monkeypatch.setattr(relay.subprocess, "run", verify)
    monkeypatch.setattr(relay, "run_guarded", fail_job)
    # Training artifacts have an independent real-validator integration test above.
    monkeypatch.setattr(relay, "validate_artifacts", lambda *_: {"metrics.json": "e" * 64})
    args = argparse.Namespace(budget_hours=30, python=sys.executable, gpu="0")
    result = relay.queue(tmp_path, args, types.SimpleNamespace(fd=9), gpu)
    assert result == (3 if exit_code == 124 else 1 if exit_code else 0)
    assert len(calls) == (1 if exit_code else 2)
    state = relay.read(tmp_path / OUT / "queue_state.json")
    assert state["gpu_seconds_used"] == (12.0 if exit_code else 24.0)
    assert state["status"] == ("incomplete" if exit_code == 124 else "failed" if exit_code else "complete")
    events = [json.loads(line)["event"] for line in (tmp_path / OUT / "queue_manifest.jsonl").read_text().splitlines()]
    assert events.count("science_start") == (1 if exit_code else 2)
    assert events.count("science_complete") == (0 if exit_code else 2)
    assert (tmp_path / OUT / "Qwen3-1.7B-v6-seed43").exists() is (exit_code == 0)


def test_verification_failure_blocks_all_training(tmp_path: Path, monkeypatch) -> None:
    import argparse
    import subprocess
    import types
    import run_v6_relay as relay

    monkeypatch.setattr(relay, "check_release", lambda _: {})
    monkeypatch.setattr(relay, "checked_plan", lambda _: checked_plan(ROOT))
    launched = []
    monkeypatch.setattr(relay, "run_guarded", lambda *_args, **_kwargs: launched.append(True))

    def failed_verification(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "verify_dataset_v6.py")

    monkeypatch.setattr(relay.subprocess, "run", failed_verification)
    args = argparse.Namespace(budget_hours=30, python=sys.executable, gpu="0")
    with pytest.raises(subprocess.CalledProcessError):
        relay.queue(tmp_path, args, types.SimpleNamespace(fd=9), {})
    assert launched == []
    state = relay.read(tmp_path / OUT / "queue_state.json")
    assert state["status"] == "failed" and state["gpu_seconds_used"] == 0

