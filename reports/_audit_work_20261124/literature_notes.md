# ConsDAG 本地全文证据审计（2026-11-24）

本文件为主审计的文献证据附件，不改动实验设计、数据或既有报告。核查范围为用户点名的 15 篇本地 `*_fulltext.txt`，逐篇阅读了方法、实验与局限相关段落；以下版本号、题名、arXiv 编号均来自本地抽取文本。**没有联网独立核验题名、作者、版本或发表状态，也没有据此断言全领域不存在某方法。** 行号从对应文件第一行起，按 Python `splitlines()` 计数；文本抽取可能含断词或页面分隔。

标签含义：**【全文事实】**可直接回到短引文/行号；**【解释推断】**为机制对照或研究判断；**【待验证】**为现有全文或本项目实验尚不能支持的命题。E/I/N 始终指本项目 explicit / implicit / none 数据条件，**不是证据强度等级**。A 路线的 clear-0 / ambiguous-1 / clear-2 是信息充分性/决策歧义分层，与 E/I/N 分开。

## 结论先行

- **编译器最近邻**是 CGAP、Sapien、NOMOS：请求解析、证据片段、参数/状态/顺序绑定、编译后执行门控均已有直接先例。“首次自然语言约束编译/首次局部编译器/首次 scope binding”不成立。
- **基准和控制最近邻**是 LogiSafetyBench、AM-Bench、EffectWorld、LIFT：隐含合规、任务与安全联合通过、成对控制、作用域、无旁及修改、near-miss、实际澄清或澄清估计均有先例。原方案更可信的差异是具体的 E/I/N 适用性反事实、紧凑编译器以及独立执行诊断组合；是否有足够新增价值仍需实验。
- **A 路线最近邻**至少包括 AM-Bench、EffectWorld、Implicit Intelligence、Sapien、ATLAS，另有 PRefine 对歧义的主动排除。不能以“首次处理信息不足/首次询问用户”立题。较可检验的差异是：对模型可见信息建立可核验的决策歧义 oracle，分别评价可推断与需澄清样本，再做实际信息恢复干预及成本衡量。这仍是待验证研究假设。
- NOMOS 已明确承认“漏编译条款会静默失去执行”；Sapien 明确承认模糊请求可能产生过宽 policy。它们直接支持本项目审计 fail-open，而非支持声称静态/执行验证能够保证语言语义编译正确。
- ConstrainedGRPO、RLVP、TAG 已占据奖励分解、分通道归一化、路径惩罚与锚点门控。现阶段没有理由以一般 reward factorization 或 anchor gating 复活已失败的 GRPO 主贡献。

## 逐篇证据

### 1. CGAP — Capability-Grounded Agentic Planning（2610.41040v1）

本地全文：[2610.41040_CGAP_fulltext.txt](../../literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt)。版本标识 L98；本次读段 L407–466、623–704、805–854、1018–1040。

- **【全文事实】**操作表示包含 capability、entity/time/scope requirement、用户消息证据片段及状态。短引文 L424–427：`requirement ri (entity, time, and scope), evidence spans ϵi in the user’s messages`。
- **【全文事实】**证据校验检查边界、字面值与 schema，但语义是否表达目标操作仍靠 LLM。短引文 L435–437：`Whether a span actually expresses the intended operation remains a judgment of the LLM`。
- **【全文事实】**规划认证只针对编译出的模型；L652–654 证明返回计划有效且最少动作，L671–675 的 NOPLAN 保证同样以编译模型为前提。L1030–1031：`authorization, privacy, and the decision whether an action is appropriate remain the application’s job`。
- **【解释推断】**证据承载的请求 IR 和最小动作规划已存在；ConsDAG 的可比差异应具体落在参数级授权/隐私约束、E/I/N applicability 及紧凑编译器训练，不能把 evidence-bearing IR 或最少修改概念本身当作首次。
- **【待验证】**项目 evidence span 是否真的支持所编译约束，需要独立语义核查；执行 faithful 不能替代该项。A 路线如只在规划无解后补信息，也未必超出此类“编译模型条件保证”。

### 2. LogiSafetyBench — Evaluating Implicit Regulatory Compliance in LLM Tool Invocation via Logic-Guided Synthesis（2601.08196v1）

