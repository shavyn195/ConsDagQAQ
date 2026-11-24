# ConsDagQAQ 投稿方案（主投 EMNLP 2027，备选 NAACL/COLING）

版本：2026-11-24 定稿。**本文档取代旧"三创新点"概念（旧评分 4.13/4.18/4.28 对应概念已被 v5 实证推翻，作废）。**

---

## 0. 现状快照

| 项      | 状态                                                                                          |
| ------ | ------------------------------------------------------------------------------------------- |
| 数据     | v6 冻结：17,100 条 E/I/N 配对，witness 全过、跨切分 0 重叠、SHA-256 确定性复现、fail-closed 评测器                   |
| 语义有效性  | 定案：作者亲审 + agent B 预检 60 条（4/4 与金标一致，2 条 uncertain 均为 tool_auth/order 边界）。**人审环节已裁撤**（作者拍板） |
| v5 主结果 | 1.7B/4B 三 seed 齐；DeepSeek 10-shot / qwen-max 缓存齐（哈希验证）                                      |
| v6 主结果 | **空**——G1 六 run 未跑                                                                          |
| ①架构证据  | **空**——B1/A/C1 未跑（本方案 §4）                                                                   |
| 投稿概率   | 今天原样投 20-30%；补完 §4 后 40-55% 主会 + ~2 成 Findings                                             |

---

## 1. 贡献表述定稿（三条）与已死主张红线

### 1.1 贡献列表（按此顺序写进论文）

> **C1（③，主骨）ConsDagQAQ：E/I/N 配对可执行约束基准。**
> 同一 DAG 任务生成显式/隐式/无约束三版语义等价查询；金标为生成器级构造条件并经 hidden witness 反事实验证；fail-closed 评测；四 held-out（措辞/工具/结构/类型组合）；strict/core/record/evidence/faithful 五轴分列。

> **C2（①，方法臂）编译-规划分离的约束编译器架构。**
> 独立训练的小模型（0.6B–4B LoRA）把逐请求参数级约束（金额上限/时限/数据类）编译为 typed 约束对象（type/state/severity/scope/params/evidence_span），供下游规划器/执行器消费。主张的是**架构与接口**（可插拔、可训练、可独立评测），**不是**打赢前沿 PE。

> **C3（裂缝+归因，发现）行为-记录裂缝与可归因失效分类。**
> 首次测量"执行正确但编译记录缺陷"：4B tool_ho 执行 699/700 而完整记录仅 552/700；并用交叉干预（换编译器救回 112/118=读错约束；换候选规划器救回 47/138=搜索受限）把裂缝归因成两类失效。

### 1.2 已死主张红线（任何段落不得出现）

| 红线                          | 原因                                                                        | 替代写法                                                                               |
| --------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| "小模型打平强模型"                  | H2 失败：4B tool_ho 87.00±11.40 vs DeepSeek 99.71，最好 seed 上界 95.62 仍差 4.1pp | "部署效率：1.7B 3.36GiB 断网推理 2.93s"+ 诊断价值                                               |
| "新奖励算法/信用分配有效"              | GRPO 三臂三 seed 无稳定收益（+1/0/−1、0/+2/−2、+1/−3/−6；冻结权重留出 +0/+1/+3 道）           | 诚实负结果章 + 2×2 正面发现顶前                                                                |
| "human-validated semantics" | 人审已裁撤                                                                     | "labels are construction conditions" + 强模型一致性（DeepSeek 隐式 608/700）+ 随包发布 250 条盲审工件 |
| 行为轴主指标                      | DeepSeek 700/700 饱和                                                         | 主对比轴=strict record F1 / implicit recovery / N alarm；faithful 只作参考列                 |
| "小模型也能做约束任务"（作为卖点）          | EffectWorld 已做小模型 LoRA+可执行约束                                              | 卖点改"架构分离+表示系统化+记录轴"                                                                |

---

## 2. 防御矩阵（贡献 × 七近邻逐篇）

近邻全文精读已完成（三线 agent 交叉验证，行号已复核）。逐篇防御句式：

