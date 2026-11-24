# CCF-B 可投性审计：七篇近邻原文与概念边界

日期：2026-11-24。范围：本报告是总审计的文献和概念证据附件；不替代 v5 指标复算、v6 代码审计或实际 GPU 结果。全文阅读了七篇本地原文提取文本（含附录、参考文献，共 17,781 行）、v6 设计和历史 CCFA 评估。未改动冻结数据、指标或 `reports/v5_*`。文献事实取自仓库中的全文版本；没有在本次子审计中重新联网核对其发表状态，不把预印本称为已录用论文。

## 1. 可守结论

当前最有希望形成可送审论文的主线是：**在受控的逐请求参数约束任务中，用 E/I 等价对和 N 近似对照区分正确恢复、过度施加约束与执行成功，并实证揭示小模型训练收益、OOD 不稳定性及编译记录和执行结果之间的脱节。** 这个主线允许 H2 失败；需要可检验的问题和完整证据闭环，不要求小模型全面打败强模型。

v6 新增 composition 留出、严格解析和三通道 N 误报，是实验严谨性的必要补充，但本身不证明新编译器架构、新训练算法或普适的组合泛化。typed representation、证据片段、参数级检查、双成功指标、成对变体、可执行合成任务、小模型 LoRA 和局部修复，各自已有近邻。新颖性必须落在**明确的新问题、受控对照的作用和由此能得到的独特诊断结论**，而不能只列组件清单。

CCF-B 是场所分级，没有本项目统一的 4.3 分送审门槛。历史 4.18/4.28 是内部概念评价，不能当成投稿准备度或录用概率。本文也不重新生成一个伪精确概念总分。

## 2. 七篇原文对照

以下行号均指第 7 节登记的本地全文 txt，包含提取页分隔行。

| 工作 | 实际任务和主要指标 | 与本项目重合 | 本项目仍可守的差异及必须补证据 |
|---|---|---|---|
| CGAP | 工具目录编译成规划域，LLM 将请求编译成 goals/requirements，执行时补实体调用；测端到端成功、工具调用等。requirements 已含 entity/time/scope、active/cancelled 和证据片段（L424–437）；正式保证以 R1–R3 等条件和已编译域为限（L629–675）。 | typed 编译、证据、规划/语义验证分离、参数来源、planner 交叉替换都不是空白。其固定其他部件更换 planner 的分析见 L848–956，provenance/verifier 消融见 L958–964。 | CGAP 的域谓词由应用人工给出（L354–368）；ConsDAG 可强调训练的小模型逐请求恢复参数约束，以及 E/I/N 的受控识别问题。必须证明 E/I 可恢复、N 不应误施加、字段错误如何影响具体 consumer。仅输出 evidence/scope 不构成因果增益。 |
| LogiSafetyBench | 规章到 LTL finite-trace oracle，逻辑引导合成、隐藏安全步骤；240 个人工核查任务；模型仍看到原规章、工具 schema、masked query（L104–146、L741–747）。主指标 safe success pass@1（L1040–1046），completion/compliance 分开（L609–623）。 | 隐式安全指令、合成、goal 与 safety 双评价、人工核查已有。 | 原文局限明确只处理 API 时序、不能细查 safe amount 等参数（L1291–1307）。本项目的请求内可恢复线索、参数级约束、N 豁免/他方规则近似对照是可区分部分；不要泛称“首个隐式合规基准”。 |
| AM-Bench | 48 基任务，每个 Full 加 goal/context/constraint 各 ambiguous/missing，共七种信息条件；5 models × 4 harness × 3 repeats；Completion、Compliance、Success=二者乘积（L210–244）。 | 固定意图的成对信息变体，完成与遵守的区分，重复结果稳定性问题已有。 | AM-Bench 的 missing/ambiguous 条件可缺少完成意图所需信息；ConsDAG 的 I 应能仅由可见请求恢复，并有 E/I 同语义验证。N 是相反/豁免/无约束对照，不能与 E/I 一起叫“三种等价表达”。AM-Bench 澄清收益是 matched Full counterfactual estimate，并非真实回答后续交互（L1840–1866）。 |
| EffectWorld | effect-typed 可执行工具环境、replay verifier、optimizer 负例；LoRA 与负例目标；任务成功含目标、答案事实、无 collateral、effect-safe（L439–457）；hard/domain 留出（L460–497）。 | 小模型训练 + 可执行约束 + 反事实负例 + OOD 组合已有；同正例同训练步控制见 L614–616。 | 本项目可以聚焦逐请求编译的恢复/过约束分离，而不是声称首个小模型可执行安全任务。EffectWorld 也指出 BFCL 不可解析输出可被计作 decline（L1389–1395、L1445–1448），因此 v6 fail-closed 修复应作为必要测量修正，不宣称首次发现。 |
| LIFT | synthetic drafting 中的 scoped constraints，既测主内容又测形式遵守；固定 topic/outline/content 变化 scope/density（L214–241、L295–307）；judge 人工验证 scoped macro-F1 0.73（L1482–1575）。 | scope、多约束组合、配对干预和内容/遵守分测已有；它实际检验 scope 对 judge 的作用。 | LIFT 是生成满足约束的文档，ConsDAG 是生成供执行器消费的约束；前者没有全局一致性 verifier（L1117–1120）。本项目 witness 和逐条必要性有区分价值，但必须说明它们减少了何种评估歧义，不能仅罗列生成检查。 |
| CIRCE | 从题目抽 CIR，再由约束图预测目标模型答对概率；核心指标 Bernoulli NLL、AUROC 和 grouped CV，不是工具安全（L487–504）。格式/语义验证分开，三类自动 checker、其余四类各 20 条人工检查（L945–1017、L1685–1706）。 | 约束中间表示、可编译不等于语义正确、共享结构与后续模型分离已有。 | CIRCE 的边界是输入中已有约束，不覆盖把推断约束作为解题的一部分（L1077–1085）；本项目可以研究可恢复 I，但需独立恢复性审计。CIRCE 是 `2610.41089`，不能误引为 SCA。 |
| SCA | 从 API 文档和训练执行轨迹挖全局工具约束，用 SMT 检查，warning 或唯一解 repair；测 call-error precision/recall/F1、task success 和 cost（L583–607、L641–706）。 | 参数约束、自动修复、可执行规则、faithful 与 validity 分测、误报造成成功率损失都有实证（L1735–1769、L1877–1890）。 | SCA 明确规则是跨未来请求复用的 global invariant，禁止 prompt-specific literals（L1559–1577、L1622–1628）。本项目逐请求参数约束与 E/I/N 可恢复性有不同研究对象。不能将“symbolic constraints + repair”当本项目新算法。SCA 是 `2610.25552`。 |

