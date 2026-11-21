#!/usr/bin/env bash
# E1 v4 正式队列：同一服务器、同一 git 提交、同一依赖；bf16、seed 42；串行 Qwen3-0.6B -> 1.7B -> 4B。
# 每个模型先跑 2 步 smoke（不评测），通过后跑完整 zero-shot -> LoRA -> trained 评测；
# 单个模型失败（含 NaN 防护触发）只记录、不中断后续模型。用法：bash scripts/run_e1_queue_v4.sh
set -u
cd "$(dirname "$0")/.."
PY=${PY:-/root/miniconda3/bin/python}
DATA=data/processed_v4
MANIFEST=outputs/e1_v4_queue_manifest.jsonl
mkdir -p outputs/e1 outputs/e1_preflight
echo "{\"event\":\"queue_start\",\"time\":\"$(date -Is)\",\"commit\":\"$(git rev-parse HEAD)\"}" >> "$MANIFEST"
for spec in Qwen3-0.6B:48 Qwen3-1.7B:32 Qwen3-4B:16; do
  M=${spec%%:*}; BS=${spec##*:}
  OUT=outputs/e1/${M}-v4
  if [ -f "$OUT/metrics.json" ]; then
    echo "{\"event\":\"skip_done\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"; continue
  fi
  if ! $PY -u src/run_e1.py --model models/$M --data-dir $DATA --precision bf16 --seed 42 \
      --out-dir outputs/e1_preflight/${M}-v4 --skip-zeroshot --smoke-train-steps 2 \
      > outputs/e1_preflight/${M}-v4.log 2>&1; then
    echo "{\"event\":\"smoke_failed\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"; continue
  fi
  echo "{\"event\":\"train_start\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
  if $PY -u src/run_e1.py --model models/$M --data-dir $DATA --precision bf16 --seed 42 \
      --out-dir "$OUT" --eval-batch-size "$BS" > outputs/e1/${M}-v4.log 2>&1; then
    echo "{\"event\":\"done\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
  else
    echo "{\"event\":\"failed\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
  fi
done
echo "{\"event\":\"queue_end\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
