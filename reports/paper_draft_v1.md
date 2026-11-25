# ConsDagQAQ：逐请求参数级约束的编译-规划分离与行为-记录裂缝（论文草稿 v1）

版本：2026-11-25。依据：`reports/submission_plan_v3_20261124.md`（第一波第 4 项）、`reports/submission_plan_emnlp2027.md` §1、§5、§6。
写作纪律：
- 每个数字后括号注明来源，括号里的 JSON 字段路径用 `文件:字段` 表示；
- 尚未完成的实验用 `TODO(v6)` 占位，不写预测值；
- 不出现已死主张：小模型打平/超越强模型、human-validated semantics、GRPO/信用分配有效、跨域泛化。

本稿复核数字的来源包括：
- `outputs/submission/audit_20261124/recompute.json`，由 `scripts/submission/audit_recompute_20261124.py` 生成；
- `outputs/submission/audit_20261124/draft_numbers.json`，由 `scripts/submission/draft_numbers_20261124.py` 生成。
- `outputs/submission/audit_20261125/v5_record_axes_three_seed.json`，三seed含证据记录与N误报复算。
- `outputs/submission/audit_20261125/training_token_budget.json`，冻结训练配方的token重放计数。
- `reports/e3_ablation_readout_20261125.md` 与 `outputs/submission/followup_20261125/paired_replay.json`，E3四臂逐样本复算和按任务组配对区间。

以上分析只读冻结资产，零GPU；不替代原始预测和训练日志。近邻复核见 `reports/literature_architecture_recheck_20261125.md`。

---

## 摘要（占位）

TODO(v6)：摘要待 v6 主结果落地后定稿。完整公开输入 E2 已完成，其单 seed 限定见 §5.4；E3 消融现已完成并进入 §5.6。现阶段可写的三句：
1. 我们发布 E/I/N 配对的可执行约束基准；
2. 我们实现独立训练与审计的编译-规划分离架构，并在明确版本和消费者条件下评估组件替换；
3. 我们测得行为轴与记录轴的差异，并分解其跨 seed 错误模式。

---

## 1 引言（骨架）

**动机一：行为轴饱和。**
v5 基准上，DeepSeek 十示例编译器接符号规划器后，受约束 faithful 在四个切分上为 99.33% / 99.29% / 99.71% / 99.86%（`outputs/v5_analysis/main.json:table.deepseek-v4-pro-0813-few.*.faithful_mean`，dev/tpl/tool/struct 顺序）。按含证据完整记录计，同一系统只有 85.67% / 82.86% / 88.71% / 77.71%（同文件 `.exact_with_evidence_mean`）。只看执行结果已无法区分强系统。

**动机二：执行结果不足以检验约束记录。**
已有工作包含约束管理、中间表示与检查机制，不能声称记录评测一片空白。SpecHarness还在独立开发集比较七个编译器的覆盖率与记录有效性（Appendix A.1/Table8）。本文具体研究同一请求的类型化记录与执行结果能否给出一致的质量判断，重点是受训练编译器的字段、留出条件和seed差异。我们测得的差异（§5.3）表明，在明确字段消费规则的情况下，两者仍需分别报告。

**动机三：隐式约束失效。**
在 v4 的 tpl_ho+tool_ho 隐式题（共 700 条）上，两个强模型都用十示例提示，完整记录正确数分别为：
- DeepSeek：608/700（`outputs/e1_v4_side/deepseek-v4-pro-0813-few/full-scores.json:{test_tpl_ho,test_tool_ho}.v5.record_exact_match_by_variant.implicit` × 350 求和）；
- qwen-max：243/700（`outputs/e1_v4_side/qwen-max-few/scores.json`，同口径）。

隐式约束的可恢复性因模型而强烈分化。

**贡献（按 C1→C2→C3 排序）：**
- **C1 基准。** ConsDagQAQ 将同一构造任务的 E/I/N 呈现、类型化请求记录和固定规划器执行结果放在同一评测协议中。SCHEDBench 已测同一调度实例的自然语言表述变化与求解器可行性，DisasterBench 已测类型化工具工作流并做首个失败点归因；因此本文不主张配对表述、可执行约束评测或工具失败诊断本身首创。可检验的增量限于 E/I/N 状态、约束记录与下游 faithful execution 的联合分析。金标是生成器级构造条件，由 witness 计划经检查器验证，未独立验证自然语言语义。
- **C2 系统架构。** 编译-规划分离：独立训练的小编译器输出 typed 约束对象，由下游规划器消费，并单独审计记录。Qwen3＋LoRA 未改变底座网络结构；本项是系统组织与可检验接口设计，不是新神经网络。seed42 的完整公开输入 E2 中，编译器加符号规划器在四个切分的 faithful execution 均高于直出计划单体；但训练目标与 token 量不同，因此只支持当前合成设置下两套方案的结果差异，不能单独识别普遍架构因果或成本收益。
- **C3 发现。** 本文分析记录字段质量与固定规划器 faithful execution 的不一致，并用字段消融和多 seed 分解检验哪些记录错误会传到执行指标。DisasterBench 已有通用工作流首错归因，故这里不把“提出失败归因”当新贡献。现有 seed 分析显示执行轴的波动主要关联规划器消费的 params 字段；scope 的记录缺陷在多数切分上较稳定，却对执行指标不敏感。

完整公开输入 E2 是公开披露的探索性公平输入修正；四切分差值和限制见 §5.4。informed 旧臂和不完整输入旧臂仅作诊断，不进入公平架构比较。seed42 上当前差异不等于训练种子总体推断，CI 也未作多重比较校正。

---

## 2 相关工作（骨架：只列近邻与定位差异）

近邻清单与分组取自 `reports/submission_plan_emnlp2027.md` §2、§2.1、§8.3。ATLAS、CGAP、SpecHarness、Coordination Tax、CARL、CIRCE、SOTERIA 的原文与 arXiv 元数据已核验，笔记及参考条目见 `literature/review_20261125/`；其余行仍是待逐篇确认的定位提纲，不以未复核概括论证独创性。