补充边界：CGAP 的字符 offset/类型检查不保证请求语义，SCA 的形式 faithful 不等于规则合理有效，EffectWorld 的 replay 正确不意味着真实用户确认被理解。这些都支持本项目把结构正确、字段正确、约束语义和执行成功分列；也说明这种区分的原则本身并非无人讨论。

## 3. 4.18 / 4.28 到 4.3：概念修订与实验补证必须分开

已核读实际规则：

- `literature/ccfa_skills_v0.12.1/ccf-idea-reviewer/references/rubric.md` L3、L37 明确：实验、基线、消融、可复现和投稿完整性不在默认概念评分内，缺实验不能降低 idea 分。L9–14 六维权重为问题 20、近邻新颖性 25、概念洞察 20、机制逻辑 20、组件必要性 10、受众契合 5。
- 同目录 `calibration.md` L3、L9–14、L30 明确：4.3 是 `accept-to-develop`，不等于录用或投稿准备度；缺实验不构成覆写概念判断的理由。
- `reports/ccfa_v5_assessment_20261123.md` L10 只保留 4.13/4.18/4.28 聚合数，本次未发现该报告中的六维子分和逐条扣分依据。不能据聚合数反推“补某实验必加 0.02/0.12”。同一规则下应先写修订后的概念和关切 ID，再由同口径复评；不是给历史分机械加分。

### ② 交叉干预分析（历史 4.18）

**概念上缺的不是一个更大提升数字，而是独特、可证伪的分解问题。** “修复比重排好”已被 SCA、CGAP 等相邻思路覆盖。应明确：在同一可行候选域、同一调用/编辑预算下，失败由请求解释误差还是计划搜索不足导致；什么条件下换 gold compiler 能恢复，什么条件下换 planner 能恢复，二者交互又表示什么。需定义 oracle 可达上限、不可恢复失败和交互项，避免把不同搜索空间的收益误当成编译因果收益。

投稿证据上应补：gold/predicted compiler × fixed/rerank/repair planner 的交叉表；同任务、同候选集合和编辑预算；每一格的成本、失败类型、配对差异和 seed 敏感性。已有预测可以 CPU 重放的部分无需重训。历史报告 L30 的 682/1400→1144/1400、+33.0pp 只是本次引用的历史结果；本子审计未重新核它的原始逐题预测。旧 GRPO `+1/0/-1`（历史报告 L32）不支持成功新算法，应保留为负结果，不能被 v6 换数据掩盖。

### ③ 可执行配对基准（历史 4.28）

