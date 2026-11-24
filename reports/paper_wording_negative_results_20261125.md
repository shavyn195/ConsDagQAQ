# 论文措辞件：负结果章与 symbolic 列防御（2026-11-24 深夜，R1-R3 建议吸收）

依据：投稿方案 v3 第一波「写作层修正」第 2、3 项。本文件只定措辞，不改任何实验口径；所有数字引自已核验素材（`reports/submission_plan_emnlp2027.md` §7 速查、`outputs/submission/e1_grid/results.json`）。

## 1. GRPO 负结果章（R3 口径：不声称证明为零，只声称未检出）

**禁止出现**：「GRPO 无效」「零收益」「没有提升」。

**定稿措辞**（负结果章内）：

> We evaluate three GRPO credit-assignment variants—action-level attribution, preventive-action rewards, and a weighted-SFT mixture—each across three training seeds. Under our measurement power (three seeds; paired task-group bootstrap intervals spanning roughly ±1-2 points on the constrained faithful rate), we observe **no stable effect** in any direction: mean differences across seeds are +1/0/−1, 0/+2/−2, and +1/−3/−6 percentage points for the three variants respectively, with the frozen-weight held-out control at +0/+1/+3. We therefore **do not detect** a benefit of reward-side credit assignment on this task; we explicitly do not claim to have proven the effect is zero, as the confidence intervals of our design cannot exclude effects below approximately 2 points.
>
> The diagnostic instrument built for this evaluation—the 2×2 attribution protocol isolating compiler-side recovery (112/118) from planner-side recovery (47/138)—is retained in the main analysis as a measurement contribution, independent of the training outcome.

中文对照（内部审校用）：三臂三种子「未检出稳定效应（在本设计的功效范围内）」；区间约 ±1-2pp，不能排除 <2pp 的效应；不写「证明为零」。2×2 归因协议（编译器救回 112/118、规划器救回 47/138）作为测量贡献保留在主分析，与训练结果脱钩。

**配套 Limitation 句**：GRPO 消融为单架构、单数据域、三 seed；功效上限约 ±1-2pp，更小效应本设计不可检。

## 2. symbolic 规划器列措辞防御（R2「单调=构造必然」一刀的防御）

**风险**：审稿人读 E1 网格，符号规划器行随编译器质量单调上升（0.7893 → 0.8836 → 0.9786 → 0.9950），会判「这是构造必然，不是发现」。

**定稿措辞**（结果章，紧贴网格表）：

> The monotone row for the symbolic planner is expected by construction—a perfectly obedient consumer converts compiler quality into execution quality without loss. We report it as an **interface sanity check, not as a result**: it verifies that our compile-plan-execute decomposition adds no attenuation of its own, which is precisely the property required before the separation can carry any interpretation.
>
> The non-constructive evidence is the prompted-compiler cell: DeepSeek's 10-shot compiler output, fed through the same symbolic interface, **exceeds our best trained 4B compiler (0.9950 vs 0.9786 faithful)**. The interface is therefore not tuned to our own models—it is consumable by a compiler we did not train, at a quality level our own training has not reached. Conversely, the two SFT-planner columns stay flat at 0.25-0.30 across all four compilers (safe success 0.88-0.95), showing that consumer quality, not compiler quality, is the binding constraint in that regime.

中文对照（内部审校用）：符号行单调是构造必然，只作「接口无衰减验证」，不是卖点；**非常构造性的证据是 DeepSeek 行 > 4B 行**（接口不被自家模型特化，未被训练到的编译质量也能无损消费）；反向证据是 SFT 规划器两列对编译器质量全平（0.25-0.30，safe 0.88-0.95）——该区间瓶颈在消费者不在编译器。

**E1 汇总表引用口径**（与 `scripts/submission/summarise_e1.py` 输出一致，五轴分列时 faithful 列必须标注为受约束行口径 faithful_constrained）：

| 编译器 \ 规划器 | SFT-order42 | SFT-order44 | symbolic |
|---|---:|---:|---:|
| 0.6B-SFT | 0.2514 / 0.8776 | 0.2607 / 0.9043 | 0.7893 / 0.8767 |
| 1.7B-SFT | 0.2657 / 0.8990 | 0.2786 / 0.9190 | 0.8836 / 0.9267 |
| 4B-SFT | 0.2793 / 0.9229 | 0.2886 / 0.9390 | 0.9786 / 0.9857 |
| prompted-compiler(skill-style, DeepSeek 10-shot) | 0.2814 / 0.9305 | 0.2950 / 0.9486 | 0.9950 / 0.9967 |

（格式：faithful_constrained / safe_success；n=2100，v4 tpl_ho+tool_ho 冻结回放；bootstrap 10000 次、seed 20261124、按 group 重采样。）

## 3. seed 方差段的配套措辞（R3 红旗→富矿，配 `reports/seed_variance_analysis_20261125.md`）

> Cross-seed swings in the constrained faithful rate (up to 19.9pp on tool_ho) are not driven by systematically hard samples: only 2.1% (15/700) of records fail under all three seeds, and errors in the planner-consumed params field overlap across seeds at Jaccard 0.01-0.08. The largest error category—scope role binding, present in 300-420 records per seed—is highly consistent across seeds (IoU 0.63-0.81 on 1.7B and 4B struct_ho) yet invisible to the execution axis, because the planner never reads scope. Record-axis and behaviour-axis failures are therefore separable in this task, which is the empirical motivation for reporting both.

限定词（必须随段写出）：描述性分解，固定观测 seed，无 seed 总体区间；同 type 贪心匹配，未建模多约束匹配歧义；scope 的系统性结论在 4B tool_ho 不成立（该切分 scope 错误率 seed 间 67→309→446 在飘），按切分分别陈述。

## 4. 下一步（不属本文件）

- E2 落地后：若单体 faithful >> 0.30，R2「神经消费者不可行」批评自动化解，写作时在 Discussion 引 E2；若也 ~0.3，触发 E5 条件分叉。
- DeepSeek-planner 臂（第三波）：把 2×2 升级为强弱交叉，届时本文件 §2 的「消费者也可换」一句才完整。