| 线 | 近邻 | 与本文的定位差异（一句话） |
|---|---|---|
| 约束编译 / 中间表示 | CGAP（2610.41040）、CIRCE（2610.41089）、ATLAS（2509.25586）、SafeOrchestrate（2611.09364）、Compile-Then-Page（2607.11346）、SpecHarness（2609.29921） | 这些工作已覆盖请求解析、自然语言到规格、工具角色映射、形式化中间表示、运行时检查及记录审计。SafeOrchestrate 的架构与编译—规划—执行门控尤其接近，但其评测任务大多单规则且约束集为空，交叉规则安全检查主要用示例展示。本文只能主张受控逐请求训练和诊断实验，不能主张首次解耦或首次规格编译 |
| 约束学习与隐式规划 | CARL（2607.04854） | CARL 以约束／无约束输入的输出分布差构造奖励，在 BlocksWorld、TravelPlanner、T-Eval 上训练规划模型；T-Eval 隐式约束由 GPT-4o 提取。本文的 GRPO 信用分配无稳定收益且不再作为贡献；编译器训练是否补充不同能力须由有效单体对照验证 |
| 隐式约束与执行基准 | LogiSafetyBench（2601.08196）、ToolPrivacyBench（2606.28061） | LogiSafetyBench 已用 LTL oracle、可执行轨迹和 240 条经人工核验任务测隐式监管合规；ToolPrivacyBench 有 2,150 条合成及公开衍生工作流，并对授权标签抽样复标。本文的具体评测差异是同一任务的 E/I/N 配对渲染与类型化记录—执行联合分析；生成器 witness 不验证请求语义 |
| 运行时规格与安全基准 | SOTERIA（2611.17880）、SCA（2610.25552）、AM-Bench（2610.18090）、EffectWorld（2610.35981） | SOTERIA 在 207 个真实工具任务、4 个模型上报告零规格违规，并测成功率、违规和成本；输入规格来自领域政策／工具文档，经半自动形式化及人工检查后复用。本文关注逐请求语言约束能否被编译成记录；当前合成语义金标未经独立人审，不能把程序可执行性写成人类语义有效性 |
| 隐式约束 / 约束下规划 | LogiSafetyBench（2601.08196）、AdaPlanBench（2606.05622）、CARL（2607.04854）、HOB（2603.29025）、ToolMaze（2606.05806）、HyperAgent（2608.02650） | 已有隐式约束合规、交互式重规划和受约束规划研究。AdaPlanBench 研究反馈逐步披露后的重规划；LogiSafetyBench 检验从政策上下文推断隐藏步骤；本文只测同一构造任务不同语言呈现下的记录与执行结果，不将隐式约束评测本身称新 |
| 可执行配对世界与结构诊断 | NormWorlds-CF（2607.03957）、EffectWorld（2610.35981）、AM-Bench（2610.18090） | NormWorlds-CF 已有 solver-verified paired worlds、结构化变化记录、按根族切分与三 seed 实验；本文的具体差别是同任务 E/I/N 语言变体及约束记录到固定规划器的执行联动，不主张配对可执行评测或结构诊断首创 |
| 语言表述变化与约束忠实度 | SCHEDBench（Findings of EMNLP 2026） | 1,132 个经典调度实例、13 个模型、求解器标签；100 条分层样本经两位专家独立核验、协商后报告零语义错误。已覆盖同实例不同自然语言表述下的约束忠实度。本文不能主张“配对表述评测”首创；差异只能是 E/I/N 三态与 typed record—固定 planner 执行联合评测，且自身语义金标质量仍弱于其已报告的抽查证据。 |
| 类型化工具工作流与失败归因 | DisasterBench（Findings of EMNLP 2026） | 233 个任务、26 个工具，评测工具、参数、依赖，并以 FPoF 归因首错；参考工作流经过四位博士两轮专家审阅。故本文不能泛称工具约束基准或失败诊断新颖，需收窄到约束记录字段对 faithful execution 的条件影响。 |
| 安全规格与工具执行验证 | Towards Verifiably Safe Tool Use for LLM Agents（ICSE-NIER 2026） | 已有从安全需求到形式规格、工具标记及验证的架构先例。正文本轮无法从 ACM 获取，具体方法细节需在投稿前复核；无论如何，通用“规格编译后再执行检查”不能单独作为 C2 创新。 |
| 约束表示的可靠性验证 | CIRCE（2610.41089） | CIRCE 对三个基准的结构表示做全量规则核验，对另四个基准各抽20例人工核验；它预测解题难度而非生成执行约束。该设计说明，即便有程序检查，语义正确性仍需独立证据 |
| 分解成本之争 | Coordination Tax（2610.37700）、MA-Evolve（2609.04217） | Coordination Tax已含异构角色对照，3.22倍是其特定实验结果而非本研究门槛。本文E2控制底座、训练行、更新次数与LoRA配置，另核算用量；同更新数不等于计算匹配，训练 target 和 token 量也不同（§5.4） |
| 评测器可靠性 / 失效归因 | DisasterBench（Findings of EMNLP 2026）、Trace 审计（2610.30491）、Who&When Pro（2607.09996） | DisasterBench 的 FPoF 已定位工具工作流首错；本文只能检验约束记录字段错误如何对应固定 planner 的执行成功，不把一般失效归因作为贡献。 |
| skill 范式 | Agentic Skills 综述（2608.29596）、Skill 参考架构（2606.20631）、SkillFusion（2610.15481）、SkillBrowser（2610.23554） | 放入 Discussion "Why not a skill?"（本稿未写） |

收尾定位句（写作时用）：本文在单一合成可执行世界中联合评估执行行为与逐请求记录，并报告留出集、seed及消费者切换的失败模式；不声称首次提出约束解析、隐式约束学习、奖励分解、记录审计或运行时规格验证，也不把构造期可行性当作真实请求语义验证。

---

## 3 方法：编译-规划分离

### 3.1 架构

管线分三段：
1. **编译器** C：查询 + 工具目录 → typed 约束集合；
2. **规划器** P：任务结构 + 约束集合 → 计划；
3. **检查器** K：计划 + 金标约束 → 判定。

推理时C向P提供typed约束对象，P向旁路评测器K提供计划；隐藏金标只对K可见。监督训练使用金标作为target，不能将“推理无金标”混称训练也无金标。编译器的提示由三部分组成：策略卡、工具目录（每个角色给出名称、付费/免费、本地/外发）、输出schema（`src/run_e1.py:87-106`）。编译器从不看到任务的阶段结构，也不看到工具的成本和时长数值。成本、时长、阶段结构只由P与K使用。

### 3.2 typed 约束对象

