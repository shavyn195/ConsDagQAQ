#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
export TOKENIZERS_PARALLELISM=false
export PYTHONPATH=/root/ConsDagV6Frozen/src
PY=/root/miniconda3/bin/python
BASE=/root/consdag_audits/architecture_20261125
"$PY" tests/test_constraint_alignment.py
timeout 3600 nice -n 15 "$PY" -u scripts/architecture/run_alignment_pilot.py \
  --project-root /root/ConsDagV6Frozen \
  --config configs/architecture_alignment_20261125.json \
  --out "$BASE/alignment_smoke_v1" --smoke
timeout 3600 nice -n 15 "$PY" -u scripts/architecture/run_alignment_pilot.py \
  --project-root /root/ConsDagV6Frozen \
  --config configs/architecture_alignment_20261125.json \
  --out "$BASE/alignment_pilot_v1"
