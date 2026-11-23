# v4 当前结果与可主张范围

日期：2026-11-22

## 三项贡献的当前表述

**① 带原文证据的约束编译。** 独立训练的小模型从每次用户请求中提取显式或情境暗示的约束，输出类型、参数、原文证据及适用的工具角色。没有相应约束时可以输出空集。规划器和检查器可以读取同一条记录，研究者也可以逐字段追溯错误。现有执行实验主要验证类型和参数的下游效用。校准、拒判以及证据与作用范围字段各自带来的执行收益仍需单独验证。

**② 通过交叉干预区分约束解释和计划搜索的执行失败。** 固定任务、候选计划与允许的编辑，枚举可达的功能完成方案并用金标离线验收，计算候选空间允许的安全完成上限。再交叉更换约束编译器和产生候选的规划器权重，记录每一种干预实际救回和损失的题。由此能回答面对同一次失败，改进约束解释有没有机会，以及改变候选计划有没有奏效。局部修复提供可枚举的编辑空间。②按实证贡献投稿，原 GRPO 奖励分解作为负结果。

**③ 按约束表达方式成对构造的可执行基准。** 同一任务和同一约束分别生成显式表达和情境暗示的配对查询，再生成一个无约束对照。每个任务附有可执行环境、金标约束、适用工具角色和经检查的可行计划。由此可以分别测量约束能否提取、计划能否安全完成，以及没有约束时是否无端修改默认方案。当前 v4 有 5,000 组、15,000 条合成样本，测试包括未见措辞和未见工具名。隐式线索的人类盲审仍待回收。

方法适用于具备工具目录和可执行检查器的规划问题。可信数据工作流是本研究的实验案例。以上②为根据实验提出的修订版本。

## 面向投稿的引言贡献段

We study how tool planners can carry constraints expressed in a user's request through to an executable plan. We distinguish errors in interpreting the request from failures to propose or select a plan that satisfies it.

1. We formulate request-level constraint compilation as a supervised prediction task. A compact model identifies explicitly stated or contextually implied constraints and emits typed parameters, supporting text spans, and the tool roles to which each constraint applies. The resulting record lets us evaluate extraction separately from whether a downstream plan completes the task under the user's constraints.
2. We characterize failures of constraint-aware tool planning through paired execution and crossed interventions. For each query, we enumerate the strictly complete candidates reachable under a fixed edit budget and evaluate them against the target constraints. We then independently vary the constraint compiler and the candidate-producing planner weights to measure which failures each intervention resolves and which previously successful tasks it breaks.
3. We introduce a paired executable benchmark with 5,000 task groups. Each group contains an explicit request and a contextually implied request with the same target constraints, together with a matched unconstrained control. Feasible witness plans, constraint-to-role annotations, and held-out wording and tool names support separate evaluation of extraction, safe task completion, and unnecessary changes to unconstrained plans.

局部修复与等搜索范围对照及经过同一收尾规范化的符号求解器比较。②的直接相关工作包括执行验证、候选覆盖上限和系统组件替换。③的隐式语用主张还取决于独立标注者能否从公开信息恢复同一金标。详细划界与 2×2 结果见[投稿取舍记录](contributions_submission_decision.md)。

1.7B 规划器的新实验覆盖了两个留出集的全部 700 个任务组。0.6B 提取约束后，仅从四条候选中选择，可在 1,400 道受约束题上安全完成 682 道。允许执行器尝试一个工具动作的修改并验证后，安全完成 1,144 道。按 DAG 配对计算，提升 33.0 个百分点，95% 区间为 30.0 至 36.1。给符号求解器相同的收尾格式修正后，它完成 1,149 道。两种方法的搜索成本不同。此实验支持编译输出在推理阶段帮助纠正计划。三种训练顺序下，修复动作加权相对普通 SFT 的安全完成净变化为 +1、−3、−6 道，各以 80 道为分母。详见[实验台账](experiment_log.md)及[配对结果](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/paired-summary.json)。

## 已完成的 E1 对照

所有执行分数都是冻结 data/processed_v4 上的 faithful_success：计划完成、满足全部金标约束，并且改动数与金标最小计划一致；受约束查询单列。它不是严格 JSON/F1 的替代品。

| 系统 | dev | template holdout | tool-name holdout |
|---|---:|---:|---:|
| Qwen3-0.6B LoRA | 97.33% (584/600) | 82.29% (576/700) | 75.57% (529/700) |
| Qwen3-1.7B LoRA | 100.00% (600/600) | 95.71% (670/700) | 81.00% (567/700) |
| Qwen3-4B LoRA | 100.00% (600/600) | 95.86% (671/700) | 99.86% (699/700) |
| qwen-max PE, zero-shot | 90.50% (543/600) | 87.43% (612/700) | 86.86% (608/700) |
| qwen-max PE, ten-shot | 88.17% (529/600) | 85.00% (595/700) | 89.14% (624/700) |
| deepseek-v4-pro-0813 PE, ten-shot | 99.33% (596/600) | 99.00% (693/700) | 100.00% (700/700) |