每条约束有六个字段：
- `type` ∈ {budget, deadline, privacy, tool_auth, order}；
- `state` ∈ {explicit, implicit}，记录层另有 `query_state` ∈ {explicit, implicit, none}；
- `severity`；
- `scope`：绑定到目录角色集合；
- `params`：类型专属参数，例如 `max_total_cost_cny`、`max_duration_hours`、`approval_role`/`required_role`；
- `evidence_span`：从查询中逐字拷贝的句子。

schema 见 `src/run_e1.py` 的 `SCHEMA_HINT_V4`；每种类型的参数与 scope 约定见 `src/dataset_v5_spec.py` 的 `POLICY_CARD`。

**字段消费方分层（设计声明）。** 规划器与检查器的归一化函数只读 `type` 与 `params`（`src/trust_env.py:33-61`，`normalize_constraint`）。`state`、`severity`、`scope`、`evidence_span` 只进入记录轴评分。因此，scope 或 evidence 错误不改变执行结果是**构造性质**，不是实验发现。§5.3 中"scope 错误对执行不可见"的表述以此为前提。

### 3.3 最小改动规划器

符号规划器 `plan()`（`src/trust_env.py:164-190`）的做法：
1. 在阶段备选的笛卡尔积、finish 块的全部排列、可选匿名化步骤上做穷举；
2. 为前置类约束插入缺失的可选前置步骤（`_close_precedence`，同文件 134-148）；
3. 在执行完成且不违反任何输入约束的候选中，取改动数最小者。

改动数 = 阶段替换数 + finish 逆序对数 + 匿名化插入数 + 前置插入数。并列时依次比较成本、时长、字典序。

同一改动数也可以对任意给定计划独立计算（`plan_change_count`，同文件 197-221）。E1 的 symbolic 列用这两种算法分别计数，1400 条受约束行上逐条一致（审计复算，差异 0）。

### 3.4 独立检查器与 faithful 定义

检查器 `check()`（`src/trust_env.py:113-126`）执行计划，并逐条检查金标约束是否被违反：`safe_success` = 完成目标且无违反。

- 受约束行：**faithful** = `safe_success` 且计划改动数等于金标约束下的最小改动数；
- 无约束（N）行：faithful = 不偏离默认计划。

上述定义见 `src/eval_exec.py:33-54`（`record_outcome`）与 `src/sub_e1_grid.py:101-104`。

faithful 排除了"多改几步也安全"的过编辑。保守参照臂不做最小改动，它的 faithful 在四个切分上全为 0，safe 为 0.6733 / 0.6343 / 0.6143 / 0.5543（`outputs/v5_analysis/main.json:table.conservative_reference`）。

### 3.5 fail-closed 记录评测

记录轴评分只认严格解析成功的输出（`src/run_e1.py:199-214`，`strict_parse`），结构契约见同文件 169-196。结构不完整时：
- 该条视为无效，金标约束全部计 FN；
- 不产生 FP；
- 不给状态分。

匹配键为 (type, state, severity, scope 集合, params 规范化)（同文件 239-256）。core 键只看 (type, params)（同文件 270-273）。

### 3.6 训练配置

编译器使用 Qwen3 0.6B/1.7B/4B 的 LoRA，参数为：r=16，α=32，lr=2e-4，3 epoch，梯度累积 4，bf16（`outputs/e1/Qwen3-1.7B-v5-seed42/metrics.json:config`）。主结果跑三个 seed（42/43/44）。

---

## 4 基准：ConsDagQAQ

### 4.1 数据构造

- **E/I/N 最小三元组。** 每个任务组生成显式、隐式、无约束三条查询，三者共享同一任务。v5 的每个切分中，三种变体条数严格相等（`outputs/submission/audit_20261124/draft_numbers.json:dataset_v5.*.variants`）。
  - E：用指令句陈述约束；
  - I：不含指令，约束由查询中的事实推出（可能需要算术或映射）；
  - N：含干扰句。干扰句分四个子类型：豁免、撤销、他方规则、许可。
- **witness 与构造条件。** 生成器用 `plan()` 求出 witness 计划，再由 `check()` 确认安全；任一步失败即丢弃该样本（`src/build_dataset_v5.py:238-239`）。在 v5 train 的 8000 条受约束行上，witness 计划 8000/8000 安全，且 8000/8000 改动数等于最小改动（`outputs/submission/audit_20261124/recompute.json:v5_train_witness`）。
- **金标性质声明。** labels are construction conditions, not human-validated semantics。金标是生成器声明的构造条件，没有经过正式人审。LogiSafetyBench 报告了 oracle 与样本的人类核验；ToolPrivacyBench 报告了分层抽样的授权标签复标与一致率。因此本数据集不能以 witness 正确性替代语义验证，250 条盲审工件也不能写成已完成的人评（`reports/submission_plan_emnlp2027.md` §5.1）。
- **验证门槛。** 设计文档记录了 V1–V14 的全部门槛均为 PASS（`reports/design_v5_ccfb.md:201-210`），包括：
  - witness 执行；
  - 逐条必要；
  - 跨切分零重叠；
  - struct 签名与 train 不相交；
  - 保守规划器 faithful ≤ 0.05。

### 4.2 切分与 held-out 设计

各切分均按任务组整体划分，同一组的 E/I/N 三条不会跨切分。

| 切分 | 组 | 条 | 测什么 | 来源 |
|---|---:|---:|---|---|
| train | 4000 | 12000 | — | `draft_numbers.json:dataset_v5.train` |
| dev | 300 | 900 | 同分布 | `draft_numbers.json:dataset_v5.dev` |
| test_tpl_ho | 350 | 1050 | 措辞 OOD（test 措辞池） | `draft_numbers.json:dataset_v5.test_tpl_ho`；`reports/design_v5_ccfb.md:190` |
| test_tool_ho | 350 | 1050 | 名称级 OOD（结构与 train 同，工具名不同） | `draft_numbers.json:dataset_v5.test_tool_ho`；`reports/design_v5_ccfb.md:191` |
| test_struct_ho | 350 | 1050 | 结构 OOD | `draft_numbers.json:dataset_v5.test_struct_ho`；`reports/design_v5_ccfb.md:192` |

表中"组"为任务组数，"条"为记录数。v5 共 16050 条（`draft_numbers.json:dataset_v5.total_rows`）。

test_struct_ho 的 299 种任务结构签名全部不出现在 train 中（`draft_numbers.json:v5_structure_and_tool_values.test_struct_ho`）。tool_ho 被如实标为"名称级"：其结构与 train 相同，签名不重叠仅因工具名不同（`reports/design_v5_ccfb.md:146`）。

