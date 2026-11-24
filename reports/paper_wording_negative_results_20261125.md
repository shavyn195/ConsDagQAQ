# 论文措辞件：负结果章与 symbolic 列防御（2026-11-24 深夜，R1-R3 建议吸收）

依据：投稿方案 v3 第一波「写作层修正」第 2、3 项。本文件只定措辞，不改任何实验口径；所有数字引自已核验素材（`reports/submission_plan_emnlp2027.md` §7 速查、`outputs/submission/e1_grid/results.json`）。

## 1. GRPO 负结果章（R3 口径：不声称证明为零，只声称未检出）

**禁止出现**：「GRPO 无效」「零收益」「没有提升」。

**定稿措辞**（负结果章内）：

> In the tested v4 setting, action-level and preventive credit assignment show no consistent improvement over whole-trajectory rewards. Their per-seed changes are +1/0/−1 successful cases out of 120, and 0/+2/−2 out of 90, respectively. The paired task-group intervals, conditional on the three observed seeds, are [−3.89, +3.61] and [−4.81, +4.45] percentage points. These are uncertainty intervals, not minimum detectable effects or confidence intervals over training seeds. Separately, whole-trajectory rewards exceed functional-only rewards by +4/+2/+7 cases out of 120, with a conditional interval of [+0.28, +7.22] points; this is evidence for adding a constraint signal in that setting, not for the proposed credit allocation. The frozen-transfer comparison is separate and must not inherit that interval. Weighted repair-SFT is also separate from GRPO: its three training-order changes are +1/−3/−6 cases out of 80. We do not infer a universal zero effect from these experiments.
>
> Provenance: `outputs/e2_v4/action-credit-1.7B-pilot-v1/rechecked-original-42-43-44.json`, its `preventive-comparison-v1/rechecked-prevention-42-43-44.json`, and `outputs/e2_v4/verified-repair-sft-1.7B-orders-v1/independent-replay.json`. The inventory audit `recompute.json` is not the source of GRPO intervals.
>
> The diagnostic instrument built for this evaluation—the 2×2 attribution protocol isolating compiler-side recovery (112/118) from planner-side recovery (47/138)—is retained in the main analysis as a measurement contribution, independent of the training outcome.

中文审校：净增数字是“道”，不是 pp；分母120／90／80不同。正区间 [+0.28,+7.22] 属原面板 trace-minus-function，不属于冻结迁移；区间不含0不能同时称“无法与噪声区分”。训练顺序与模型种子分开。

**配套 Limitation 句**：单架构、单数据域、三个观测 seed，条件区间仍较宽；未进行前瞻性功效分析，不报告 MCD。

## 2. symbolic 规划器列措辞防御（R2「单调=构造必然」一刀的防御）

**风险**：审稿人读 E1 网格，符号规划器行随编译器质量单调上升（0.7893 → 0.8836 → 0.9786 → 0.9950），会判「这是构造必然，不是发现」。

**定稿措辞**（结果章，紧贴网格表）：

> On the frozen v4 panel, all four compilers can supply records to the same symbolic consumer. We report the resulting execution rates as a compatibility check within this interface. The ordering of aggregate rates does not establish lossless compilation: the consumer uses type and params and ignores several audited fields.
>
> DeepSeek's ten-shot compiler yields 0.9950 constrained faithful success through this interface, compared with 0.9786 for the tested 4B compiler. This demonstrates use by an external compiler in the measured setting. The two neural candidate-pool-and-repair consumers yield faithful rates of 0.25–0.30 despite safe success of 0.88–0.95, consistent with excess edits limiting faithful performance. These observations do not prove portability to arbitrary consumers or isolate architecture as the cause.

中文审校：称“所测接口兼容性”，删除“无衰减／任何人可接／完全与编译质量无关”。神经列须写明四候选池＋单编辑修复，不能冒充单次神经规划器。

**E1 汇总表引用口径**（与 `scripts/submission/summarise_e1.py` 输出一致，五轴分列时 faithful 列必须标注为受约束行口径 faithful_constrained）：

| 编译器 \ 规划器 | SFT-order42 | SFT-order44 | symbolic |
|---|---:|---:|---:|
| 0.6B-SFT | 0.2514 / 0.8776 | 0.2607 / 0.9043 | 0.7893 / 0.8767 |
| 1.7B-SFT | 0.2657 / 0.8990 | 0.2786 / 0.9190 | 0.8836 / 0.9267 |
| 4B-SFT | 0.2793 / 0.9229 | 0.2886 / 0.9390 | 0.9786 / 0.9857 |
| prompted-compiler(skill-style, DeepSeek 10-shot) | 0.2814 / 0.9305 | 0.2950 / 0.9486 | 0.9950 / 0.9967 |

（格式：faithful_constrained / safe_success；n=2100，v4 tpl_ho+tool_ho 冻结回放；bootstrap 10000 次、seed 20261124、按 group 重采样。）

## 3. seed 方差段的配套措辞（R3 红旗→富矿，配 `reports/seed_variance_analysis_20261125.md`）

> Cross-seed swings in the constrained faithful rate (up to 21.7pp on tool_ho) are dominated by seed-specific errors rather than a systematically hard sample core: only 2.1% (15/700) of records fail under all three seeds, and errors in the planner-consumed params field overlap across seeds at Jaccard 0.01-0.08. That common hard core is nonetheless real: it exceeds the independent-failure expectation by 3.7-6.0× (15 vs 3.96 on 1.7B tool_ho; 6 vs 1.61 on 1.7B struct_ho; 4 vs 0.67 on 4B tool_ho). The largest error category—scope role binding, present in up to 446 records per seed—is highly consistent across seeds (IoU 0.735/0.810 on 1.7B/4B struct_ho; 0.629 on 1.7B tool_ho) yet invisible to the execution axis, because the planner never reads scope. Record-axis and behaviour-axis failures are therefore separable in this task, which is the empirical motivation for reporting both.

限定词（必须随段写出）：描述性分解，固定观测 seed，无 seed 总体区间；同 type 贪心匹配（与暴力最优匹配相比，仅 0-2 条记录判定翻转）；scope 的系统性结论在 4B tool_ho 不成立（该切分 scope 错误率 seed 间 67→309→446 在飘），按切分分别陈述。

数字来源：`outputs/submission/audit_20261124/recompute.json`（摆幅、独立假设期望、共杀比）与 `outputs/v5_analysis/seed_variance_decomposition_20261125.json`（字段 IOU），已由 2026-11-24 审计独立复算。

## 4. 下一步（不属本文件）

- E2 落地后先核对公开信息与原始输出。单个分数不能识别“任务难／架构缺陷／监督不足”；E5 根据有效对照和错误类型决定。
- DeepSeek-planner 臂（第三波）：把 2×2 升级为强弱交叉，届时本文件 §2 的「消费者也可换」一句才完整。
