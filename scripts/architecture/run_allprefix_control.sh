#!/usr/bin/env bash
# Sequential, low-priority CPU-only diagnostic. Frozen GPU relay is untouched.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
BASE=/root/consdag_audits/architecture_20261125
PY=/root/miniconda3/bin/python
export PYTHONPATH=/root/ConsDagV6Frozen/src
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
for SEED in 42 43; do
  timeout 3600 nice -n 15 "$PY" -u scripts/architecture/run_pointer_pilot.py \
    --lattice-dir "$BASE/s0" --model /root/autodl-tmp/models/Qwen3-0.6B \
    --out "$BASE/pilot_allprefix_seed$SEED" \
    --config "configs/architecture_allprefix_seed${SEED}_20261125.json" \
    --steps 1000 --train-groups 256 --dev-groups 300 --threads 2 \
    --project-root /root/ConsDagV6Frozen
  nice -n 15 "$PY" scripts/architecture/analyze_pointer_pilot.py \
    --run "$BASE/pilot_allprefix_seed$SEED" \
    --out "$BASE/pointer_allprefix_seed${SEED}_analysis.json"
done