本地全文：[2601.08196_LogiSafetyBench_fulltext.txt](../../literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt)。版本 L98；读段 L340–437、496–514、609–644、715–766、1290–1307。

- **【全文事实】**法规转换为确定性 LTLf，安全 oracle 与任务状态匹配分开，再报告联合成功（L374–376、609–623）。输入保留原始法规，去除用户指令显式安全要求。短引文 L742–745：`Tool Schema (Dapi), the Raw Regulatory Document (Ptxt), and the User Instruction (I) where explicit safety requirements are removed`。
- **【全文事实】**方法局限是调用时序，非细粒度参数安全。短引文 L1297–1300：`exclusively on the temporal ordering of API calls, limiting our ability to analyze the safety of specific function arguments`。
- **【解释推断】**“隐式合规 + 可执行 oracle + task/safety 联合指标”已被直接覆盖；项目可能不同之处是请求内参数/作用域/状态约束与 E/I/N 最小反事实。
- **【待验证】**相对该类时序基准，参数级 gold 真的可从可见语境恢复吗？应核查所有模型可见规则，不能把“未直接写在用户请求”当作真正信息缺失。A 路线需分开隐含可推导与缺失不可定。

### 3. AM-Bench — Understanding Agents under Task Underspecification across Models and Harnesses（2610.18090v1）

本地全文：[2610.18090_AM-Bench_fulltext.txt](../../literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt)。版本 L63；读段 L164–339、738–777、1671–1698。

- **【全文事实】**显式区分 ambiguity 和 missingness，含 restrictions/authorization 的缺失条件（L210–217）。短引文 L231–232：`Ambiguity (A) supports multiple reasonable interpretations; missingness (M) omits a key requirement`。
- **【全文事实】**各变体仍用同一完整任务约束评安全。L242–244：`S checks the same fully specified task constraints across conditions, including undisclosed requirements`。任务信息还可能位于工具描述/返回值，因此不能一概断言 KM gold 对 agent 永远不可恢复（L277–306 的输入审计范围）。
- **【全文事实】**已有澄清请求统计与澄清收益估计，采用同 task/model/harness 的 Full 结果替代 requesting run 的 outcome。短引文 L253–254：`we use Full runs matched by task, model, and harness as a common complete-information reference`。L261–262 明示假设：`complete information restoration and Full-like execution`。这不是实际交互用户答复后的 rollout。
- **【解释推断】**这是 A 路线直接最近邻；ambiguity/missingness/clarification 三者均不能当作新概念。可辩护差异须是可核验的信息集/决策等价性 oracle、clear-0/ambiguous-1/clear-2 分层，以及实际信息恢复干预，而非 Full outcome substitution。
- **【待验证】**本项目若批评 AM-Bench，应写“在隐藏完整 gold 下衡量信息不足时的行为，不能单独归因为推理失败”，而非“其所有 missingness gold 都不可恢复”。需逐例确认 agent 信息集。

### 4. EffectWorld — Small Agents Should Know What Their Tools Do（2610.35981v1）

本地全文：[2610.35981_EffectWorld_fulltext.txt](../../literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt)。版本 L52；读段 L261–279、359–466、480–498、701–756、1338–1381、1767–1783。

- **【全文事实】**任务有 optimal/naive plan；回放确定性评分，同时检查 goal、effect-safety、额外动作/时延和旁及状态。短引文 L450–452：`no entity outside the goal changed (such a change is collateral and fails the task)`。
- **【全文事实】**已有实际脚本用户澄清，而非只有离线估计。短引文 L455–457：`a scripted user that confirms proposals, supplies missing information once ... its replies are deterministic`。
- **【全文事实】**已有同主题但无用的 near-miss 工具训练。L1362：`an offered tool from the request’s own topic that cannot serve it`。未见 schema/tool 类型的跨域测试，但 effect 结构保持相同（L485–493）。脚本用户会确认错实体，作者承认局限（L1769–1773）。
- **【解释推断】**“无需改变默认计划时保持不动”“near-miss”“不做额外修改”“实际澄清”均有很近先例。ConsDAG N 针对不存在/豁免/不适用约束，可能与“无工具可完成请求”有机制差别，但必须用成对样例说明。faithful 的 edit-count equality 是定量执行条件，不能据此宣称语义/证据忠实性。
- **【待验证】**A 路线必须超过一个 scripted clarification benchmark：用已知决策歧义的反事实分层，验证只在必要时问、回答后安全执行且代价合理。与其“no collateral changes”及最优计划 oracle 的差异需明确。

