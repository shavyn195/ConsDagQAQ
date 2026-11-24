#!/usr/bin/env bash
# Run in a persistent session. Never interrupts the existing v5 process.
set -euo pipefail
PY=${PY:-/root/miniconda3/bin/python}
PROJECT_ROOT=${PROJECT_ROOT:-/root/ConsDagV5}
cd "$PROJECT_ROOT"
exec "$PY" src/run_v6_relay.py --mode wait "$@"
