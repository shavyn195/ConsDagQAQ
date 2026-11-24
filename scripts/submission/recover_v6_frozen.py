"""Recover an inventory-only interrupted release without changing sealed bytes.

Copies only the original seal inventory into an isolated root, validates any
completed job, and resumes after the currently running submission supervisor.
No training process is signalled. The existing 30-hour accounting is retained.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def prepare(source, target):
    seal_path = Path("configs/v6_release_sha256.json")
    seal = json.loads((source / seal_path).read_text())
    for name, expected in seal["sha256"].items():
        if sha(source / name) != expected:
            raise ValueError(f"Original sealed content changed: {name}")
    target.mkdir(parents=True, exist_ok=True)
    for name in [*seal["sha256"], str(seal_path)]:
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            if sha(dest) != sha(source / name):
                raise ValueError(f"Different isolated file: {name}")
        else:
            shutil.copy2(source / name, dest)
    for name in ["models", "outputs"]:
        dest = target / name
        if not dest.exists():
            dest.symlink_to(source / name, target_is_directory=True)
        if dest.resolve() != (source / name).resolve():
            raise ValueError(f"Unexpected link: {name}")
    sys.path.insert(0, str(target / "src"))
    import run_v6_relay as relay
    relay.check_release(target)
    state_path = source / "outputs/e1_v6/queue_state.json"
    state = relay.read(state_path)
    if state["active"] is not None:
        raise ValueError("Active reservation needs a separate audit")
    recovered = []
    for run in sorted((source / "outputs/e1_v6").glob("Qwen*-v6-seed*")):
        if not run.is_dir() or not (run / "metrics.json").exists():
            continue
        provenance = relay.read(run / "provenance.json")
        expected = {k: provenance[k] for k in (
            "config", "data_sha256", "source_sha256", "model_sha256", "environment", "gpu", "git")}
        if (expected["source_sha256"] != seal["sha256"] or relay.environment() != expected["environment"]
                or relay.model_hashes(target, Path(expected["config"]["model"]).name) != expected["model_sha256"]):
            raise ValueError("Source, model or environment differs from the original run")
        if relay.provenance_record(expected)["fingerprint"] != provenance["fingerprint"]:
            raise ValueError("Provenance fingerprint differs")
        artifacts = relay.validate_artifacts(target, run, expected)
        if (run / "completion.json").exists():
            if relay.read(run / "completion.json")["artifact_sha256"] != artifacts:
                raise ValueError("Existing completed artifacts differ")
            continue
        last = state["last_job"]
        if (last["outcome"] != "complete" or last["seed"] != expected["config"]["seed"]
                or last["model"] != Path(expected["config"]["model"]).name
                or "Release file inventory" not in state.get("failure", "")):
            raise ValueError("Incomplete run is not the audited inventory-only interruption")
        relay.write(run / "completion.json", relay.completion_record(expected, artifacts))
        recovered.append(run.name)
    audit = {"source": str(source), "isolated_root": str(target), "time": relay.utc(),
             "reason": "Only unsealed submission scripts were added; every sealed byte still matches",
             "recovered_completion": recovered, "budget_seconds_used": state["gpu_seconds_used"],
             "original_failure_preserved": state.get("failure"), "release_seal_sha256": sha(source / seal_path)}
    audit_path = source / "outputs/submission/audit_20261125/v6_recovery.json"
    previous = relay.read(audit_path) if audit_path.exists() else {}
    audit["all_recovered_completion"] = sorted(set(recovered) | set(
        previous.get("all_recovered_completion", previous.get("recovered_completion", []))))
    with audit_path.with_suffix(".jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(audit) + "\n")
    relay.write(audit_path, audit)
    print(json.dumps(audit), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=Path("/root/ConsDagV5"))
    p.add_argument("--target", type=Path, default=Path("/root/ConsDagV6Frozen"))
    p.add_argument("--after-pid", type=int)
    p.add_argument("--public-control-root", type=Path,
                   help="Run the validated public-input E2 control after the current supervisor, before v6")
    a = p.parse_args()
    prepare(a.source, a.target)
    if a.after_pid is None:
        return
    process = Path(f"/proc/{a.after_pid}")
    # Hold an identity using Linux start time, so a reused PID does not block us.
    initial = (process / "stat").read_text().rsplit(")", 1)[1].split()[19] if process.exists() else None
    while process.exists():
        try:
            current = (process / "stat").read_text().rsplit(")", 1)[1].split()[19]
        except FileNotFoundError:
            break
        if current != initial:
            break
        time.sleep(30)
    if a.public_control_root:
        import run_v6_relay as relay
        gpu = relay.gpu_state("0")
        relay.require_device(gpu)
        with relay.GpuLock(gpu["uuid"]) as lock:
            relay.wait_idle(a.target, "0", 30)
            log = a.source / "outputs/submission/e2_public_contract.log"
            with log.open("a") as stream:
                status = subprocess.call([sys.executable, "-u", "src/sub_e2_public_contract.py"],
                                         cwd=a.public_control_root, stdout=stream, stderr=subprocess.STDOUT,
                                         env=dict(os.environ, PYTHONPATH=str(a.source / "src"),
                                                  CUDA_VISIBLE_DEVICES="0", TOKENIZERS_PARALLELISM="false"),
                                         pass_fds=(lock.fd,))
            print(json.dumps({"event": "public_control_finished", "exit_code": status}), flush=True)
            # A failed new control stays failed; the independent frozen queue can proceed.
    env = dict(os.environ, GIT_DIR=str(a.source / ".git"), GIT_WORK_TREE=str(a.target))
    command = [sys.executable, "-u", "src/run_v6_relay.py", "--project-root", str(a.target),
               "--mode", "wait", "--budget-hours", "30", "--python", sys.executable]
    raise SystemExit(subprocess.call(command, cwd=a.target, env=env))


if __name__ == "__main__":
    main()
