"""汇总 E1 网格结果为可读表（stdout）。"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
d = json.load(open(root / "outputs/submission/e1_grid/results.json", encoding="utf-8"))
print("=== E1 网格 faithful_constrained / safe_success（v4 面板 1400 受约束条）===")
for name, cell in d["cells"].items():
    o = cell["overall"]
    fc = o["faithful_constrained"]
    ss = o["safe_success"]
    print(f"{name:55s} faithful={fc:.4f}  safe={ss:.4f}  n={o['n']}")
print()
print("=== 按 split ===")
for name, cell in d["cells"].items():
    parts = []
    for split in ("test_tpl_ho", "test_tool_ho"):
        v = cell[split]["faithful_constrained"]
        parts.append(f"{split.replace('test_','')}={v:.3f}" if v is not None else f"{split}=NA")
    print(f"{name:55s} " + "  ".join(parts))
