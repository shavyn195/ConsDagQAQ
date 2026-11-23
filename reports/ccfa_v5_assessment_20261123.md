# ConsDAG v5：CCFA 对照与 CCF-B 投稿距离

日期：2026-11-23  
依据：`literature/ccfa_skills_v0.12.1` 的 idea-reviewer、experiment-designer、evidence-design、experiment-discipline；仓库内已核验论文、v4 已完成结果、v5 数据与验证报告。

## 结论

项目仍有 CCF-B 机会，但现在不能写成“稳投”。最可守的论文结构是：①训练式逐请求约束编译器，③可执行 E/I/N 配对基准，②作为约束解释与候选计划搜索的交叉干预分析。原“外部锚门控 GRPO 已解决 reward hacking”不应继续作为已证实算法贡献。

CCFA v0.12.1 的六维历史分数为：① 4.13、② 4.18、③ 4.28。三项均属于 `revise`，因为 `accept-to-develop` 的门槛是 4.3。该分数评估概念，不等同于 CCF-B 投稿准备度。

## 当前创新点

### ① Evidence-bound constraint compiler

输入用户请求和公开工具/策略目录，输出带 `type`、参数、`explicit/implicit/none` 状态、证据片段和作用角色的结构化约束记录。可守的贡献是：专门训练的小模型、逐请求 typed/parameterized 输出、可审计接口，以及在执行层把编译错误与计划错误分开测量。不能写成“首次约束编译”“已证明校准/拒判/每个字段都有因果收益”或“全面胜过强模型”。

直接相关工作：

