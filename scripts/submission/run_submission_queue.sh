#!/bin/bash
# 投稿实验 GPU 接力队列：等 v6 主表队列结束后，依次执行 E2(B1 单体) -> E3(A3/A4/A2/A1 字段消融)。
# 前置条件：src/sub_e2_monolithic.py、src/sub_e3_ablation.py 已同步到服务器同路径。
# 用法：nohup bash scripts/submission/run_submission_queue.sh > /dev/null 2>&1 &
set -u
ROOT=/root/ConsDagV5
PY=/root/miniconda3/bin/python
OUT=$ROOT/outputs/submission
mkdir -p "$OUT"
LOG=$OUT/queue_launch.log

log() { echo "{\"event\":\"$1\",\"time\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" >> "$LOG"; }

log "submission_queue_start pid=$$"

# 1. 等 v6 主表队列进程结束（不 kill、不干扰）
while pgrep -f "run_v6_relay.py --mode queue" > /dev/null; do
  log "wait_v6_queue"
  sleep 300
done
log "v6_queue_done"

# 2. 等 GPU 真正空闲（显存 < 2GiB）
while true; do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
  if [ "${used:-99999}" -lt 2000 ]; then break; fi
  log "wait_gpu_free used_mib=$used"
  sleep 120
done
log "gpu_free"

cd "$ROOT" || { log "cd_failed"; exit 1; }

# 3. E2：B1 单体对照（1.7B，同底座同数据同预算，~8.5h）
log "e2_start"
$PY src/sub_e2_monolithic.py \
  --data-dir data/processed_v5 \
  --model models/Qwen3-1.7B \
  --pipeline-run outputs/e1/Qwen3-1.7B-v5-seed42 \
  --seed 42 --precision bf16 \
  --out-dir outputs/submission/e2_monolithic \
  > "$OUT/e2.log" 2>&1
log "e2_done code=$?"

# 4. E3：A 系字段消融（0.6B 单 seed，按方案顺序 A3 -> A4 -> A2 -> A1）
for arm in A3 A4 A2 A1; do
  log "e3_${arm}_start"
  $PY src/sub_e3_ablation.py \
    --arm "$arm" \
    --data-dir data/processed_v5 \
    --model models/Qwen3-0.6B \
    --seed 42 --precision bf16 \
    --out-dir "outputs/submission/e3_ablation/$arm" \
    > "$OUT/e3_${arm}.log" 2>&1
  log "e3_${arm}_done code=$?"
done

log "submission_queue_done"
