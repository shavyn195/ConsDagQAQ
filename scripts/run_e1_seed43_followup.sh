#!/usr/bin/env bash
# Follow-up E1 replication: wait for the current 1.7B seed-43 run, then
# serialize the remaining 0.6B and 4B seed-43 runs on the same GPU.
set -u
cd "$(dirname "$0")/.."
PY=${PY:-/root/miniconda3/bin/python}
DATA=data/processed_v4
MANIFEST=outputs/e1_seed43_followup_manifest.jsonl
mkdir -p outputs/e1 outputs/e1_preflight

echo "{\"event\":\"followup_start\",\"time\":\"$(date -Is)\",\"commit\":\"$(git rev-parse HEAD)\"}" >> "$MANIFEST"

# Wait only while the known Python training PID still owns this output path.
PRIOR_PID=${PRIOR_PID:-100368}
while [ -r "/proc/$PRIOR_PID/cmdline" ]; do
  if tr '\0' ' ' < "/proc/$PRIOR_PID/cmdline" | grep -F -- 'outputs/e1/Qwen3-1.7B-v4-seed43' >/dev/null; then
    sleep 60
  else
    break
  fi
done
echo "{\"event\":\"prior_1.7B_finished\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"

for spec in Qwen3-0.6B:48 Qwen3-4B:16; do
  M=${spec%%:*}; BS=${spec##*:}
  OUT=outputs/e1/${M}-v4-seed43
  if [ -f "$OUT/metrics.json" ]; then
    echo "{\"event\":\"skip_done\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
    continue
  fi
  if ! $PY -u src/run_e1.py --model models/$M --data-dir "$DATA" --precision bf16 --seed 43 \
      --out-dir "outputs/e1_preflight/${M}-v4-seed43" --skip-zeroshot --smoke-train-steps 2 \
      > "outputs/e1_preflight/${M}-v4-seed43.log" 2>&1; then
    echo "{\"event\":\"smoke_failed\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
    continue
  fi
  echo "{\"event\":\"train_start\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
  if $PY -u src/run_e1.py --model models/$M --data-dir "$DATA" --precision bf16 --seed 43 \
      --out-dir "$OUT" --eval-batch-size "$BS" --max-seq-len 1280 --max-new-tokens 384 \
      --epochs 3 --learning-rate 2e-4 --lora-rank 16 --lora-alpha 32 --gradient-accumulation-steps 4 \
      > "outputs/e1/${M}-v4-seed43.log" 2>&1; then
    echo "{\"event\":\"done\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
  else
    echo "{\"event\":\"failed\",\"model\":\"$M\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
  fi
done
echo "{\"event\":\"followup_end\",\"time\":\"$(date -Is)\"}" >> "$MANIFEST"
