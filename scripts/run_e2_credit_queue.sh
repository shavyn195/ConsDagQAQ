#!/usr/bin/env bash
# A bounded four-arm pilot; complete existing artifacts are never overwritten.
set -euo pipefail
cd "$(dirname "$0")/.."
py=/root/miniconda3/bin/python
out=outputs/e2_v4/action-credit-1.7B-pilot-v1
exec 9>"$out/queue.lock"
flock -n 9 || exit 75
test -s "$out/cache-ready.json"
test -s "$out/warm/dev-scores.json"
export PYTHONPATH="$PWD/src"
"$py" scripts/check_e2_credit_values.py
for arm in trace action shifted function; do
  run="$out/${arm}-s42"
  if test -s "$run/done.json"; then continue; fi
  test ! -e "$run" || { echo "partial output: $run; inspect before retry"; exit 1; }
  echo "$(date -Is) start $arm" | tee -a "$out/events.log"
  if ! "$py" -u src/train_e2_credit.py --arm "$arm" --seed 42 >"$out/$arm.log" 2>&1; then
    echo "$(date -Is) failed $arm" | tee -a "$out/events.log"
    exit 1
  fi
  test -s "$run/done.json"
  echo "$(date -Is) done $arm" | tee -a "$out/events.log"
done
echo "$(date -Is) finished" | tee -a "$out/events.log"
