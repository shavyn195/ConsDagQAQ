#!/usr/bin/env bash
# E1 v5 正式队列（设计见 reports/design_v5_ccfb.md §6–§8）。
# 同一服务器、同一 git 提交、bf16；超参与 v4 完全相同（LoRA r16/α32/0.05，lr 2e-4，3 epoch，grad-accum 4，
# max_seq 1280，max_new 384）。顺序按"先能回答主问题"排：1.7B/4B 三个种子在前，0.6B 在后。
# - 启动前：数据 sha256 必须与已提交的 data/processed_v5/generation_report.json 一致，否则拒绝启动；
# - 若同机已有 run_e1.py 进程（例如旧工作区 v4 seed43 的收尾评测），先等它结束，不并发抢 GPU；
# - 每个 (模型, 种子) 先跑 2 步 smoke；零样本只在 seed 42 跑一次（确定性解码，与种子无关）；
# - 单个任务失败（含 NaN 防护触发）只记录、不中断后续任务；完成后立即用 CPU 重算 faithful 等辅助指标。
# 用法：bash scripts/run_e1_queue_v5.sh   （可用 PLAN="Qwen3-1.7B:32:42 ..." 覆盖队列）
set -u
cd "$(dirname "$0")/.."
PY=${PY:-/root/miniconda3/bin/python}
DATA=data/processed_v5
MANIFEST=outputs/e1_v5_queue_manifest.jsonl
PLAN=${PLAN:-"Qwen3-1.7B:32:42 Qwen3-4B:16:42 Qwen3-1.7B:32:43 Qwen3-4B:16:43 Qwen3-1.7B:32:44 Qwen3-4B:16:44 Qwen3-0.6B:48:42 Qwen3-0.6B:48:43 Qwen3-0.6B:48:44"}
mkdir -p outputs/e1 outputs/e1_preflight outputs/e1_v5_side
log() { echo "{\"event\":\"$1\",\"time\":\"$(date -Is)\"${2:+,$2}}" >> "$MANIFEST"; }

if ! $PY - <<'EOF'
import hashlib, json, sys
want = json.load(open("data/processed_v5/generation_report.json"))["sha256"]
got = {s: hashlib.sha256(open(f"data/processed_v5/{s}.jsonl", "rb").read()).hexdigest() for s in want}
sys.exit(0 if got == want else 1)
EOF
then
  log data_sha_mismatch; echo "data sha256 mismatch; regenerate with src/build_dataset_v5.py" >&2; exit 1
fi
log queue_start "\"commit\":\"$(git rev-parse HEAD)\""

while pgrep -f "src/run_e1.py" >/dev/null; do sleep 60; done
log gpu_free

for spec in $PLAN; do
  IFS=: read -r M BS S <<< "$spec"
  OUT=outputs/e1/${M}-v5-seed${S}
  TAG="\"model\":\"$M\",\"seed\":$S"
  if [ -f "$OUT/metrics.json" ]; then log skip_done "$TAG"; continue; fi
  if ! $PY -u src/run_e1.py --model models/$M --data-dir $DATA --precision bf16 --seed "$S" \
      --out-dir "outputs/e1_preflight/${M}-v5-seed${S}" --skip-zeroshot --smoke-train-steps 2 \
      > "outputs/e1_preflight/${M}-v5-seed${S}.log" 2>&1; then
    log smoke_failed "$TAG"; continue
  fi
  ZS=""; [ "$S" = "42" ] || ZS="--skip-zeroshot"
  log train_start "$TAG"
  if $PY -u src/run_e1.py --model models/$M --data-dir $DATA --precision bf16 --seed "$S" $ZS \
      --out-dir "$OUT" --eval-batch-size "$BS" --max-seq-len 1280 --max-new-tokens 384 \
      --epochs 3 --learning-rate 2e-4 --lora-rank 16 --lora-alpha 32 --gradient-accumulation-steps 4 \
      > "outputs/e1/${M}-v5-seed${S}.log" 2>&1; then
    log done "$TAG"
    for pair in trained:trained zero:zeroshot; do
      pred="$OUT/${pair#*:}_predictions"
      res="outputs/e1_v5_side/${pair%:*}-${M}-seed${S}.json"
      if [ -d "$pred" ] && [ ! -e "$res" ]; then
        nice -n 10 $PY src/rescore_v4_side.py --data $DATA --pred "$pred" --out "$res" \
          && log rescored "$TAG,\"kind\":\"${pair%:*}\""
      fi
    done
  else
    log failed "$TAG"
  fi
done
log queue_end
