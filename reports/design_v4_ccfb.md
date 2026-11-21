# ConsDAG 改进设计方案 v4（面向 CCF-B）

日期：2026-11-21；2026-11-22 修订（见 §9）。

依据：
- 蓝本 `Pasted text.txt`、v3 数据与 0.6B v3 结果、全部源码；
- 文献部分：首版依据的是子代理摘要（二手）；修订版依据主会话逐篇核对，见 `reports/literature_audit_v4.md`（116 条原文全部带行号）。`papers/` 下 9 个目录错装，见 §2.4。

中期报告只取了可信约束的定义，**它的实验数据一律没有使用**。

---

## 0. 结论

| 问题 | 结论 | 依据（均已复算） |
| --- | --- | --- |
| 1️⃣ v3 数据集是否 ok | **不 ok**。结构上干净（无泄漏、配对一致），但构念效度不成立，不能进 CCF-B 主表 | 见 §1 的四个硬伤 |
| 2️⃣ 实验设计是否 ok | **不 ok**。E1 只测解析级 F1，测到的是"背模板"；零样本和 PE 对照不公平；没有执行级指标 | 0.6B 在 dev/tool_ho 上 strict F1 都是 1.0000，tpl_ho 的错误全部是 state 翻转 |
| 3️⃣ 处置 | 重建 **dataset v4**，加入**执行级 E1-exec**；已在服务器重启三模型队列 | commit `f63c727`；服务器 `/root/ConsDagQAQ` |

---

## 1. v3 硬伤（全量 15,000 条复算）

1. **N 版捷径**：N 版 query 与 task_goal 完全相同，5000/5000；E/I 版全部是"goal + 额外句"，10000/10000。判断有没有约束，看句子数量就够了。
2. **约束不起约束作用**：17,574/17,574 条金标约束已被唯一的 witness/默认计划满足（budget 上限 = 总价 + 余量；deadline 大于总时长；PII 只放本地节点；order/auth 的顺序就是拓扑序）。在 v3 上做执行级评测，无约束基线就是 100%，指标没有区分度。
3. **state 由模板池决定，而不是语义**：I 版线索里有 1930/8787 条含指令词或顺序词，例如 "Order of operations here: X, then Y."。tpl_ho 上 87 个错误全部是 explicit/implicit 翻转，说明 state 标签测的是措辞风格。
4. **对零样本/PE 不公平**：severity 是 type 的常函数（budget/deadline/privacy=high，tool_auth/order=medium），scope 由图结构确定性推出，confidence 恒为 1.0，但这些约定都不在提示里，却参与严格匹配。所以零样本和 qwen-max 的 F1≈0 主要是契约不可知造成的，不能用来证明"训练优于提示"。
5. 附带问题：
   - 机械重复文本占 4.7–6.7%。
   - 3400/4000 个训练组的目录里出现了 held-out 角色名。
   - v3 的 1.7B 在第 5600 步时 loss 已到 1e-5 量级，任务被过度拟合。这次重启时停掉了该运行，结果作废。

**v2/v3 的全部 E1 数字只作为 legacy 诊断保留，不进任何表。**

---

## 2. 文献范式（4 组精读 + 补充检索）

### 2.1 同类工作的实验设计共性

- **数据**
  - 方法类论文大多复用公开基准（TravelPlanner、τ²-bench、AppWorld 等），测试集几百到一千条。
  - 自建基准都带人工或 LLM 审计：PRefine 有 Fleiss κ 0.70/0.88；ANCHOR 五名工程师、Gwet AC1 0.91–0.97；Firefly 用 50+50 盲审加 χ²；ToolTurns 120 条盲审。
  - 以训练集为卖点的论文规模在 5k–35k（LIFT 34k，RECAST 30k）。
- **基线**：多个强闭源模型 PE、公开方法官方复刻（逐条写明改造点）、结构消融（w/o 编译器、gold 注入、RAW/SELF）。
- **指标**：执行级任务成功 + 约束满足 + **联合指标**（safe completion / process-valid / SPR / Verif.&NoDiff / both），再加违规次数和 hacking 诊断。
- **统计**：较好的论文用 3–5 个 seed 或 trial，加 10k 次按任务配对 bootstrap，或 Wilson CI / McNemar / Holm 校正。约一半论文没有统计，这是我们可以胜出的地方。
- **held-out**：EffectWorld 做了三个 held-out（未见工具和任务类型）；NormWorlds-CF 和 CIRCE 按根族或分组切分。

