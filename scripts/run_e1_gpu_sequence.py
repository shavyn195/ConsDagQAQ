"""Run audited BF16 E1 diagnostics sequentially on the remote GPU server."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_HASHES = {
    "train.jsonl": "4358c60dc196bf596a69b278e7beb9ce370a41de9c6abe624e88b59c73d91091",
    "dev.jsonl": "143619f3c26f64ce1cd6de641effdf182b4385588845d724006d6bdf094423df",
    "test_tpl_ho.jsonl": "44083a84831e0eafea933aa3250d48fc9c1da5d49a706037b19694d1f73cf003",
    "test_tool_ho.jsonl": "363b3f0b584f168bc41486910f94d4a23e55aebc93625d1a0e5c064217362241",
}
MODEL_ORDER = ["Qwen3-0.6B", "Qwen3-1.7B", "Qwen3-4B"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_logged(command: list[str], log_path: Path, cwd: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write(json.dumps({"command": command, "started_at": utc_now()}, ensure_ascii=False) + "\n")
        log.flush()
        result = subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=False)
        log.write(json.dumps({"return_code": result.returncode, "finished_at": utc_now()}) + "\n")
        log.flush()
    return result.returncode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", choices=MODEL_ORDER, default=MODEL_ORDER)
    parser.add_argument("--out-root", type=Path, default=ROOT / "outputs" / "gpu_e1_scope_context_20261121")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--max-seq-len", type=int, default=1024)
    parser.add_argument("--max-new-tokens", type=int, default=384)
    parser.add_argument("--eval-batch-size", type=int, default=16)
    parser.add_argument(
        "--skip-zeroshot", action="store_true",
        help="Skip the duplicate zero-shot pass in full runs; use a separately frozen zero-shot run when needed.",
    )
    parser.add_argument("--smoke-steps", type=int, default=2)
    args = parser.parse_args()

    data_dir = ROOT / "data" / "processed_v2"
    observed_hashes = {name: sha256(data_dir / name) for name in DATA_HASHES}
    if observed_hashes != DATA_HASHES:
        raise SystemExit(f"frozen dataset hash mismatch: expected={DATA_HASHES}, observed={observed_hashes}")

    code_hash = sha256(ROOT / "src" / "run_e1.py")
    manifest_path = args.out_root / "sequence_manifest.json"
    manifest: dict[str, Any] = {
        "experiment": "E1 scope-context diagnostic rerun",
        "claim_status": "synthetic feasibility only; not CCF-B evidence",
        "started_at": utc_now(),
        "status": "running",
        "host": os.uname().nodename,
        "gpu": subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,compute_cap", "--format=csv,noheader"],
                              capture_output=True, text=True, check=False).stdout.strip(),
        "dataset": {"version": "processed_v2", "sha256": observed_hashes},
        "runner_sha256": code_hash,
        "config": {
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "lora_rank": args.lora_rank,
            "lora_alpha": args.lora_alpha,
            "gradient_accumulation_steps": args.gradient_accumulation_steps,
            "max_seq_len": args.max_seq_len,
            "max_new_tokens": args.max_new_tokens,
            "eval_batch_size": args.eval_batch_size,
            "seed": args.seed,
            "precision": "bf16",
            "smoke_steps": args.smoke_steps,
        },
        "models": [],
    }
    atomic_json(manifest_path, manifest)

    python = sys.executable
    script = str(ROOT / "src" / "run_e1.py")
    common = [
        "--epochs", str(args.epochs),
        "--learning-rate", str(args.learning_rate),
        "--lora-rank", str(args.lora_rank),
        "--lora-alpha", str(args.lora_alpha),
        "--gradient-accumulation-steps", str(args.gradient_accumulation_steps),
        "--max-seq-len", str(args.max_seq_len),
        "--max-new-tokens", str(args.max_new_tokens),
        "--seed", str(args.seed),
        "--precision", "bf16",
    ]

    for model_name in args.models:
        model_path = ROOT / "models" / model_name
        if not (model_path / "config.json").is_file() or not list(model_path.glob("*.safetensors")):
            raise SystemExit(f"model files are missing or incomplete: {model_path}")

        run_dir = args.out_root / f"{model_name}-seed{args.seed}-bf16"
        smoke_dir = run_dir / "preflight_smoke"
        run_record: dict[str, Any] = {
            "model": model_name,
            "model_path": str(model_path),
            "status": "smoke_running",
            "started_at": utc_now(),
            "runner_sha256": code_hash,
            "dataset_sha256": observed_hashes,
            "config": manifest["config"],
        }
        # Keep evaluation within the 32 GB card while avoiding an unnecessarily
        # small batch for the two smaller backbones. The 4B setting matches the
        # previously validated batch size.
        model_eval_batch = {
            "Qwen3-0.6B": max(args.eval_batch_size, 64),
            "Qwen3-1.7B": max(args.eval_batch_size, 32),
            "Qwen3-4B": args.eval_batch_size,
        }[model_name]
        run_record["eval_batch_size_effective"] = model_eval_batch
        run_record["skip_zeroshot"] = args.skip_zeroshot
        manifest["models"].append(run_record)
        atomic_json(manifest_path, manifest)

        smoke_cmd = [
            python, "-u", script, "--model", str(model_path), "--data-dir", str(data_dir),
            "--out-dir", str(smoke_dir), "--skip-zeroshot", "--smoke-train-steps", str(args.smoke_steps),
            *common,
        ]
        started = time.monotonic()
        rc = run_logged(smoke_cmd, run_dir / "smoke.log", ROOT)
        run_record["smoke_seconds"] = round(time.monotonic() - started, 1)
        run_record["smoke_return_code"] = rc
        if rc != 0 or not (smoke_dir / "smoke.json").is_file():
            run_record.update({"status": "smoke_failed", "finished_at": utc_now()})
            manifest.update({"status": "stopped_on_smoke_failure", "finished_at": utc_now()})
            atomic_json(manifest_path, manifest)
            raise SystemExit(f"{model_name} smoke failed; queue stopped")

        run_record["status"] = "training_and_eval_running"
        run_record["full_run_started_at"] = utc_now()
        atomic_json(manifest_path, manifest)
        full_cmd = [python, "-u", script, "--model", str(model_path), "--data-dir", str(data_dir),
                    "--out-dir", str(run_dir), "--eval-batch-size", str(model_eval_batch), *common]
        if args.skip_zeroshot:
            full_cmd.append("--skip-zeroshot")
        started = time.monotonic()
        rc = run_logged(full_cmd, run_dir / "run.log", ROOT)
        run_record["full_run_seconds"] = round(time.monotonic() - started, 1)
        run_record["return_code"] = rc
        metrics_path = run_dir / "metrics.json"
        adapter_path = run_dir / "adapter" / "adapter_config.json"
        if rc == 0 and metrics_path.is_file() and adapter_path.is_file():
            run_record.update({
                "status": "complete",
                "finished_at": utc_now(),
                "metrics_sha256": sha256(metrics_path),
                "adapter_config_sha256": sha256(adapter_path),
            })
        else:
            run_record.update({"status": "failed", "finished_at": utc_now()})
            manifest.update({"status": "stopped_on_model_failure", "finished_at": utc_now()})
            atomic_json(manifest_path, manifest)
            raise SystemExit(f"{model_name} failed; queue stopped")

        atomic_json(manifest_path, manifest)

    manifest.update({"status": "complete", "finished_at": utc_now()})
    atomic_json(manifest_path, manifest)
    print(f"sequence complete: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