### 5. LIFT — Scoped Constraints for Evaluating and Training Instruction Following（2610.28819v1）

本地全文：[2610.28819_LIFT_fulltext.txt](../../literature/extracted/library/03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt)。版本 L60；读段 L210–324、670–721、773–835。

- **【全文事实】**约束绑定于文档 outline 的 leaf path；每任务携带评估约束，结构/内容分别加权并用于 RL。L235：`Every task carries the list of constraints it will be evaluated against`。
- **【全文事实】**结构 scope 与全局 scope 使用相同 topic、outline、constraint content。短引文 L299–302：`compare scoped and globally-scoped prompting directly, holding topic, outline, and constraint content fixed`。实验覆盖多模型、重复采样和按样本区间（L316–318）。
- **【解释推断】**scope binding、成对控制和受约束任务指标均已有先例。项目差异是约束并非全都显式列给 agent、输出为工具计划、含参数及 N applicability 反事实，而非首次研究作用域。
- **【待验证】**结构 OOD 必须说明改变的是 constraint composition、作用域组合还是模板/措辞；单一生成器内 holdout 不能自然升级为任意结构泛化。A 路线可借其“保持内容只改变信息表达”的控制，但不能复用 scope 标题代替信息充分性定义。

### 6. Sapien — A Stateful Policy Engine for Autonomous AI Agents（2610.00797v1）

本地全文：[2610.00797_Sapien_fulltext.txt](../../literature/extracted/library/01_constraint_compiler/2610.00797_Sapien/2610.00797_Sapien_fulltext.txt)。版本 L101；读段 L326–440、487–531、651–682、858–897、1380–1405。

- **【全文事实】**从任务 prompt 生成/安装 policy，包含工具顺序、参数、变量绑定、返回值和 runtime Python predicate（L407–429、487–502、662）。短引文 L500–502：`allowing the policy LLM to synthesize both the policy expression and predicate logic`。
- **【全文事实】**隔离/执行机制并不证明语言到 policy 的语义完整性（L338–361）。L384–388 明确承认：`a vague or ambiguous prompt ... generate a wide policy that might permit harmful calls`，并要求独立确认机制。
- **【解释推断】**请求特定、参数/状态/时序 policy synthesis 已存在；ConsDAG 的 compact SFT 与 E/I/N 诊断可以形成特定实证问题，但不能声称首个请求级 policy compiler。Sapien 对模糊请求的自认风险支持 A 路线动机。
- **【待验证】**A 路线若新增“在 policy 生成前识别信息不充分”，需证明比简单风险确认或保守拒绝更有效；未完成前不能宣称修复该安全问题。ConsDAG 的合成实验不能自动支持抗 prompt injection 安全主张。

### 7. NOMOS — Compiling Written Policies into Statically Verified Tool-Call Gates for LLM Agents（2610.11030v2）

本地全文：[2610.11030_NOMOS_fulltext.txt](../../literature/extracted/library/01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt)。版本 L74；读段 L589–664、779–811、998–1020、1387–1420、1755–1797、2927–2982。

- **【全文事实】**rule 含 id/type/tools/predicate/原文 clause，固定 predicate vocabulary + 静态检查；静态检查不保证词表项目与条款语义一致（L593–599、623–633、658–661）。
- **【全文事实】**缺事实时 precondition 默认阻断，forbidden 规则可能静默放行。L602–605：`a precondition whose supporting fact is missing blocks by default, whereas a forbidden rule with a missing fact passes silently`。
- **【全文事实】**直接承认漏编译的 fail-open。L2945–2947：`a clause the compiler misses is silently unenforced`，因此使用独立 compliance checker。另有 26B 本地模型结果，但“不显著差”不等于证明 noninferiority（L1777–1782）。L2969 预设已有 written policy。
- **【解释推断】**这是项目 fail-open 审计最直接先例。ConsDAG 与 written-policy compilation 的差别应是请求/语境推导约束和 E/I/N applicability；本地部署与 evidence clause 本身不是新贡献。
- **【待验证】**需分别测漏约束造成的 unsafe、虚构约束造成的 unnecessary edits、错参/错 scope；总 F1 或执行器“编译规则下安全”不能替代独立 gold check。A 路线还须分清未知 supporting fact 与根本不存在的约束。