Qwen 与 DeepSeek 的十示例臂共享 v4 提示、训练示例、temperature 0、384 个最大输出 token。DeepSeek 全量 3,000 条都正常结束、非空；已核对每条请求哈希与模型名。90 条预选面板包含在全量中，不重复计数。模板留出的 N 版还须单独看：322/350 没有多改计划，315/350 的完整输出正确。工具名留出的 E/I 共 700 条全部成功，含证据整条全对是 655/700。十示例调用量大，不在未测真实价目和摊销时声称小模型更便宜。

DeepSeek 的成对比较显示，它相对 1.7B 的受约束执行差为 dev -0.67 个百分点、模板留出 +3.29 个百分点、工具名留出 +19.00 个百分点；相对 4B 为 -0.67、+3.14、+0.14 个百分点。对应原始结果在 outputs/e1_v4_side/deepseek-v4-pro-0813-few/full-paired.json，区间是按任务组 bootstrap 的描述性区间。它已经证明跨家族强模型 PE 必须纳入主表，也没有支持“训练模型全面胜过强模型”的说法。

4B 的工具名留出有 699/700 条执行成功，但含证据的完整记录只有 552/700；因此证据、scope 和执行成功不能合并成一个指标，也不能用执行分数替代证据保真度。

## 数据和代码审计

对 15,000 条、5,000 个三元组执行了独立验证：

- outputs/dataset_audit/v4-all-pairs-recheck.json 为 PASS；
- train/dev/template-holdout/tool-name-holdout 的 query、goal、group_id 两两无重叠；
- 每个文件的 subset 标签与文件名一致；
- witness、全组必要性检查、E/I/N 配对、证据子串、隐式指令词、held-out 工具和下游刻度通过；
- 显式 privacy 证据必须包含与 protected_data_classes 对应的受保护数据类名；故意换错类别或不提类别时，验证器均能拒绝；
- 本地 pytest -q tests/test_dataset_v4.py tests/test_v4_side_jobs.py：17 passed。

新增校验只影响未来审计，不修改原始 v4 数据或已完成的训练结果。原始验证器曾只检查训练集与其他切分的交集，现在改为所有切分两两检查。

1.7B、4B 的已保存 dev 响应在 900/900 条上逐字等于规范金标，两份文件哈希相同。适配器的哈希及工具名留出响应哈希均不同。从两个适配器独立重载，在按组确定性抽取的同一批 27 条 dev 样本上各重现 27/27 条原始响应（outputs/dataset_audit/dev-replay-v1/scores.json）。这个现象与同分布开发集饱和一致，不足以证明真实查询的语言理解或排除所有数据捷径。

89 条模板留出隐私题的字段示例干预在已训练 1.7B 上完成：原策略卡与移除字段示例的策略卡分别得到 88/89、88/89 的正确隐私参数恢复；含证据的整条全对为 76/89 与 74/89。它是小规模机制诊断，不是新增主表，也不能证明模型没有记忆训练映射。

## E2 后续实测（2026-11-22 15:45）

E2 已完成三种子动作归因对照、预防动作对照和 2,160 条冻结留出推理。两种动作信用都没有稳定优于整计划约束奖励，不支持“动作归因抗奖励投机”的主张。另一个推理实验使用相同四候选：两个留出面板共 80 道受约束题，使用预测约束重排相对首个功能完成提高 17→28，11 胜 0 负；金标选择上限 31，使用同一预测约束另构计划的符号求解器为 65。重排是①的使用证据，不是②的训练收益。完整三种子差值、分母、无约束结果、复核和适用范围见 [实验台账](experiment_log.md) 15:45 条目。

## E2 训练前诊断（历史记录）

E2 还没有训练结果。1.7B 原始规划器的 40 条格式可达性抽样中，工具名输出只有 1/40 严格可解析且 0/40 安全完成；改成数字 codebook 后为 0/40。这个结果不证明 planner 无法学习，只说明当前接口下不能直接启动长 GRPO 并声称公平比较。漏检奖励已验证：固定 query 常数罚在组内中心化后为零，只有轨迹实际违反漏掉的金标约束时才产生差异。

论文范围：① 有逐查询参数化编译、证据字段和符号规划执行的对照；没有证据说明这些字段的存在提升了执行成绩。③ 有可执行的 E/I 配对及 N 对照，指定字段通过泄漏检查，工具名留出仍与训练世界结构同构。要把结论扩大到自然隐式约束，需新增独立人工盲审和不同结构的任务；不能事后剔除答错样本来修改冻结主表。② 仍是待训练和待消融的假设。优先用 train 组做所有奖励臂共享的规划器格式/行动示范预热，再用独立 train 组验证同组有可比较的完成轨迹，最后才值得跑 GRPO。