### 2.2 对三个创新点最危险的邻居

| 创新点 | 最危险邻居 | 威胁 | 我们必须拿出的差异化证据 |
| --- | --- | --- | --- |
| ① 训练的证据绑定编译器 | **CGAP**：由 prompt 驱动的 LLM（gpt-oss-20b / Qwen3-32B / GPT-5 mini，未训练；原文没有"zero-shot"一词）把请求解析成带 evidence span 的 operation，外加**无类型**的全局约束 Λt；授权和隐私明确留给应用（audit Q22–Q25）。**Sapien（修订新增）**：用现成 LLM 把**逐个 prompt**编译成可执行策略（Q14）。**NOMOS / PolicyGuide**：编译的是**域级书面 policy**；本机 26B 编译不显著劣于前沿模型（Q15–Q17）。**BeyondReAct**：同为 Qwen3 0.6–8B，训练的是 planner（Q1） | "为什么不直接 prompt 一个大模型？""Sapien 不就是逐 query 编译吗？" | 同 schema、同策略卡下的**强模型 PE 对照**（零样本 + few-shot）；faithful 执行级指标；按 I 档和 tool_ho 分开报告 |
| ② 约束锚定奖励分解 | TAG：门控辅助信用；在其简化的二通道模型中证明，存在难题时静态权重不安全（Q49 Q50）。RLVP：逐动作罚 + 结果奖励，折叠成标量会变慢，原则是"penalize commission, never omission"（Q35 Q40）；首版写的"outcome-gating"**无原文支撑**，已删除。Constrained GRPO：先标量化奖励再归一化，会造成共享分母耦合（Q28）；"会扭曲非对称比例"是**我方推论**。DAGent：GRPO 中按 DAG 拓扑分配**结果奖励**的信用（Q45）。SiLR：计数型违规奖励的组内区分度会坍塌（Q108） | g(A) 很容易被看成"TAG 换成外部锚" | 外部锚、节点归因、非对称罚三者**各自独立的增益**；ScAdv/GDPO 对照臂；同预算 TAG 臂；φ 不用计数型 |
| ③ E/I/N 配对可执行基准 | **LogiSafetyBench 2601.08196**（已读全文）：自称首个隐式合规工具评测；240 个人工验证任务；可执行 + LTL 预言。但其隐式来源是系统提示里的法规全文，只有两种时序模板，自认无法处理参数级约束（Q100–Q104）。AM-Bench：同任务约束的显式/模糊/缺失配对，其 KM 档的 gold 不可从输入恢复（Q67–Q70）。ExecutionFirst：同一轨迹生成三档显式度，但变的是执行细节，校验由同一 LLM 完成（Q62 Q63）。LIFT：合成 + 同一约束双渲染 + 训练集，约束全部显式（Q72）。ToolPrivacyBench：隐私执行级审计（Q105） | "隐式约束工具基准已经有人做过" | 放弃一切"首个"表述；只主张**参数级约束** + query 内可恢复的隐式线索 + N 近似干扰对照 + 咬合且逐条必要 + 训练集 + faithful 执行刻度 |

另外，Implicit Intelligence 定义隐式为 "requirements that users expect but never explicitly state"。按这个定义，我们 I 版的证据仍在 query 里，所以论文里必须把 implicit 定义为**表达状态**（不陈述指令，但可由 query 内事实推出），并引用它来划界。

### 2.3 补检索（修订：全文已下载入库 `literature/extracted/library/06_web_supplement_20261121/`）

- **LogiSafetyBench（2601.08196）**：已深读。对③构成高威胁，差异点见 §2.2。
- **ToolPrivacyBench（2606.28061）**：已读摘要、引言和标注协议。规模 2,150 例；policy KB 只用于事后审计（Q106）；κ 是抽样复标（Q107）。属于可对照和外部 OOD 候选。
- **SiLR（2609.04629）**：已核实"计数奖励最多只有 B+1 个取值"（Q108）。
- **When Lower Privileges Suffice（2606.20023）**：已核实 SFT→GRPO，奖励对过早升权重罚（Q109 Q110）。
- **PlanBench-XL（2606.22388）**：其"implicit subgoals"指检索式规划中的子目标，与约束无关，**降为低相关**。
- **PeakBench（2608.24509）**：PDF 只能抽出 2 页，**只读了摘要与引言**；内容是依赖/并发结构加资源调度，降为低相关。

### 2.4 文献库卫生

