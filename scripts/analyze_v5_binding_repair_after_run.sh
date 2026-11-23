#!/usr/bin/env bash
# Separate CPU analysis; never changes the registered GPU jobs or raw results.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-/root/miniconda3/bin/python}
PANEL=data/diagnostic_v5_binding_20261123
RUNS=outputs/v5_binding_diagnostic
OUT=outputs/v5_binding_repair_analysis.json
mkdir -p outputs
exec 9>/tmp/consdag-v5-binding-repair-analysis.lock
flock -n 9 || exit 1
event() { "$PY" -c 'import datetime,json,sys; print(json.dumps({"time":datetime.datetime.now().astimezone().isoformat(),"event":sys.argv[1]}))' "$1"; }
ready() {
  local arm
  for arm in Qwen3-1.7B-v5-seed42 Qwen3-1.7B-v5-seed43 Qwen3-4B-v5-seed42; do
    test -f "$RUNS/$arm/metrics.json" || return 1
  done
}
if test -f "$OUT"; then event existing_result_preserved; exit 0; fi
deadline=$((SECONDS + 172800))
event waiting_for_complete_binding_predictions
while ! ready; do
  if (( SECONDS >= deadline )); then event stopped_after_48h; exit 2; fi
  if ! pgrep -f '^bash scripts/run_v5_binding_after_queue.sh$' >/dev/null; then
    event incomplete_outputs_and_no_diagnostic_worker; exit 3
  fi
  sleep 30
done
event analysis_start
CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 nice -n 10 "$PY" src/analyze_v5_binding_repair.py \
  --panel "$PANEL" --runs "$RUNS" --protocol configs/v5_binding_repair_analysis.json --out "$OUT"
event analysis_complete
