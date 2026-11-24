#!/usr/bin/env bash
# GPU 串行接力（2026-11-25）：E2 信息对齐版 -> E3 四臂消融
# 由 2026-11-24 深夜审计触发：旧 E2 复用编译器提示，单体看不到任务结构，对照不公平；
# E3 存在 N 误报字段 bug 与 A1 自由文本下游恒 0 的口径缺陷，已修。
set -u
cd "$(dirname "$0")/../.."
PY=${PY:-/root/miniconda3/bin/python}
LOG=outputs/submission/queue2.log
mkdir -p outputs/submission

log() { echo "{\"event\":\"$1\",\"time\":\"$(date -Is)\"${2:+,$2}}" | tee -a "$LOG"; }

wait_gpu() {
  while true; do
    used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')
    if [ "${used:-99999}" -lt 2000 ] && ! pgrep -f "sub_e2_monolithic.py|sub_e3_ablation.py" >/dev/null; then return 0; fi
    sleep 60
  done
}

log queue2_start
wait_gpu
log gpu_free

# 1) E2 信息对齐版（同底座 1.7B、同数据、同预算、bf16、seed 42）
OUT=outputs/submission/e2_monolithic_informed
if [ ! -f "$OUT/metrics.json" ]; then
  log e2_informed_start
  $PY -u src/sub_e2_monolithic.py --prompt-mode informed --data-dir data/processed_v5 \
      --model models/Qwen3-1.7B --pipeline-run outputs/e1/Qwen3-1.7B-v5-seed42 \
      --seed 42 --precision bf16 --out-dir "$OUT" >> outputs/submission/e2_informed.log 2>&1 \
    && log e2_informed_done || log e2_informed_failed
else
  log e2_informed_skip
fi

# 2) E3 四臂（0.6B，seed 42，bf16）：A3 -> A4 -> A2 -> A1
for ARM in A3 A4 A2 A1; do
  OUT=outputs/submission/e3_${ARM}
  if [ -f "$OUT/metrics.json" ]; then log "e3_skip" "\"arm\":\"$ARM\""; continue; fi
  wait_gpu
  log e3_start "\"arm\":\"$ARM\""
  $PY -u src/sub_e3_ablation.py --arm $ARM --data-dir data/processed_v5 \
      --model models/Qwen3-0.6B --baseline-run outputs/e1/Qwen3-0.6B-v5-seed42 \
      --seed 42 --precision bf16 --out-dir "$OUT" >> "outputs/submission/e3_${ARM}.log" 2>&1 \
    && log e3_done "\"arm\":\"$ARM\"" || log e3_failed "\"arm\":\"$ARM\""
done

log queue2_end
