# Seed 方差机制分解（2026-11-24 深夜，R3 必做项 · 零 GPU）

输入：v5 三种子冻结预测（本地 `outputs/e1/*/trained_predictions`，4B seed44 自服务器拉回）。
脚本：`scripts/submission/seed_variance_decomposition.py`；产物：`outputs/v5_analysis/seed_variance_decomposition_20261125.json`。
口径：faithful = 编译器预测 → 符号规划器 `plan()` → `check()` 的 safe_success 且改动数等于金标最小改动（v5 主表 e1_exec_v2 口径）。
**口径自校验**：本分析算出的 faithful 与 v5 主表单 seed 数字逐项一致（1.7B tool_ho 91.71/75.71/71.86、struct_ho 95.86/75.29/77.57；4B tool_ho 91.00/95.86/74.14、struct_ho 99.71/97.00/93.57），证明回放与字段比对可信。

## 1. 行为 faithful（受约束 700 条，%）

| 模型 | split | seed42 | seed43 | seed44 |
|---|---|---:|---:|---:|
| 1.7B | dev | 98.50 | 98.00 | 99.67 |
| 1.7B | tpl_ho | 96.71 | 95.57 | 97.86 |
| 1.7B | tool_ho | 91.71 | 75.71 | 71.86 |
| 1.7B | struct_ho | 95.86 | 75.29 | 77.57 |
| 4B | dev | 100.00 | 99.83 | 100.00 |
| 4B | tpl_ho | 97.43 | 92.86 | 99.71 |
| 4B | tool_ho | 91.00 | 95.86 | 74.14 |
| 4B | struct_ho | 99.71 | 97.00 | 93.57 |

## 2. 失败重叠：三 seed 共杀的记录极少

700 条受约束记录按「被几个 seed 判 faithful 失败」分布（0/1/2/3）：

| 模型·split | 0 seeds | 1 seed | 2 seeds | 3 seeds |
|---|---:|---:|---:|---:|
| 1.7B tool_ho | 409 | 172 | 104 | **15 (2.1%)** |
| 1.7B struct_ho | 434 | 179 | 81 | **6 (0.9%)** |
| 4B tool_ho | 493 | 145 | 58 | **4 (0.6%)** |
| 4B struct_ho | 634 | 64 | 2 | **0** |

record 级失败 Jaccard：1.7B tool_ho 42v43=0.146 / 42v44=0.123 / 43v44=0.335；1.7B struct_ho 0.058/0.057/0.310；4B tool_ho 0.045/0.226/0.111；4B struct_ho 0/0/0.031。
**含义**：执行级失败几乎不同时发生——同一批样本极少被所有 seed 同时击穿。这不是「系统性难度」，是 seed 特异波动。

## 3. 字段级归因：两类字段、两种机制

对失败记录做金标-预测字段比对（同 type 贪心匹配；未匹配记 missed/extra）。

### 3.1 params（规划器实际消费的字段）= 训练噪声

params 错误记录数 per seed 与三 seed 交集 IOU：

| 模型·split | params 错误 (42/43/44) | 三 seed 交集 | IOU |
|---|---|---:|---:|
| 1.7B tool_ho | 54 / 173 / 184 | 20 | 0.077 |
| 1.7B struct_ho | 38 / 182 / 129 | 8 | 0.033 |
| 4B tool_ho | 70 / 31 / 216 | 4 | 0.018 |
| 4B struct_ho | 3 / 26 / 52 | 1 | 0.014 |

实例（`scripts/submission/diag_field_mismatch_samples.py` 抽查）：`max_total_cost_cny` 金标 100 预测 1000；`tool_auth.required_role` 金标 `rent_cloud_gpu_job` 预测 `launch_fl_production_round`。
**含义**：直接决定规划器行为的字段，其错误在不同 seed 间几乎不重叠（IOU 0.01-0.08）——执行级 faithful 的跨 seed 波动主要由 params 的 seed 特异性错误驱动，是训练噪声，不是样本固有难度。

### 3.2 scope（记录轴独有、规划器不消费）= 系统性绑定缺陷，执行级不可见

scope 错误记录数 per seed 与三 seed 交集 IOU：

| 模型·split | scope 错误 (42/43/44) | 三 seed 交集 | IOU |
|---|---|---:|---:|
| 1.7B tool_ho | 384 / 352 / 404 | 288 | **0.629** |
| 1.7B struct_ho | 358 / 426 / 418 | 349 | **0.735** |
| 4B struct_ho | 302 / 355 / 365 | 299 | **0.810** |
| 4B tool_ho | 67 / 309 / 446 | 22 | 0.048 |

实例：金标 budget scope 是计费角色集合 `['role:lease_partner_dataset','role:rent_cloud_gpu_job']`，模型绑定到 `['role:billable_steps']` 或与预算无关的角色三连；privacy scope 金标 4 个外发角色，模型漏绑 `sync_to_partner_hub`。
**含义（分两种）**：
- 1.7B 与 4B struct_ho：scope 绑定错误规模大（每 seed 300-420 条记录）且 seed 间高度一致（IOU 0.63-0.81）——**系统性缺陷：模型学不会角色绑定**；
- 4B tool_ho：scope 错误率本身在 seed 间飘（67→309→446），是 seed 稳定性问题。
- 共同点：`plan()` 只读 type+params，scope 错误对 faithful 零影响——**记录轴上最大规模的缺陷在执行级指标中完全不可见**。

## 4. 可写入论文的发现（C3 延伸，非伤口）

按预注册口径如实表述：

1. **行为轴的跨 seed 方差主要由规划器实际消费的 params 字段的 seed 特异性错误驱动**（三 seed 共杀率 0-2.1%；params 错误 IOU 0.01-0.08）。单 seed 排序不可信有机制解释：seed 换的是 params 噪声，不是能力。
2. **记录轴存在规模最大且 seed 间高度一致的缺陷类别（scope 角色绑定，IOU 0.63-0.81），但执行级指标对其完全不敏感**（规划器不消费 scope）。只看 faithful 会漏掉它；只看记录轴会把行为无关的 scope 错误计为模型失败。
3. 合起来：「记录轴与行为轴可分离」在本任务上有实证——行为指标单独报告不足以刻画编译器质量，这正是双轴评测（记录轴 + 执行轴）作为基准设计的理由，也直接支撑 C3 的诊断定位。
4. 限定词（必须写进论文）：分析为固定观测 seed 的描述性分解，无 seed 总体区间推断；字段匹配为同 type 贪心最优，未建模多约束的匹配歧义；scope 的系统性结论在 4B tool_ho 上不成立（该切分 scope 错误率 seed 间在飘），须按切分分别陈述。

## 5. 对后续实验的指向（不改变队列）

- E3 A4（去 scope）预期「下游 faithful 不变」——本节的 3.2 给出先验：scope 不被规划器消费，去掉它执行轴应不动，但部署成本（字段契约）下降。若 A4 下游确实不变而记录轴显著劣化，则 scope 的诊断价值得到正面证明。
- E2 单体对照若 faithful 也平坦，注意区分「任务难」与「架构缺陷」：本节证明规划器消费的 params 在小模型上噪声大，单体直出计划同样要写对这些字段。
