#!/usr/bin/env bash
# Frozen, inference-only diagnostics. No training, no preemption, no edits to the active checkout.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-/root/miniconda3/bin/python}
SOURCE=${SOURCE:-/root/ConsDagV5}
PANEL=data/diagnostic_v5_binding_20261123
mkdir -p outputs/v5_binding_diagnostic
exec 9>/tmp/consdag-v5-binding-diagnostic.lock
flock -n 9 || { echo "Diagnostic worker already exists"; exit 1; }
event() { "$PY" -c 'import json,sys,datetime; print(json.dumps({"time":datetime.datetime.now().astimezone().isoformat(),"event":sys.argv[1]}))' "$1"; }
gpu_idle() {
  local gpu_processes gpu_memory
  gpu_processes=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits) || return 1
  gpu_memory=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -n 1) || return 1
  [[ -z "$gpu_processes" && "$gpu_memory" =~ ^[0-9]+$ && "$gpu_memory" -lt 1024 ]]
}
queue_running() { pgrep -f '^bash scripts/run_e1_queue_v5.sh$' >/dev/null; }
deadline=$((SECONDS + 172800))
event waiting_for_registered_queue_and_idle_gpu
while queue_running || ! gpu_idle; do
  if (( SECONDS >= deadline )); then event stopped_after_48h_wait; exit 2; fi
  sleep 30
done
event registered_queue_finished
for arm in Qwen3-1.7B-v5-seed42 Qwen3-1.7B-v5-seed43 Qwen3-4B-v5-seed42; do
  model=${arm%-v5-seed*}
  test -f "$SOURCE/outputs/e1/$arm/metrics.json"
  test -f "$SOURCE/outputs/e1/$arm/adapter/adapter_config.json"
  test -d "$SOURCE/models/$model"
  # Re-check between arms; never compete with a newly started unrelated job.
  while queue_running || ! gpu_idle; do
    if (( SECONDS >= deadline )); then event stopped_after_48h_wait; exit 2; fi
    sleep 30
  done
  event "start_$arm"
  "$PY" -u src/run_v5_diagnostic_panel.py --model "$SOURCE/models/$model" \
    --adapter "$SOURCE/outputs/e1/$arm/adapter" --panel "$PANEL" \
    --out "outputs/v5_binding_diagnostic/$arm"
  event "completed_$arm"
done
event complete
