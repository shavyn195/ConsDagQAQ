# ConsDAG v4：CCFA 对照、当前证据与 CCF-B 距离

日期：2026-11-23

本报告基于 `literature/ccfa_skills_v0.12.1` 中的 CCFA idea-reviewer、experiment-designer、evidence-design 和 experiment-discipline 规则，结合 v4 数据审计、E1/E2 原始结果、PE 对照、效率测量和已核验文献。它区分概念质量、已完成证据和投稿准备度；三者不是同一个分数。

## 结论先行

项目仍有 CCF-B 机会，但当前不能称为“稳稳够投”。最稳的论文主线是：

1. **① 训练式、可审计的逐请求约束编译器**：将用户请求和公开工具/策略目录编译为带类型、参数、表达状态、证据片段和作用角色的约束对象。
2. **③ E/I/N 配对的可执行约束基准**：同一任务骨架与约束集形成显式表达、请求内情境表达和受控无约束对比，附构造期可行性、必要性和执行检查。
3. **② 约束解释与候选计划搜索的交叉干预分析**：区分编译器错误和候选计划搜索错误，并测量局部修复能救回多少安全完成。

原先的“外部锚门控、节点归因、非对称罚的 GRPO 已稳定解决 reward hacking”目前没有足够的稳定多种子正向证据，不能作为已验证的第二个算法贡献。应将它降为设计边界/负结果，或继续补齐同预算、多种子、完整消融后再决定是否恢复为方法贡献。

CCFA v0.12.1 的历史概念分数为：① 4.13、② 4.18、③ 4.28。按校准规则，三者都属于 `revise`（`accept-to-develop` 要求至少 4.3）。这不是 CCF-B 录用概率，也不因已有实验自动上调。

## 三个创新点的当前口径

### ① Evidence-bound constraint compiler

可守的定义是：一个 planner-independent、训练得到、可审计的逐请求编译器，输入用户请求与公共工具/策略目录，输出 typed 约束对象。对象至少包含约束类型、参数、表达状态（explicit/implicit/none）、原文证据和抽象角色 scope。它把“约束解释失败”和“后续计划失败”分成可检查的接口，并支持本机部署。

当前证据支持：在冻结的 v4 合成工具世界中，LoRA 训练相对同底座零样本有明显收益；1.7B/4B 在部分留出集接近强模型 PE；小模型的自托管资源和延迟更低。当前证据不支持：全面胜过强模型 PE、已经证明 confidence 校准/拒判有用、每个字段都有独立因果收益、或已达到人类隐式约束理解水平。`scope`、`evidence`、`confidence` 应作为审计接口和待验证字段，不要写成已逐字段证明的机制。

### ② 交叉干预而非已证实的 GRPO 新目标

固定任务和候选计划空间，分别替换编译器输出或候选计划/局部修复器，观察安全完成是否恢复。这一分析有直接结果支持。现有动作信用、预防动作和加权 SFT 结果没有显示稳定的净增，不能把原 reward factorization 写成成功算法。若继续投入 ②，最低证据要求是同预算、至少三个训练种子、显式/隐式分层、功能成功率、约束安全成功率、无约束保持率和完整消融；否则正式论文中应保留交叉干预和负结果。

### ③ Executable paired constraint benchmark

每个任务组保留同一任务骨架和约束集，生成 E（显式）、I（约束不直陈但由请求内情境线索恢复）和 N（约束相关内容受控删除/近似干扰）。论文必须写“(E,I) 等价对 + (N) 对比臂”，不能写“三版语义等价”。每组带 witness、逐条必要性检查、角色绑定、执行检查器、模板留出和工具名留出。

该组合在受控合成工具世界内是可复核的基准贡献；不能写成“首个隐式约束工具基准”，也不能把名称级 tool holdout 写成全面结构 OOD。独立人类/外部强模型恢复率仍是关键缺口。

## 与相关工作的边界

以下使用组合差异表述，避免把已被先例覆盖的局部组件写成首次。

