#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-/root/miniconda3/bin/python}
# Credentials come only from DASHSCOPE_API_KEY. A verified complete cache can
# resume without a key; the Python runner requires it before any new request.
"$PY" src/run_pe_v6.py --model deepseek-v4-pro-0813 --style few
"$PY" src/run_pe_v6.py --model qwen-max --style zero
"$PY" src/run_pe_v6.py --model qwen-max --style few
"$PY" src/analyze_v6_main.py