**概念上需证明三个条件各自解决哪一种现有基准混淆。** E/I 控制请求含义而改变表达；N 控制词汇/任务外观而改变约束是否成立。明确 I 是“可由当前输入恢复”，N 是“有理由不施加”，并界定 infeasible、ambiguous、外部常识与合法豁免。说明逐条必要性和 witness 为什么是识别该问题所需，哪些字段只有审计作用，哪个可证伪发现是其他近邻不能直接回答的。

投稿证据上最缺的是独立双人盲审和真实模型结果：两名标注者对同 250 条独立判断后仲裁，按设计检验 raw agreement 与 adjudicated compatibility；分别披露 I 恢复率、N 子类型误施加、歧义样本和修订历史。强模型复核可补充，不能替代 v6 已承诺的两名人类。验证器 PASS 证明生成工件自洽，不证明人能恢复语义。接着需要三 seed 的 composition 结果和逐臂分析，才能证明对照设计有诊断价值。

两者的实验都提高证据可信度和投稿准备度；**它们不自动提高概念分**。如果概念只是重述已有组件，即使跑满结果仍可能维持 revise；如果问题和机制已修订明确，也不能因 GPU 尚未运行而按当前 rubric 直接扣概念分。

## 4. H2 与 composition 留出的保守判断

### H2：v6 不能“挽救”已失败的 v5 命题

v5 与 v6 是不同数据/评估协议。v5 已完成 H2 结论必须保留；不能把后续新分布的成功写成原失败翻案。v6 可以检验一个新的、预先指定 split 和比较协议的 H2，但必须在 v6 同数据、同 evaluator、同模型/API 版本和固定提示预算下重跑强基线，不能拿 v5 DeepSeek 的 99% 数字与 v6 训练结果直接比较。

v6 没有已知的、专门针对 tool-HO 跨训练 seed 崩落的训练改进。把 fail-open 改成 fail-closed 会使原本由解析失败“获益”的预测失去虚假成功；这个修复本身不产生新的模型能力。增加 composition 留出也不会使旧 tool-HO 更稳。因此在完整结果前，**全 split 的 −3pp 非劣效应按低把握目标规划**，不能将其设为论文能否成立的唯一条件。

逐 split 的配对下置信界必须满足预先规定的 −3pp 条件；高平均值、单个最优 seed、仅 dev 通过或将 split 合并，都不能替代该判定。对任务组 bootstrap 时固定三个训练 seed，只量化当前 seed 集合下任务抽样不确定性，不是训练 seed 总体置信区间。若要成本—效果主张，应给实测延迟/吞吐/显存/调用或 token 成本，并清楚保留质量差距；不能从模型小直接推断全部成本占优。

### composition 的 seed 方差不能预先承诺小于 tool-HO

有减小方差的理由：使用训练工具世界和训练措辞，减少名称和词汇分布偏移。有增大方差的理由：唯一未见的 `privacy + tool_auth` 类型对要求正确结合两个约束；合取成功由薄弱环节决定；删除其他 split 中包含该类型对的超集会同时改变约束基数和可行任务分布；端到端二元成功阈值可能放大少数系统性漏编译。

因此目前无法由 v5 tool-HO 数字校准 composition 的标准差。保守资源/判胜规划应将其当作**同量级、并允许更大方差的风险**，而不是先假定更稳。这里不是断言其期望方差必然更大。即使三个 seed 稳定，也只支持该固定留出类型对和生成分布，不能外推到任意组合。只有一个类型对时，它是明确的组合留出探针，仍不是多种独立组合层面的泛化证明。

## 5. 不用 GPU 的优先补证与 GPU 证据边界

以下成本为计划估计，成功概率指“在该工作量内获得完整、可如实报告的证据”，不指假设获胜、4.3 过线或论文录用；是主观规划范围，未经历史频率校准。现有缓存完整性和标注者可用性会改变估计。

