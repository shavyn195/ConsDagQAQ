"""Hosted-GPU entrypoint for the bounded compiler pilot."""

from pathlib import Path
import subprocess
import sys
import json
import os
import hashlib
import time

root = Path(__file__).resolve().parent
asset_root = Path(os.environ.get("EXPERIMENT_ASSET_ROOT", root)).resolve()
output_root = Path(os.environ.get("EXPERIMENT_OUTPUT_ROOT", root / "outputs")).resolve()
output_root.mkdir(parents=True, exist_ok=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

try:
    import torch
    gpu_info = {
        "cuda_available": bool(torch.cuda.is_available()),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "gpu_count": torch.cuda.device_count(),
        "gpu_memory_gib": round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
        if torch.cuda.is_available() else None,
    }
except Exception as exc:
    gpu_info = {"cuda_available": False, "gpu_name": None, "gpu_count": 0, "gpu_memory_gib": None,
                "gpu_probe_error": repr(exc)}
print(json.dumps({"runtime_gpu": gpu_info}, ensure_ascii=False))

metadata = {
    "asset_root": str(asset_root),
    "output_root": str(output_root),
    "started_unix": time.time(),
    "runtime_gpu": gpu_info,
    "asset_sha256": {
        "train_jsonl": sha256(asset_root / "data" / "processed" / "train.jsonl"),
        "test_jsonl": sha256(asset_root / "data" / "processed" / "test.jsonl"),
        "run_pilot_py": sha256(asset_root / "src" / "run_pilot.py"),
    },
}

try:
    import torch
    import transformers
    import peft
    metadata["versions"] = {
        "python": sys.version,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "peft": peft.__version__,
    }
except Exception as exc:
    metadata["dependency_probe_error"] = repr(exc)

try:
    import transformers  # noqa: F401
    import peft  # noqa: F401
except ImportError:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.51.0", "peft>=0.15.0", "accelerate>=1.6.0", "sentencepiece>=0.2.0"],
        check=True,
    )
command = [sys.executable, str(asset_root / "src" / "run_pilot.py"),
           "--train", str(asset_root / "data" / "processed" / "train.jsonl"),
           "--test", str(asset_root / "data" / "processed" / "test.jsonl"),
           "--output", str(output_root / "pilot_run.json"),
           "--adapter-output", str(output_root / "adapter"),
           "--prediction-dir", str(output_root / "predictions"),
           "--max-steps", "75", "--max-train-examples", "500"]
metadata["command"] = command
(output_root / "run_metadata.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
with (output_root / "run_stdout.log").open("w", encoding="utf-8") as log:
    completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
metadata["return_code"] = completed.returncode
metadata["finished_unix"] = time.time()
(output_root / "run_metadata.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
if completed.returncode:
    raise SystemExit(completed.returncode)
