"""Kaggle entrypoint for the bounded compiler pilot."""

from pathlib import Path
import subprocess
import sys
import json
import zipfile

root = Path(__file__).resolve().parent
asset_mount = Path("/kaggle/input")
asset_root = next(
    (script.parent.parent for script in asset_mount.rglob("run_pilot.py")
     if script.parent.name == "src"),
    None,
)
if asset_root is None:
    asset_archive = next(asset_mount.rglob("experiment_assets.zip"), None)
    if asset_archive is not None:
        asset_root = Path("/kaggle/working/consdag_assets")
        asset_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(asset_archive) as archive:
            archive.extractall(asset_root)
if asset_root is None:
    asset_root = root
print(json.dumps({"asset_root": str(asset_root)}, ensure_ascii=False))

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

try:
    import transformers  # noqa: F401
    import peft  # noqa: F401
except ImportError:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-U", "transformers>=4.51.0", "peft>=0.15.0", "accelerate>=1.6.0", "sentencepiece>=0.2.0"],
        check=True,
    )
subprocess.run(
    [sys.executable, str(asset_root / "src" / "run_pilot.py"),
     "--train", str(asset_root / "data" / "processed" / "train.jsonl"),
     "--test", str(asset_root / "data" / "processed" / "test.jsonl"),
     "--output", "/kaggle/working/outputs/pilot_run.json",
     "--adapter-output", "/kaggle/working/outputs/adapter",
     "--prediction-dir", "/kaggle/working/outputs/predictions",
     "--max-steps", "75", "--max-train-examples", "500"],
    check=True,
)