`literature/extracted/papers/` 下有 9 个目录装的是无关论文：ATLAS_2605.16668、CARL_2505.23300、LANG-NCO_2603.07613、RLVP_2510.07896、TAG_2508.09112、ARMA、Hermes、Instructed-Use-Tools、NCP-Benchmark。**一律不得作为证据引用**；以 `literature/extracted/library` 为准。

---

## 3. 创新点口径（收窄后，能立住的版本）

- **①**：一个**可训练、planner-agnostic、输出可审计**的约束编译器，输出 typed 约束对象（type/params/state/severity/scope/evidence_span）。主张落在"同一信息条件下，小模型训练后的编译质量和下游 **faithful** 执行级成功率，不低于（或优于）强模型 PE"。
  - 修订：划界表必须加入 Sapien（逐 prompt 编译）和 CGAP（带 span 的解析）。
  - "可本机部署"不能单独作为卖点，因为 NOMOS 已报告本机 26B 编译不显著劣于前沿模型（Q17）。
  - **不得**声称训练编译器、evidence span、隐式约束、拒判是"零先例"。
  - **校准/拒判在 v4 中不主张**：gold confidence 已删除；E5 改为用序列对数概率做 selective risk 的事后分析，且需要单独构造歧义集（§4.4）。
- **②**：只有在 E2 跑出"外部锚、节点归因、非对称罚各自有独立增益"之后才能写成贡献。在那之前只写成方法设计。
- **③**：主张"**参数级约束 + 咬合且逐条必要的约束集 + E/I/N 最小三元组 + 训练集 + faithful 执行刻度**"这个组合。
  - **禁写"三版语义等价"**，改写为"(E, I) 等价对 + N 对比臂"。
  - **禁写"首个隐式约束 / 隐式合规工具基准"**，因为 LogiSafetyBench 已经这样自称（Q103）。
  - tool_ho 只能写成"名称级 held-out"（见 §4.3）。
- 蓝本里"CGAP、RLVP 两次点名 open problem，由我们闭合"的说法需要修正：
  - CGAP 的"outside our scope"指从自然语言诱导**能力的状态依赖规则**（Q114），不是用户约束；
  - RLVP 的"open challenge"指从**环境 affordance** 自动发现约束（Q36）。
  - 改写为："与 RLVP 人工指定罚、CGAP 把授权/隐私留给应用不同，我们从用户 query 学习编译约束。"
- 首创句式必须附检索协议（日期、库、查询式），并把 LogiSafetyBench、AM-Bench、ExecutionFirst、LIFT、Sapien、CGAP 加进划界表。

---

## 4. 数据集 v4（已实现、已验证）

### 4.1 v3 → v4 变更

| 维度 | v3 | v4 |
| --- | --- | --- |
| 任务世界 | 单一 DAG = 唯一计划 | 5 个阶段、每阶段 1–3 个备选工具（费用/时长/本地或外发/是否清除 PII），可插入审批、脱敏、校验步骤，finish 两步顺序可交换 |
| 约束咬合 | 0%（全部被默认计划满足） | **100%**：默认计划违反每条金标约束（V3）；**逐条必要**：去掉 c 后的最小改动计划必违反 c（V4，5000 组全量复核） |
| N 版 | = goal 原句 | 同一句槽换成**同主题近似干扰句**（豁免、否定、他人适用、已撤销）；40% 的组另带一条三版共享的干扰槽 |
| I 版 | 指令改写 | 无指令词（词边界正则，V6）；budget/deadline 的 d2/d3 需要减法或加法，金标数值不出现在句中（含"1,350 含 350"这类尾数捷径，V6）。privacy 的 d2/d3 只给字段名。**修订**：策略卡把 test 池的字段短语也列成了示例（`src/dataset_v4_spec.py` L178），所以这一步实际上是在 prompt 里**查表**，不是推理。真正需要算术的只占隐式约束的 21.6%（1,693/7,826）。order 类 I 模板在 train/test 两池都是 5/6 条先提 after 角色，存在位置伪影 |
| held-out 工具 | 训练目录里出现 held-out 名 | held-out 世界 22 个工具名**从未出现**在 train/dev/tpl_ho 的任何模型输入中（V7） |
| 契约公平性 | severity/scope 是隐藏约定 | 策略卡随 prompt 给出类型、参数键、severity、scope 规则和 state 定义；删掉恒定的 confidence/description |
| 规模 | 5000 组 × 3 | 相同：train 4000 / dev 300 / tpl_ho 350 / tool_ho 350 组（15,000 条） |
| 分布 | — | 约束数 1/2/3 = 2665/1844/491；类型：order 2058、privacy 1764、tool_auth 1563、deadline 1352、budget 1089；I 难度 d1/d2/d3 = 2387/3073/2366；干扰槽比例 0.407（`generation_report.json`） |

