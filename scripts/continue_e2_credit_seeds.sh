#!/usr/bin/env bash
# The continuation depends on train signal coverage, never the dev win/loss direction.
set -euo pipefail
cd "$(dirname "$0")/.."
py=/root/miniconda3/bin/python
d=outputs/e2_v4/action-credit-1.7B-pilot-v1
exec 8>"$d/replication.lock"
flock -n 8 || exit 75
exec 9>"$d/queue.lock"
flock -w 3600 9
export PYTHONPATH="$PWD/src"
for arm in trace action shifted function; do test -s "$d/$arm-s42/done.json"; done
if ! "$py" src/summarize_e2_credit.py --seed 42 --require-signal; then
  echo "$(date -Is) replication held; inspect paired-dev-s42 and train coverage" | tee -a "$d/events.log"
  exit 1
fi
for seed in 43 44; do
  for arm in trace action shifted function; do
    run="$d/$arm-s$seed"
    if test -s "$run/done.json"; then continue; fi
    test ! -e "$run"
    echo "$(date -Is) start $arm seed $seed" | tee -a "$d/events.log"
    if ! "$py" -u src/train_e2_credit.py --seed "$seed" --arm "$arm" >"$d/$arm-s$seed.log" 2>&1; then
      echo "$(date -Is) failed $arm seed $seed" | tee -a "$d/events.log"
      exit 1
    fi
    echo "$(date -Is) done $arm seed $seed" | tee -a "$d/events.log"
  done
  "$py" src/summarize_e2_credit.py --seed "$seed"
done
echo "$(date -Is) bounded replication finished" | tee -a "$d/events.log"
