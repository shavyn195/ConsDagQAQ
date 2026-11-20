# 从 ModelScope 下载干净的基座模型到项目 models/ 目录
# 用途：避免使用可能被旧任务污染的 HF 缓存
import sys
from pathlib import Path

from modelscope import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ["Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B"]

for model_id in TARGETS:
    local_dir = ROOT / "models" / model_id.split("/")[-1]
    print(f"下载 {model_id} -> {local_dir}", flush=True)
    path = snapshot_download(model_id, local_dir=str(local_dir))
    print(f"完成: {path}", flush=True)

print("ALL DONE", flush=True)
