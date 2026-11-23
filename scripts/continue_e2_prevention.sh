#!/usr/bin/env bash
# One bounded extension after all original seed replications finish.
set -euo pipefail
cd "$(dirname "$0")/.."
py=/root/miniconda3/bin/python
d=outputs/e2_v4/action-credit-1.7B-pilot-v1
out="$d/preventive-comparison-v1"
run=src/run_e2_prevention.py
exec 7>"$out/continuation.lock"
flock -n 7 || exit 75
echo "$(date -Is) waiting for original seeds" >> "$out/events.log"
exec 8>"$d/replication.lock"
flock -w 7200 8
exec 9>"$d/queue.lock"
flock -w 600 9
for seed in 42 43 44; do test -s "$d/paired-dev-s$seed.json"; done
code=0
"$py" "$run" gate || code=$?
if [ "$code" -eq 3 ]; then echo "$(date -Is) original method cleared revision gate" >> "$out/events.log"; exit 0; fi
if [ "$code" -ne 0 ]; then exit "$code"; fi
trap 'echo "$(date -Is) failure at line $LINENO" >> "$out/events.log"' ERR
for seed in 42 43 44; do
  for arm in protect protect_shifted; do
    echo "$(date -Is) train $arm $seed" >> "$out/events.log"
    "$py" -u "$run" train --arm "$arm" --seed "$seed" >"$out/train-$arm-$seed.log" 2>&1
  done
  for arm in trace action protect protect_shifted; do
    echo "$(date -Is) dev $arm $seed" >> "$out/events.log"
    "$py" -u "$run" assess --arm "$arm" --seed "$seed" >"$out/dev-$arm-$seed.log" 2>&1
  done
done
"$py" "$run" compare
echo "$(date -Is) done" >> "$out/events.log"