| 工作 | URL | 已覆盖部分 | ConsDAG 可守差异 |
|---|---|---|---|
| ATLAS | https://arxiv.org/abs/2509.25586 | 提示词多 agent、显式/隐式要求、scope | 训练专用小编译器、typed 参数、证据字段和执行级 E/I/N 配对 |
| CGAP | https://arxiv.org/abs/2610.41040 | 工具目录到操作/规则的编译、来源证据、运行时门控 | 逐请求用户约束的训练编译；其对象是能力/状态依赖规则，不是同一 query 约束接口 |
| Sapien | https://arxiv.org/abs/2610.00797 | 从 prompt 生成可执行工具策略 | 使用现成 LLM，未提供本项目的 typed 约束记录和 E/I/N 执行基准 |
| NOMOS | https://arxiv.org/abs/2610.11030 | 书面 policy 编译为 runtime gate、本机编译 | 域级 policy 与逐 query 约束对象不同；本机部署本身不是新颖性 |
| CARL | https://arxiv.org/abs/2607.04854 | planner 本体约束感知 RL/KL | 不物化独立约束对象，也没有本项目的配对执行基准 |
| TAG | https://arxiv.org/abs/2610.21404 | 内部锚门控辅助信用 | 锚和信用来源设计不同；现有结果不支持优于 TAG |
| RLVP | https://arxiv.org/abs/2607.07435 | 结果奖励加逐动作可验证罚 | 约束人工给定；本项目的自动 query 编译仍是目标，但当前只支持交叉干预 |
| SEVerA | https://arxiv.org/abs/2603.25111 | 形式合同、验证回退、硬/软分离 | 约束由形式规约给定，不处理自然语言逐请求发现 |
| DAGent | https://arxiv.org/abs/2609.39154 | DAG 拓扑级结果信用 | 对象是研究证据 DAG，不是用户约束编译和参数验收 |
| LogiSafetyBench | https://arxiv.org/abs/2601.08196 | 隐式法规合规、工具执行和时序验证 | 依赖法规/系统提示，缺少本项目的 query 级参数编译、N 对照和训练接口 |
| AM-Bench | https://arxiv.org/abs/2610.18090 | 同任务显式、模糊、缺失变体 | 缺失档不保证从输入恢复金标；本项目 I 档有请求内线索，N 是受控对比 |
| ExecutionFirst | https://arxiv.org/abs/2607.29175 | 同轨迹多档表达、执行优先验证 | 操纵执行细节明确度，不是约束表达状态 |
| LIFT | https://arxiv.org/abs/2610.28819 | 合成、双渲染和大规模训练集 | 约束全显式；没有参数级 I 线索、N 干扰和逐条执行咬合的组合 |
| ToolPrivacyBench | https://arxiv.org/abs/2606.28061 | 工具调用隐私执行审计 | 可作外部 OOD 候选，但不是逐请求约束编译基准 |
| Beyond ReAct | https://arxiv.org/abs/2511.10037 | Qwen3 工具 DAG planner 和合成工作流 | 只作为下游可信工具规划案例，方法层不绑定该基座 |

建议主张：

> 在已核验的检索范围内，尚未发现同时具备训练专用逐请求 typed 参数编译、请求内可恢复 I 线索、N 对照、逐条必要执行检查和双留出切分的工作。

不要写“首次约束编译”“首次隐式约束”“首次 scope 绑定”，也不要把扫描篇数当作无人做过的证明。

## 数据集审计

v4 有 5,000 个任务组、15,000 条记录：训练 12,000、开发 900、模板留出 1,050、工具名留出 1,050。约束类型为 privacy、deadline、tool_auth、order、budget；每组 1--3 条约束。生成报告记录了 SHA256，验证报告 verdict 为 `PASS`。

已核对的强项：

- witness 达成目标且满足约束；逐条必要性检查无失败；
- query、task goal、group id 在各切分之间重叠为 0；
- E/I 配对和 N 对照完整；
- 58 个本地测试通过，独立 verifier 复核为 PASS；
- 原始记录、哈希和配置可复核。

必须诚实写出的局限：

1. 数据是合成、手工模板化语言，不是自然业务流量。
2. tool holdout 主要是工具名/属性留出，流程阶段、拓扑和数值范围仍较同构，不能称全面结构 OOD。
3. 公共策略卡对部分测试 PII 字段提供了映射，privacy OOD 结果需作为敏感性诊断。
4. 主生成器没有必须 abstain 的歧义样本，confidence/拒判还没有被训练和验证。
5. I/N 独立人评包已生成但仍标记 `pending_human_review: true`；作者自行试读不能替代双标注、空集误报率和一致性报告。

可信约束的背景只能作为案例来源。当前 E1 的五类 query-level 约束并不等于中期材料中的 C1--C5：没有直接实现 trust score、sensitivity propagation、跨部门配额、sandbox tier 或 critical-path SLA 的完整语义。因此论文应写“trusted-data-space-inspired case instantiation”，不能写“已评测 C1--C5”。

## 实验与结果

### E1 编译器主表

当前已审计的 faithful execution 主结果为：