### 8. CIRCE — Divines LLM Task Complexity from Constraint Structure（2610.41089v1）

本地全文：[2610.41089_CIRCE_fulltext.txt](../../literature/extracted/library/01_constraint_compiler/2610.41089_CIRCE/2610.41089_CIRCE_fulltext.txt)。版本 L105；读段 L209–308、462–504、1059–1106。

- **【全文事实】**NL 转换为包含变量、类型、域、constraint、query 的 CIR，再变为 typed graph，带语法/语义检查与 repair（L257–279）。任务是预测正确率/复杂度，而非执行门控（L462–483）。
- **【全文事实】**作者明确排除需要推导约束的问题。L1077–1081：`its scope is limited to the problems whose constraints are part of the input. It does not cover the problems where inferring constraints is part of the reasoning process`。
- **【解释推断】**typed IR/compiler 不是新；隐式 applicability inference 和执行后果确与其目标不同。这是范围区别，不能当作已证明项目泛化优势。
- **【待验证】**A 路线可把“约束在输入内”“可由输入推导”“多个可能约束都兼容输入”严格分开。现有 E/I/N 名称并未自动形成这种可识别性保证。

### 9. ATLAS — Constraints-Aware Multi-Agent Collaboration for Real-World Travel Planning（2509.25586v1）

本地全文：[2509.25586_ATLAS_fulltext.txt](../../literature/extracted/library/01_constraint_compiler/2509.25586_ATLAS/2509.25586_ATLAS_fulltext.txt)。版本 L47；读段 L155–183、269–327、366–432、472–484、1105–1145。

- **【全文事实】**其 explicit 包括用户明确写出或 query 暗示的要求；implicit 指常识/物理 invariants。L166–170：`explicitly stated or implied by Q`；`stem from commonsense domain rules and physical realities`。这与 ConsDAG E/I 定义并不一一对应。
- **【全文事实】**manager 解析/推导约束，planner/checker 循环，unsat 触发搜索获取新信息。L419–426：`When the Checker returns an unsat verdict ... impossible with the current information ... diagnose the underlying information gap`。
- **【解释推断】**约束解释与规划/搜索分离已有架构先例。ConsDAG 的 compiler × candidate generator 交叉干预可能是更细的诊断，但不能以“分离语义和搜索”概念本身主张首次。ATLAS 是 A 路线信息获取邻居，但工具搜索补充候选域与向用户消除决策歧义仍有区别。
- **【待验证】**须区分真实不可行、当前搜索域不完整、可见信息不足以唯一决策；不要把所有 unsat/失败归因信息缺失，也不要把其 explicit/implicit 分类直接拿来对照项目 E/I。

### 10. Implicit Intelligence — Evaluating Agents on What Users Don’t Say（2602.20424v1）

本地全文：[2602.20424_ImplicitIntelligence_fulltext.txt](../../literature/extracted/library/01_constraint_compiler/2602.20424_ImplicitIntelligence/2602.20424_ImplicitIntelligence_fulltext.txt)。版本 L47；读段 L112–180、269–321、444–482、665–741。

- **【全文事实】**YAML 世界提供 context/entities/actions/execution rules 和 rubric；agent 不直接见隐含需求，可探索环境；主要是 LLM rubric 判分及人审样本（L287–321、451–480）。失误包含探索不足、功能配置不全、状态保留（L674–688）。
- **【全文事实】**作者主动区分隐式推断与澄清，但当前单轮不允许问用户。L706–711：`single-turn interaction where agents cannot ask users to clarify ambiguous requirements`；`measure both implicit inference and strategic question-asking as separate skills`。
- **【解释推断】**“推断和提问是不同能力”已有明确论述。项目可以通过确定性 oracle/歧义分层把它操作化，但应写成具体实现和评估差异，而非首次概念发现。
- **【待验证】**A 路线需直接验证：同一可见输入下是否存在不同行为 gold 的可行世界、问题是否消除相关差异、可恢复样本是否仍能不问正确执行。不能仅把失败样本重标为 ambiguous 以提高结果。

### 11. Execution-First Synthetic Tool-Use Trace Generation for LLM Agents（2607.29175v2）