验证门槛 V1–V9（`src/verify_dataset_v4.py`）全部 PASS，跨 split 的 query/goal/group 重叠为 0。
SHA256（LF）：train `eaabe109…`、dev `e7ff77f1…`、test_tpl_ho `04de746c…`、test_tool_ho `23e8b9b6…`。服务器重新生成后哈希逐一相同。

### 4.2 执行级刻度（E1-exec，`src/eval_exec.py`）

编译输出经严格解析后交给**最小改动约束感知规划器**（代表完美服从约束的 planner），产出计划，再由**独立检查器**用金标约束判定 safe_success（完成目标且零违反）。

- 刻度两端：none 档（默认计划）在 E/I 上为 0、在 N 上为 1；gold 档处处为 1。
- 附带指标：逐类型违反率；N 版的不必要偏离率；E/I 版安全时的过度改动率；group bootstrap 95% CI；两系统间做配对 bootstrap + 精确 McNemar。

**修订（被证伪的部分）**：首版说"这一项回答了 F1 高是否有用"，这是夸大。
- 一个**不看约束的保守规划器**（每阶段选本地且最便宜的工具，并插入全部可选步骤），在 E 版上的 safe_success 为 dev 0.673 / tpl_ho 0.634 / tool_ho 0.614。原因是它会顺带满足 budget、privacy、tool_auth。
- 因此 safe_success 单独不能把成功归因到编译。
- 必须以 **faithful_success** 为主指标（E/I：安全且改动数等于金标最小改动计划；N：安全且不偏离默认计划），并把保守规划器列为参考档。保守规划器的计划与金标计划一致率为 0。
- 这两项改动要等队列结束后再改代码（audit §6 T1）。

### 4.3 仍有的局限（如实写进 limitations）

- 纯模板合成；held-out 世界与训练世界**结构同构**（阶段数、备选位置、配对模式、数值区间都相同，`src/dataset_v4_spec.py` L71–150），只是名字和属性没见过。零样本下 tool_ho 并不比 dev 难（受约束 safe 0.107 对 0.077）。所以 tool_ho 只能称为"名称级 held-out"。对照 EffectWorld 的未见 commerce 域，要主张结构泛化，需要另造结构不同的世界。
- 模板池小（每类每池 E 8 条、I 6 条、N 4 条）。tool_auth/order 的 difficulty 只是名义标签。
- 规划器是符号的最小改动规划器，不是 LLM planner。E6 再换 LLM planner。

### 4.4 数据侧待补（P0/P1）

| 优先级 | 内容 | 做法 | 依赖 |
| --- | --- | --- | --- |
| P0 | I 版可恢复性 oracle | ≥2 家强模型零样本恢复约束，**看不到 gold**；恢复集 = 金标（type+params）才准入；N 版须恢复出空集；按类型和难度报一致率 | 有效 API（Claude/Codex 中转可用；qwen-max 的 key 要复核） |
| P0 | 人工盲审 | 2–3 人，每类型 ≥50 条，共 ≥250 条；按"可恢复 / 唯一 / 自然 / N 无约束"四维打分；报 Krippendorff α 或 Gwet AC1 | 标注人 |
| P1 | 改写 OOD 子集 | 强模型改写 300 组 tpl_ho，**约束保持门**用 gold 规划器加检查器复核（LIFT 的教训：改写模型可能"执行"约束），人工抽审 | API |
| P1 | 外部 OOD | ToolPrivacyBench 或 τ²-bench 的子集映射到我们的 schema，作为零训练迁移评测 | 获取数据 |
| P2 | 歧义档 A | 对接 AM-Bench：线索不足以唯一确定参数，gold = abstain，用于 E5 | 设计 gold 语义 |

---

## 5. 实验设计（v4）

### 5.1 E1 主表（编译器）：同服务器、同代码、同依赖、bf16、seed 42

