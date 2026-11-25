"""Run the registered v6 API arms serially without changing frozen sources.

Requires DASHSCOPE_API_KEY in the inherited environment. All predictions remain
in the frozen runner's own resumable caches; this only records orchestration.
"""
from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    audit = args.audit_dir.resolve()
    if not os.environ.get("DASHSCOPE_API_KEY"):
        raise RuntimeError("API credential missing; no request was started")
    sys.path.insert(0, str(root / "src"))
    from run_v6_relay import check_release

    check_release(root)
    audit.mkdir(parents=True, exist_ok=True)
    cache_root = root / "outputs/e1_v6_side"
    cache_root.mkdir(parents=True, exist_ok=True)
    lock = (cache_root / ".registered_queue.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    os.nice(10)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", TOKENIZERS_PARALLELISM="false", PYTHONUNBUFFERED="1")
    state = {
        "schema_version": 1, "status": "running", "pid": os.getpid(),
        "project_root": str(root), "credential_source": "inherited environment",
        "gpu_use": False, "arms": [],
    }

    def save() -> None:
        state["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        target = audit / "state.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
        print(json.dumps(state), flush=True)

    save()
    for model, style in (("deepseek-v4-pro-0813", "few"), ("qwen-max", "zero"), ("qwen-max", "few")):
        check_release(root)
        arm = {"model": model, "style": style, "status": "running", "workers": 8,
               "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        state["arms"].append(arm)
        save()
        command = [sys.executable, "-u", "src/run_pe_v6.py", "--model", model,
                   "--style", style, "--workers", "8"]
        started = time.monotonic()
        with (audit / f"{model}-{style}.log").open("a") as output:
            status = subprocess.call(command, cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT)
        arm.update(exit_code=status, elapsed_seconds=round(time.monotonic() - started, 3),
                   status="complete" if status == 0 else "failed")
        if status:
            state["status"] = "failed"
            save()
            return status
        save()
    check_release(root)
    with (audit / "analysis.log").open("a") as output:
        status = subprocess.call(
            [sys.executable, "-u", "src/analyze_v6_main.py", "--out", str(audit / "main_after_pe.json")],
            cwd=root, env=env, stdout=output, stderr=subprocess.STDOUT,
        )
    state.update(status="complete" if status == 0 else "analysis_failed", analysis_exit_code=status)
    save()
    return status


if __name__ == "__main__":
    raise SystemExit(main())