本地全文：[2607.29175_ExecutionFirst_fulltext.txt](../../literature/extracted/library/03_paired_benchmark/2607.29175_ExecutionFirst/2607.29175_ExecutionFirst_fulltext.txt)。版本 L111；读段 L303–339、380–429、501–538、568–603、1181–1201。

- **【全文事实】**先生成执行有效 trace，再合成用户任务；生成基于 template DAG/block pool 等控制结构复杂度。L307–309：`first constructs and executes valid tool traces, then synthesizes user tasks only after execution-based validation`。
- **【全文事实】**验证时尚无 user question，因此只验 trace 内部一致性；而非 query/trace 一致性。L507–510：`no user question exists at this point ... only the consistency of the executed trace, rather than its agreement with a user query`。
- **【全文事实】**Basic/Intermediate/Challenging 分别省略执行细节，仍对应同一 validated execution trace（L523–535）。
- **【解释推断】**execution-first 合成、多表述同 gold、DAG 复杂度控制均已有先例。ConsDAG 的 E/I/N 若真正改变约束存在性/默认计划 gold，比“只改表述保留 trace”有可检验区别；但执行正确并不证明用户可见文本足够恢复 gold。
- **【待验证】**应独立审计从文本到 gold 的可恢复性，尤其 I。A 路线必须在生成时构造可区分/不可区分信息集，而非只删几个关键词就声称歧义受控。

### 12. PRefine — Latent Preference Modeling for Multi-Session Personalized Tool Calling（2604.17886v3）

本地全文：[2604.17886_PRefine_fulltext.txt](../../literature/extracted/library/01_constraint_compiler/2604.17886_PRefine/2604.17886_PRefine_fulltext.txt)。版本 L95；读段 L268–310、449–487、577–646、1346–1379、1590–1640、1660–1678。

- **【全文事实】**从历史 H 推断 query q 未明确给出的 preference-sensitive API 参数。L289–291：`preference-sensitive arguments unspecified in q must be inferred by modeling the user’s latent preference from H`。含 evidence support/actionability/temporal consistency 的 verifier 和未见函数测试（L631–639、1628–1639）。
- **【全文事实】**benchmark 故意排除模糊 preference（L484–487）；每 query 一个持久偏好以保持 gold 不歧义。L1668–1671：`each MPT query targets only one ... keeps the gold argument unambiguous`。
- **【解释推断】**证据支撑的隐含参数推断和 unseen function 泛化已经存在；ConsDAG 差异是请求级约束与适用性，而非多轮持久偏好。它为 A 路线提供“明确保证可恢复”的对照，而非从未研究过参数隐式推理。
- **【待验证】**项目 gold 可恢复保证是否同样明确？需评估多条线索冲突/无充分支持的处理；不得把 PRefine 人为保留清晰 gold 误写为它忽略了所有歧义问题。

### 13. Constrained Group Relative Policy Optimization（2602.05863v4）

本地全文：[2602.05863_ConstrainedGRPO_fulltext.txt](../../literature/extracted/library/02_objective_factorization/2602.05863_ConstrainedGRPO/2602.05863_ConstrainedGRPO_fulltext.txt)。版本 L57；读段 L151–187、284–328、400–432、464–491、918–950、1902 起的局限段。

- **【全文事实】**明确区分 reward-level scalarization 和 component advantage 后 scalarization，研究组内标准化的影响。L290–295：`within-group standardization: subtracting the group mean and dividing by the group standard deviation`，以及 `first computing component-wise advantages for each reward and cost`。L406–426 给出分量 advantage 组合式。
- **【全文事实】**有五 seed gridworld 与 GSM8K 不同大小模型实验，比较稳定性/可行率（L478–491、918–950）。
- **【解释推断】**奖励与成本信号的归一化耦合已有直接研究。每 query 固定的 penalty 在组内减均值时抵消，是标准公式的直接推论，不能单独作为新算法。该论文不解决 NL constraint compiler 或信息歧义。
- **【待验证】**若未来重做 RL，先在候选响应内验证 reward/penalty 确有差异、梯度信号非零，并给出比已有分量标准化更具体的新增机制；当前负结果不支持把该线当主贡献。

### 14. RLVP — Penalize the Path, Reward the Outcome（2607.07435v1）

本地全文：[2607.07435_RLVP_fulltext.txt](../../literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt)。版本 L80；读段 L253–268、304–316、358–389、437–459、491–515、866–881。