**v6 发布版。** 共 17100 条（`draft_numbers.json:dataset_v6.total_rows`）。v6 新增 test_composition_ho（350 组 / 1050 条，`draft_numbers.json:dataset_v6.test_composition_ho`），用作类型组合 held-out 探针。按设计文档声明，只称"held-out pair 探针"，不称因果干预。
TODO(v6)：v6 六个 run 的结果与 v5 的一致性检查；主表是否切到 v6，按方案 v3 §4 的决策树决定。

### 4.3 评测轴

本文报告五个轴：
- strict 记录 F1；
- 隐式行记录 F1（implicit recovery）；
- N 误报率（N alarm）；
- 含证据完整记录率；
- 执行 faithful。

前三者是主对比轴，faithful 是参考列（`reports/submission_plan_emnlp2027.md` §1.2）。理由见引言动机一：faithful 在强模型上已经饱和。

---

## 5 实验

### 5.1 v5 主结果（三 seed）

**表 1：受约束 faithful（%）。** 单元格内容为均值 ± 样本标准差，括号内为逐 seed 值（42/43/44）。

| 编译器 + 符号规划器 | dev | tpl_ho | tool_ho | struct_ho |
|---|---|---|---|---|
| 1.7B LoRA | 98.72±0.86 (98.50/98.00/99.67) | 96.71±1.14 (96.71/95.57/97.86) | 79.76±10.53 (91.71/75.71/71.86) | 82.90±11.28 (95.86/75.29/77.57) |
| 4B LoRA | 99.94±0.10 (100.00/99.83/100.00) | 96.67±3.49 (97.43/92.86/99.71) | 87.00±11.40 (91.00/95.86/74.14) | 96.76±3.08 (99.71/97.00/93.57) |

来源：`outputs/submission/audit_20261124/draft_numbers.json:v5_three_seed_faithful`。逐 seed 值取自 `outputs/v5_analysis/seed_variance_decomposition_20261125.json:models.*.*.per_seed.*.faithful_rate`。1.7B 的三 seed 均值与标准差与 `outputs/v5_analysis/v5_main_0530_20261124.json:table.Qwen3-1.7B-LoRA` 一致。

**表 2：参考臂（单次）。** 每格为 faithful / 含证据完整记录 / N 误报。

| 参考臂 | dev | tpl_ho | tool_ho | struct_ho |
|---|---|---|---|---|
| DeepSeek 十示例 | 99.33 / 85.67 / 0.33 | 99.29 / 82.86 / 0.00 | 99.71 / 88.71 / 0.86 | 99.86 / 77.71 / 2.00 |
| qwen-max 零示例 | 83.83 / 33.67 / 57.67 | 86.00 / 33.71 / 53.71 | 81.86 / 28.14 / 47.43 | 79.29 / 25.29 / 60.57 |
| Qwen3-1.7B 零示例 | 17.17 / 0.33 / 99.33 | 19.14 / 1.00 / 98.86 | 13.43 / 0.43 / 99.43 | 25.86 / 1.00 / 100.00 |
| Qwen3-4B 零示例 | 51.50 / 1.67 / 99.33 | 53.00 / 1.57 / 96.29 | 56.71 / 2.71 / 98.00 | 57.57 / 1.57 / 99.43 |

来源：`outputs/v5_analysis/main.json:table.<arm>.<split>.{faithful_mean, exact_with_evidence_mean, none_false_alarm}`。

**表 3：strict 记录 F1（逐 seed 42/43/44）。** 每格为全体约束 F1 | 隐式行 F1。

| 编译器 | dev | tpl_ho | tool_ho | struct_ho |
|---|---|---|---|---|
| 1.7B LoRA | .986/.972/.998 \| .973/.966/.996 | .935/.920/.967 \| .924/.925/.984 | .599/.535/.398 \| .601/.533/.387 | .631/.424/.513 \| .640/.435/.502 |
| 4B LoRA | 1.000/.998/1.000 \| 1.000/.996/1.000 | .965/.955/.989 \| .990/.972/.997 | .932/.679/.443 \| .932/.675/.446 | .720/.595/.588 \| .690/.621/.592 |

来源：`outputs/e1/Qwen3-{1.7B,4B}-v5-seed{42,43,44}/metrics.json:trained.<split>.constraint_micro.f1` 与 `.per_variant.implicit.f1`。

**补充：三 seed 记录完整性与 N 误报。** 含证据完整记录只统计受约束 E/I 行；N 误报包括非空约束、错误 query_state 或畸形输出。数字均为百分比，完整记录列为均值±样本标准差，N 列为均值。

| 模型、口径 | dev | tpl_ho | tool_ho | struct_ho |
|---|---:|---:|---:|---:|
| 1.7B 含证据完整记录 | 97.50±2.09 | 90.71±4.83 | 37.00±9.42 | 34.86±10.19 |
| 4B 含证据完整记录 | 99.89±0.19 | 95.00±3.71 | 58.67±30.13 | 45.71±8.89 |
| 1.7B N 误报 | 0.33 | 9.14 | 0.19 | 0.00 |
| 4B N 误报 | 0.00 | 2.29 | 0.00 | 0.00 |

来源：`outputs/submission/audit_20261125/v5_record_axes_three_seed.json`，服务器 CPU 基于全部冻结预测重算，288 条抽查与原 `rescore_v4_side.outcome` 完全一致。含证据完整记录与只看约束匹配键的 `record_exact_match` 不同，不可混称。4B tool_ho 记录轴的 30.13pp 标准差进一步要求保留逐 seed 数字，而不是只报最好 seed。

**如实陈述：**
- **训练增益（seed42 单次）。** 1.7B 训练臂相对同底座零样本的 faithful 差在四个切分上为 +81.33 / +77.57 / +78.29 / +70.00pp。按组 bootstrap 的 95% 区间全部大于 0（`outputs/v5_analysis/main.json:decisions.H1_training_gain_1.7B`；该文件训练臂只含 seed42）。
- **非劣效（H2）不成立。** 预注册标准是"训练臂减 DeepSeek 的 faithful 差，95% CI 下界大于 −3pp"（`reports/design_v5_ccfb.md:175`）。在 tool_ho 上，4B 三 seed 均值为 87.00%（同表 1），DeepSeek 为 99.71%（表 2），差距超过 12pp。单 seed 判定结果：
  - 1.7B 在 tpl/tool/struct 三个切分上均不满足（`main.json:decisions.H2_noninferiority_vs_deepseek_1.7B`）；
  - 4B seed42 在 tpl/tool 上不满足（`main.json:decisions.H2_noninferiority_vs_deepseek_4B`）。

  本文不主张小编译器在质量上与强模型相当。小编译器的定位是部署属性（§5.5）加诊断价值。
