"""The shell entry point delegates the full queue to the audited scheduler."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_v6_queue.sh"
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
BASH = str(GIT_BASH) if os.name == "nt" and GIT_BASH.exists() else shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="Bash is required for queue wrapper tests")


def test_queue_wrapper_is_valid_bash_and_uses_fixed_scheduler_contract():
    result = subprocess.run([BASH, "-n", str(SCRIPT)], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    source = SCRIPT.read_text(encoding="utf-8")
    assert "exec \"$PY\" src/run_v6_relay.py --mode queue \"$@\"" in source
    assert "PY=${PY:-/root/miniconda3/bin/python}" in source
    assert "smoke" not in source.lower()
    assert "fp16" not in source.lower()