| 优先级 | 工作 | 估计成本 | 完成证据的规划概率 | 对投稿的作用 |
|---|---|---|---|---|
| P0，无 GPU | 两名独立标注者完成同一 250 条，再仲裁并发布误差清单 | 每人每条 2–4 分钟，合计约 17–33 人时，加 2–4 人时仲裁 | 人员到位后 80%–95%；语义兼容率能否超过 90% 尚不可估 | 解决“生成标签自洽但 I/N 不可恢复”的硬缺口。若未过，须如实限定或修订数据并重冻结，不能标作通过。 |
| P0，无 GPU | claim—evidence 对照、七近邻差异和概念重写 | 4–8 人时 | 90%–98% 能形成可核查版本；新颖性复评过线不保证 | 将新架构/新算法过度主张收窄为配对基准与诊断贡献。 |
| P0，无 GPU | 对现存预测做字段 mutation、字段错误 × faithful 四象限、N 三通道和子类型表 | 2–6 人时；CPU 分钟到数小时，取决于缓存规模 | 缓存齐全时 90%–98% | 不把 strict/core 差距藏在执行高分后；scope/state/severity/evidence 未被消费时明确只测记录质量。 |
| P1，无 GPU 为主 | 交叉 compiler/planner 重放和可达上限分析 | 4–12 人时；CPU 数小时，需核实可重放缓存 | 75%–90% | 支撑②的分析型定位。若需新 LLM planner 调用，另计 API 费用，不以假缓存冒充。 |
| P0，需本地 GPU 推理/训练 | v6 预定模型/seed 完整实验和同底座零样本 | 由总审计依据历史日志和实际队列核算，全部受 30 GPU 小时硬限 | 本附件不虚构 GPU 完工概率 | 没有实际完整结果，不能声称 v6 H1/H2 或 composition 成立。不得用 smoke/缩小实验补主表。 |
| P0，不占本地 GPU | v6 同协议 DeepSeek PE 与其他声明的 API 对照、缓存/请求记录 | API 计费和 wall time 由实际请求长度、限流、缓存命中决定；不可从样本数伪造费用 | 账户/服务可用时工程完成通常高；指标达标未知 | 为 H2 提供同版本比较。应明确系统比较含训练和示例预算差异。 |
| P1，无 GPU | 最终数据声明、匿名化、许可证、文献元信息、目标 venue 范围/篇幅核对 | 4–8 人时 | 90%–98% | 可送审的稿件/工件要求；CCF-B 类别本身不替代具体 venue 要求。 |

不建议在 30 小时内追加无预先定义价值的奖励训练或无限扫 seed。当前必须保全既定三 seed 和 honest failure reporting；若预算使矩阵不完整，应标 incomplete，而不是选择完成且较好的 seed 发表为“三 seed”。

## 6. 特别容易写错的六点

1. `E/I` 等价不推出 `E/I/N` 等价；N 的作用是受控近似对照。
2. witness/necessity/verifier PASS 不推出自然语言 gold 正确或人能恢复 I。
3. strict F1、core F1、所有记录字段正确率、faithful execution 不是同一量；不被 executor 消费的字段不能宣称有执行因果收益。
4. 名称级 tool-HO、结构级 struct-HO、单类型对 composition-HO 不能互换名称；composition 过滤带来的联合分布改变应公开。
5. 三次推理重复、任务 bootstrap、训练 seed 方差不是同一种不确定性。近邻的低推理 sd 不能为本项目训练方差背书。
6. 负结果不等于不可投稿；“H2 失败但测量协议严谨且揭示可解释边界”可以形成可审稿论证。只补工程检查、没有独特研究问题，也不会自动达到该标准。

## 7. 全文阅读登记

已逐行阅读，截断输出部分已分块补齐；行数按 PowerShell UTF-8 `Get-Content` 统计。

| 文献 | 本地路径 | 行数 | SHA-256 |
|---|---|---:|---|
| CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | 2930 | `6D427AA7BCAA2464632C280A3931F3BEF96BF959F2E73609EEF0E430F092CEAF` |
| LogiSafetyBench | `literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt` | 1552 | `B67CFC4F2FEF4F773F8B2A824AD8EB7968C740CB108059FFB94E7D91E362A365` |
| AM-Bench | `literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt` | 3806 | `8558ADCCDCCD0F567EE6E2E42C775F92CBF37BC36AE3F5D832A9DC8927564B6E` |
| EffectWorld | `literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt` | 2794 | `085F416A65C04DAADC71BE5A00A475F267A52811F52CB2DB0C8F804039E43C15` |
| LIFT | `literature/extracted/library/03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt` | 2349 | `9871502BB93DC7F171E6E335C88F04AB1568621ADED518CB4821A2C31A55FF05` |
| CIRCE | `literature/extracted/library/01_constraint_compiler/2610.41089_CIRCE/2610.41089_CIRCE_fulltext.txt` | 2235 | `1CE080A2E6B580E34C776105502083236F0AEEBE4546BD2E31DD39A312C4DA78` |
| SCA | `literature/extracted/library/01_constraint_compiler/2610.25552_SCA/2610.25552_SCA_fulltext.txt` | 2115 | `F003D9A243A9D8D9D627556150E7C5754167E1190835D0CC2DF53181F9E5E120` |

另全文读 `reports/design_v6_ccfb.md` 74 行、`reports/ccfa_v5_assessment_20261123.md` 91 行，以及 rubric 45 行和 calibration 36 行。设计的运行精度等工程文字在同次任务中由其他子任务修订，本文不把阅读时旧精度规则当成当前应执行方案；所有新实验遵守用户指定 bf16。