| 近邻                                                                                    | 他们有什么                                               | 我们的区别（防御句）                                                                                                     | 证据行号                                           |
| ------------------------------------------------------------------------------------- | --------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| [CGAP](https://arxiv.org/abs/2610.41040)                                              | planner 轴替换（search/LLM/依赖图）、plain-agent 对照、15 组配对区间 | ①编译器轴从未被替换过（其目录编译是确定性 gold，无"编译器"部件）；②自认"从未审计解析/引用错误的发生频率"——我们的 record 轴测的正是这个                                 | L793-821（plain agent）、L996（自认缺口）               |
| [SCA](https://arxiv.org/abs/2610.25552)                                               | 运行时安全检查器                                            | ①明文禁止逐请求规则、只许全局不变量；②自认"检测不了 omission、对失败以漏调为主的弱模型帮助甚微"——小模型需要**训练**而非外部检查的动机引文                                 | L1112-1115                                     |
| [LogiSafetyBench](https://arxiv.org/abs/2601.08196)                                   | 240 任务、三轮作者人审、LTL 合规                                | 自认 LTL"只管调用时序、无法验证转账金额是否在安全限额内"——参数级约束的直接空位；且只测行为不测记录                                                          | L1297-1300                                     |
| [EffectWorld](https://arxiv.org/abs/2610.35981)                                       | 小模型 LoRA+可执行 effect 约束+诚实负结果先例                      | ①其约束是工具级 effect，非逐请求参数级；②只测行为纪律（effect discipline），无记录轴；③自认"effect discipline 绑死在训练工具上"——我们的隐式恢复跨工具 0.994 与之对照 | L346、L1125、L1317、L1810                         |
| [CIRCE](https://arxiv.org/abs/2610.41089)                                             | CIR 中间表示                                            | CIR 无下游消费者、无被评测的编译器部件——我们的 typed 对象有下游规划器消费+可插拔验证                                                              | 全文结构                                           |
| [ATLAS](https://arxiv.org/abs/2509.25586)                                             | Constraint Manager 组件+消融先例                          | 其 Manager 无独立训练、无字段级评测、从未被替换；我们的 w/o Constraint Manager 式字段消融（A 系）做得更细                                         | L512、L1107（w/o CM：41.67/30.00 暴跌——审稿人期待这张表的背书） |
| [AM-Bench](https://arxiv.org/abs/2610.18090)                                          | 20,160 run 全量审计、matched-Full                        | 其 matched-Full 只是 RQ3 估计器不进主表；其 A=多解释，我们的 I=唯一可恢复——设计目标相反                                                      | RQ3 节                                          |
| [CARL](https://arxiv.org/abs/2607.04854)                                              | base vs fine-tuned 同款对照                             | 我们的三规模零样本 F1=0（0.6B/1.7B/4B 全线指令工程失效）比其单点更强                                                                    | 实验章                                            |
| [LIFT](https://arxiv.org/abs/2610.28819) / [ANCHOR](https://arxiv.org/abs/2610.16859) | 305 对人审 / κ=0.78                                    | 我们无对应人审——用构造条件+强模型一致性替代，Limitation 主动声明                                                                        | —                                              |

### 2.1 增补近邻（2026-11-24 定稿；全部经下载全文精读核验，行号见各核验笔记；写作时并入防御矩阵）

| 近邻                                                                           | 他们有什么                                                                                                                                                                                                                                      | 我们的区别（防御句）                                                                                                                                                                                                                                                                                                                                                                                                                                                       | URL                                |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| [SpecHarness](https://arxiv.org/abs/2609.29921)（Who Holds the Pen?, 2026-09） | 两个 gap：understanding–execution gap（理解≠执行）+ state–authority gap（**agent 完成自称率超出评测通过率 28.7-37.9pp**）；把规格编译成 source-linked obligations 并由外部运行时裁定                                                                                              | **划界（必须正面引）**：它测的是"agent 的自我声明 vs 外部判定"（claim 不可信），我们测的是"外部可验证执行 vs 类型化编译记录"（**做对了也未必说得清自己受了什么约束**）——方向相反、互补不冲突；其 compiler 从规格文本抽 task directions，不处理用户查询中的参数级隐式约束、无 E/I/N 配对、无小模型训练。引用句式：*SpecHarness shows self-reports cannot be trusted; we show the complementary failure — externally verified behavior still leaves typed records incomplete*                                                                                                             | <https://arxiv.org/abs/2609.29921> |
| [HOB / Heuristic Override](https://arxiv.org/abs/2603.29025)（CMU, 2026-03）   | 隐式约束被表面线索压制：500 提示×4 启发式×5 约束族、CORE-100 人审 minimal pairs、14 模型实测；presence 类隐式约束是最难家族——12/14 模型上均分 61.5% vs 其他家族 82–93%（全文核验：摘要 L110）；**12 个预注册提示词干预仅 1 个有效、9 点提示词增益不迁移（selectivity −0.04，L118）——prompt 修不好隐式约束**                           | **友军（I 版设计的动机背书）**：独立证明"隐式约束是被系统性忽略的推理漏洞"——我们 I 版 608/700（DeepSeek）vs 243/700（qwen-max）的跨模型分化是其发现在 tool-planning 域的对应物；其"提示词干预基本无效"恰与我方 Z 臂零 F1 + SFT .07→1.00 外部同构。区别：它测纯推理选择（walk vs drive），不涉及工具调用、无编译产物、无 witness。引用位置：I 版设计动机段                                                                                                                                                                                                                              | <https://arxiv.org/abs/2603.29025> |
| [Compile, Then Page](https://arxiv.org/abs/2607.11346)（2026-07）              | SOP 约束编译成可执行伪代码+能力门控运行时；**强模型 +16 点、弱模型受害**；三臂 70.4→86.4→92.8                                                                                                                                                                              | **双面弹药（Discussion 引）**：正面—"约束需要编译成显式人造物"被独立验证，与我们 typed 对象路线同向；反面—其"弱模型受害"恰与我们 Z 臂三规模实证互证（弱模型消化不了 context 里的约束信息→必须训练专门件，不能靠塞 context）。区别：其约束来自 SOP 规格文本（非用户查询）、无逐请求参数级、无训练编译器                                                                                                                                                                                                                                                                                   | <https://arxiv.org/abs/2607.11346> |
| [AdaPlanBench](https://arxiv.org/abs/2606.05622)（UIUC, 2026-06）              | 世界+用户双约束下渐进披露的交互式重规划基准；最好模型 67.75%                                                                                                                                                                                                         | 正交（非竞争）：其约束由环境反馈逐步揭示、测重规划能力；我们的一次性编译恢复、测编译记录。**共同证明"约束下的 agent 评测"是 2026 活跃痛点——受众契合度论据**                                                                                                                                                                                                                                                                                                                                                                         | <https://arxiv.org/abs/2606.05622> |
| [ToolMaze](https://arxiv.org/abs/2606.05806)（2026-06）                        | 工具失效下动态重规划；隐式语义失败伤害最大（PRR 掉 37%）                                                                                                                                                                                                           | 正交：测故障恢复非约束编译；其"隐式语义失败最伤 agent"与我们隐式恢复轴共享痛点诊断——Related Work 热区证据                                                                                                                                                                                                                                                                                                                                                                                                 | <https://arxiv.org/abs/2606.05806> |
| [AgentSLABench](https://arxiv.org/abs/2608.00805)（2026-08）                   | 资源约束（CPU/内存/时延/成本）下的 agent 性能画像（EASR）                                                                                                                                                                                                      | 正交：测"跑不跑得动"，不测"约束有没有被正确编译记录"；其"高精度但超预算不可部署"立场与我们部署故事（1.7B 断网 2.93s）同向——成本列的外部背书                                                                                                                                                                                                                                                                                                                                                                                  | <https://arxiv.org/abs/2608.00805> |
| [Trace 审计](https://arxiv.org/abs/2610.30491)（What the Trace Shows, 2026-11）  | 审计评测器本身：自动化标签（κ=0.29 最弱）与 trace 实况系统性不符；主张"标签必须附带 trace 证据"                                                                                                                                                                                | **方法论同源友军**：其立场=我们 fail-closed+记录评测的哲学（不能只看最终标签）；引用它=让独立团队背书我们的评测协议设计。区别：它审计"评测器可靠性"，我们提供"被评测的记录产物"——互补                                                                                                                                                                                                                                                                                                                                                          | <https://arxiv.org/abs/2610.30491> |
| [Who&When Pro](https://arxiv.org/abs/2607.09996)（2026-10）                   | 12,326 条失败轨迹的归因基准（注入错误+金标定位）                                                                                                                                                                                                               | 正交：归因对象是"多模态轨迹中定位错误步"，非编译器轴干预；我们的 2×2 是"换部件救不救得活"而非"哪步错了"——失效归因的两种正交操作化，Related Work 划一句即可                                                                                                                                                                                                                                                                                                                                                                       | <https://arxiv.org/abs/2607.09996> |
| [HyperAgent](https://arxiv.org/abs/2608.02650)（UNSW, 2026-07，**真对手**，全文已核验）  | Tool-Schema Hypergraph + schema 级 Task DAG 工具规划框架；GPT-4o 骨干 training-free；承认逐请求约束 "expressed or implied"（L145-146）并用于检索锚点+子任务验证（"expected outputs, effects, and constraints of the current subtask"，L354-357）；AppWorld TGC 63.1/35.7 纯行为指标 | **非威胁、三重弹药**：①动机背书——2026 工具 agent 前沿独立承认逐请求约束是一等问题（受众契合度第 9 个数据点）；②C2 分离主张的 live 对照——它把约束**内嵌规划提示**由宿主 GPT-4o 消化（=C1 网格 prompted compiler 贵档同型），我们用**独立训练编译器**专职消化；③测量面零覆盖——无 typed 记录、无 record 轴、无 E/I/N、无训练件，行为-记录裂缝在其范式内不可观测。防御句：*HyperAgent consumes per-request constraints inside the planning prompt; it neither compiles them into typed, auditable records nor measures record correctness — our separated, trained compiler makes that gap measurable* | <https://arxiv.org/abs/2608.02650> |

**关键定位句（Related Work 收尾）**：近邻测的都是"模型做没做对"；我们首次测"模型做对了但**记录**对不对"。

---

## 3. 反击弹药（审稿人质疑 → 引文回击）

| 预期质疑                          | 反击                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| "约束编译=又一个 wrapper"            | SCA 自认外部检查器救不了漏调型弱模型（L1112-1115）；CGAP 自认从未审计解析错误频率（L996）→ 记录轴测量是真空，不是 wrapper                                                                                                                                                                                                                                                                                                                                                                                                 |
| "金额/时限这种约束别人也测过"              | LogiSafetyBench 自认 LTL 验不了金额上限（L1297-1300）→ 参数级逐请求约束无先例                                                                                                                                                                                                                                                                                                                                                                                                                       |
| "基准行为轴刷满分没意义"                 | DeepSeek 700/700 恰是论据：行为轴饱和→社区被迫转向记录轴；strict record F1 大分离（4B 三 seed .93/.68/.44 摆动）                                                                                                                                                                                                                                                                                                                                                                                          |
| "隐式版是否真可恢复"                   | qwen-max 243/700 vs DeepSeek 608/700：隐式可恢复性因模型分化——这本身是发现；金标=构造条件（generator 声明）                                                                                                                                                                                                                                                                                                                                                                                                |
| "为什么不和 GPT-5 级打擂"             | EffectWorld 先例：核心对照全在同底座 ≤4B 家族内（主张决定对照组）；DeepSeek/qwen-max 作为参考数字已报（缓存白嫖）                                                                                                                                                                                                                                                                                                                                                                                                    |
| "GRPO 失败=方法不行"                | 负结果诚实报告有先例（EffectWorld 摘要即含负结果）；我们另有正面发现（2×2 归因）——失败被定位到成因而非被掩盖                                                                                                                                                                                                                                                                                                                                                                                                               |
| "合成话语/单域"                     | Limitation 主动声明+范围收窄；EffectWorld 同款天花板照样发                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| **"SpecHarness 已发现行为与判定的差距"** | **必须主动划界（2026-09 新近邻）**：[SpecHarness](https://arxiv.org/abs/2609.29921) 测的是 agent **自称完成** vs **外部判定**的差（claim 不可信，28.7-37.9pp）；我们测的是**外部验证执行已通过**的前提下编译记录仍缺陷（做对了也说不清）。二者是同一枚硬币的两面且方向相反：它说"别信模型的自评"，我们说"别只看外部判定——记录另有独立的失效空间"。引用句式：*SpecHarness shows self-reports cannot be trusted; we show the complementary failure — externally verified behavior still leaves typed records incomplete*（699/700 vs 552/700）。且其 compiler 对象是规格文本的 task directions，无 E/I/N 配对、无参数级、无训练编译器 |
| **"隐式约束失效是已知现象"**             | **承认并借力**：[HOB](https://arxiv.org/abs/2603.29025)（CMU）已在纯推理域证明表面线索压制隐式约束（presence 家族 12/14 模型均分 61.5% vs 其他家族 82–93%；且 12 个预注册提示词干预仅 1 个有效、9 点增益不迁移 −0.04——prompt 修不好）——我们在 tool-planning 域给出对应证据（qwen-max 243/700 vs DeepSeek 608/700 的跨模型分化），且更进一步：HOB 只测"选错答案"，我们测"编译记录错在哪"（typed 字段级），并给出训练干预（I 版记录 F1 训练后大幅恢复）——从诊断推进到了干预；其"提示词基本无效"恰是"必须训练专门件"的外部佐证                                                                                                                     |
| **"评测器/标签本身可信吗"**             | 正面接：[Trace 审计](https://arxiv.org/abs/2610.30491) 证明自动化标签 κ 低至 0.29——所以我们的协议**生来就是 fail-closed+五轴分列+全预测落盘+SHA-256 复现**，恰好是该论文主张的"标签须附带证据"的实例化；引用它把质疑转化为协议设计依据                                                                                                                                                                                                                                                                                                                  |

---

## 4. 补充实验执行清单（可直接照跑）

**总原则**：全部挂 **v5**（三 seed 基线现成、强模型缓存直接复用、不等 G1）。单卡口径 ~20-25 GPU 时。

### E1（C1 插拔网格）——优先级最高，纯推理 ~2h

- **网格**：编译器轴 {0.6B SFT, 1.7B SFT, 4B SFT, DeepSeek 10-shot 缓存} × 规划器轴 {SFT-v1, SFT-v2, 符号规划器}
- **已有素材**：2×2（0.6B 编译器×两权重）、符号规划器 1,149/1,400、DeepSeek 编译器行 1,255/1,292
- **判定**：换编译器应单调可预期；DeepSeek 行作"接口任何人可接"验证（0.6B 达其救回率 91-93%）
- **产出**：网格表 + task-group 配对 bootstrap 区间（学 CGAP 15 组全带区间的惯例）

### E2（B1 单体对照）——分离性生死实验，1 次训练 ~8.5h

- **构造**：同底座 1.7B、同 v5 数据，训"查询→计划"直出单体（跳过编译阶段）
- **预算匹配（CGAP 惯例，防"单体被绑手脚"质疑）**：单体训练样本=查询→witness 计划直接映射，样本量对齐管线总训练量
- **判定**：单体若打平管线 → 架构主张死（如实报）；管线赢 → 分离性成立
- **产出**：faithful 对照表 + 配对区间

### E3（A 系字段消融）——0.6B 单 seed，~3h/臂

| 臂      | 去掉什么           | 测什么轴                       | 诚实预期                                 |
| ------ | -------------- | -------------------------- | ------------------------------------ |
| A3     | 三态（塌缩为有/无）     | I 版记录 F1                   | 隐式恢复崩 → 三态必要                         |
| A4     | scope          | deadline/order 下游 faithful | 角色绑定类崩                               |
| A2     | evidence_span | 记录完整率                      | **执行不受影响**——只主张记录轴必要（执行器不消费它，仓库审计红线） |
| A1（可选） | typed（退化为自由文本） | 下游 faithful                | lite 版：不重训规划器只换输入                    |

- **纪律**：主结果三 seed、消融单 seed（社区惯例），Limitation 声明一句
- **格式**：学 ATLAS "每行去一个组件"同格式表（L1107 先例）

### E4（可选项，按投稿窗口决定）

| 项                           | 成本              | 触发条件                               |
| --------------------------- | --------------- | ---------------------------------- |
| G1 v6 六 run（1.7B/4B×三 seed） | 22-25 GPU 时     | 主表切 v6 时必须                         |
| N2 强模型 v6 重测                | ~15,300 API 请求 | 主表切 v6 时必须（v5 缓存不可跨版本复用）           |
| DeepSeek-planner 臂          | 纯 API           | 若想让 2×2 从"小模型内互证"升级为强弱交叉（近零成本，推荐做） |

### 执行顺序

1. E1 网格（白送）→ 2. E2 B1（架构核心）→ 3. E3 A3+A4 → 4. E3 A2 → 5.（可选）A1/E4。一个 30h 窗口装得下全部。

---

## 5. 数据集处置

### 5.1 不改的部分（冻结理由）

- v6 数据本体不动：验证链已到顶（witness 全过、0 重叠、确定性复现、fail-closed）；语义层已定案（亲审+agent B 印证）
- 人审不恢复（作者拍板）
- 250 条盲审包（132 I + 118 N）作为**发布工件**随数据放出

### 5.2 发布包（基准论文的生死线，缺=没人能来对比）

1. HuggingFace datasets + GitHub：数据、生成器、fail-closed 评测器、冻结 seed/SHA
2. 一键评测 harness（30 分钟内可复现一个分数）
3. 参考数字表：v5/v6 全部自家数字 + DeepSeek/qwen-max 数字
4. Leaderboard 提交协议：固定切分、固定 384 token、fail-closed 判定、五轴分列

### 5.3 让步清单（审稿人要求时的后备）

- A003 审批歧义 44 条：敏感性分析随包发布（排除后 1.7B 820/1,006 vs 原 849/1,050）
- composition_ho 筛选效应：只称"held-out pair 探针"，不称因果干预（设计文档 L26 已自我声明）
- 范围声明：合成话语、无 paraphrase、单工具世界、2 次调用级任务
- 金标声明："labels are construction conditions, not human-validated semantics"

---

## 6. 写作义务清单

| # | 义务                                                                                                                               | 素材   |
| - | -------------------------------------------------------------------------------------------------------------------------------- | ---- |
| 1 | 贡献排序 ③→①→裂缝归因；②不占贡献位（藏在 C3 里当方法）                                                                                                 | §1.1 |
| 2 | 主对比轴钉死：strict record F1 / implicit recovery / N alarm；faithful 参考列                                                               | §1.2 |
| 3 | 负结果章：2×2 正面数字顶前、GRPO 负结果后置+定位分析                                                                                                  | §3   |
| 4 | Related Work 三条线：constraint compilation（CGAP/CIRCE/SCA/ATLAS）、安全基准（LogiSafetyBench/AM-Bench/EffectWorld）、训练专门化（CARL/EffectWorld） | §2   |
| 5 | Limitation：合成话语/单域/无人审/消融单 seed/OOD seed 方差 ±11pp                                                                                | §5.3 |
| 6 | 强模型数字的用法：锚点非擂台（DeepSeek 饱和=记录轴必要性的实证）                                                                                            | §3   |
| 7 | 部署故事：1.7B 3.36GiB 断网 2.93s                                                                                                       | §1.2 |

---

## 7. 风险登记册

| 风险               | 概率 | 缓解                       |
| ---------------- | -- | ------------------------ |
| B1 单体打平管线（架构主张死） | 中  | 如实报+故事重心本就在③基准；①降为"参考实现" |
| 审稿人坚持要人审         | 中  | §5.3 让步清单+构造条件写法+盲审工件随包  |
| A 系某臂不降（组件"不必要"） | 低  | 如实报并定位原因（字段消费方分层声明已预防）   |
| 行为轴被误读为主卖点       | 低  | §6 写作纪律                  |
| v6 G1 结果与 v5 不一致 | 低  | 架构实验全挂 v5，v6 仅作基准发布数字    |

---

## 附：核心数字速查

- **v5 三 seed faithful（%）**：1.7B 98.72±0.86 / 96.71±1.14 / 79.76±10.53 / 82.90±11.28（dev/tpl/tool/struct）；4B 99.94±0.10 / 96.67±3.49 / 87.00±11.40 / 96.76±3.08
- **DeepSeek 10-shot**：99.33 / 99.29 / 99.71 / 99.86；同底座零样本（1.7B）17.17 / 19.14 / 13.43 / 25.86
- **strict F1（v4，4B）**：零样本 .071/.065/.094 → 微调 1.000/.926/.855（dev/tpl/tool）
- **裂缝**：4B tool_ho 执行 699/700 vs 完整记录 552/700；隐式恢复 qwen-max 243/700 vs DeepSeek 608/700
- **2×2**：换编译器救回 112/118；换候选规划器救回 47/138；DeepSeek 编译器行 1,255/1,292
- **GRPO**：责任动作 +1/0/−1；预防 0/+2/−2；修复 +1/−3/−6（留出 +0/+1/+3 道）

---

## 8. Discussion 章设计："Why not a skill?"（审稿必问，主动设防）

**背景**：2026 年 agent skills 已成生态（Anthropic/OpenAI 原生支持、出现系统综述与参考架构）。审稿人几乎必然问："约束解析为什么不做成宿主 agent 的一个 skill？"以下论证链全部基于 2026 年新文献（本轮网络检索补充），与 §2/§3 的近邻防御互补。

### 8.1 论证链（五层，每层带新引文）

**第一层：skill 是 prompt 介导的，在弱模型上空转——我们有三规模实证**

skill 的定义即"把行为指引打包进 agent 的工作上下文"（[SkillBrowser](https://arxiv.org/abs/2610.23554)："loaded Skills contribute instructions directly to the agent's working context"）。这本质是 in-context 激活。我们的 Z 臂数据：0.6B/1.7B/4B 在**给足完整 schema+角色词表的指令**下约束 F1 全 0（4B parse 0.98 但语义崩）——即"把 skill 说明书塞进上下文"在 ≤4B 档完全失效。skill 生态自己也承认这一点：SkillBrowser 自认"benefits remain model- and task-dependent, with under-invocation of useful skills and additional latency as key limitations"；[Agentic Skills 综述](https://arxiv.org/abs/2608.29596) §3.8.2 专节讨论 "When Skills Do Not Help"，并把"Cross-Model Portability and Small Language Model (SLM) Deployment"（§6.1）列为 open challenge——**我们的工作正是这个 open challenge 的第一个定量数据点：弱模型上，skill 形态零收益，训练形态 .07→1.00**。

**外部互证**：[Compile, Then Page](https://arxiv.org/abs/2607.11346)（SOP 编译+能力门控运行时）独立发现同样的分界——**强模型**从编译后的 SOP 受益（三臂 70.4→86.4→92.8，最高 +16 点），**弱模型受害**；其结论"runtime guidance is capability-gated"与我们的 Z 臂数据在两个不同问题上交叉验证了同一条规律：约束信息的显式化对强模型是助力、对弱模型是负担，唯一的弱模型出路是把它**训练进权重**（SFT）而非**塞进上下文**（prompt/skill）。

**第二层：skill 不留可审计的记录——记录轴在 skill 范式里不可观测**

这是要害。[Skill-Mediated Agents 参考架构](https://arxiv.org/abs/2606.20631)（36 个实践系统+51 篇论文的多声文献综述）把 agent skill 的架构责任分成四层（Supply Chain / Mediation / Execution Control / **Evidence & Feedback**），其核心实证发现是：8 个被映射系统里"前三层基本实现，**Evidence & Feedback 层 14/15 项 partial 或未建立**"——即**现网 skill 系统普遍不记录、不验证 skill 的使用**。我们的 typed 约束对象+fail-closed 记录评测恰好是这一层的实例化：行为 699/700 vs 记录 552/700 的裂缝，在"约束用完即逝于上下文"的 skill 范式下**根本无法被观测**。综述同样指出自然语言 skill 表示存在"Fundamental Verifiability Trade-Off"（§3.2.3 "The Fundamental Verifiability Trade-Off and Security Blindspot"，全文核验）——我们的 typed 表示是站在这个 trade-off 的可验证一侧。

**第三层：skill 生态自己正在走向 typed 约束——验证我们的表示选择**

[SkillFusion](https://arxiv.org/abs/2610.15481)（2026-10）处理 skill 合成冲突时的核心机制是"make composition decisions explicit through **typed, scoped constraints** linked to their source directives"——与我们的表示（typed+scoped 约束对象）同构。但它的对象是 **skill 指令之间的离线调和**（合并多个作者写的 SKILL.md），不是**运行时逐请求的用户约束编译**。引用它反而是加分项：**连 skill 生态自己都发现 free-form 指令不可靠、必须升级到 typed 约束表示**——我们只是把这个升级用在了正确的地方（用户的逐请求约束），并且给了它一个可训练的执行器和可测的基准。

**第四层：分解不是免费午餐——我们不主张"管线永远赢"，B1 就是拿来对赌的**

诚实处理社区最新的反分解证据：[Coordination Tax](https://arxiv.org/abs/2610.37700)（2026-10）实测 planner-coder-reviewer 管线"costs 3.22x as much as a single strong call, takes 3.24x as long, and solves no more tasks"；[MA-Evolve](https://arxiv.org/abs/2609.04217)（同骨干 7B 等推理预算下）"multi-agent structure does not beat a single frozen agent"（0.769 vs 0.754, p=0.80），且 planner/critic 的角色 prompt 进化成空转。**这两篇是 B1 的存在理由而非威胁**：它们的结论是"同能力模型的 prompt 角色分解不划算"，而我们的 B1 是"同预算下、训练出的专职编译阶段 vs 单体"，且编译器是 0.6B 级便宜件（恰是 Coordination Tax 自己指出的"saving lies in choosing a model per task"——我们正是按任务选了小模型）。Discussion 里主动引这两篇，把 B1 定位成"在约束编译这个特定功能上、用训练而非 prompt 角色回答分解是否划算"——审稿人反而无话可说，因为我们比他们更早引用了反对自己的文献。反向支撑也有：[AgentFlow](https://arxiv.org/abs/2510.05592) 指出单体全上下文策略 "scales poorly with long horizons and diverse tools and generalizes weakly to new scenarios"，且其 planner/executor/verifier 分解训练后 7B 超越 GPT-4o——**训练化的阶段分解**（非 prompt 角色分解）是被证实有效的路线，我们是约束子问题的对应物。

**第五层：skill 方案已被收编，不是被排除**

C1 网格里 DeepSeek 10-shot 当编译器（1,255/1,292）就是"强模型+prompt 解析"档位——**skill 形态是我们接口上的一个贵档**，训练小模型是便宜档（0.6B 达其救回率 91-93%，服务成本约 1/1000）。论文表述：We do not reject the skill paradigm; we price it, bound it, and replace its most expensive instance where the host model is weak.

### 8.2 Discussion 章成文骨架（四段）

1. **段 1**（承认生态）：skill 范式的成功与规模（引综述+参考架构+MetaSkill），及其对弱模型/可验证性的两个公认短板（§8.1 一、二层引文）
2. **段 2**（正面对比表）：skill vs 训练编译器六维对照（上下文依赖/记录产物/可替换性/失败归因/成本/弱模型可用性）——§上一轮口头对比表的正式化
3. **段 3**（对赌声明）：引 Coordination Tax/MA-Evolve 承认分解有税，声明 B1 的实验设计正是"等预算、训练阶段"版的分解检验；引 AgentFlow 说明训练化分解的先例
4. **段 4**（收编）：C1 网格中的强模型编译器行=skill 档位的价格标签；构造性共存而非对立

### 8.3 文献清单增补（新近邻，全部真实 URL，写作时进 Related Work）

| 论文                                    | arXiv                                          | 用途                                                                                                                                   | 立场                                              |
| ------------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------- |
| A Systematic Survey of Agentic Skills | [2608.29596](https://arxiv.org/abs/2608.29596) | "When Skills Do Not Help"+SLM 部署 open challenge+可验证性 trade-off                                                                       | 友军（弱点背书）                                        |
| Harnessing Agent Skills（参考架构）         | [2606.20631](https://arxiv.org/abs/2606.20631) | Evidence & Feedback 层 14/15 未建立——记录轴真空的权威背书                                                                                          | 友军（记录轴背书）                                       |
| SkillFusion                           | [2610.15481](https://arxiv.org/abs/2610.15481) | skill 生态自我升级到 typed 约束——表示选择的外部验证；离线调和≠运行时编译                                                                                         | 友军兼最近邻（需在 Related Work 划清：skill 指令调和 vs 用户约束编译） |
| SkillBrowser                          | [2610.23554](https://arxiv.org/abs/2610.23554) | 上下文污染/盲注入干扰/弱模型 under-invocation                                                                                                     | 友军                                              |
| The Coordination Tax                  | [2610.37700](https://arxiv.org/abs/2610.37700) | 分解税 3.22x——B1 的存在理由，Discussion 必引                                                                                                    | 敌军转化为诚实背书                                       |
| MA-Evolve                             | [2609.04217](https://arxiv.org/abs/2609.04217) | 等预算下 prompt 角色分解不胜单体——同上                                                                                                             | 同上                                              |
| AgentFlow                             | [2510.05592](https://arxiv.org/abs/2510.05592) | 单体全上下文策略扩展性差+训练化分解有效先例                                                                                                               | 友军                                              |
| MetaSkill                             | [2611.29274](https://arxiv.org/abs/2611.29274) | skill 编排生态补注（可选引用）                                                                                                                   | 中性                                              |
| Compile, Then Page（SOP 编译+能力门控运行时）    | [2607.11346](https://arxiv.org/abs/2607.11346) | **双面弹药**：正面—"约束须编译为显式人造物"的独立验证（同向）；反面—弱模型受害+强模型 +16 点（三臂 70.4→86.4→92.8）恰与我们 Z 臂实证互证：弱模型消化不了 context 里的约束→必须训练专门件。Discussion 第一/四层引用 | 友军兼反证收编                                         |
| SpecHarness（Who Holds the Pen?）       | [2609.29921](https://arxiv.org/abs/2609.29921) | 自评 vs 判定 gap——Discussion"记录轴"段落正面划界后引用（互补方向）                                                                                         | 划界友军                                            |
| HOB（Heuristic Override Benchmark）     | [2603.29025](https://arxiv.org/abs/2603.29025) | 隐式约束系统性失效的独立证据——I 版动机段引用                                                                                                             | 友军（动机背书）                                        |

### 8.4 对实验设计的三点反哺

1. **B1 优先级再升**：既然 Coordination Tax/MA-Evolve 已公开质疑分解，B1（等预算、训练阶段版）是全文唯一能正面回应这场质疑的实验——从"架构主张的验证"升格为"参与社区正在进行的分解之争"
2. **B1 报告口径增加成本列**：除了 faithful，须报 token 成本/时延——Coordination Tax 的批评维度就是成本，我们的优势恰是编译器端便宜（0.6B），成本列能把 3.22x 的批评反转成卖点
3. **C1 网格的 DeepSeek 行改名为 "prompted compiler (skill-style)"**：把这个档位显式标注为 skill 范式的代表，网格即成为"skill vs 训练"的价格-性能表
