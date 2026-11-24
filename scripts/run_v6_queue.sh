#!/usr/bin/env bash
# Full bf16 experiments only. The Python scheduler enforces the single-GPU
# lock, immutable provenance, fail-closed completion checks and 30-hour cap.
set -euo pipefail
PY=${PY:-/root/miniconda3/bin/python}
PROJECT_ROOT=${PROJECT_ROOT:-/root/ConsDagV5}
cd "$PROJECT_ROOT"
exec "$PY" src/run_v6_relay.py --mode queue "$@"