- **OOD 切分方差大。** tool_ho 与 struct_ho 上，faithful 的跨 seed 摆幅最大达 21.71pp（4B tool_ho，`outputs/submission/audit_20261124/recompute.json:seed_variance_derived."Qwen3-4B | test_tool_ho".faithful_swing_pp`）。因此单 seed 排序不可信，机制见 §5.3。

### 5.2 E1 插拔网格：编译器轴 × 规划器轴

**设置。** 12 个格子全部为冻结缓存的 CPU 回放，不训练也不推理（`src/sub_e1_grid.py`）。
- 编译器轴：0.6B/1.7B/4B LoRA，以及 DeepSeek 十示例。DeepSeek 一档称为 prompted compiler（skill-style）。
- 规划器轴：两个 SFT 神经规划器（同一 1.7B 规划器的两种训练顺序 order42/order44，四候选池 + 单编辑修复，`src/sub_e1_grid.py:37-41`），以及符号规划器。
- 面板：**v4 的 tpl_ho+tool_ho**，共 2100 条，其中受约束 1400 条、N 700 条（`outputs/submission/e1_grid/results.json:design`）。

注：方案要求"架构实验挂 v5"，本网格目前挂在 v4 面板上，见待决策清单。

**表 4：E1 网格。** 每格为受约束 faithful [按组 bootstrap 95% CI] / safe_success（全 2100 行）。

| 编译器 \ 规划器 | SFT-order42 | SFT-order44 | symbolic |
|---|---|---|---|
| 0.6B LoRA | .2514 [.2257,.2771] / .8776 | .2607 [.2343,.2879] / .9043 | .7893 [.7614,.8164] / .8767 |
| 1.7B LoRA | .2657 [.2400,.2921] / .8990 | .2786 [.2514,.3057] / .9190 | .8836 [.8629,.9036] / .9267 |
| 4B LoRA | .2793 [.2521,.3064] / .9229 | .2886 [.2607,.3164] / .9390 | .9786 [.9700,.9864] / .9857 |
| prompted (DeepSeek 10-shot) | .2814 [.2543,.3086] / .9305 | .2950 [.2671,.3236] / .9486 | .9950 [.9900,.9993] / .9967 |

来源与口径：
- faithful 及其 CI 来自 `outputs/submission/audit_20261124/recompute.json:e1_constrained.cells.*`：受约束 1400 行、700 组，10000 次 bootstrap，seed 20261124；
- safe 来自 `outputs/submission/e1_grid/results.json:cells.*.overall.safe_success`；
- `results.json` 中的 `faithful_ci95_group` 是对全 2100 行 faithful 计算的，与本表的受约束口径不同，不要混用。

**发现：**
1. **symbolic 列在所测四类编译器上可运行，执行率依次上升。** 这是当前接口的兼容性观察；不证明无信息损失或任意消费者适配。该消费者只读取 type/params，完整记录错误与执行失败不是同一指标。
2. **接口可消费外部编译器输出。** 在 symbolic 列中，DeepSeek 十示例减所测 4B LoRA 的受约束 faithful 为 +1.64pp，按组配对 95% CI 为 [+0.93, +2.43]（`recompute.json:e1_constrained.symbolic_deepseek_minus_4B`）。该结果支持此接口在一个外部编译器上的可用性，尚不能独自证明普遍可移植性或架构优势。
3. **SFT 规划器两列对编译器质量几乎平坦。**
   - 受约束 faithful 只在 .2514–.2950 之间，safe 却达到 .8776–.9486（表 4），说明瓶颈在消费者，而不在编译器。
   - 同两列在 N 行上的 faithful 只有 .0529–.0829（`results.json:cells.*.overall.by_variant.none.faithful`），说明 SFT 规划器在无约束题上也系统性地偏离默认计划。
4. **2×2 失效归因（v4，同一面板）。** 固定编译器换候选池、固定候选池换编译器，四格受约束 safe 分别为 1144 / 1199 / 1255 / 1292（分母 1400，`outputs/e2_v4/failure-interventions-2x2-v1/results.json:cells`）。初始失败分两类：
   - **可达失败** 118 例（一步邻域或原候选中有安全解，93+25 例）：只换编译器救回 112 例（87+25）；
   - **不可达失败** 138 例（无安全邻居或无完整计划，128+10 例）：只换候选池救回 47 例（43+4）。

   以上均来自同文件 `interventions_on_initial_failures`。前者对应"读错约束"，后者对应"搜索受限"。

完整公开输入 E2 × symbolic 对照、N 版计划偏离和单体实际用量见 §5.4；API 消费者交叉结果另见报告 `reports/consumer_cross_results_20261125.md`。API 响应数与模型生成 token 不能和单体时延混为同一成本口径。

**补充：v5强弱编译器×外部消费者交叉。** 两个冻结编译器分别接符号消费者和DeepSeek零样本消费者（thinking关闭、最多384输出token）。四切分受约束faithful（%）：

| 编译器→消费者 | dev | tpl_ho | tool_ho | struct_ho |
|---|---:|---:|---:|---:|
| 1.7B seed42→符号 | 98.50 | 96.71 | 91.71 | 95.86 |
| DeepSeek十示例→符号 | 99.33 | 99.29 | 99.71 | 99.86 |
| 1.7B seed42→DeepSeek零示例 | 39.67 | 37.43 | 29.86 | 30.71 |
| DeepSeek十示例→DeepSeek零示例 | 40.50 | 37.57 | 34.29 | 31.86 |

来源：`outputs/submission/deepseek_planner_v5_parse_parity/e2_shared_analysis.json:table`。原API读取器直接要求整个回答为JSON，5339次响应中5337次带Markdown代码块，原受约束全零作为格式遵从成绩保留。此表是披露后的缓存评分对齐，复用原E2读取器，且只移除单个代码块也得到完全相同的8100条执行判定；不改工具／顺序／数值，无新模型调用。不可把格式零分当规划能力结论，也不可把修正成绩追认为预注册。

