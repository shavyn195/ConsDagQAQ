"""Fail-closed single-GPU v6 handoff and complete-experiment queue.

No torch import, SSH, credential handling, short training, or precision fallback.
Create the release seal once on the reviewed local checkout with --seal-release;
copy that seal alongside its files. The server launch only checks this seal.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

SPLITS = ("train", "dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho", "test_composition_ho")
DATA = Path("data/processed_v6")
OUT = Path("outputs/e1_v6")
PLAN = Path("configs/v6_queue_plan.json")
SEAL = Path("configs/v6_release_sha256.json")
MAX_BUDGET = 30 * 3600
BAD_LOG = re.compile(r"out of memory|\bOOM\b|cuda error|non[- ]finite|\b(?:loss|grad(?:ient)?)['\"]?\s*[:=]?\s*(?:nan|inf)\b|\bFloatingPointError\b", re.I)
TRAIN_PROCESS = re.compile(r"(?:^|[/\s])(?:run_e1(?:_v6)?\.py|(?:train(?:ing)?|finetun(?:e|ing)|sft)(?:[._-][\w.-]+)?\.py|torchrun)(?:\s|$)|accelerate\s+launch|torch\.distributed\.(?:run|launch)", re.I)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)


def event(root: Path, name: str, **details: Any) -> None:
    record = {"event": name, "time": utc(), **details}
    path = root / OUT / "queue_manifest.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(record, ensure_ascii=False), flush=True)


def release_files(root: Path) -> list[Path]:
    files = set(root.glob("src/*.py")) | set(root.glob("tests/*.py"))
    files |= set(root.glob("scripts/*v6*.sh")) | set(root.glob("configs/*v6*"))
    files |= set((root / DATA).glob("*.jsonl")) | set((root / DATA).glob("*.json"))
    files |= {root / "reports/design_v6_ccfb.md"}
    files |= set(root.glob("*requirements*.txt")) | set(root.glob("*lock*"))
    files |= set(root.glob("gpu_kernel/*requirements*.txt")) | set(root.glob("pyproject.toml"))
    return sorted(path for path in files if path.is_file() and path != root / SEAL)


def seal_release(root: Path) -> None:
    files = release_files(root)
    required = {root / PLAN, root / "src/run_v6_relay.py", root / "scripts/run_v6_queue.sh"}
    required |= {root / DATA / f"{split}.jsonl" for split in SPLITS}
    if not required.issubset(set(files)):
        raise ValueError("Cannot seal an incomplete v6 checkout")
    write(root / SEAL, {"schema_version": 1, "created_at": utc(),
                       "instruction": "Locally reviewed release. Verify on server; never regenerate during launch.",
                       "sha256": {p.relative_to(root).as_posix(): digest(p) for p in files}})


def check_release(root: Path) -> dict[str, str]:
    seal = read(root / SEAL)
    expected = seal.get("sha256", {})
    actual_names = {p.relative_to(root).as_posix() for p in release_files(root)}
    if seal.get("schema_version") != 1 or actual_names != set(expected):
        raise ValueError("Release file inventory differs from the locally sealed inventory")
    for name, sha in expected.items():
        path = root / name
        if path.resolve().is_relative_to(root.resolve()) is False or digest(path) != sha:
            raise ValueError(f"Release SHA-256 mismatch: {name}")
    return expected


def checked_plan(root: Path) -> dict[str, Any]:
    plan = read(root / PLAN)
    recipe = {"epochs": 3, "learning_rate": 2e-4, "lora_rank": 16, "lora_alpha": 32,
              "lora_dropout": .05, "gradient_accumulation_steps": 4, "max_seq_len": 1280, "max_new_tokens": 384}
    wanted = {(m, s) for m in ("Qwen3-0.6B", "Qwen3-1.7B", "Qwen3-4B") for s in (42, 43, 44)}
    jobs = plan.get("jobs", [])
    if (plan.get("schema_version") != 1 or plan.get("precision") != "bf16"
            or plan.get("recipe") != recipe or plan.get("gpu_budget_seconds") != MAX_BUDGET
            or len(jobs) != 9 or {(j["model"], j["seed"]) for j in jobs} != wanted
            or any(not isinstance(j.get("eval_batch_size"), int) or j["eval_batch_size"] < 1 for j in jobs)):
        raise ValueError("Queue plan differs from the registered complete bf16 3-seed recipe")
    return plan


def capture(command: list[str], *, root: Path | None = None) -> str:
    result = subprocess.run(command, cwd=root, check=True, capture_output=True, text=True, timeout=30)
    return result.stdout.strip()


def gpu_state(index: str, *, nvidia_smi: str = "nvidia-smi") -> dict[str, Any]:
    text = capture([nvidia_smi, "-i", index, "--query-gpu=index,name,uuid,memory.used,memory.total,driver_version", "--format=csv,noheader,nounits"])
    rows = list(csv.reader(text.splitlines(), skipinitialspace=True))
    if len(rows) != 1 or len(rows[0]) != 6:
        raise ValueError(f"Expected exactly one GPU, got {text!r}")
    number, name, uuid, used, total, driver = rows[0]
    processes = capture([nvidia_smi, "-i", index, "--query-compute-apps=pid,process_name", "--format=csv,noheader,nounits"])
    ps = capture(["ps", "-eo", "pid=,args="])
    training = [line.strip() for line in ps.splitlines()
                if ("python" in line.lower() or "torchrun" in line.lower() or "accelerate" in line.lower())
                and TRAIN_PROCESS.search(line)]
    return {"index": number, "name": name, "uuid": uuid, "memory_used_mib": int(used),
            "memory_total_mib": int(total), "memory_mib": total, "driver": driver,
            "compute_processes": processes.splitlines() if processes else [],
            "training_processes": training}


def idle(gpu: dict[str, Any]) -> bool:
    return gpu["memory_used_mib"] < 5 * 1024 and not gpu["compute_processes"] and not gpu["training_processes"]


def require_device(gpu: dict[str, Any]) -> None:
    if "RTX 4080 SUPER" not in gpu["name"] or not 32000 <= gpu["memory_total_mib"] <= 33792:
        raise ValueError(f"Expected the registered RTX 4080 SUPER 32 GB; found {gpu['name']} {gpu['memory_total_mib']} MiB")


class GpuLock:
    """One lock per physical UUID across checkout directories; inherited by children."""
    def __init__(self, uuid: str):
        self.uuid = uuid
        # A fixed Linux path prevents different TMPDIR values/checkouts from
        # creating independent locks for the same physical GPU.
        self.path = Path("/tmp") / f"consdag-v6-gpu-{hashlib.sha256(uuid.encode()).hexdigest()[:24]}.lock"
        self.fd: int | None = None

    def __enter__(self) -> "GpuLock":
        import fcntl  # The real queue is Linux-only; CPU pure-function tests work on Windows.
        inherited = os.environ.get("CONSDAG_V6_LOCK_FD")
        if inherited:
            fd = int(inherited)
            a, b = os.fstat(fd), self.path.stat()
            if (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino) or os.environ.get("CONSDAG_V6_GPU_UUID") != self.uuid:
                raise ValueError("Inherited GPU lock does not belong to the selected physical device")
            self.fd = os.dup(fd)
        else:
            self.fd = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self.fd)
            self.fd = None
            raise ValueError("Another v6 relay/queue already holds the physical GPU lock") from None
        os.set_inheritable(self.fd, True)
        return self

    def __exit__(self, *_args: Any) -> None:
        if self.fd is not None:
            os.close(self.fd)


def wait_idle(root: Path, index: str, poll: float) -> dict[str, Any]:
    while True:
        gpu = gpu_state(index)
        require_device(gpu)
        if idle(gpu):
            # Two observations prevent transient release/reallocation from passing the gate.
            time.sleep(min(2.0, poll))
            again = gpu_state(index)
            if again["uuid"] != gpu["uuid"]:
                raise ValueError("GPU identity changed while waiting")
            if idle(again):
                return again
        event(root, "waiting_for_idle", gpu=gpu)
        time.sleep(poll)


def model_hashes(root: Path, model: str) -> dict[str, str]:
    directory = root / "models" / model
    paths = [p for p in sorted(directory.rglob("*")) if p.is_file()
             and not {".git", ".cache", ".locks"}.intersection(p.relative_to(directory).parts)]
    if not (directory / "config.json").is_file() or not list(directory.glob("*.safetensors")):
        raise ValueError(f"Missing model config or safetensors: {directory}")
    return {p.relative_to(directory).as_posix(): digest(p) for p in paths}


def environment() -> dict[str, Any]:
    packages = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions() if d.metadata["Name"]}
    import platform
    return {"python": sys.version, "executable": sys.executable, "platform": platform.platform(),
            "packages": dict(sorted(packages.items()))}


def load_state(root: Path, budget: int) -> dict[str, Any]:
    path = root / OUT / "queue_state.json"
    if path.exists():
        state = read(path)
        if state.get("schema_version") != 2 or state.get("budget_seconds") != budget:
            raise ValueError("Queue accounting schema/budget changed; refusing to reset prior consumption")
        if state.get("active"):
            active = state["active"]
            # Unclean supervisor death: charge the whole reservation and stop. A lost
            # watchdog must never silently grant another 30 hours on restart.
            state["gpu_seconds_used"] += active["reserved_seconds"]
            state.update(active=None, status="incomplete", failure="unclean supervisor termination")
            write(path, state)
            raise ValueError("Unclean prior queue termination; budget conservatively exhausted, manual audit required")
        if state.get("status") in ("failed", "incomplete"):
            raise ValueError("Prior failed/incomplete queue is preserved; automatic continuation is disabled")
    else:
        if list((root / OUT).glob("Qwen3-*-v6-seed*")):
            raise ValueError("Existing runs lack budget accounting; refusing unaccounted restart")
        state = {"schema_version": 2, "budget_seconds": budget, "gpu_seconds_used": 0, "active": None, "status": "ready"}
    if not isinstance(state.get("gpu_seconds_used"), (float, int)) or not math.isfinite(state["gpu_seconds_used"]) or state["gpu_seconds_used"] < 0:
        raise ValueError("Invalid GPU accounting consumption")
    write(path, state)
    return state


def kill_group(process: subprocess.Popen[Any]) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.kill()
    process.wait()


def run_guarded(command: list[str], *, root: Path, log: Path, seconds: float, pass_fds: tuple[int, ...] = ()) -> tuple[int, str, float]:
    """Watch only our new process group. Existing v5 processes are never signalled."""
    started = time.monotonic()
    if seconds <= 0:
        return 124, "budget_exhausted", 0.0
    if os.name == "posix":
        timeout = shutil.which("timeout")
        if not timeout:
            raise RuntimeError("GNU timeout is required for a budget watchdog that survives supervisor death")
        command = [timeout, "--signal=KILL", f"{seconds:.6f}s", *command]
    with log.open("w", encoding="utf-8", newline="\n") as stream:
        kwargs: dict[str, Any] = {"cwd": root, "stdout": stream, "stderr": subprocess.STDOUT,
                                  "start_new_session": os.name == "posix"}
        if os.name == "posix":
            kwargs["pass_fds"] = pass_fds
        process = subprocess.Popen(command, **kwargs)
        observed = 0
        tail = ""
        try:
            while True:
                # Scan the live log so a process that logs NaN/OOM and hangs
                # cannot continue consuming the registered GPU budget.
                try:
                    with log.open("r", encoding="utf-8", errors="replace") as monitor:
                        monitor.seek(observed)
                        chunk = monitor.read()
                        observed = monitor.tell()
                except OSError:
                    chunk = ""
                observed_text = tail + chunk
                tail = observed_text[-160:]
                if BAD_LOG.search(observed_text):
                    kill_group(process)
                    return 1, "oom_or_nonfinite", time.monotonic() - started
                remaining = seconds - (time.monotonic() - started)
                if remaining <= 0:
                    kill_group(process)
                    return 124, "budget_exhausted", time.monotonic() - started
                try:
                    code = process.wait(timeout=min(remaining, .25))
                except subprocess.TimeoutExpired:
                    continue
                elapsed = time.monotonic() - started
                text = log.read_text(encoding="utf-8", errors="replace")
                if BAD_LOG.search(text):
                    return code or 1, "oom_or_nonfinite", elapsed
                if (os.name == "posix" and code in (124, 137, -signal.SIGKILL)
                        and elapsed >= seconds - min(.1, seconds * .01)):
                    stream.write(json.dumps({"watchdog_exit_code": code, "normalized_exit_code": 124,
                                             "elapsed_seconds": elapsed}) + "\n")
                    stream.flush()
                    return 124, "budget_exhausted", elapsed
                # SIGKILL/137 well before the deadline may be an OS OOM kill or
                # external intervention. Preserve it as a failure, not a budget stop.
                return code, "complete" if code == 0 else "subprocess_failed", elapsed
        except BaseException:
            kill_group(process)
            raise


def validate_artifacts(root: Path, run: Path, expected: dict[str, Any]) -> dict[str, str]:
    if (run / "training_failure.json").exists():
        raise ValueError(f"Training failure evidence exists: {run}")
    metrics = read(run / "metrics.json")
    config = metrics.get("config", {})
    # lora_dropout is a source-level constant in run_e1.py and is separately
    # sealed in the registered config/provenance; CLI metrics do not expose it.
    if any(config.get(k) != v for k, v in expected["config"].items() if k != "lora_dropout"):
        raise ValueError(f"Saved training config differs: {run}")
    if metrics.get("model_path") != expected["config"]["model"] or metrics.get("seed") != expected["config"]["seed"]:
        raise ValueError(f"Saved model/seed differs: {run}")
    if metrics.get("data_sha256") != expected["data_sha256"] or metrics.get("code_sha256") != expected["source_sha256"]["src/run_e1.py"]:
        raise ValueError(f"Saved data/trainer SHA-256 differs: {run}")
    hashes = {"metrics.json": digest(run / "metrics.json")}
    for tag in ["trained"] + ([] if expected["config"]["skip_zeroshot"] else ["zeroshot"]):
        if set(metrics.get(tag, {})) != set(SPLITS[1:]):
            raise ValueError(f"Missing evaluation splits: {run}/{tag}")
        for subset in SPLITS[1:]:
            ids = [json.loads(line)["sample_id"] for line in (root / DATA / f"{subset}.jsonl").read_text(encoding="utf-8").splitlines()]
            file = run / f"{tag}_predictions" / f"{subset}.jsonl"
            rows = [json.loads(line) for line in file.read_text(encoding="utf-8").splitlines()]
            score = metrics[tag][subset]
            if ([r.get("sample_id") for r in rows] != ids or any(not isinstance(r.get("raw"), str) for r in rows)
                    or score.get("records") != len(ids) or score.get("exec", {}).get("metrics_version") != "e1_exec_v6_fail_closed"):
                raise ValueError(f"Incomplete predictions or incompatible evaluator: {file}")
            hashes[file.relative_to(run).as_posix()] = digest(file)
    adapter = run / "adapter"
    weights = list(adapter.glob("adapter_model.*"))
    if not (adapter / "adapter_config.json").is_file() or not weights:
        raise ValueError(f"Adapter config/weights missing: {run}")
    adapter_config = read(adapter / "adapter_config.json")
    if any(adapter_config.get(key) != value for key, value in {"r": 16, "lora_alpha": 32, "lora_dropout": .05}.items()):
        raise ValueError(f"Saved adapter recipe differs: {run}")
    coverage = read(run / "token_coverage.json")
    expected_counts = {"train": 12000, "dev": 900, **{split: 1050 for split in SPLITS[2:]}}
    parts = coverage.get("splits", {})
    if (coverage.get("status") != "PASS" or coverage.get("max_seq_len") != 1280
            or coverage.get("max_new_tokens") != 384 or set(parts) != set(SPLITS)
            or any(parts[split].get("records") != expected_counts[split] or parts[split].get("dropped") != 0
                   or not 0 < parts[split].get("max_gold_with_eos", 0) <= 384 for split in SPLITS)
            or not 0 < parts["train"].get("max_prompt_plus_gold", 0) <= 1280):
        raise ValueError(f"Token coverage did not pass: {run}")
    hashes["token_coverage.json"] = digest(run / "token_coverage.json")
    for file in [adapter / "adapter_config.json", *weights]:
        hashes[file.relative_to(run).as_posix()] = digest(file)
    return hashes


def job_config(job: dict[str, Any], plan: dict[str, Any], run: Path) -> dict[str, Any]:
    return {"model": f"models/{job['model']}", "data_dir": DATA.as_posix(), "out_dir": run.as_posix(),
            "precision": "bf16", "seed": job["seed"], **plan["recipe"],
            "eval_batch_size": job["eval_batch_size"], "skip_zeroshot": job["seed"] != 42,
            "skip_train": False, "smoke_train_steps": None}


def job_command(python: str, config: dict[str, Any]) -> list[str]:
    command = [python, "-u", "src/run_e1_v6.py"]
    for key, value in config.items():
        if key in ("skip_train", "smoke_train_steps", "lora_dropout"):
            continue
        if key == "skip_zeroshot":
            if value:
                command.append("--skip-zeroshot")
        else:
            command.extend(["--" + key.replace("_", "-"), str(value)])
    return command


def provenance_record(expected: dict[str, Any]) -> dict[str, Any]:
    stable = {"schema_version": 1, "kind": "science", **{k: v for k, v in expected.items() if k != "git"}}
    return {**stable, "git": expected["git"], "fingerprint": canonical_hash(stable)}


def completion_record(expected: dict[str, Any], artifacts: dict[str, str]) -> dict[str, Any]:
    return {"status": "complete", "kind": "science", "fingerprint": provenance_record(expected)["fingerprint"],
            "source_sha256": expected["source_sha256"], "data_sha256": expected["data_sha256"],
            "model_path": expected["config"]["model"], "seed": expected["config"]["seed"],
            "precision": "bf16", "completed_at": utc(), "artifact_sha256": artifacts,
            "metrics_sha256": artifacts["metrics.json"]}


def queue(root: Path, args: argparse.Namespace, lock: GpuLock, gpu: dict[str, Any]) -> int:
    source = check_release(root)
    plan = checked_plan(root)
    budget = int(args.budget_hours * 3600)
    state = load_state(root, budget)
    state_path = root / OUT / "queue_state.json"
    try:
        # Write a fresh report outside the sealed dataset; the verifier must not
        # mutate any sealed bytes, even if its implementation changes formatting.
        verification = root / OUT / "preflight_verification.json"
        with (root / OUT / "preflight_verification.log").open("w", encoding="utf-8") as stream:
            subprocess.run([args.python, "src/verify_dataset_v6.py", "--data-dir", DATA.as_posix(), "--out", str(verification)],
                           cwd=root, stdout=stream, stderr=subprocess.STDOUT, check=True)
        report = read(verification)
        data_hashes = {s: source[f"{DATA.as_posix()}/{s}.jsonl"] for s in SPLITS}
        if report.get("verdict") != "PASS" or report.get("sha256") != data_hashes:
            raise ValueError("Fresh independent dataset verification or fixed SHA-256 comparison failed")
        check_release(root)
        models = {j["model"]: None for j in plan["jobs"]}
        for model in models:
            models[model] = model_hashes(root, model)
        env = environment()
        gpu_provenance = {"index": gpu["index"], "name": gpu["name"], "uuid": gpu["uuid"],
                          "memory_mib": gpu["memory_mib"], "driver": gpu["driver"]}
        snapshot = {"started_at": utc(), "gpu": gpu_provenance, "source_sha256": source, "data_sha256": data_hashes,
                    "model_sha256": models, "environment": env, "plan_sha256": digest(root / PLAN), "release_seal_sha256": digest(root / SEAL)}
        snapshot_path = root / OUT / "_provenance" / f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{os.getpid()}.json"
        write(snapshot_path, snapshot)
        event(root, "queue_start", gpu=gpu, budget_seconds=budget, snapshot=str(snapshot_path))
        for job in plan["jobs"]:
            relative = OUT / f"{job['model']}-v6-seed{job['seed']}"
            run = root / relative
            log = root / (relative.as_posix() + ".log")
            config = job_config(job, plan, relative)
            expected = {"config": config, "data_sha256": data_hashes, "source_sha256": source,
                        "model_sha256": models[job["model"]], "environment": env, "gpu": gpu_provenance,
                        "git": {"head": capture(["git", "rev-parse", "HEAD"], root=root),
                                "status": capture(["git", "status", "--short"], root=root)}}
            provenance = provenance_record(expected)
            fingerprint = provenance["fingerprint"]
            if run.exists() or log.exists():
                if not (run / "completion.json").exists() or read(run / "provenance.json").get("fingerprint") != fingerprint:
                    raise ValueError(f"Existing run is incomplete/incompatible; preserved: {run}")
                complete = read(run / "completion.json")
                if complete.get("fingerprint") != fingerprint or complete.get("artifact_sha256") != validate_artifacts(root, run, expected):
                    raise ValueError(f"Existing completed artifacts changed: {run}")
                event(root, "skip_verified", **job)
                continue
            remaining = budget - state["gpu_seconds_used"]
            if remaining <= .5:
                state.update(status="incomplete", failure="budget_exhausted")
                write(state_path, state)
                event(root, "incomplete", reason="budget_exhausted", **job)
                return 3
            check_release(root)
            if model_hashes(root, job["model"]) != models[job["model"]] or environment() != env:
                raise ValueError("Model files or Python environment changed after queue preflight")
            current = gpu_state(args.gpu)
            if current["uuid"] != gpu["uuid"] or not idle(current):
                raise ValueError("GPU became busy before launch; no second training process was started")
            run.mkdir(parents=True)
            write(run / "provenance.json", {**provenance, "snapshot": str(snapshot_path)})
            state.update(status="running", active={"model": job["model"], "seed": job["seed"],
                         "started_at": utc(), "reserved_seconds": remaining})
            write(state_path, state)
            event(root, "science_start", **job, remaining_seconds=remaining, gpu=current)
            # Reserve a small amount for spawning/accounting. Never permit a
            # graceful shutdown interval to extend a registered GPU reservation.
            status, outcome, elapsed = run_guarded(job_command(args.python, config), root=root, log=log,
                                                  seconds=max(0, remaining - .25), pass_fds=(lock.fd,))
            state["gpu_seconds_used"] += elapsed
            state.update(active=None, status="ready" if status == 0 else "incomplete" if outcome == "budget_exhausted" else "failed")
            state["last_job"] = {**job, "outcome": outcome, "gpu_seconds": elapsed, "finished_at": utc()}
            write(state_path, state)
            if status:
                write(run / "incomplete.json", {"status": state["status"], "reason": outcome, "exit_code": status, "time": utc()})
                event(root, state["status"], **job, reason=outcome, exit_code=status, log=str(log))
                return 3 if outcome == "budget_exhausted" else 1
            artifacts = validate_artifacts(root, run, expected)
            check_release(root)
            if model_hashes(root, job["model"]) != models[job["model"]] or environment() != env:
                raise ValueError("Model files or Python environment changed during job")
            write(run / "completion.json", completion_record(expected, artifacts))
            event(root, "science_complete", **job, gpu_seconds=elapsed, budget_used_seconds=state["gpu_seconds_used"], fingerprint=fingerprint)
        analysis = root / "outputs/v6_analysis/main.json"
        analysis.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([args.python, "src/analyze_v6_main.py", "--data", DATA.as_posix(),
                                 "--runs-root", OUT.as_posix(), "--out", analysis.relative_to(root).as_posix()],
                                cwd=root, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"CPU rescore failed after completed jobs: {result.stderr[-2000:]}")
        event(root, "analysis_complete", path=str(analysis.relative_to(root)))
        state["status"] = "complete"
        write(state_path, state)
        event(root, "queue_complete", budget_used_seconds=state["gpu_seconds_used"])
        return 0
    except BaseException as exc:
        state.update(status="failed", failure=f"{type(exc).__name__}: {exc}")
        # Preserve an active reservation on supervisor interruption: restart will
        # conservatively charge it and require a manual audit.
        write(state_path, state)
        event(root, "queue_failed", reason=state["failure"])
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(os.environ.get("PROJECT_ROOT", "/root/ConsDagV5")))
    parser.add_argument("--python", default=os.environ.get("PY", "/root/miniconda3/bin/python"))
    parser.add_argument("--mode", choices=("wait", "queue"), default="wait")
    parser.add_argument("--gpu", default=os.environ.get("CUDA_VISIBLE_DEVICES", "0"))
    parser.add_argument("--poll-seconds", type=float, default=30)
    parser.add_argument("--budget-hours", type=float, default=float(os.environ.get("GPU_BUDGET_HOURS", "30")))
    parser.add_argument("--seal-release", action="store_true", help="LOCAL PREPARATION ONLY: create the reviewed SHA-256 release manifest")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    if args.seal_release:
        seal_release(root)
        print(root / SEAL)
        return 0
    if os.name != "posix":
        parser.error("GPU relay execution requires the Linux server; no GPU task was started")
    if not re.fullmatch(r"\d+", args.gpu) or not 0 < args.budget_hours <= 30 or not 0 < args.poll_seconds <= 60:
        parser.error("Select one numeric GPU, budget > 0 and <= 30 hours, polling > 0 and <= 60 seconds")
    if not Path(args.python).is_file():
        parser.error(f"Python executable missing: {args.python}")
    os.environ["CUDA_VISIBLE_DEVICES"] = args.gpu
    (root / OUT).mkdir(parents=True, exist_ok=True)
    # Convert TERM into an exception so our child process group is killed too.
    def interrupted(signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt(f"relay received signal {signum}")
    signal.signal(signal.SIGTERM, interrupted)
    try:
        check_release(root)
        gpu = gpu_state(args.gpu)
        require_device(gpu)
        with GpuLock(gpu["uuid"]) as lock:
            event(root, "relay_start" if args.mode == "wait" else "queue_invoked", gpu=gpu, pid=os.getpid())
            if args.mode == "wait":
                ready = wait_idle(root, args.gpu, args.poll_seconds)
                event(root, "relay_handoff", gpu=ready)
                env = dict(os.environ, PY=args.python, PROJECT_ROOT=str(root), CONSDAG_V6_LOCK_FD=str(lock.fd), CONSDAG_V6_GPU_UUID=gpu["uuid"])
                command = ["bash", "scripts/run_v6_queue.sh", "--project-root", str(root), "--gpu", args.gpu,
                           "--python", args.python, "--budget-hours", str(args.budget_hours)]
                process = subprocess.Popen(command, cwd=root, env=env, pass_fds=(lock.fd,), start_new_session=True)
                try:
                    status = process.wait()
                    event(root, "relay_queue_exit", exit_code=status)
                    return status
                except BaseException:
                    # Let the queue supervisor kill its separately isolated
                    # training group before the outer handoff process exits.
                    process.send_signal(signal.SIGTERM)
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        kill_group(process)
                    raise
            if not idle(gpu):
                raise ValueError("GPU is busy; use scripts/wait_and_run_v6.sh for a natural handoff")
            assert lock.fd is not None
            return queue(root, args, lock, gpu)
    except (Exception, KeyboardInterrupt) as exc:
        event(root, "relay_stopped", reason=f"{type(exc).__name__}: {exc}")
        print(f"V6 stopped without starting another job: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
