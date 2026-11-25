# v6：执行成功与记录正确性的逐题交叉诊断

日期：2026-11-25。范围：Qwen3-1.7B-v6 seed42/43 的全部五个评估切分；seed44 尚未完成。本分析是冻结结果的事后诊断，不增加确认性假设、不调整金标、提示词、权重或测试集。

## 核心读数

这里把两个指标放到**同一批受约束 E/I 题**上比较。此前报告的 overall `record_exact_match` 还包括容易全对的 N 行，不能直接与 constrained faithful 当成相同分母。

| 切分 | seed | E/I 分母 | 执行 faithful | 严格记录正确 | 执行成功但记录不正确 |
|---|---:|---:|---:|---:|---:|
| dev | 42 / 43 | 各600 | 各600（100%） | 各600（100%） | 各0 |
| tpl_ho | 42 | 700 | 665（95.00%） | 648（92.57%） | 17 |
| tpl_ho | 43 | 700 | 685（97.86%） | 669（95.57%） | 16 |
| tool_ho | 42 | 700 | 687（98.14%） | 383（54.71%） | 304 |
| tool_ho | 43 | 700 | 698（99.71%） | 460（65.71%） | 238 |
| struct_ho | 42 | 700 | 653（93.29%） | 434（62.00%） | 219 |
| struct_ho | 43 | 700 | 699（99.86%） | 395（56.43%） | 304 |
| composition_ho | 42 / 43 | 各700 | 各700（100%） | 各700（100%） | 各0 |

严格记录正确沿用冻结评分器：query_state 正确，且 type/state/severity/scope/params 的约束多重集完全相同。它不含 evidence/description/confidence，不能改称“所有输出字段全对”。所有已观察行中“严格记录正确但执行失败”计数为0。

**事实：** tool/struct 执行高分掩盖了大批记录错误。尤其 struct_ho 的 seed43 执行好于seed42，但严格记录正确率反而更低。这是同批样本的实测排序分离，不能用执行分数替代编译记录质量。

## 字段与种子诊断

在 type+params 完全匹配的约束之间，按冻结评分器的 scope 顺序无关口径逐字段核对：

- tool_ho 两seed合计607次 scope 字段错误，其中 budget 282次、privacy 325次；没有观察到这些已匹配约束的 state/severity/evidence 错误。
- struct_ho 两seed合计546次 scope 字段错误，其中 budget 359次、privacy 187次；其余上述字段未见差错。
- tpl_ho 出现26次 constraint state 错误。无约束 N 行仍有29/350、46/350的契约警报（8.29%、13.14%）。这些是小模型诊断；正式H4指定DeepSeek，不能用它们代替H4检验。
- 两seed scope 错误记录集合的 Jaccard：tool 234/308=0.760；struct 226/293=0.771。相较之下，执行失败任务组的交集/并集为 tool 1/14、struct 0/37。记录错误较集中地重复出现，执行失败则更受当前种子影响；仅两seed，不能据此完成训练随机性的机制归因。

“607/546”是跨seed的**错误约束字段次数**，不是独立题目数、错误记录数或额外样本量。字段诊断条件于 core 已匹配，不应外推成全部错误都仅由scope引起；漏检、额外约束和params不匹配另外计数。

**实现事实：** 当前符号规划器从 type+params 构造行为，不消费 scope/state/severity/evidence；因此这些字段错误未影响执行，是当前接口的性质。这里只能说明执行指标不能审计完整记录，不能宣称这些字段对当前执行有因果贡献，也不能借此证明一个新架构普遍优于其他规划器。

## 复现与解释边界

脚本：`scripts/submission/analyze_v6_seed_diagnostics.py`。输入完成标记、模型配方、来源/数据/产物哈希全部经冻结验证器核验；重新解析 raw、重放冻结执行器，复算的strict F1/record exact/faithful与原metrics一致。没有使用预测文件中较宽松的解析副本代替raw评分。

产物：`outputs/submission/followup_20261125/v6_1p7b_seed42_43_execution_record_diagnostic.json`。包含每个run的完成指纹、产物SHA-256、数据与诊断源码哈希。服务器使用独立CPU审计目录 `/root/consdag_audits/v6_seed_diagnostic_20261125`，不向运行中的冻结训练目录新增文件。

本机11项专项测试通过；服务器没有pytest，直接调用9个无fixture的回归测试函数全部通过，没有为此安装依赖或改训练环境。服务器CPU对原始预测重算的JSON与本机结果逐字节相同，SHA-256=`8ab240c16d339f4730653de7f8fb3f8ccc0fecacaca6d21707be476bd51e0f03`；核对记录：`outputs/submission/followup_20261125/v6_seed_diagnostic_server_parity.json`。这验证了分析一致性，不等同于新训练重复实验。

不将v6与v5/E2不同数据及评分器直接做差；不把两seed均值当三seed结论；不把模板组合切片满分当真实语言泛化或无泄漏证明。独立语义验证仍缺失。当前结果支持双轴诊断的必要性，但尚不足以单独宣称创新性或CCF-B准备完成。

下一步：等待seed44的完整评测及完成标记，按相同脚本纳入第三seed；保持既有4B→0.6B接力和30小时预算，不为了门槛改动已冻结测试集。

14:29:38 CST服务器只读快照：seed44到8,300/9,000步，84条loss全部有限，最新loss `1.09729e-5`；GPU56%、17,420/32,760MiB，队列仍running、最终metrics/completion尚未产生。观察到8,100步的loss短暂升至0.01643，之后回落；它是有限值，不能误报为NaN，也不能由此推断最终泛化。