在API消费者下，强减弱编译器的tool_ho差为+4.43pp、任务组配对95%CI[+2.29,+6.71]；dev/tpl/struct分别+0.83/+0.14/+1.14pp，区间均含零。该观察不支持无衰减换消费者，且不能代表DeepSeek的规划能力上限；零样本消费者与十示例编译器是不同子任务。强编译器→API的有效计划中，仍有大量已给定时限与隐私违反，并非只因最小改动指标苛刻（`failure_diagnostic.json`）。完整结果与限定见 `reports/consumer_cross_results_20261125.md`。

该v5交叉与上方v4 SFT网格版本不同，分表报告；不拼成同面板三向排名。区间条件于固定权重和API缓存，未作多重比较校正。实际5339请求共6,331,727 token，只是规划阶段用量，不含编译、未返回usage的重试和完整账单，不能用于宣称端到端价格优势。

### 5.3 行为-记录裂缝与 seed 方差的双轴机制

**裂缝（v5，三 seed）。** 1.7B LoRA 在 tool_ho 上：
- 受约束 faithful 三 seed 均值 79.76%（表 1）；
- 含证据完整记录三 seed 均值只有 37.00%；
- struct_ho 上对应为 82.90% 对 34.86%。

完整记录数字来自 `outputs/v5_analysis/v5_main_0530_20261124.json:table.Qwen3-1.7B-LoRA.{test_tool_ho,test_struct_ho}.exact_with_evidence_mean`。

v4 单 seed 上的典型样例：4B tool_ho 执行 faithful 699/700，含证据完整记录 552/700（`outputs/e1_v4_side/supplement-4B-paired.json:test_tool_ho.arms.4B`）。

**seed 方差分解。** 脚本为 `scripts/submission/seed_variance_decomposition.py`，产物为 `outputs/v5_analysis/seed_variance_decomposition_20261125.json`。审计复跑结果与产物逐字段一致。在每个切分的 700 条受约束行上，对金标与预测做同 type 匹配后逐字段比对。

1. **三 seed 共杀在绝对量上很少，但高于独立基线。** tool_ho/struct_ho 上，同一条记录被三个 seed 同时判失败的数量为：

   | 切分 | 观测 | 独立期望 | 观测/期望 |
   |---|---:|---:|---:|
   | 1.7B tool_ho | 15 | 3.96 | 3.79× |
   | 1.7B struct_ho | 6 | 1.61 | 3.73× |
   | 4B tool_ho | 4 | 0.67 | 5.97× |
   | 4B struct_ho | 0 | 0.00 | — |

   观测值见 `seed_variance_decomposition_20261125.json:models.*.*.record_failure_count_by_number_of_seeds."3"`；独立期望 = n·∏(失败率)，见 `outputs/submission/audit_20261124/draft_numbers.json:three_seed_cofail`。

   因此，跨 seed 的失败**主要**是 seed 特异的，但存在一个超出独立假设 3.7–6.0 倍的小规模共同难例核。不能表述为"完全不是系统性难度"。另外，record 级 Jaccard 受各 seed 失败基数不等的机械约束。例如 1.7B tool_ho 的 seed42 有 58 条失败、seed44 有 197 条，Jaccard 上界为 58/197（`recompute.json:seed_variance_derived."Qwen3-1.7B | test_tool_ho".failed`）。所以 Jaccard 低不能单独作为噪声证据。

2. **params 字段（规划器消费）的错误跨 seed 几乎不重叠。** 出现 params 错误的记录，其三 seed 交集/并集为：
   - 1.7B tool_ho 0.077，struct_ho 0.033；
   - 4B tool_ho 0.018，struct_ho 0.014。

   来源：`seed_variance_decomposition_20261125.json:models.*.*.field_stability.params.intersection_over_union`。执行轴的跨 seed 波动与 params 的 seed 特异错误同向。

3. **scope 字段（只进记录轴）错误规模最大，且在三个切分上跨 seed 高度一致。** 带 scope 错误的记录数（seed 42/43/44）与三 seed IOU 为：

   | 切分 | 记录数 | IOU |
   |---|---|---:|
   | 1.7B tool_ho | 384/352/404 | 0.629 |
   | 1.7B struct_ho | 358/426/418 | 0.735 |
   | 4B struct_ho | 302/355/365 | 0.810 |

   来源：同文件 `field_stability.scope`。由 §3.2 的消费方分层可知，这些错误对 faithful 不可见。这一点是构造性质；**发现**在于，记录轴上规模最大的缺陷是跨 seed 稳定的系统性绑定缺陷，只报执行轴会把它完全漏掉。

   例外：4B tool_ho 上 scope 错误记录数为 67/309/446，IOU 0.048，属于 seed 不稳定，不属于系统性缺陷。须按切分分别陈述。

4. **两轴排序不一致。** 4B tool_ho 上：
   - 按 faithful，seed 排序为 43 > 42 > 44；
   - 按 strict F1，排序为 42 > 43 > 44。

   来源：`recompute.json:seed_variance_derived."Qwen3-4B | test_tool_ho".{seed_rank_by_faithful, seed_rank_by_strict_f1}`。单轴报告会给出不同的"最好模型"。这是双轴分列的直接经验理由。

**限定词（必须随段写出）：**
- 这是对固定观测 seed 的描述性分解，不做 seed 总体推断；
- 字段匹配取同 type 的第一个未用预测。v5 测试切分上没有同 type 的多条金标，与暴力最优匹配相比，每切分只有 0–2 条记录的 params/scope 判定会翻转（审计抽查 1.7B tool/struct、4B struct）；
- params 比较未做整/浮点规范化。1158 处 params 不一致中，0 处仅为整/浮差异，1 处行为等价（审计抽查）。

### 5.4 E2 单体对照（完整公开输入）

完整设置、逐切分结果与 N 版分解见 `reports/e2_public_contract_readout_20261125.md`。简表报告受约束 E/I 的 faithful success；差值为单体减编译器+符号规划器，区间按 E/I 任务组 bootstrap 10,000 次，条件于当前 seed42 权重：

| 切分 | 单体 | 编译器+符号规划器 | 差值 pp [95% CI] |
|---|---:|---:|---:|
| dev | 90.67% | 98.50% | −7.83 [−11.17, −4.67] |
| tpl_ho | 87.29% | 96.71% | −9.43 [−12.86, −6.00] |
| tool_ho | 38.14% | 91.71% | −53.57 [−59.00, −48.14] |
| struct_ho | 14.29% | 95.86% | −81.57 [−84.86, −78.14] |
| 合并 E/I | 56.37% | 95.59% | −39.22 [−41.85, −36.52] |

