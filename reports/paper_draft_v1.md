# ConsDagQAQ：逐请求参数级约束的编译-规划分离与行为-记录裂缝（论文草稿 v1）

版本：2026-11-24。依据：`reports/submission_plan_v3_20261124.md`（第一波第 4 项）、`reports/submission_plan_emnlp2027.md` §1、§5、§6。
写作纪律：
- 每个数字后括号注明来源，括号里的 JSON 字段路径用 `文件:字段` 表示；
- 待补实验用 `TODO(E2)` / `TODO(E3)` / `TODO(v6)` 占位，不写预测值；
- 不出现已死主张：小模型打平/超越强模型、human-validated semantics、GRPO/信用分配有效、跨域泛化。

本稿新增的复核数字只有两个来源：
- `outputs/submission/audit_20261124/recompute.json`，由 `scripts/submission/audit_recompute_20261124.py` 生成；
- `outputs/submission/audit_20261124/draft_numbers.json`，由 `scripts/submission/draft_numbers_20261124.py` 生成。

两者只读冻结资产，零 GPU。

---

## 摘要（占位）

TODO(E2) TODO(E3)：摘要待 E2 单体对照与 E3 消融落地后定稿。现阶段可写的三句：
1. 我们发布 E/I/N 配对的可执行约束基准；
2. 我们提出编译-规划分离架构，并给出插拔网格证据；
3. 我们测得行为轴与记录轴的裂缝及其 seed 方差机制。

---

## 1 引言（骨架）

**动机一：行为轴饱和。**
v5 基准上，DeepSeek 十示例编译器接符号规划器后，受约束 faithful 在四个切分上为 99.33% / 99.29% / 99.71% / 99.86%（`outputs/v5_analysis/main.json:table.deepseek-v4-pro-0813-few.*.faithful_mean`，dev/tpl/tool/struct 顺序）。按含证据完整记录计，同一系统只有 85.67% / 82.86% / 88.71% / 77.71%（同文件 `.exact_with_evidence_mean`）。只看执行结果已无法区分强系统。

**动机二：记录轴真空。**
近邻工作（§2）评测的是"计划做没做对"。没有工作评测"系统对它所受约束的类型化记录是否正确"。我们测得的裂缝（§5.3）表明，两者可以显著分离。

**动机三：隐式约束失效。**
在 v4 的 tpl_ho+tool_ho 隐式题（共 700 条）上，两个强模型都用十示例提示，完整记录正确数分别为：
- DeepSeek：608/700（`outputs/e1_v4_side/deepseek-v4-pro-0813-few/full-scores.json:{test_tpl_ho,test_tool_ho}.v5.record_exact_match_by_variant.implicit` × 350 求和）；
- qwen-max：243/700（`outputs/e1_v4_side/qwen-max-few/scores.json`，同口径）。

隐式约束的可恢复性因模型而强烈分化。

**贡献（按 C1→C2→C3 排序）：**
- **C1 基准。** ConsDagQAQ 是 E/I/N 最小三元组配对的可执行约束基准。金标是生成器级构造条件，由 witness 计划经独立检查器验证。评测 fail-closed，并按多个 held-out 切分与多轴分列报告。
- **C2 架构。** 编译-规划分离：独立训练的小编译器输出 typed 约束对象，由可替换的下游规划器消费。我们主张的是接口可插拔、可独立评测，不主张打赢前沿提示工程。
- **C3 发现。** 我们测得行为-记录裂缝，并做了可归因的失效分类。seed 方差分析进一步显示：执行轴上的跨 seed 波动主要来自规划器消费的 params 字段；记录轴上最大规模的 scope 绑定缺陷在多数切分上跨 seed 高度一致，却对执行指标不可见。

TODO(E2)：若 E2 预注册判定为"分离成立"，C2 段补一句单体对照结论；若判定为"架构主张死"，C2 降为"参考实现"，按 `reports/submission_plan_emnlp2027.md` §7 风险登记册处理。

---

## 2 相关工作（骨架：只列近邻与定位差异）

近邻清单与分组取自 `reports/submission_plan_emnlp2027.md` §2、§2.1、§8.3。具体论断（行号级引文、对方数字）待写作时逐篇回原文核验后再写入，本稿不写。

| 线 | 近邻 | 与本文的定位差异（一句话） |
|---|---|---|
| 约束编译 / 中间表示 | CGAP（2610.41040）、CIRCE（2610.41089）、ATLAS（2509.25586）、Compile-Then-Page（2607.11346）、SpecHarness（2609.29921） | 它们的约束要么来自规格/目录，要么由宿主模型在提示内消化；本文编译的是**用户查询中逐请求的参数级约束**，编译器是可替换、可独立评测的训练部件，且单独测其记录正确性 |
| 运行时检查 / 安全基准 | SCA（2610.25552）、LogiSafetyBench（2601.08196）、AM-Bench（2610.18090）、EffectWorld（2610.35981） | 它们测行为合规或全局不变量；本文测逐请求参数级约束，并在行为轴之外加记录轴 |
| 隐式约束 / 约束下规划 | HOB（2603.29025）、AdaPlanBench（2606.05622）、ToolMaze（2606.05806）、HyperAgent（2608.02650） | 它们测推理选择、交互式重规划或在提示内消费约束；本文用 E/I/N 最小三元组隔离"隐式可恢复性"，并产出可审计的 typed 记录 |
| 训练专门化 | CARL（2607.04854）、EffectWorld、AgentFlow（2510.05592） | 本文的训练对象是约束编译这一子功能，下游规划器可替换 |
| 分解成本之争 | Coordination Tax（2610.37700）、MA-Evolve（2609.04217） | 它们研究同能力模型的提示角色分解；本文的 E2 是等预算的训练阶段分解对照（TODO(E2)） |
| 评测器可靠性 / 失效归因 | Trace 审计（2610.30491）、Who&When Pro（2607.09996） | 它们审计评测标签或定位错误步；本文的 2×2 是"换部件能否救回"式干预归因 |
| skill 范式 | Agentic Skills 综述（2608.29596）、Skill 参考架构（2606.20631）、SkillFusion（2610.15481）、SkillBrowser（2610.23554） | 放入 Discussion "Why not a skill?"（本稿未写） |

