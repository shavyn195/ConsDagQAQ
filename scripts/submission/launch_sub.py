"""Windows 本地启动器：为 Unix-only 的分析依赖注入无操作 fcntl shim，再运行 submission 脚本。

shim 只影响 eval_repair_sft.__main__ 里的文件加锁路径；回放/评测路径不触及，语义无损。
用法：python scripts/submission/launch_sub.py sub_e1_grid [--out ...]
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def install_fcntl_shim() -> None:
    if "fcntl" in sys.modules:
        return
    fake = types.ModuleType("fcntl")
    fake.LOCK_EX = 1
    fake.LOCK_UN = 2
    fake.LOCK_NB = 4
    fake.LOCK_SH = 1
    fake.flock = lambda *args, **kwargs: None
    fake.lockf = lambda *args, **kwargs: None
    sys.modules["fcntl"] = fake


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    install_fcntl_shim()
    sys.path.insert(0, str(ROOT / "src"))
    module_name = sys.argv[1]
    sys.argv = [module_name] + sys.argv[2:]
    import importlib
    module = importlib.import_module(module_name)
    if not hasattr(module, "main"):
        raise SystemExit(f"{module_name} has no main()")
    module.main()


if __name__ == "__main__":
    main()