来源（逐行顺序与表格一致）：`e2_public_contract_independent_audit.json:splits.dev.paired_monolithic_minus_pipeline`、`.splits.test_tpl_ho.paired_monolithic_minus_pipeline`、`.splits.test_tool_ho.paired_monolithic_minus_pipeline`、`.splits.test_struct_ho.paired_monolithic_minus_pipeline`、`.overall_paired_monolithic_minus_pipeline`；各臂点估计分别来自同对象的 `monolithic_faithful_constrained`、`pipeline_faithful_constrained` 字段。

该探索性 seed42 比较支持当前合成设置下分离管线具有更高 faithful execution；它不是架构总体优势检验。两臂均用 Qwen3-1.7B、12,000 行、bf16、LoRA 和 9,000 更新，但单体 target 是计划、编译器 target 是约束。三轮 prompt/target/total token 分别为编译器 26.06M/2.67M/28.73M，单体 35.35M/1.06M/36.40M；故更新数相同不代表 FLOPs 或监督量相同。单体 `elapsed_s=8028.5` 含初始化、训练、评测和分析；不据此主张训练或推理效率。

完整公开输入单体的 planned/safe/faithful 均报告。其 tpl_ho N 版有 83/350 条有效计划偏离默认值（`e2_public_contract_independent_audit.json:splits.test_tpl_ho.none.counts`）；struct_ho 有 8/350 条计划无效（`.splits.test_struct_ho.none.counts`），二者分开计数，不能将所有非-faithful N 结果叫约束抽取误报。评测有 59 条 struct_ho 的提示加金标计划超过 1,280-token 训练上限（`.coverage_note.test_struct_ho_rows_over_max_seq_len`），但评测输入没有被截断；训练集无长度丢弃。独立 CPU 复算对齐所有数据与源哈希、逐条结果和配对区间；没有重新调用模型。

早期 informed 诊断臂缺少公开政策、工具显示名称和 data_class，保留为不完整信息诊断，不进入该主比较（`reports/e2_informed_readout_20261125.md`）。

### 5.5 部署测量

在同一台 RTX 4080 SUPER、同一组 30 条请求上：
- 1.7B 本地编译器端到端中位延迟 2.93 s，PyTorch 峰值已分配显存 3.36 GiB，完整记录正确 17/30（`outputs/compiler_efficiency_v1/results.json:arms.1.7B.{median_s, peak_allocated_bytes, correct}`；显存按 3,607,655,424 B 换算为 GiB）；
- DeepSeek 十示例完整记录正确 29/30（同文件 `arms.api10.correct`）。

推理进程在加载模型前禁止创建 IPv4/IPv6 套接字（同文件 `arms.1.7B.ip_socket_probe`）。本节只报告实际用量与断网可行性，不主张单位货币成本优势，也不主张质量相当。

### 5.6 E3 字段消融

E3 在 0.6B、bf16、seed42 上依次完成四个 9,000-step 消融；每臂使用同一训练行、LoRA 配方和冻结 v5 执行评分，完整基线先投影到与消融相同的字段。差值区间按 E/I 任务组配对 bootstrap 10,000 次，条件于 seed42，不是训练 seed 总体推断；16 个点态比较未做多重校正。完整设置与逐切分记录见 `reports/e3_ablation_readout_20261125.md`。

| 消融 | dev Δpp | tpl_ho Δpp | tool_ho Δpp | struct_ho Δpp | tool/struct 无效输出率 |
|---|---:|---:|---:|---:|---:|
| A1：type/params 字符串序列化 | −0.50 [−1.50, 0.50] | −5.86 [−8.86, −2.71] | −13.43 [−17.57, −9.29] | −18.14 [−23.00, −13.29] | 12.29% / 16.67% |
| A2：去 evidence_span | +0.17 [−0.83, 1.17] | +4.29 [+2.14, +6.43] | −14.43 [−18.00, −11.00] | −36.29 [−41.29, −31.29] | 27.81% / 25.24% |
| A3：合并 explicit/implicit | +0.50 [−0.33, 1.33] | +1.29 [−0.86, 3.57] | −24.00 [−28.14, −20.00] | −29.00 [−34.43, −23.43] | 24.19% / 25.33% |
| A4：去 scope | +1.00 [+0.33, +1.83] | +2.57 [+0.29, +5.00] | +0.57 [−3.29, +4.29] | +7.00 [+3.00, +11.14] | 8.57% / 9.24% |

表中为消融减完整基线同字段投影的百分点差及组配对点态 95% 区间。A1 在结构留出上的 faithful 为 53.57%（基线同投影 71.71%），但其输出是字符串，记录项数量不能解释为字段准确率。A2/A3 的留出下降伴随较高的无效输出率；A3 的 tpl_ho N false-alarm 为 71/350（20.29%），其他三个切分为 0。每臂训练 token 不同：A1/A2/A3/A4 的监督 completion token 分别 0.894M/1.868M/2.521M/2.169M；9,000 次更新不代表相同 FLOPs 或监督量。

结果仅支持有限的单 seed 结论。A3 在 tool/struct 留出低 24/29pp，与三态监督有用的假设一致，但它同时改变 prompt、query_state、constraint.state、schema 与 target，且无效输出率升高，不能隔离为三态的因果效应。A2 也在 OOD 切分下降，不能将全部差异归因于 evidence 的语义价值。A4 去 scope 后 tool_ho 与基线近似，struct_ho 高 7pp（区间 [+3.00,+11.14]）；这否定“每个字段都被证明对执行必要”的宽泛表述。由于执行器本来不读取 scope，且只有一个训练 seed，该结果不能证明去 scope 提升性能；它要求将 scope 的价值限定为记录完整性或另行验证其消费者效用。所有结论限于当前合成基准和 seed42。

---

### 5.7 v6 扩展：1.7B 三种子

v6 的1.7B三种子已完成；4B尚未完成三seed，因此本节单列扩展结果，保持v5主表和架构实验版本不变。v6采用自己的数据和fail-closed评分，不与v5直接计算提升。以下为受约束E/I行faithful的三seed均值±样本标准差（%），由逐条成功数计算；任务组bootstrap条件于固定seed，不是训练seed总体置信区间。