收尾定位句（写作时用）：近邻测的是"模型做没做对"；本文测"做对之后，记录对不对"。

---

## 3 方法：编译-规划分离

### 3.1 架构

管线分三段：
1. **编译器** C：查询 + 工具目录 → typed 约束集合；
2. **规划器** P：任务结构 + 约束集合 → 计划；
3. **检查器** K：计划 + 金标约束 → 判定。

三段之间只通过 typed 约束对象交互。金标只对 K 可见。编译器的提示由三部分组成：策略卡、工具目录（每个角色给出名称、付费/免费、本地/外发）、输出 schema（`src/run_e1.py:87-106`）。编译器从不看到任务的阶段结构，也不看到工具的成本和时长数值。成本、时长、阶段结构只由 P 与 K 使用。

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
- **金标性质声明。** labels are construction conditions, not human-validated semantics。金标是生成器声明的构造条件，没有经过正式人审。随包发布 250 条盲审工件（`reports/submission_plan_emnlp2027.md` §5.1）。
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

**N 误报（1.7B LoRA 三 seed 均值）。** dev 0.33%、tpl_ho 9.14%、tool_ho 0.19%、struct_ho 0.00%（`outputs/v5_analysis/v5_main_0530_20261124.json:table.Qwen3-1.7B-LoRA.*.none_false_alarm`）。4B 三 seed 的 N 误报和含证据完整记录还没有聚合成单一产物，待补。

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

TODO(E2)：插入 E1 × E2 × symbolic 三向对照，包括单体直出计划的 faithful 与成本列（token、时延）。
待补（第三波，需 API 授权，见待决策清单）：DeepSeek 作为规划器的一列，用来把"消费者可换"补成双向插拔。

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

### 5.4 E2 单体对照（等预算训练阶段分解）

TODO(E2)：
- 预注册判定写在 `src/sub_e2_monolithic.py:4-6`，内容为：单体 faithful_constrained ≥ 管线 −1pp 且配对 CI 跨 0 ⇒ 分离主张证伪，如实报。
- 待补：四个切分加 overall 的配对差与 CI、训练 token 账、推理生成 token 与时延。
- 判定的三分支表述，以及单体 prompt 的信息对齐问题，见待决策清单，用户裁定后再写本节。

### 5.5 部署测量

在同一台 RTX 4080 SUPER、同一组 30 条请求上：
- 1.7B 本地编译器端到端中位延迟 2.93 s，PyTorch 峰值已分配显存 3.36 GiB，完整记录正确 17/30（`outputs/compiler_efficiency_v1/results.json:arms.1.7B.{median_s, peak_allocated_bytes, correct}`；显存按 3,607,655,424 B 换算为 GiB）；
- DeepSeek 十示例完整记录正确 29/30（同文件 `arms.api10.correct`）。

推理进程在加载模型前禁止创建 IPv4/IPv6 套接字（同文件 `arms.1.7B.ip_socket_probe`）。本节只报告实际用量与断网可行性，不主张单位货币成本优势，也不主张质量相当。

### 5.6 E3 字段消融

TODO(E3)：表格格式学 ATLAS，每行去掉一个组件。四臂（`src/sub_e3_ablation.py:3-6`）：
- A1 将 typed 对象改为保留 type/params 的字符串序列化表示；
- A2 去 evidence_span；
- A3 去三态；
- A4 去 scope。

每臂报记录轴、full-contract 解析率与下游 faithful。主结果三 seed，消融单 seed（0.6B seed42），在 Limitation 中声明。注意：A1 的下游列与 N 误报列在当前代码中存在口径问题，见待决策清单，修正口径后再写。

---

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
5. **消融单 seed。** TODO(E3)。
6. **GRPO 功效。** 条件区间宽约 ±4–5pp，三 seed，单架构，单数据域（§6）。
7. **强模型对照。** 强模型数字只作锚点，不是擂台。训练编译器在 OOD 切分上的 faithful 未达到 DeepSeek 十示例的非劣效标准（§5.1）。
8. **部署测量规模小。** 30 条请求、单卡、两种 Qwen3 尺寸（§5.5）。

---

## 附：本稿 TODO 汇总

- TODO(E2)：摘要；引言 C2 句；相关工作"分解成本之争"行；§5.2 三向对照；§5.4 全节。
- TODO(E3)：摘要；§5.6 全节；§7 第 5 条。
- TODO(v6)：§4.2 v6 结果与主表决策；§7 第 4 条。
- 非 TODO 标签的待补项：4B 三 seed 的 N 误报与完整记录聚合；DeepSeek-planner 列；Discussion "Why not a skill?"；§6 冻结迁移行的分母确认。