- **【全文事实】**确定性规则对 pre-action state/action 判定，违约惩罚归于 offending action tokens，义务完成可加 credit，outcome/path 独立归一化。L360–366：`a second, per-action channel`；`The two channels are normalized separately`。
- **【全文事实】**强调只惩罚可验证具体行为，避免惩罚“没进展”使 agent 停止行动。L495–500：`penalize commission, never omission`。局限 L870–872：`penalties were manually identified based on domain rules`，自动发现可罚约束仍为开放问题。
- **【解释推断】**路径/结果分信号、行动级约束与稳定训练并非空白。ConsDAG compiler 可成为自动规则来源是组合方向，但必须证明编译错误不会扩大错误惩罚；不能把该潜在连接当已完成贡献。
- **【待验证】**A 路线若把“没问问题”设为一律罚项，可能混淆 omission 与具体不安全行动。应对真正决策歧义、代价及澄清后的执行作分别测量，而非奖励所有提问。

### 15. TAG — Multi-Reward Hacking: From Aggregation-Induced Drift to Trust-Anchored Defense（2610.21404v1）

本地全文：[2610.21404_TAG_fulltext.txt](../../literature/extracted/library/02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt)。版本 L89；读段 L429–470、505–525、560–594、774–800、887–948。

- **【全文事实】**独立优化各信号，按 policy drift 选择 anchor，再以 anchor satisfaction 控制 auxiliary credit。L435–437：`first elects an anchor based on the policy drift induced by optimizing each channel independently ... then conditions auxiliary credit on anchor satisfaction`。
- **【全文事实】**GRPO hard prompt 内全无 primary-success 时，group standardization 可抹掉 auxiliary weight。L515–518：`its rewards take only two levels and the group standardization erases the auxiliary weight`。作者承认低 drift 并不保证 true reward alignment，理论模型简化（L937–943）。
- **【解释推断】**anchor gating 和 reward hacking 分析已有直接先例，故本项目一般“以任务/安全为锚”不构成算法创新。它也解释简单调权重可能无效，但不能替代本项目真实日志分析。
- **【待验证】**若恢复算法线，需证明区别于现有 anchor-selection/gating 且在项目任务上有效；无正证据前应保留负结果和删除算法贡献的决定。

## A 路线与原贡献的最小可辩护表述

**【解释推断】原 v5 可以写的窄贡献候选**：一个可执行的约束适用性诊断基准，通过保持请求词汇/工具结构相近的 E/I/N 反事实，观察紧凑编译器何时遗漏、错绑或过度添加约束，并以独立 gold 执行检查和编译器/候选搜索交叉替换拆解后果。这是具体组合及证据贡献，不是上述组件的首次发明；是否达到论文贡献强度还取决于 seed 稳定性、结构泛化、数据泄漏排除、机制诊断及有效对照。

**【解释推断】A 路线可以验证的研究问题**：在固定模型可见信息下，区分“可以决定无需干预”“存在多个要求不同安全决策的兼容情境”“额外信息已经足以决定”的情形；测试 agent 是否在必要时索取能消除相关决策差异的信息，并在回答后完成任务。其潜在增量不在 clarification 一词，而在可核验的歧义构造、clear-0 / ambiguous-1 / clear-2 因果控制以及实际信息恢复效果。

**【待验证】A 路线还没有被这些文献对照自动证明新颖或有效**：需写出可见信息集和兼容世界/允许决策集合的定义；避免把隐藏作者意图当唯一规范 gold；明确问题回答是否改变 world、约束还是知识；比较不问、总问、保守拒绝、规则 oracle 及适当模型基线；实际 rollout 及任务/风险/提问成本缺一不可。这里至少 AM-Bench、EffectWorld、Implicit Intelligence、Sapien、ATLAS、PRefine 提供直接或相邻反证，CGAP、LogiSafetyBench、CIRCE、ExecutionFirst 进一步限定保证范围和生成逻辑。

**【全文事实范围】**上述 15 篇在本地全文中未发现“与本项目拟议的全部配置完全相同”的系统，不意味着全领域无此组合；不能把未搜索到当创新证据，也不能以摘要/文件名相似度代替机制对照。只有本次列出的具体正证据和范围限制可以用于主报告。