| 系统 | Dev | Template HO | Tool-name HO |
|---|---:|---:|---:|
| Qwen3-0.6B LoRA | 97.33% | 82.29% | 75.57% |
| Qwen3-1.7B LoRA | 100.00% | 95.71% | 81.00% |
| Qwen3-4B LoRA | 100.00% | 95.86% | 99.86% |
| Qwen-Max PE zero-shot | 90.50% | 87.43% | 86.86% |
| Qwen-Max PE ten-shot | 88.17% | 85.00% | 89.14% |
| DeepSeek PE ten-shot | 99.33% | 99.00% | 100.00% |

这支持“训练相对同底座零样本有收益”，也支持 1.7B/4B 在该合成世界接近部分强模型 PE。它不支持“小模型全面胜过强模型 PE”。解析 F1、faithful execution、evidence、scope、N 误报必须分开报告；4B tool holdout 的执行几乎满分，但证据完整性低于执行成功，不能用执行分替代证据保真度。

### E2

现有证据最稳的结论是：在固定候选空间中，编译器输出替换和一次验证过的局部修复可以把一部分失败重新变成安全完成；这支持“约束解释错误”和“候选计划搜索错误”可分离。原动作信用/预防动作/加权 SFT 没有稳定多种子正收益，因此不能报告为已成功的 GRPO 奖励方法。旧报告中条件编码不同的数字不能合并成一个主表，必须以配对原始文件和统一条件解释。

### PE 与效率

强模型 PE 已覆盖 Qwen-Max 零示例/十示例和 DeepSeek 十示例。DeepSeek 在留出集仍高于小模型，是必须保留的强对照。效率测量在同一 RTX 4080 SUPER、BF16、batch=1、固定输入/输出长度下，1.7B 解码中位 37.38 ms/token，4B 为 48.75 ms/token，1.7B 快 23.3%，峰值显存约 3.36 GiB 对 7.72 GiB。该结果只支持“本实验硬件和固定长度下小模型更快、更省显存”的工程结论，不支持普遍优于托管强模型；端到端 API 延迟和本地解码也不可直接当作同一成本。

## 代码与数值可靠性

当前 `run_e1.py` 已有有限 loss 检查、梯度裁剪、优化器更新后参数有限性检查、失败文件落盘和失败时不保存适配器。旧 FP16 NaN 运行必须隔离，不得进入主表；BF16 seed43 队列应继续使用这一保护路径。数据 verifier 和测试已通过，但每个 publication-facing 数字仍需绑定到模型、数据哈希、代码哈希、seed 和评估版本。

## 距离 CCF-B 的差距

### 必须补齐

1. **I/N 独立可恢复性**：两名独立标注者或不参与构造的强模型，只看请求、目录和策略卡，恢复 type+params+evidence，允许回答信息不足；报告一致率、N 空集误报和争议样本。
2. **训练方差**：至少给 0.6B/1.7B 的逐 seed、均值和标准差；单 seed 加 bootstrap 不能替代训练随机性。
3. **结构泛化**：补一个流程拓扑/阶段结构真正不同的冻结 OOD 子集，或者将主张明确收窄为名称级合成工具世界。
4. **② 定位**：若保留 GRPO，须有同预算、多种子、稳定正向增益和清晰消融；否则正式主线固定为 ①+③，②作为交叉干预和负结果。
5. **指标纪律**：将解析、证据、scope、N 误报、faithful execution、safe success、延迟和显存分列，避免一个高分掩盖另一项失败。

### 已具备

- 可复核的数据生成、witness、必要性、泄漏和哈希记录；
- 同底座零样本、LoRA、Qwen-Max、DeepSeek PE 对照；
- 执行级指标、字段错误分析、效率测量和失败记录；
- NaN 失败已识别并有防护代码；
- 与主要邻近工作的 URL 和边界已建立。

## 最终判断

**①和③可以继续做成 CCF-B 方向，但当前仍是“有机会、需补证据”，不是稳投。②原 GRPO 主张目前不成立，最安全的处理是交叉干预/设计边界；若想把它恢复为第二个算法贡献，必须先用统一条件、多种子和同预算实验证明稳定收益。**

最关键的三项工作是：完成独立 I/N 可恢复性审查、收齐训练多种子并明确结构 OOD 边界、冻结②的最终论文口径。完成后，项目会从“合成环境中有说服力的初步结果”提升到“可认真准备 CCF-B 投稿的证据包”；在此之前不应写成已经达到投稿标准。

## 可复核文件

- `data/processed_v4/generation_report.json`
- `data/processed_v4/verification_report.json`
- `reports/literature_audit_v4.md`
- `reports/trusted_constraints_literature_audit.md`
- `reports/compiler_efficiency_v1.md`
- `reports/e2_action_credit_pilot.md`
- `outputs/e1_v4_side/`
- `outputs/e2_v4/`
- `outputs/dataset_audit/v4-implicit-human-review-v1/`