- [ATLAS](https://arxiv.org/abs/2509.25586)：显式/隐式要求与 scope 的提示词多 agent；未覆盖本项目的训练小编译器和配对执行契约。
- [CGAP](https://arxiv.org/abs/2610.41040)：工具目录到 PDDL、证据来源和运行时门控；对象主要是能力/状态规则，不是本项目的逐 query typed 约束接口。
- [Sapien](https://arxiv.org/abs/2610.00797)：逐 prompt 生成可执行工具策略；使用现成 LLM，未提供本项目的编译器训练接口与 E/I/N 基准。
- [NOMOS](https://arxiv.org/abs/2610.11030)：域级 policy 编译和本机运行时 gate；本机部署本身不是新颖性。
- [LangNCO](https://arxiv.org/abs/2610.23190)：自然语言到 DSL 编译，但其验证器不保证语义一致。

因此 ①可以立住，但必须把新颖性写成“组合与可验证后果”，而不是单个组件首创。v4 结果支持训练相对同底座零样本有明显收益；DeepSeek 十示例仍是强对照，不能写训练小模型全面胜出。

### ② 交叉干预分析

固定任务、候选计划和局部编辑预算，分别替换编译器输出或候选计划生成器，记录哪些失败可恢复，并给出候选空间可达上限。这一口径有直接结果支撑：1,400 道受约束题上，四候选重排到一次验证式局部修复由 682/1,400 提升至 1,144/1,400，配对提升 33.0 个百分点（95% CI 约 30.0–36.1）；交叉替换显示解释错误和搜索错误可分离。

原 GRPO/动作信用版本没有稳定收益：三个训练种子的动作归因相对整轨迹奖励净变化为 `+1/0/-1`，预防动作版本也没有稳定正向增益。与 [TAG](https://arxiv.org/abs/2610.21404)、[RLVP](https://arxiv.org/abs/2607.07435)、[DAGent](https://arxiv.org/abs/2609.39154)、[SEVerA](https://arxiv.org/abs/2603.25111) 的局部机制已有重叠；除非重新完成同预算、多种子和完整消融，否则不能把它写成成功的新奖励算法。论文应将 ② 定位为分析型贡献，并把原 GRPO 结果作为负结果和设计边界。

### ③ Executable paired constraint benchmark

每个任务组保留同一任务骨架和约束集，形成 `(E,I)` 等价对与 `(N)` 对比臂：E 直陈约束，I 用请求内情境线索表达，N 用近似否定/豁免/他方规则干扰。每组有 witness、逐条必要性检查、角色绑定、执行检查器、措辞留出、工具名留出和 v5 结构留出。禁止写“三版语义等价”或“首个隐式约束基准”。

直接邻居包括 [LogiSafetyBench](https://arxiv.org/abs/2601.08196)、[AM-Bench](https://arxiv.org/abs/2610.18090)、[ExecutionFirst](https://arxiv.org/abs/2607.29175)、[LIFT](https://arxiv.org/abs/2610.28819)、[ANCHOR](https://arxiv.org/abs/2610.16859) 和 [EffectWorld](https://arxiv.org/abs/2610.35981)。这些工作分别覆盖隐式合规、信息变体、执行细节渲染、合成双渲染、约束分类或 replay 验证；当前可守差异是参数级 query 约束、请求内可恢复 I、受控 N 近似对照、逐条必要性、faithful 主指标和结构不相交 OOD 的组合。

## 数据集审计

v5 生成与验证已完成，数据仍是合成且手工模板化，不能代表自然业务流量。规模为 5,350 个任务组、16,050 条记录：train/dev/template-HO/tool-name-HO/struct-HO = 4,000/300/350/350/350 组。`data/processed_v5/verification_report.json` verdict 为 `PASS`，跨切分 query、goal、group id 重叠为 0，witness、逐条必要性、N 近似门槛、策略卡无别名、结构签名不相交均通过。

v5 的 `test_tool_ho` 是名称级留出；真正结构 OOD 是 `test_struct_ho`（6 阶段、4 路备选、3 步 finish、审批锚点）。v5 仍缺独立人类/外部 oracle 对 I/N 的恢复率、一致率和空集误报率；作者试读不能替代双标注。可信约束只作为可信数据工作流案例背景，不等于中期材料 C1–C5 的完整实验。

## 已完成结果与未完成结果

### v5 seed42 更新（2026-11-23）

已完成并在本地重新评分的 v5 训练臂为 Qwen3-1.7B 和 Qwen3-4B，均为同一服务器、BF16、seed 42；0.6B v5 训练结果尚未落盘。下表是受约束记录的 `faithful_success`（显式和隐式各占一半），不是解析 F1：

| 系统 | dev | template-HO | tool-name-HO | structure-HO |
|---|---:|---:|---:|---:|
| Qwen3-1.7B LoRA | 98.50% | 96.71% | 91.71% | 95.86% |
| Qwen3-4B LoRA | 100.00% | 97.43% | 91.00% | 99.71% |
| DeepSeek ten-shot | 99.33% | 99.29% | 99.71% | 99.86% |

同底座零样本的 v5 faithful_success 分别为 17.17%/19.14%/13.43%/25.86%（1.7B，四个子集）和 51.50%/53.00%/56.71%/57.57%（4B）。因此训练增益在四个子集上都为正；这只能支持“训练相对同底座零样本有效”，不能替代多 seed 方差或强模型非劣效结论。

当前 v5 的预注册判定：1.7B 相对 DeepSeek 在 dev 可落入 3 个百分点非劣界内，但在 template-HO、tool-name-HO、structure-HO 均未达到；4B 在 dev 和 structure-HO 达到，在两个名称/措辞留出上未达到。结构留出必须单独报告，不能把 tool-name-HO 写成结构泛化。N 近似对照中 DeepSeek 各子类型误报率均不超过 5%，因此 H4 目前通过；Qwen-Max 零样本误报率约 47%–61%，不能作为干净安全基线。

v4 同服务器、BF16、seed 42 的 faithful execution 主表：

| 系统 | dev | template-HO | tool-name-HO |
|---|---:|---:|---:|
| Qwen3-0.6B LoRA | 97.33% | 82.29% | 75.57% |
| Qwen3-1.7B LoRA | 100.00% | 95.71% | 81.00% |
| Qwen3-4B LoRA | 100.00% | 95.86% | 99.86% |
| Qwen-Max PE zero-shot | 90.50% | 87.43% | 86.86% |
| Qwen-Max PE ten-shot | 88.17% | 85.00% | 89.14% |
| DeepSeek ten-shot | 99.33% | 99.00% | 100.00% |

这些数字是 v4 已完成证据，不能当成 v5 结果。v5 的强模型侧已有部分预测文件，但三尺寸 LoRA 的 v5 训练主表尚未完成；因此不能提前宣称结构 OOD 泛化或 v5 非劣效。

## 距离 CCF-B

已经具备：文献逐篇核验和 URL 边界、可执行数据生成/验证、同底座训练与强模型 PE 对照、faithful/safe/证据分列、失败分析、NaN 防护和可复现哈希。

投稿前必须补齐：

1. 完成 v5 的 0.6B，并补齐 1.7B/4B 的 seed 43/44，报告均值、标准差和逐 seed 失败记录；任务 bootstrap 不能代替训练方差。
2. 完成 `test_struct_ho` 结果，并按预注册 H1–H5 判定，不把名称级 tool-HO 写成结构泛化。
3. 完成至少两名独立标注者或不参与构造的强模型对 I/N 的恢复、空集误报和一致性。
4. 最终主表分列解析 F1、核心字段、证据、scope、N 误报、faithful、safe、延迟和显存；不能以一个高分覆盖字段错误。
5. 把 ② 固定为交叉干预/负结果，除非新的多种子 GRPO 实验满足预先写明的同预算判胜条件。

## 当前执行状态与下一步

v5 数据、验证器、测试和队列脚本已经提交到仓库；本地可继续做 CPU 审计和结果汇总。远端 SSH 当前因本机 `~/.ssh/config` 两条格式错误且现有密钥未通过认证，无法安全读取运行状态；在确认非交互凭据前不启动新 GPU，避免抢占或重复训练。每小时自动检查会继续只读监控、收集已完成结果、校验哈希并在 GPU 确认空闲且依赖满足时推进下一项。

最终判断：**①和③有机会形成 CCF-B 投稿主线，②只能按当前证据收窄；项目距离“可认真投稿”还差 v5 多 seed、结构 OOD 和独立可恢复性三类证据，距离“稳投”仍有明显差距。**