| 臂 | 系统 | 状态 |
| --- | --- | --- |
| Z1–Z3 | Qwen3-0.6B/1.7B/4B 零样本（同一 v4 prompt 含策略卡） | **运行中**（队列内） |
| T1–T3 | 同底座 LoRA（r16/α32/dropout 0.05，lr 2e-4，3 epoch，grad-accum 4，max_seq 1280，completion-only loss） | **运行中**（串行 0.6B→1.7B→4B） |
| P1–P2 | 强模型 PE（同 prompt，temperature 0）：Claude（relaxycode 中转）/ gpt-6-astra（Codex 中转）/ qwen-max（待 key 复核） | 待跑（CPU/API；可在服务器上跑） |
| P3 | 强模型 PE + few-shot（每类型 2 例，取自 train） | 待跑 |
| O | gold 与 none 刻度 | 已内置 |

**指标**：
- e1_score_v5：严格 F1、核心 F1、state 准确率、记录全对率、N 误报率、逐类型和逐难度、parse rate、malformed 数。
- e1_exec_v1：safe_success（总体 / 受约束 / 按 variant）、95% CI、逐类型违反率、N 不必要偏离率。

**判胜（预注册）**：
- T 优于同底座 Z：训练增益。
- T 对 P：报差值和配对 CI。核心主张压在 **I 档**和 **tool_ho**。
- 若 T 输给 P，按蓝本 R1 转向"本机部署 + 成本/延迟"轴，**照实报告**。

### 5.2 E4 泛化

- dev（in-domain）、tpl_ho（模板、goal、背景 held-out；**修订**：PII 字段别名经策略卡泄漏，不算 held-out）、tool_ho（未见的工具**名称**；结构同构）分列。
- 预注册判据：I 档在 tpl_ho 上的下降幅度；tool_ho 的 safe-success。若崩溃，结论改写为"组合泛化仍是 open problem"。

### 5.3 E5 校准（降级）

- 用序列平均对数概率做 risk–coverage 曲线、ECE（以 safe_success 为正确性标签）。
- 不宣称"学会拒判"，直到 §4.4 的 A 档补齐。

### 5.4 E6 planner 可移植性

把同一编译输出喂给 ≥3 个 LLM planner（Qwen3-4B/8B、一个异家族模型），用同一检查器判 safe_success。只做推理，可在服务器上跑。

### 5.5 E2/E3（GRPO，阶段 3）：前置条件与设计修正

**前置条件**：v4 的规划世界已经提供独立的成功检查器，以及违反判定（RLVP 式的可验证规则），E2 的信息权限问题由此闭合：
- C* 只用于离线评测与 ② 的漏检罚。
- 所有臂拥有相同的信息权限。
- 训练用 train 世界，评测用 held-out。

**臂（同预算，1.7B LoRA）**：
- vanilla GRPO
- ToolRLA 加法（λ=10）
- GDPO/ScAdv（按分量标准化）
- TAG 乘性门控（按其探针协议）
- RLVP 逐动作罚
- ②完整版
- ②去门控 / 去归因 / 对称罚

**必报**：
- 四格（成功 × 满足）、反躺平三联、组内方差可达性预诊断（VarG）。
- 编译器噪声注入（FP/FN 各 3 档）存活曲线。
- 3 个 seed 加配对 bootstrap。

**风险（修订）**：首版引用 RLVP 的 "chain 0.6B/1.7B (too weak)" 来说明 1.7B 上的罚可能无效，这是**断章取义**。
- 该句是图注，说的是稠密 progress potential 的收益只在可达阈值之后才出现（Q37 Q38）；
- RLVP 的惩罚通道恰恰"generalizes from 1.7B to 8B models"（Q39）。
- 因此 1.7B 作为主战场没有文献层面的反对理由。仍需先测组内方差 VarG 与 dead-update 比例。

### 5.6 统计纪律

- 所有比较都在同一测试集上做**配对**检验：group bootstrap 1000 次以上，加精确 McNemar；多重比较做 Holm 校正。
- 种子：按用户要求主表统一 seed 42。论文里需要注明"单 seed + 数据层 bootstrap"。算力允许时，补 0.6B/1.7B 的 seed 43/44，作为训练方差估计。
- 预注册方向；不支持的结果照报；发散或中止的运行单列计数。

---

## 6. 代码审计结论

