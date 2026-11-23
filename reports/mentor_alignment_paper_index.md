# 66 篇文献的实验设计索引

用途：帮助选择 ConsDAG 的对照，而非宣告首创。第一列为归档身份和原文入口；行号是本地全文中的回查点，最后一列是我们建议借用或防止误用的做法，不是该论文对 ConsDAG 的结论。保留了少数低相关对照以披露范围。本文在既有逐篇审计之上核读实验相关段落，没有逐页重读所有附录。

| 论文与原文 | 本地行 | 实验启示 |
|---|---:|---|
| [2511.10037_BeyondReAct](../literature/extracted/library/00_base/2511.10037_BeyondReAct/2511.10037_BeyondReAct_fulltext.txt) | 325 | 结构错误分级、边 F1、完全匹配。不要把原奖励写成已有用户合规奖励；用作 DAG 实例和结构参照。 |
| [2509.25586_ATLAS](../literature/extracted/library/01_constraint_compiler/2509.25586_ATLAS/2509.25586_ATLAS_fulltext.txt) | 804 | 实验从沙箱转到多轮实用设置；显式/隐式约束管理已有先例，强提示基线要保留。 |
| [2510.08992_ConstraintsOfThought](../literature/extracted/library/01_constraint_compiler/2510.08992_ConstraintsOfThought/2510.08992_ConstraintsOfThought_fulltext.txt) | 667 | 主观透明度和任务成绩独立测；不能让“输出证据”代替证据是否有用的验证。 |
| [2602.20424_ImplicitIntelligence](../literature/extracted/library/01_constraint_compiler/2602.20424_ImplicitIntelligence/2602.20424_ImplicitIntelligence_fulltext.txt) | 506 | 跨场景并报告分类表现；隐式任务在不同语境中的成功率不应只取总体均值。 |
| [2604.17886_PRefine](../literature/extracted/library/01_constraint_compiler/2604.17886_PRefine/2604.17886_PRefine_fulltext.txt) | 3040 | 用多名标注者的一致性检验偏好解释；借用协议来审隐式线索是否唯一可恢复。 |
| [2606.05622_AdaPlanBench](../literature/extracted/library/01_constraint_compiler/2606.05622_AdaPlanBench/2606.05622_AdaPlanBench_fulltext.txt) | 980 | 对错误计划做反馈修正分析；把读错约束和计划无法履行分开复核。 |
| [2607.04854_CARL](../literature/extracted/library/01_constraint_compiler/2607.04854_CARL/2607.04854_CARL_fulltext.txt) | 1003 | 在不同规划任务上将微调与约束关注度联系；这是 planner 内训练的对照，不能写成没人训练约束感知。 |
| [2608.19861_PolicyGuide](../literature/extracted/library/01_constraint_compiler/2608.19861_PolicyGuide/2608.19861_PolicyGuide_fulltext.txt) | 793 | RAW 和 SELF 分别改变策略表示和外部跟踪；不要同时换输入、执行器和评分器。 |
| [2610.00797_Sapien](../literature/extracted/library/01_constraint_compiler/2610.00797_Sapien/2610.00797_Sapien_fulltext.txt) | 893 | 同一方法跨模型评估，昂贵模型可用固定小子集；逐请求生成可执行策略不是空白。 |
| [2610.11030_NOMOS](../literature/extracted/library/01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt) | 1305 | 以任务做配对区间；区分策略编译和执行时开销。 |
| [2610.23190_LangNCO](../literature/extracted/library/01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt) | 904 | 分别看约束可行性与求解结果；能执行不保证原意解析正确。 |
| [2610.25552_SCA](../literature/extracted/library/01_constraint_compiler/2610.25552_SCA/2610.25552_SCA_fulltext.txt) | 689 | 以同一任务比较不使用约束与不同使用方式；约束来源是 API 文档，不能等同用户意图。 |
| [2610.36570_CASEL](../literature/extracted/library/01_constraint_compiler/2610.36570_CASEL/2610.36570_CASEL_fulltext.txt) | 36 | 仿真中的行动与不确定性决策；模拟干预不能写成真实安全成效。 |
| [2610.41040_CGAP](../literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt) | 848 | 把搜索替换为接收相同规划问题的 LLM；是检验独立于特定 planner 的直接方法先例。 |
| [2610.41089_CIRCE](../literature/extracted/library/01_constraint_compiler/2610.41089_CIRCE/2610.41089_CIRCE_fulltext.txt) | 732 | 难度预测有模型依赖，报告哪类切分失效；不把代理指标当任务成绩。 |
| [2611.09364_SafeOrchestrate](../literature/extracted/library/01_constraint_compiler/2611.09364_SafeOrchestrate/2611.09364_SafeOrchestrate_fulltext.txt) | 589 | 运行时仲裁与直接执行对比；只作为运行时约束基线，勿与训练收益混报。 |
| [2602.05863_ConstrainedGRPO](../literature/extracted/library/02_objective_factorization/2602.05863_ConstrainedGRPO/2602.05863_ConstrainedGRPO_fulltext.txt) | 925 | 多目标优化与优势标量化的基线；比较前检查组内标准化是否使奖励等价。 |
| [2603.01620_ToolRLA](../literature/extracted/library/02_objective_factorization/2603.01620_ToolRLA/2603.01620_ToolRLA_fulltext.txt) | 572 | 同时报完成率和工具调用错误；比较加法信号时也保留失败任务。 |
| [2603.25111_SEVerA](../literature/extracted/library/02_objective_factorization/2603.25111_SEVerA/2603.25111_SEVerA_fulltext.txt) | 1707 | 有拒绝原因反馈与无状态重采样对照；形式合同已给定不代表解决了自然语言发现。 |
| [2605.08327_InteractiveCritiqueRevision](../literature/extracted/library/02_objective_factorization/2605.08327_InteractiveCritiqueRevision/2605.08327_InteractiveCritiqueRevision_fulltext.txt) | 606 | 将整体成绩与决策单元变化分开；可借来报告“修对/改错”的流向。 |
| [2605.23382_PARPO](../literature/extracted/library/02_objective_factorization/2605.23382_PARPO/2605.23382_PARPO_fulltext.txt) | 1348 | 并排报告训练奖励及验证成功，奖励上涨本身非方法胜出。 |
| [2607.02599_AgentLTL](../literature/extracted/library/02_objective_factorization/2607.02599_AgentLTL/2607.02599_AgentLTL_fulltext.txt) | 696 | 比较默认与严格 grounding 的提示；提醒固定工具目录和可用信息。 |
| [2607.07435_RLVP](../literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt) | 859 | 区分代理任务和真实部署；已有逐动作罚，贡献不能只写粒度更细。 |
| [2607.22649_STAIF](../literature/extracted/library/02_objective_factorization/2607.22649_STAIF/2607.22649_STAIF_fulltext.txt) | 960 | 同报指令级与整条请求级、严格和宽松评价；局部对不等于约束全部满足。 |
| [2607.29246_DontMixRewards](../literature/extracted/library/02_objective_factorization/2607.29246_DontMixRewards/2607.29246_DontMixRewards_fulltext.txt) | 1055 | 看权重改变时各分量怎样变化；不要把平均分稳定误读成无代价。 |
| [2609.00213_AggregationRewardHacking](../literature/extracted/library/02_objective_factorization/2609.00213_AggregationRewardHacking/2609.00213_AggregationRewardHacking_fulltext.txt) | 1396 | 直接度量走捷径的轨迹比例；抗刷分需要独立于训练奖励的判据。 |
| [2609.27421_CounterfactualConstraintDistill](../literature/extracted/library/02_objective_factorization/2609.27421_CounterfactualConstraintDistill/2609.27421_CounterfactualConstraintDistill_fulltext.txt) | 525 | 保留普通蒸馏与针对约束的变体；避免把额外教师信息误判为归因增益。 |
| [2609.39154_DAGent](../literature/extracted/library/02_objective_factorization/2609.39154_DAGent/2609.39154_DAGent_fulltext.txt) | 553 | 模型共享检索后端并另核每任务开销；节点级分配本身非新颖。 |
| [2610.09219_CM-DPO](../literature/extracted/library/02_objective_factorization/2610.09219_CM-DPO/2610.09219_CM-DPO_fulltext.txt) | 623 | 同底座 SFT 等训练对照与强模型提示分列；不将两种比较混成一个主张。 |
| [2610.19525_RewardHackingVerifiableIF](../literature/extracted/library/02_objective_factorization/2610.19525_RewardHackingVerifiableIF/2610.19525_RewardHackingVerifiableIF_fulltext.txt) | 1299 | 逐步增加约束，同时报全部满足和平均满足；适合解释多约束失败。 |
| [2610.21404_TAG](../literature/extracted/library/02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt) | 890 | 训练探针和留出题参与选锚；不能把随意定义的门称为 TAG 忠实复现。 |
| [2611.12865_ShortcutsBoundaries](../literature/extracted/library/02_objective_factorization/2611.12865_ShortcutsBoundaries/2611.12865_ShortcutsBoundaries_fulltext.txt) | 769 | 新措辞、新授权上下文、新机制分测；只有独立判据判定违规，才能评价行为走捷径。 |
| [2611.16304_StateAlign](../literature/extracted/library/02_objective_factorization/2611.16304_StateAlign/2611.16304_StateAlign_fulltext.txt) | 325 | 成对改变任务状态再比较行动；可借来测输入改动是否应改变约束。 |
| [2611.17880_SOTERIA](../literature/extracted/library/02_objective_factorization/2611.17880_SOTERIA/2611.17880_SOTERIA_fulltext.txt) | 474 | 同时比较原始效用和合规后的成功；推理期方法应和训练方法区分。 |
| [2505.19030_RECAST](../literature/extracted/library/03_paired_benchmark/2505.19030_RECAST/2505.19030_RECAST_fulltext.txt) | 3312 | 人工验证生成的指令；文本指令数据不等同工具执行任务。 |
| [2603.03205_MOSAIC](../literature/extracted/library/03_paired_benchmark/2603.03205_MOSAIC/2603.03205_MOSAIC_fulltext.txt) | 1082 | 区分不加选择的拒绝和真正安全的决策；N 臂与任务完成不能省略。 |
| [2605.17558_Firefly](../literature/extracted/library/03_paired_benchmark/2605.17558_Firefly/2605.17558_Firefly_fulltext.txt) | 531 | 小模型与底座、大模型同条件比较，另有域外测试；可部署性不能靠一个域内分数证明。 |
| [2606.21140_MatchingMatters](../literature/extracted/library/03_paired_benchmark/2606.21140_MatchingMatters/2606.21140_MatchingMatters_fulltext.txt) | 877 | 按任务配对 bootstrap；同组改写不能当成独立样本。 |
| [2607.03957_NormWorldsCF](../literature/extracted/library/03_paired_benchmark/2607.03957_NormWorldsCF/2607.03957_NormWorldsCF_fulltext.txt) | 364 | 任务按反事实家族切分，不让同一源实例跨集合。 |
| [2607.29175_ExecutionFirst](../literature/extracted/library/03_paired_benchmark/2607.29175_ExecutionFirst/2607.29175_ExecutionFirst_fulltext.txt) | 720 | 执行先行、从多维度评价输出；语言流畅不能证明轨迹可行。 |
| [2609.09072_ToolLoop](../literature/extracted/library/03_paired_benchmark/2609.09072_ToolLoop/2609.09072_ToolLoop_fulltext.txt) | 493 | 用两个外部基准补合成训练评估；迁移应事先限定可映射的子任务。 |
| [2610.16859_ANCHOR](../literature/extracted/library/03_paired_benchmark/2610.16859_ANCHOR/2610.16859_ANCHOR_fulltext.txt) | 962 | 原子约束与约束关系分别计分；既报局部错误，也报整题成功。 |
| [2610.18090_AM-Bench](../literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt) | 23 | 固定任务跨模型和执行框架，区分信息模糊与信息缺失；不能把“应澄清”标成 none。 |
| [2610.26359_DiscoveryProbabilityGraph](../literature/extracted/library/03_paired_benchmark/2610.26359_DiscoveryProbabilityGraph/2610.26359_DiscoveryProbabilityGraph_fulltext.txt) | 1064 | 对齐不同动作时长的真实成本；仅比较 rollout 次数不充分。 |
| [2610.28819_LIFT](../literature/extracted/library/03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt) | 758 | 把训练数据压平作为对照以隔离结构；E/I 配对价值也需要控制语料量。 |
| [2610.34634_AgentProofBench](../literature/extracted/library/03_paired_benchmark/2610.34634_AgentProofBench/2610.34634_AgentProofBench_fulltext.txt) | 19 | 相同指令下切换初始状态来测验证器能否复用；不要只在生成器原世界验回放。 |
| [2610.35981_EffectWorld](../literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt) | 1788 | 新任务类型与未见业务域分别留出；工具名替换不足以证明结构迁移。 |
| [2611.14925_ToolTurns](../literature/extracted/library/03_paired_benchmark/2611.14925_ToolTurns/2611.14925_ToolTurns_fulltext.txt) | 431 | 分别评估代理与模拟用户质量；隐式措辞是否成立需要独立验证。 |
| [2605.03327_TIDE](../literature/extracted/library/04_credit_assignment/2605.03327_TIDE/2605.03327_TIDE_fulltext.txt) | 839 | 独立留出题上跟踪探索与下游准确率，过程曲线不代替结果。 |
| [2609.12424_GranularityAdaptiveCredit](../literature/extracted/library/04_credit_assignment/2609.12424_GranularityAdaptiveCredit/2609.12424_GranularityAdaptiveCredit_fulltext.txt) | 431 | 固定预算、最佳点、最终点分开列；避免用最佳 checkpoint 与对手最终值比。 |
| [2610.00838_SHARPO](../literature/extracted/library/04_credit_assignment/2610.00838_SHARPO/2610.00838_SHARPO_fulltext.txt) | 397 | 固定训练步数、独立训练种子，对照整轨迹共享信用；适合②的小规模消融。 |
| [2610.29292_ContrastiveAttributionTopology](../literature/extracted/library/04_credit_assignment/2610.29292_ContrastiveAttributionTopology/2610.29292_ContrastiveAttributionTopology_fulltext.txt) | 421 | 固定短优化预算比较归因；避免额外搜索预算混进效果。 |
| [2409.16299_HyperAgent-SE](../literature/extracted/library/05_review_queue/2409.16299_HyperAgent-SE/2409.16299_HyperAgent-SE_fulltext.txt) | 604 | 分任务族评测；软件工程域不作①的直接对手。 |
| [2510.10611_HyperAgent-Hypergraph](../literature/extracted/library/05_review_queue/2510.10611_HyperAgent-Hypergraph/2510.10611_HyperAgent-Hypergraph_fulltext.txt) | 935 | 换两个底座检验架构效果；多代理通信不等于用户约束编译。 |
| [2510.24663_OrchDAG](../literature/extracted/library/05_review_queue/2510.24663_OrchDAG/2510.24663_OrchDAG_fulltext.txt) | 463 | 图距离与二值全匹配奖励对照；图结构分不替代用户约束检查。 |
| [2603.19461_HyperAgentsSurvey](../literature/extracted/library/05_review_queue/2603.19461_HyperAgentsSurvey/2603.19461_HyperAgentsSurvey_fulltext.txt) | 444 | 留出集性能与统计不确定性分开；不拿同名方法作已实现 DAG 约束的证据。 |
| [2601.08196_LogiSafetyBench](../literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt) | 732 | 功能与合规用不同判据；已有隐式合规工具基准，不宣称首创该题目。 |
| [2606.20023_LowerPrivileges](../literature/extracted/library/06_web_supplement_20261121/2606.20023_LowerPrivileges/2606.20023_LowerPrivileges_fulltext.txt) | 280 | 对请求不必要的权限单独计量；把过度阻拦与漏违规分别统计。 |
| [2606.22388_PlanBenchXL](../literature/extracted/library/06_web_supplement_20261121/2606.22388_PlanBenchXL/2606.22388_PlanBenchXL_fulltext.txt) | 1248 | 限制可接受解路径本身会改变评价；等价可行计划不应因与 witness 不同而全判错。 |
| [2606.28061_ToolPrivacyBench](../literature/extracted/library/06_web_supplement_20261121/2606.28061_ToolPrivacyBench/2606.28061_ToolPrivacyBench_fulltext.txt) | 14 | 按目的追踪工具间的数据流；可信案例要有明确数据类别、接收方和检查规则。 |
| [2608.24509_PeakBench](../literature/extracted/library/06_web_supplement_20261121/2608.24509_PeakBench/2608.24509-official.html) | § Decoupled Evaluation Protocol | 一组测依赖恢复，另一组固定已验证依赖只测调度；借来做金标约束注入。官方 HTML 已补齐。 |
| [2609.04629_SiLR](../literature/extracted/library/06_web_supplement_20261121/2609.04629_SiLR/2609.04629_SiLR_fulltext.txt) | 427 | 分别比较结构化准入、终局和标量门控；训练表现与恢复行为分开判断。 |
| [AgentGym-RL_2509.08755](../literature/extracted/papers/AgentGym-RL_2509.08755/AgentGym-RL_2509.08755_fulltext.txt) | 496 | 多环境验证 RL 框架稳定性；同一生成器多模板不是多环境。 |
| [ReAct_2210.03629](../literature/extracted/papers/ReAct_2210.03629/ReAct_2210.03629_fulltext.txt) | 574 | 在未见环境中改变示例提示做稳健性检查；用于提示基线，不是约束解析器。 |
| [rStar2-Agent_2508.20722](../literature/extracted/papers/rStar2-Agent_2508.20722/rStar2-Agent_2508.20722_fulltext.txt) | 1081 | 每题多次采样，报告每题平均而不是把采样视作独立任务。 |
| [ToolRL_2504.13958](../literature/extracted/papers/ToolRL_2504.13958/ToolRL_2504.13958_fulltext.txt) | 1398 | 未见工具接口语言检验迁移；同一环境内加模型尺寸不是接口迁移。 |
