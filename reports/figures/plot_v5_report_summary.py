"""Render the report figure from frozen audit JSON, without rerunning experiments."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
analysis = json.loads((ROOT / "outputs/v5_analysis/main_audited_20261123.json").read_text(encoding="utf-8"))
measurement = json.loads((ROOT / "outputs/v5_analysis/measurement_audit_20261123.json").read_text(encoding="utf-8"))
plt.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"], "axes.unicode_minus": False,
                     "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(13.7, 5.5), gridspec_kw={"width_ratios": [1.2, 1]})
splits = ["dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho"]
series = [
    ("Qwen3-1.7B-LoRA", 0, "1.7B · seed42", "#2563eb", "o"),
    ("Qwen3-1.7B-LoRA", 1, "1.7B · seed43", "#d97706", "s"),
    ("Qwen3-4B-LoRA", 0, "4B · seed42", "#08916e", "^"),
    ("deepseek-v4-pro-0813-few", 0, "DeepSeek · 十示例", "#663399", "D"),
]
for arm, index, label, color, marker in series:
    y = [100 * analysis["table"][arm][s]["faithful_constrained_per_seed"][index] for s in splits]
    axes[0].plot(range(4), y, marker=marker, color=color, linewidth=1.8, label=label)
axes[0].set_xticks(range(4), ["开发集", "措辞留出", "工具名留出", "结构留出"])
axes[0].set_ylim(60, 102)
axes[0].set_yticks(range(60, 101, 10))
axes[0].set_ylabel("受约束题 faithful_success（%）")
axes[0].set_title("A. 两个 1.7B 种子的留出表现明显不同", loc="left", fontsize=12, pad=38)
axes[0].grid(axis="y", alpha=.2)
axes[0].legend(loc="lower left", frameon=False)
axes[0].text(.99, .04, "纵轴从 60% 起；各曲线为单次运行\n开发集 n=600；各留出 n=700", transform=axes[0].transAxes,
             ha="right", va="bottom", fontsize=8.5, color="#555555")
labels = ["执行成功", "执行谓词一致", "core 记录全对", "strict 记录全对"]
keys = ["faithful", "world_predicate_record", "core_record", "strict_record"]
x = np.arange(len(keys))
for offset, arm, label, color in [(-.18, "4B-seed42", "4B · seed42", "#08916e"),
                                 (.18, "DeepSeek-ten-shot", "DeepSeek · 十示例", "#663399")]:
    counts = measurement["joint_metrics"][arm]["counts"]
    assert counts["constrained_records"] == 700
    y = [100 * counts[k] / counts["constrained_records"] for k in keys]
    bars = axes[1].bar(x + offset, y, width=.34, label=label, color=color)
    axes[1].bar_label(bars, labels=[f"{v:.1f}" for v in y], fontsize=8.5, padding=3)
axes[1].set_xticks(x, labels, rotation=15, ha="right")
axes[1].set_ylim(0, 110)
axes[1].set_yticks(range(0, 101, 20))
axes[1].set_ylabel("记录比例（%；共同分母 n=700）")
axes[1].set_title("B. 结构留出：类型契约与执行语义须区分", loc="left", fontsize=12, pad=38)
axes[1].legend(loc="lower left", bbox_to_anchor=(0, 1.005), ncol=2, frameon=False, borderaxespad=0, fontsize=9)
axes[1].grid(axis="y", alpha=.15)
axes[1].set_axisbelow(True)
fig.text(.05, .025, "数据：2026-11-23 v5 审计快照。执行谓词一致仅指当前合成世界中的规范化等价；不代表一般语义判定。", fontsize=9, color="#555555")
fig.subplots_adjust(bottom=.20, top=.84, left=.065, right=.985, wspace=.25)
fig.savefig(Path(__file__).with_name("v5_report_summary.png"), dpi=180, facecolor="white")
plt.close(fig)