| 项 | 结论 |
| --- | --- |
| completion-only loss | 正确：prefix 的 label 置 -100，completion 后接 EOS（`train_lora`） |
| NaN 防护 | 正确：前向 loss 有限性检查、`clip_grad_norm_(error_if_nonfinite=True)`、step 后参数有限性检查、bf16 加载、失败时写 `training_failure.json`。v4 smoke 的首步 loss 为 0.683，数值有限 |
| 截断丢样 | **已修**：v4 prompt 最长约 1060 token，原 max_seq 1024 会静默丢样本。改为 1280，并打印 dropped 数（smoke 中 12000/12000 保留） |
| 评分器 | v4 提交了 fail-closed 严格解析；v5 新增核心键（整值浮点按整数处理）、记录全对、N 误报率（显式计数） |
| 数据可复现 | **已修**：Windows 写盘为 CRLF，导致哈希跨平台不一致。现在显式写 LF，服务器重新生成后哈希相同 |
| 验证器自身 | v4 单测专门验证它能抓到篡改的 witness、N 版残留约束、held-out 工具泄漏。审计中发现并修正了一次 `\b` 被 shell 吞掉、导致指令词检查空过的问题 |
| 测试 | 本地 53 个全部通过（服务器的 conda 环境没有装 pytest；代码同一提交，已在本地跑过） |

---

## 7. 风险与工作量

| 风险 | 触发 | 预案 |
| --- | --- | --- |
| v4 仍被 0.6B 打满 | dev/tpl_ho/tool_ho 的 safe-success 都 ≥0.99 | 仍有价值（对比 Z/P）。但应补改写 OOD 和外部 OOD，并加大 I 档的推理深度（三事实链） |
| T 输给强模型 PE | I 档或 tool_ho 上 T < P | 照报；叙事转向成本、延迟、本机部署 |
| 4B 显存或时间 | OOM 或单模型超过 12h | eval batch 已设为 16；必要时改用梯度检查点 |
| API 不稳定 | Codex 中转的 SSE 超时 | 断点续跑；Claude 中转作为主 P 臂 |

时间估算（4080S）：每个模型 = zero-shot 评测 + 9000 步 + 训练后评测，0.6B 约 3–4h，1.7B 约 6–8h，4B 约 9–12h，三模型串行约 18–24h。P 臂、oracle、人审与 GPU 队列并行。

---

## 8. 禁止的表述

- 用 v2/v3 或中期报告的任何数字。
- 拿解析 F1 当执行级安全成功率。
- 声称"三版语义等价"、"首次 scope 绑定/约束门控"、"零先例"。
- 说 tool_ho 证明了结构泛化（它只证明了未见名称和属性）。
- 在 E2 跑出结果之前声称 ② 有下游收益。
- 声称校准或拒判已经学会。
- 声称"首个隐式约束 / 隐式合规工具基准"（LogiSafetyBench 已这样自称）。
- 只报 safe_success 而不报 faithful_success 与保守规划器参考档。

---

## 9. 修订记录（2026-11-22，依据 `reports/literature_audit_v4.md`）

| 位置 | 修订 | 依据 |
| --- | --- | --- |
| 文首"依据" | 首版文献部分是子代理二手摘要；本版逐篇核对 | audit §0 |
| §2.2 ① | CGAP 去掉"零样本"措辞（原文无此词），注明 Λt 无类型、授权/隐私留给应用；新增 Sapien | audit F2，Q14 Q22–Q25 |
| §2.2 ② | 删除 RLVP"outcome-gating"（无原文支撑）；Constrained GRPO 的"非对称"标为我方推论；新增 SiLR | audit F4 F5 |
| §2.2 ③ / §3 | LogiSafetyBench 已读全文，禁止使用"首个"；可守的差异是参数级约束 | audit F6，Q100–Q104 |
| §2.3 | "只核实到摘要"改为已入库全文；PeakBench/PlanBench-XL 降为低相关 | audit F6 F7 |
| §3 | 修正蓝本"两次点名 open problem"的说法 | audit F3，Q114 Q36 |
| §4.1 / §5.2 | PII 别名经策略卡泄漏；隐式中需要算术的只占 21.6%；order 位置伪影 | audit F8，§5.1 |
| §4.2 | safe_success 可被保守规划器拿到 0.61–0.67，主指标改为 faithful_success | audit F9，§5.3 |
| §4.3 | tool_ho 只是名称级 held-out | audit §5.1 |
| §5.5 | 撤销 RLVP"too weak"的误引 | audit F1，Q37–Q39 |

待修代码（队列结束后由我执行）：audit §6 T1、T4、T5、T6、T8、T13、T15。

E2 设计补充义务（来自 `design_v4_independent_recheck.md`，已复核）：同一 query 下所有轨迹相同的漏检罚，会被 GRPO 组内中心化抵消。漏检罚必须依赖轨迹本身（只在计划实际违反时触发）。E1-exec 只消费 type+params，scope 的价值需要另行证明。