| dev | tpl_ho | tool_ho | struct_ho | composition_ho |
|---:|---:|---:|---:|---:|
| 98.61 ± 2.41 | 93.86 ± 4.68 | 96.67 ± 4.00 | 91.10 ± 10.04 | 97.67 ± 4.04 |

三个1.7B seed在dev和composition_ho上相对同底座零样本的配对区间下界均为正，支持该尺寸的训练收益；总体H1仍等待4B。结构留出三seed为93.29/99.86/80.14%，不能声称稳定泛化。按登记规则，tool减struct的区间[3.95,7.19]pp对应H3 `inconclusive`；v6强PE缓存尚未齐全，H2仍pending。

行为与记录质量继续分离。在同一E/I分母上，tool/struct严格记录正确率三seed均值分别56.05%/53.43%；每个seed存在大量执行成功但记录有错的样本。tpl_ho的N broad alarm为8.29/13.14/2.00%，两个seed超过5%。这些结果支持双轴诊断需求，不证明scope等未被消费者使用的字段具有执行增益，也不建立人类语义可恢复性。seed44产物哈希及全部224个适配器张量的有限性检查通过，不能将其低分归为NaN失败并排除。

来源与分母见`reports/v6_1p7b_three_seed_readout_20261125.md`及`outputs/submission/followup_20261125/{main_3seed,result_3seed}.json`。冻结汇总器先舍入每run后计算得到tool均值96.66%，逐条计数为96.6667%；仅有0.01pp显示差异，冻结分析器未修改。

## 6 负结果：奖励侧信用分配未检出稳定效应

**设置。** 1.7B 神经规划器，v4 数据，在 GRPO 式单次 on-policy 组相对策略梯度下比较奖励设计。每组 4 个 rollout，ratio=1，beta=0（`reports/v5_evidence_review_20261124.md:115`）。三个训练 seed 为 42/43/44。区间均为在 E/I 内按任务组配对的 bootstrap，**条件于这三个 seed**，不是训练 seed 置信区间。

| 对照 | 面板（受约束分母） | 逐 seed 净差（道） | 平均 | 条件 95% 区间（pp） | 来源 |
|---|---|---|---:|---|---|
| 动作级归因 − 整轨迹奖励 | 原面板（120） | +1 / 0 / −1 | 0pp | [−3.89, +3.61] | `outputs/e2_v4/action-credit-1.7B-pilot-v1/rechecked-original-42-43-44.json:contrasts.action-minus-trace` |
| 预防动作信用 − 整轨迹奖励 | 预防面板（90） | 0 / +2 / −2 | 0pp | [−4.81, +4.45] | `outputs/e2_v4/action-credit-1.7B-pilot-v1/preventive-comparison-v1/rechecked-prevention-42-43-44.json:contrasts.protect-minus-trace` |
| 整轨迹 − 只奖功能，冻结权重迁移（tpl_ho / tool_ho） | 留出面板（见注） | 0 / +1 / +3；+1 / −1 / +1 | — | 未计算 | `outputs/e2_v4/frozen-planner-transfer-v1/paired.json:trace-function-*` |

冻结迁移行的分母：`reports/experiment_log.md:334` 记为"各 80 道"，与 tpl/tool 两个切分分别计数的关系待写作时回原文确认。

**如实陈述。** 动作级与预防性两种信用分配相对整轨迹奖励均**未检出稳定效应**：三 seed 的净差符号不一致，平均为 0，条件区间跨 0。区间宽度不是最小可检测效应；我们未做前瞻性功效分析，也不声称效应为零。

另有一项需要如实披露的对照。在原面板上，"整轨迹约束奖励 − 只奖功能"的三 seed 净差为 +4/+2/+7 道（分母 120），条件区间为 [+0.28, +7.22]pp（`rechecked-original-42-43-44.json:contrasts.trace-minus-function`）。这只说明"奖励中含约束信号"优于"不含"，不构成对信用分配机制的支持。而且这一差异在冻结权重留出迁移中不稳定（上表第三行）。

**加权修复 SFT（非 GRPO，单列）。** 普通与加权两种 SFT 在三种**训练顺序**下的四候选安全覆盖为 36→37、44→41、44→38（分母 80），即 +1/−3/−6 道。平均 −3.33pp，配对区间 [−7.50, +0.42]（`outputs/e2_v4/verified-repair-sft-1.7B-orders-v1/independent-replay.json:orders.*.{uniform,repair}` 与 `.coverage_delta_pp`）。训练顺序不是独立模型 seed，本行不能与上表合并为"三臂三 seed"。

**保留的诊断工具。** 为这组实验构建的 2×2 归因协议（§5.2 第 4 点）作为测量贡献，并入 C3，与训练结果无关。

---

## 7 局限

1. **合成话语、单工具世界。** 任务为 2 次调用级。不做跨域或多工具世界推断。
2. **金标为构造条件，未经正式人审。**
   - 语义有效性依据：witness 由独立检查器验证；DeepSeek 隐式完整记录 608/700（v4，§1）；随包发布盲审工件。
   - 作者自审 spot-check 若完成，只写作 author spot-check，不称 human validation。
3. **OOD 方差。** tool_ho/struct_ho 的 faithful 跨 seed 摆幅达 21.71pp（§5.1），单 seed 结论不可信。seed 方差分解是描述性的（§5.3 限定词）。
4. **面板版本混用。** E1 网格、2×2 归因、v4 裂缝样例挂在 v4 面板上；主表与 seed 分析挂在 v5 上。两类数字不可横比。TODO(v6)：v6 只作为发布数字。
5. **消融单 seed。** E3 的 A1–A4 都只有 0.6B seed42；任务组 bootstrap 区间条件于该模型权重，不能代表 seed 总体，A3/A4 主要结论需在额外 seed 上复测（§5.6）。
6. **GRPO 功效。** 条件区间宽约 ±4–5pp，三 seed，单架构，单数据域（§6）。
7. **强模型对照。** 强模型数字只作锚点，不是擂台。训练编译器在 OOD 切分上的 faithful 未达到 DeepSeek 十示例的非劣效标准（§5.1）。
8. **部署测量规模小。** 30 条请求、单卡、两种 Qwen3 尺寸（§5.5）。

---

## 附：本稿 TODO 汇总

- TODO(v6)：§4.2 v6 结果与主表决策；§7 第 4 条。
- 非 TODO 标签的待补项：DeepSeek-planner 列；Discussion "Why not a skill?"；§6 冻结迁移行的分母确认。4B 三 seed 的 N 误报与完整记录聚合已补入 §5.1。
