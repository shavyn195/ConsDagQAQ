# 文献精读与设计复核审计（literature_audit_v4）

日期：2026-11-21 23:00 至 11-22 00:40 CST。执行人：Claude（会话 `b3f1c2a4-5d6e-4f7a-8b9c-0d1e2f3a4b5c`）。

范围：
- `literature/extracted/` 下全部 `*_fulltext.txt`，共 73 个文件；
- 本轮从 arXiv 下载入库的 7 篇补检索论文（`library/06_web_supplement_20261121/`）。

约束：
- 服务器 v4 队列运行期间，未改动 `src/`、`data/processed_v4/`、`scripts/run_e1_queue_v4.sh`；
- 服务器只执行了只读命令（cat/ls/grep/nvidia-smi）；
- 需要改代码的问题全部记入 §6 待修清单。

---

## 0. 方法与诚实声明

1. **上一轮的情况**：论文"精读"由 4 个子代理完成，主会话没有用 Read 打开过任何一篇；第 5 个检索子代理因 API 403 失败。因此上一版 `design_v4_ccfb.md` §2 的文献论断是**二手转述**，本轮全部重新核对。

2. **本轮读法**：
   - **深读 D（20 篇）**：设计文档 §2.2/§2.3 点名的 16 篇，加 LogiSafetyBench、ExecutionFirst、PolicyGuide、BeyondReAct。主会话用 Read 逐段读摘要、引言、方法、实验设置与主结果、limitations、结论，并用 Grep 定位后读上下文。
   - **抽节阅读 S（其余各篇）**：用 `outputs/_lit/sections.py` 抽出摘要、引言末段、方法首段、实验设置、主结果、limitations、结论，主会话逐篇阅读（抽取稿见 `outputs/_lit/g1.txt`–`g11.txt`）；抽取遗漏的节用 Grep 定位后补读。
   - 两种读法都**不是逐页通读**。每篇实际覆盖的章节见 §1 的"覆盖"列。

3. **引文纪律**：每条原文都用 `outputs/_lit/quotes.py` 在 fulltext 中逐条定位，并输出真实行号。结果：**116/116 条找到，0 条超过 40 词**（`outputs/_lit/quotes_verified.json`）。正文以 `Qn` 引用，原文与行号见附录 A。没有找到原文支撑的论断，标"无原文支撑"。

4. **重复与错装**：
   - `papers/ATLAS_2509.25586`、`papers/Beyond-ReAct_2511.10037`、`papers/RLVP_2607.07435` 与 library 中对应文件 **md5 相同**，各按 1 篇计。
   - `innovation1_audit/pdf/2607.04854` 与 `library/01/2607.04854_CARL` 是同一篇（都是 arXiv:2607.04854v1，只是 PDF 抽取不同）。
   - `papers/` 下有 **9 个目录错装**（按首页标题判断，Q91–Q99）。
   - 去重后，相关论文为 **60 篇本地 + 6 篇补检索 = 66 篇**（PeakBench 只读了 2 页，单列）。

5. **补检索的局限**：
   - PeakBench（2608.24509）的 PDF 字体损坏，只抽出 2 页，**只读了摘要与引言**。
   - PlanBench-XL 首次下载被截断，重下后全文 5,151 行，读了摘要、贡献、设置、结果与 limitations。

---

## 1. 逐篇清单

路径前缀统一为 `literature/extracted/`，完整路径见附录 A。

**覆盖**：D = 深读；S = 抽节阅读；T = 只核对标题。

**关系**：
- 威胁：占据我方某一创新点的核心组合；
- 可对照：应作为基线或对照臂；
- 可引用：范式或数据可借鉴；
- 无关。

①②③ 指我方三个创新点。

### 1.1 编译 / 约束抽取组（library/00_base、01_constraint_compiler）

| # | 论文 | 覆盖 | 任务域 | 数据/规模 | 主指标 | 基线 | 统计 | held-out | 关系 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | BeyondReAct 2511.10037 | D（无 limitations 节） | query→工具 DAG | ComplexTool-Plan：DeepSeek-V3 生成 workflow 再逆向生成 query；SFT 3,000 条，RL 787 条（8:2）；外加 StableToolBench | 节点/边 P/R/F1、DAG EM、SoPR | GPT-4o、Claude-3.7、DeepSeek-V3、Ernie-X1 prompt；ReAct、DFSDT、LLMCompiler | 端到端 3 次平均 | StableToolBench 的 Inst/Tool/Cat 分层 | ① 邻近（训练的是 planner）；② 可对照（fail-fast 罚） | Q1 Q2；自建合成测试上 SFT-0.6B 的 EM 0.671 高于 GPT-4o 的 0.635（主表 L542–548/L510–517） |
| 2 | ATLAS 2509.25586 | S + L165–172、L640–676、L910–925 | 旅行规划 | TravelPlanner val 180 / test 1000 | micro/macro 约束通过、Final pass | ReAct、Reflexion、EvoAgent、PMC（工具调用上限 120） | 无 | 无 | ① 可对照（显式/隐式二分 + scope，纯 prompt） | Q3 Q4 |
| 3 | Constraints-of-Thought 2510.08992 | S | MCTS 约束剪枝 | Risk CI 1,053 / CADPrompt 200 / GSM8K | EMD/HD/Acc | Direct、CoT、ToT、LLMFP | 用户研究 p<0.05 | 无 | ① 可引用（抽取误差会传给下游） | Q5 |
| 4 | Implicit Intelligence 2602.20424 | S + L323–397 | 隐式需求 agent 评测 | 205 场景 | SPR/NSS | 16 个模型 | ± | 无 | ③ 概念威胁（"隐式"定义不同） | Q6 Q7 |
| 5 | PRefine 2604.17886 | S | 跨会话偏好→工具参数 | MPT 4,695 | EXP/IMP-F1 | RAG、Mem0、LangMem | κ 人工验证 | 偏好迁移到未见函数 | ③ 可引用 | Q8 |
| 6 | AdaPlanBench 2606.05622 | S | 渐进披露约束的规划 | 307 任务 | Acc/VPR | 10 个 LLM | LLM judge + 部分人工 | 无 | ③ 邻近 | Q9 Q10 |
| 7 | CARL 2607.04854 | S | KL 约束感知 RL | BlocksWorld/TravelPlanner/T-Eval | Final pass/F1 | RFT、o1、R1 | 无 | 无 | ② 可对照（KL 臂） | Q11 |
| 8 | PolicyGuide 2608.19861 | D | 域 policy→workflow 图 | τ²-bench 三域 | Pass^k（n=4） | ReAct、PolicyGuard、FlowAgent、SELF/RAW | pooled paired | 无 | ① 邻近（域级，不训练） | Q12 Q13 |
| 9 | **Sapien 2610.00797** | S + L1408–1420 | **逐 prompt** 合成可执行工具调用策略 | AgentDojo 97、Toolathlon 108 | Utility/ASR | NoPolicy、AllowList | 未见 | 无 | **① 威胁**（上一轮漏列）：逐 query 编译为可执行对象；但使用现成 LLM，无 typed 约束，欠指定时不细化（L1409–1410） | Q14 |
| 10 | NOMOS 2610.11030 | D | 书面 policy 四遍编译为 gate | τ²-bench、AgentDojo | 违规率、pass^k、ASR | 手写、前沿编译、PolicyGuard | 10k paired bootstrap | 自认无 | ① 邻近（编译器叙事；本机 26B 编译不显著劣于前沿） | Q15 Q16 Q17 Q116 |
| 11 | LangNCO 2610.23190 | S + L338–345、L604–629 | NL 约束→DSL 掩码（CVRP） | 300 实例 × 4 类 + 组合 | 可行率 | LLMCoSolver、GPT-5 | 未见 | 无 | ③ 可引用（构造时让参考解必违反） | Q18 Q19 Q113 |
| 12 | SCA 2610.25552 | S | 从 API 文档挖 SMT 规则 | AppWorld 417、τ² 60 | 检测 P/R/F1、成功率 | Init vs Refine | 3 runs | 留出 τ² 任务 | ① 邻近（环境级规则） | Q20 |
| 13 | CASEL 2610.36570 | S + L36–52 | 选择性执行/校准 | 纯仿真，20 seeds | 有害率、ECE | 不确定性门控 | Holm 校正 | 无 | E5 可引用（自认"Intervention effectiveness is assumed, not measured"） | Q21 |
| 14 | **CGAP 2610.41040** | D | 神经符号工具规划 | ToolSandbox 120 / CFB 250 / BFCL-MT 200 / τ²-retail 114 | milestone/success/call acc | 3 个 LLM 的 plain agent + 4 个附加基线 | 3 runs + 10k 配对 bootstrap | 无 | **① 威胁**：prompt 的 LLM 把请求解析为带 evidence span 的 operation，外加全局约束 Λt；但 Λt 无类型，授权/隐私留给应用 | Q22–Q25 Q114 |
| 15 | CIRCE 2610.41089 | S | 约束图→难度预测 | 7 个基准 × 200 | NLL/AUROC | 4 种 | grouped 5-fold | 分组 CV | ① 可引用（自认不覆盖需推断约束的问题） | Q26 |
| 16 | SafeOrchestrate 2611.09364 | S | NL 意图→SMT 门控（CPS） | 3 类仿真 | 动作准确率/MCP-ES | Vanilla | 未见 | 无 | ① 邻近（评测时约束集 C 为空） | Q27 |

### 1.2 目标分解 / RL 组（library/02_objective_factorization）

| # | 论文 | 覆盖 | 任务域 | 数据/规模 | 主指标 | 基线 | 统计 | held-out | 关系 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 17 | **Constrained GRPO 2602.05863** | D | GRPO 拉格朗日约束优化 | gridworld；NAVSIM-v2（Qwen2.5-VL-3B）；GSM8K 1.5–7B | EPDMS、违规率 | GDPO、PPO-Lag、线性标量化 | gridworld 5 seeds | NAVSIM held-out | **② 威胁/警示**（先标准化再加权；乘性硬门控信号稀疏） | Q28 Q29 |
| 18 | ToolRLA 2603.01620 | S | 金融工具 agent，SFT→GRPO→DPO | FA-Bench（内部）、ToolBench、API-Bank | TCR/TIER/VR | 加法 vs 乘法 | 单次 | 无 | ② 可对照（加法/否决臂） | Q30 |
| 19 | SEVerA 2603.25111 | S | 形式合同 + 回退 + GRPO | Dafny 两套、τ²-airline、GSM-Sym | Ver.&NoDiff、Vio. | Claude、DafnyBench | 未见 | held-out 输入 | ② 邻近（约束为给定规约） | Q31 |
| 20 | Interactive Critique-Revision 2605.08327 | S | 生成器/验证器博弈 RL | TaxCalcBench（80/20） | 行准确率 | GRPO/DAPO/GSPO | 未见 | 无 | ② 低 | Q32 |
| 21 | PARPO 2605.23382 | S | 个性化奖励解耦 RL | ETAPP、SJAgent | LLM 评分 | GRPO、SkillRL 等 | paired t | 无 | ② 低（"anchor"撞名） | Q33 |
| 22 | AgentLTL 2607.02599 | S | FO-LTL 规约用于守门 + 奖励 | 12 模板合成工具 | 合规分/Acc | 7 个零样本模型 | 2 seeds × 6 | 留出模板、别名 | ② 邻近（约束来自 gold 轨迹） | Q34 |
| 23 | **RLVP 2607.07435** | D | 结果奖励 + 逐动作可验证罚 | TerminalBench、miniF2F、SWE-smith、τ-bench | 成功率、violation-free | outcome-only、DAPO 等 | 3 或 5 seeds | 部分 | **② 威胁**；可引用（约束人工指定，自动发现是开放挑战） | Q35–Q40 Q115 |
| 24 | STAIF 2607.22649 | S | 软/硬约束分阶段训练 | StaInstruct 31k | IFEval 等 | SFT、DPO、VerIF | 单次 | 外部 | ② 低 | Q41 |
| 25 | PRISM 2607.29246 | S | 策略空间组合多奖励 | GPQA、BFCL-v3、HH-RLHF | Joint | GRPO-Sum/Product、GDPO | 未见 | 无 | ② 可对照 | Q42 |
| 26 | AMRP 2609.00213 | S | 多奖励自适应权重 | NuminaMath 10k 等 | Acc | Static、GDPO、PPO | 未见 | 外部 | ② 可引用 | Q43 |
| 27 | CC-OPD 2609.27421 | S | 逐约束反事实蒸馏 | HIR-16K | IF 分 | SFT、GRPO-IR/CR、OPD | 未见 | 外部 | ② 低 | Q44 |
| 28 | **DAGent 2609.39154**（NeurIPS'26） | D | 深度研究 DAG 多 agent | BrowseComp-Plus 680/150、GAIA 103、xbench 100 | Pass@1（LLM judge） | ReAct、Fold、Flash-Searcher、GRPO 等 | RL 3 seeds | 零样本迁移 | ② 邻近（拓扑信用分配的是结果奖励，不是约束罚） | Q45 Q46 |
| 29 | CM-DPO 2610.09219 | S | 严重度 margin DPO | TravelPlanner、NaturalPlan、PlanBench | PR/SR | GPT-4o、MAS、DPO | 未见 | OOD | ② 邻近（硬约束字典序） | Q47 |
| 30 | CALIF 2610.19525 | S | IF-RLVR 奖励 hacking | IFBench | 约束满足/回答质量 | IF-RLVR、judge | 3 次评测 | 外部 | ② 可引用 | Q48 |
| 31 | **TAG 2610.21404** | D | 多奖励聚合 hacking | Big-Math、DeepCoder-RT；Qwen3-1.7B/4B 等 | pass@4、both | 7 种聚合 | 无训练种子数，只给"±0.02" | held-out 题 | **② 威胁**（锚门控；静态权重不安全） | Q49–Q52 |
| 32 | Shortcuts & Boundaries 2611.12865 | S | RL 学到有利可图的违规 | >800 可执行实例 | certified violation、safe completion | Task vs Safety 训练 | bootstrap | 未见任务 | ② 可引用（二值罚已部分有效） | Q53 |
| 33 | StateAlign 2611.16304 | S | 状态对比 RL | 30k；BFCL v4 等 | Acc/幻觉率 | ToolRL、LoopTool | 评测 SD | 外部 | ② 低 | Q54 |
| 34 | SOTERIA 2611.17880 | S | 验证计划 + 运行时监视 | τ²、Toolathlon | Util→Succ、#Viol | NeMo 等 | 部分 5 runs | 无 | ② 邻近（推理期即可零违规） | Q55 |

### 1.3 基准组（library/03_paired_benchmark）

| # | 论文 | 覆盖 | 任务域 | 数据/规模 | 主指标 | 被测模型 | 统计 | held-out | 关系 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 35 | RECAST 2505.19030 | S | 多约束指令（文本） | 30K，Test 分 4 级 | HSR | 多个闭源/开源 + DVR | 未见 | 外部 | ③ 低（约束全显式） | Q56 |
| 36 | MOSAIC 2603.03205 | S | plan-check-refuse 安全 RL | Agent-SafetyBench 等 | Harm/ASR | GPT-4o/5、Qwen、Phi-4 | 未见 | OOD | ② 低 | Q57 |
| 37 | Firefly 2605.17558 | S + L1150 | MCP 数据合成 | 5,144 | pass@k | Claude 系、Qwen3-4B | χ² | 随机 | ③ 可引用（50+50 盲审） | Q58 |
| 38 | MatchingMatters 2606.21140 | S | LM–CLI 组合 | 80 任务 | AMS | 7 × 4 | 10k 配对 bootstrap | 描述变体 | ③ 可引用 | Q59 |
| 39 | NormWorlds-CF 2607.03957 | S | 求解器验证的配对世界 | 270 族 / 1,080 对 | 关系准确率 | Qwen3-1.7B/4B | 4B 3 seeds；McNemar | 按根族切分 | ③ 可引用 | Q60 Q61 |
| 40 | **ExecutionFirst 2607.29175** | D | 执行优先的轨迹合成 | 676 模板 / 7,761 条；test n=200 | mean±SE | Qwen3.5-4B/9B | SE | 按轨迹切分 | **③ 威胁（中）**：三档显式度作用于执行细节，不是约束；校验由同一 LLM 完成 | Q62 Q63 |
| 41 | ToolLoop 2609.09072 | S | 工具数据合成 | 11k | BFCL/ACEBench | 多模型 | 未见 | Isolate 去重 | ③ 可引用 | Q64 |
| 42 | ANCHOR 2610.16859 | S + L752 | 工程约束遵循 | 358 任务 | ACR/CCR/FCCR | 10 模型 × 2 scaffold | task bootstrap | 无 | ③ 可引用（5 人 + AC1） | Q65 Q66 |
| 43 | **AM-Bench 2610.18090** | D | 欠指定的目标/上下文/约束 | 48 × 7 = 336；20,160 runs | Completion/Compliance/Success | 5 模型 × 4 harness | population SD | 无 | **③ 威胁**：同任务约束的显式/模糊/缺失；但 KM 的 gold 不可从输入恢复，与我方 I/N 语义不同 | Q67–Q70 |
| 44 | DPG/HiddenCoop 2610.26359 | S | 隐藏合作（具身） | C-WAH、TDW-MAT | SR/EET | 4 种方法 | 未见 | 无 | ③ 低 | Q71 |
| 45 | **LIFT 2610.28819** | D | scoped 写作约束 | Bench 784 / Train 34,258 | 加权约束分 | 17 个模型 × 8 次 | 95% CI | MD5 切分 | **③ 威胁（中）**：合成 + 双渲染 + 训练集；约束全显式 | Q72–Q74 |
| 46 | AgentProofBench 2610.34634 | S | Web agent 可复用验证器 | 97 任务 | BA | DeepSeek 两款 | 区间 | 初始状态配对 | ③ 低（"witness"撞名） | Q75 |
| 47 | EffectWorld 2610.35981 | S + limitations | 效应类型工具世界 | 498/775/547 | 成功/违规 | ≤4B 模型 | 只做任务采样区间 | **未见的 commerce 域** | ③ 可引用（真正的结构外 held-out） | Q76 Q77 |
| 48 | ToolTurns 2611.14925 | S | 多轮欠指定对话 | 2,620 | 子任务/全对话成功 | 9 个模型 | 未见 | 无 | ③ 可引用（120 条盲审） | Q78 |

### 1.4 信用分配组与复核队列（library/04、05）

| # | 论文 | 覆盖 | 要点 | 统计 | 关系 | 证据 |
| --- | --- | --- | --- | --- | --- | --- |
| 49 | TIDE 2605.03327 | S | token 级优势；AIME | 3 训练 seeds + bootstrap | ② 低 | Q79 |
| 50 | GACA 2609.12424 | S | 粒度自适应信用；ALFWorld/WebShop | 只有评测 seed 的 SD（反例） | ② 低 | Q80 |
| 51 | SHARPO 2610.00838 | S | 段级后见重加权 | 3 runs | ② 低 | Q81 |
| 52 | CATS 2610.29292 | S | 拓扑搜索 + LLM 归因 | 3 seeds | ② 可引用（归因器能看到分数） | Q82 |
| 53 | HyperAgent-SE 2409.16299 | S | SE 多 agent | 未见 | 无关 | Q83 |
| 54 | HyperAgent-Hypergraph 2510.10611 | S | 超图通信 | 未见 | 无关 | Q84 |
| 55 | OrchDAG 2510.24663 | S | 多轮工具 DAG 合成；train 1800 / test 250 | 10 runs | ③ 低（自认未处理隐式依赖） | Q85 |
| 56 | HyperAgents/DGM-H 2603.19461（目录名写 Survey，实为方法论文） | S | 自改进 agent | 5 runs + bootstrap + Wilcoxon | 无关（统计做法可借） | Q86 |

### 1.5 papers/ 目录

| # | 目录 | 覆盖 | 判定 | 证据 |
| --- | --- | --- | --- | --- |
| 57 | AgentGym-RL_2509.08755 | S | 多环境 agent RL，Qwen2.5-3B/7B；② 低 | Q87 |
| 58 | ReAct_2210.03629 | S | 基线范式 | Q88 |
| 59 | rStar2-Agent_2508.20722 | S | GRPO 配置先例；② 低 | Q89 |
| 60 | ToolRL_2504.13958 | S | 工具 GRPO 奖励设计；② 可对照 | Q90 |
| — | ATLAS_2509.25586 / Beyond-ReAct_2511.10037 / RLVP_2607.07435 | — | 与 library 对应文件 md5 相同 | — |
| — | 9 个错装目录 | T | 首页标题与目录名无关（GraViti、Muckenhoupt 权重、K 介子、文学翻译、p-Laplace、最短唯一子串、ACE 知识编辑、线强度图、神经元移植） | Q91–Q99 |

### 1.6 补检索入库（library/06_web_supplement_20261121）

| # | 论文 | 覆盖 | 任务域 | 数据/规模 | 主指标 | 统计 | 关系 | 证据 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 61 | **LogiSafetyBench 2601.08196** | D | 法规隐式合规的工具调用 | 240 个人工验证任务，13 个 LLM | 功能预言 ∧ LTL 安全预言 | 作者三轮一致 | **③ 高威胁**（自称首个）。差异：隐式来源是系统提示中的**法规全文**；只有两种时序模板，**不含参数级约束**；无 N 对照；无训练集 | Q100–Q104 |
| 62 | ToolPrivacyBench 2606.28061 | S | 目的绑定隐私 | 2,150 | TaskSuccess/MT-POI/FOR | κ 抽样复标 | ③ 可对照 / 外部 OOD 候选（约束不从 query 抽取） | Q105–Q107 |
| 63 | SiLR 2609.04629 | S | 违规恢复准入 + GRPO 过程奖励 | Gym-ANM、CityLearn | 恢复率 | 16 seeds（表格实验） | ② 可引用（计数奖励坍塌） | Q108 |
| 64 | When Lower Privileges Suffice 2606.20023 | S | 最小权限工具选择 | 8 域 × 5 类风险 | OPUR@k | 未见 | ② 邻近（SFT→GRPO 升权罚） | Q109 Q110 |
| 65 | PlanBench-XL 2606.22388 | S | 大工具库规划 | 327 / 1,665 工具 | Acc | 未见 | ③ 低 | Q111 |
| 66 | PeakBench 2608.24509 | **只读了摘要与引言** | 资源感知调度 | — | — | — | 低 | Q112 |

---

## 2. 威胁矩阵（创新点 × 最近邻）

| 创新点 | 已被占据的部分（附原文） | 仍未被占据、我方可守的组合 | 必须拿出的证据 |
| --- | --- | --- | --- |
| ① 训练的证据绑定约束编译器 | 逐 query 解析成带 evidence span 的结构对象并喂给规划器（CGAP Q22 Q23）；逐 prompt 编译为可执行策略（Sapien Q14）；"编译器" + 本机编译（NOMOS Q15 Q17）；显式/隐式二分 + scope（ATLAS Q3 Q4）；训练 Qwen3 小模型做 DAG 规划、在自建合成集上胜过 GPT-4o（BeyondReAct Q1） | 读过的论文中，**没有一篇训练专用小模型、把逐 query 的用户约束编译成 typed 参数化约束对象**。上述最近邻要么用现成 LLM 做 prompt（CGAP/Sapien/NOMOS/PolicyGuide/ATLAS），要么编译的是域级书面 policy（NOMOS Q16、PolicyGuide Q12），要么约束无类型且把授权/隐私留给应用（CGAP Q25） | 同 schema 的**强模型 PE 对照**（CGAP/Sapien 式 prompt）；在 tpl_ho/tool_ho 上的 OOD 证据（BeyondReAct 的胜出只在自家合成分布内）；Sapien 式欠指定案例 |
| ② 约束锚定奖励分解 | 门控辅助信用（TAG Q49）；静态权重在 GRPO 下不安全（TAG Q50）；逐动作可验证罚 + 结果奖励（RLVP Q35 Q40）；先标准化再加权（Constrained GRPO Q28）；DAG 拓扑信用（DAGent Q45）；计数奖励坍塌（SiLR Q108）；升权罚（LowerPrivileges Q110） | 罚的来源是**学到的编译器输出**，而 RLVP 是人工指定（Q36）；外部可执行锚；漏检与误拦分开计价 | E2 未跑之前，**不得写成贡献**；每个组件需要单独消融，并加 GDPO/ScAdv 臂 |
| ③ E/I/N 配对可执行基准 | 隐式合规 + 可执行 + 形式预言 + 人工验证（LogiSafetyBench Q100–Q104，自称 first）；同任务约束的显式/模糊/缺失（AM-Bench Q67–Q69）；同一轨迹三档显式度（ExecutionFirst Q62）；合成 + 双渲染 + 训练集（LIFT Q72）；构造期让参考解违反约束（LangNCO Q18） | **参数级**约束（预算、时限、数据类），而 LogiSafetyBench 自认做不了（Q102）；隐式线索在 query 内且 gold 唯一可恢复，而 AM-Bench 的 KM 不可恢复（Q68 Q69）；N 近似干扰对照；带训练集 + 执行级刻度 | 不得声称"首个隐式约束工具基准"；正面对照 LogiSafetyBench；人工/oracle 可恢复性验证 |

---

## 3. 被证伪或需修正的论断

"来源"列指被核对的文档位置。

| # | 原论断（来源） | 核对结果 | 依据 |
| --- | --- | --- | --- |
| F1 | "RLVP 明确写了 'chain 0.6B/1.7B (too weak)'，所以 1.7B 上的罚可能无效"（design §5.5） | **证伪（断章取义）**：该句是图注，原句是"稠密 progress potential 的收益只在可达阈值之后出现"。惩罚通道恰恰在 1.7B–8B 上都有效 | Q37 Q38 Q39 |
| F2 | "CGAP 零样本 LLM 解析"（design §2.2） | **措辞无原文支撑**：原文没有"zero-shot"一词。实际是 prompt 的 LLM Mθ（gpt-oss-20b/Qwen3-32B/GPT-5 mini），未训练；解析对象是 operation 加无类型的 Λt | Q22 Q23；"zero-shot"无原文支撑 |
| F3 | 蓝本 / design 沿用"CGAP、RLVP 两次点名 open problem，由我们闭合" | **部分证伪**：CGAP 的"outside our scope"指从 NL 诱导**能力的状态依赖规则**，不是用户约束；CGAP 全文没有"open problem"。RLVP 确有"open challenge"，但说的是从**环境 affordance** 自动发现约束，不是从用户 query | Q114 Q25 Q36 |
| F4 | "RLVP：逐动作罚、折叠标量对比、outcome-gating"（design §2.2） | "outcome-gating"**无原文支撑**：RLVP 的原则是保留结果奖励作为驱动；折叠对比属实 | Q40；"outcome-gating"无原文支撑 |
| F5 | "Constrained GRPO：ScRew 会扭曲非对称比例"（design §2.2） | **属于我方推论**：原文说的是标量化奖励会造成共享分母耦合、改变相对权重，没有提"非对称" | Q28 |
| F6 | "新检索论文只核实到摘要层面"（design §2.3） | **已过时**：本轮下载并深读了 LogiSafetyBench；抽节读了 ToolPrivacyBench、SiLR、LowerPrivileges、PlanBench-XL；PeakBench 仍只读了 2 页 | §1.6 |
| F7 | "PeakBench、PlanBench-XL：工具规划中的隐式数据流/隐式子目标"（design §2.3） | 降级为低相关：PlanBench-XL 的"implicit subgoals"是检索式规划子目标；PeakBench 是依赖与并发结构加资源调度 | Q111 Q112 |
| F8 | "tpl_ho 的 PII 别名全部 held-out；privacy d2/d3 需要按策略卡映射"（design §4.1、§5.2） | **证伪（自查）**：`POLICY_CARD`（`src/dataset_v4_spec.py` L172–183，L178）把 test 池的字段短语原样列为示例（national ID numbers、employee home addresses、insurance IDs），模型输入里直接可查 | 脚本核验：3/3 个 test 字段的核心短语都在 POLICY_CARD 中 |
| F9 | "E1-exec 的 none 档在 E/I 上为 0，所以 safe_success 回答了'F1 高是否有用'"（design §4.2） | **夸大（自查）**：0 只针对默认计划。一个**不看约束的保守规划器**（每阶段选本地且最便宜的工具，并插入全部可选步骤），在 E 版上的 safe_success 为 dev 0.673 / tpl_ho 0.634 / tool_ho 0.614。safe_success 单独不能把成功归因到编译 | §5.3 复算 |
| F10 | design §0 "依据 literature/extracted 全部 73 个全文" | **不实**：上一版依据的是子代理摘要；本版依据见 §0 | §0 |

经核对确认成立的论断：
- PRefine κ（Q8）、ANCHOR AC1（Q66）、Firefly χ²（Q58）、ToolTurns 120 条盲审（Q78）；
- LIFT 17 个模型与 34k 训练集（Q72 Q73）；
- AM-Bench 约束域与构造方式（Q67–Q70）；
- TAG 门控与权重不安全（Q49 Q50）；
- DAGent 拓扑信用（Q45）；
- LangNCO "do not verify semantic agreement"（Q113）；
- RLVP 纯罚全部 seed 成功率为 0（Q115）；
- LowerPrivileges 采用 SFT→GRPO 加升权罚（Q109 Q110）。

---

## 4. 三条创新点收窄口径复核

- **①**：仍然站得住，但必须进一步收窄为："**训练的小模型** + **逐 query** + **typed 参数化约束对象** + **隐式线索** + **执行级评测**"这一组合。
  - Sapien 必须加进划界表。它与我方在"逐 query 编译成可执行对象"上重叠，区别在于用现成 LLM、没有 typed 约束、对欠指定不做细化。
  - "可本机部署"不能单独成为卖点：NOMOS 已经报告本机 26B 编译不显著劣于前沿模型（Q17）。
  - 在强模型 PE 结果出来之前，只能写"可行性"。
- **②**：维持"E2 未跑之前不写成贡献"。F1 修正后，**1.7B 作为 GRPO 主战场不再有文献层面的反对理由**；仍需先测组内方差（VarG）。
- **③**：必须放弃一切"首个"表述，因为 LogiSafetyBench 已自称首个隐式合规工具评测（Q103）。可守的组合是：**参数级**约束（Q102 是对方自认的空白）+ query 内可恢复的隐式线索 + N 近似干扰对照 + 咬合且逐条必要 + 训练集 + 执行级刻度。

---

## 5. 数据集与实验设计复核（只读复算，未改代码）

### 5.1 用户点名的六个问题

| 问题 | 结论 | 证据 |
| --- | --- | --- |
| 约束是否逐条必要 | **成立，但依赖所用规划器**：V4 对 5000 组全量复核了"去掉 c 后，最小改动计划必然违反 c"。可是保守规划器在**没有任何约束**的情况下，也会顺带满足 budget/privacy/tool_auth（满足率均为 1.00），order 约 0.72，只有 deadline 是 0.01–0.06 | §5.3 |
| N 干扰句是否可能被合理判成约束 | 逐条读了 NEAR_MISS 共 40 条模板（`src/dataset_v4_spec.py` 约 L520–600）：每条都有明确的豁免/撤销/他人适用/无依赖标记，**人工判断风险低**；零样本 0.6B 的 N 误报率 0.84–0.89，说明这些句子确实具有迷惑性（是有效的困难负例）。仍需纳入人工盲审的"N 无约束"维度 | §5.2 |
| I 版是否真的需要推理 | **只有一部分需要**：在 7,826 条隐式约束中，需要算术的（budget/deadline 的 d2/d3）占 21.6%；字段映射（privacy 的 d2/d3）占 16.1%，但因 F8，这部分实际上是在 prompt 里查表；其余 62% 是 fact/consequence/convention 措辞线索，tool_auth/order 的"难度"标签只是名义上的。此外，I 版 order 模板有位置伪影：train 和 test 两池都是 5/6 条先提到 after 角色，而 E 版多数先提到 before 角色（`src/dataset_v4_spec.py` L465 起），模型可以学到"I 版就反转提及顺序" | 脚本统计 |
| held-out 是否有真实区分度 | **tpl_ho**：模板/goal/背景是分池的，但 PII 别名经 prompt 泄漏（F8）。**tool_ho**：held-out 世界与训练世界**结构同构**——同样的 5 个阶段、备选位置、配对模式和数值区间（`src/dataset_v4_spec.py` L71–150），只换了名字。零样本下 tool_ho 并不比 dev 更难：受约束 safe 分别为 tool_ho 0.107 [0.079, 0.137]、dev 0.077 [0.055, 0.102]、tpl_ho 0.073 [0.051, 0.094]。按 EffectWorld 的标准（Q76 所在论文有真正的未见域），这只能算**名称级** held-out | §5.2 |
| 是否缺强模型 PE / few-shot 基线 | **缺，属于 blocker**。design §5.1 的 P1–P3 都还没跑。没有它们，①无法主张（CGAP/Sapien/NOMOS 都用强模型做 prompt 编译） | — |
| 统计是否足够 | 不够：主表单 seed；只有 group bootstrap 加 McNemar。对标 RLVP（3–5 seeds）、DAGent/TIDE/NormWorlds（3 seeds），至少需要在 0.6B/1.7B 上补 2 个 seed，并报告逐 seed 结果 | Q39 Q46 Q60 |

### 5.2 当前实验结果（只读，服务器 `/root/ConsDagQAQ`，23:39 CST）

**队列状态**：
- manifest 记录 22:10:53 `queue_start`（commit `f63c727`）、22:11:29 0.6B `train_start`；
- 没有 failed 事件，也没有 `training_failure.json`；
- GPU 显存 14,420 MiB，利用率 41%。

**0.6B 训练 loss**：
- step 1 为 0.683；step 100 为 5.8e-4；step 300 为 5.6e-5；
- 3,700–5,100 步之间在 1e-6 到 5e-4 波动，偶有 6e-3 的尖峰（step 400）；
- 全部为有限值，没有 NaN；
- 截至 23:39 到第 5,100/9,000 步，约 88 秒/100 步，预计 00:40 前后训练结束，随后做训练后评测。

**loss 判断**：
- 这**不是数值塌陷**，而是**极快饱和**：前 400 条样本内 loss 就降到 1e-3 以下。
- 原因是目标里大部分 token 可以直接照抄：evidence_span 是原句；scope、severity 由策略卡加目录按规则推出。平均 loss 很低，并不说明 d2/d3 的算术已经学会。
- 要等训练后的 per-difficulty 和 tpl_ho/tool_ho 结果才能判断。
- 3 个 epoch 远超所需，有记忆模板风格的风险；当前无法改动。

**零样本结果**：
- 来源：把服务器上的 3 个预测文件 cat 回本地；去掉 CR 后，md5 与服务器 `md5sum` 一致（26832a6f…/9c835777…/d6e2bf6f…）。
- 评分用本地已提交的 `run_e1.score` 和 `eval_exec.evaluate`，代码与服务器同一提交。
- 下表中，faithful 指"安全且不多改"：E/I 为安全且改动数等于金标计划，N 为安全且不偏离默认计划。faithful 是本轮诊断用指标，**尚未写进代码**（见 §6 T1）。

| 子集 | strict F1 | core F1 | state acc | parse | 记录全对 | N 误报率 | safe（E / I / N） | faithful（E / I / N） | 受约束 safe（95% CI） |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dev | 0.010 | 0.105 | 0.347 | 0.889 | 0.020 | 0.893 | 0.107 / 0.047 / 0.997 | 0.103 / 0.043 / 0.903 | 0.077 [0.055, 0.102] |
| tpl_ho | 0.008 | 0.086 | 0.333 | 0.874 | 0.015 | 0.869 | 0.074 / 0.071 / 0.991 | 0.069 / 0.066 / 0.877 | 0.073 [0.051, 0.094] |
| tool_ho | 0.015 | 0.131 | 0.281 | 0.835 | 0.024 | 0.843 | 0.123 / 0.091 / 0.991 | 0.117 / 0.089 / 0.789 | 0.107 [0.079, 0.137] |

**零样本结果能支持什么**：
- 只能说明在 v4 契约下，零样本 0.6B 几乎不会编译：受约束 safe 为 7–11%（CI 下限 5%，上限 14%）。
- 它倾向于对一切输出 explicit：none→explicit 误判 211/300（dev）。
- N 版之所以 safe 接近 1，是因为它输出的约束多数不合契约（每条 N 记录平均 0.81–0.86 条不可用约束），被规划器丢弃，计划回退为默认计划。

**不能支持的**：任何关于训练增益、强模型对比、隐式推理的结论；trained 结果尚未出现。

### 5.3 复算细节（保守规划器基线）

保守规划器的规则：每个阶段选"本地且最便宜、最快"的工具，finish 保持默认顺序，插入全部可选步骤（审批、脱敏、校验）。它不看任何约束。

| 子集 | E 版 safe_success | 取 finish 两种顺序中较优者（oracle） | 逐类型满足率 |
| --- | --- | --- | --- |
| dev | 0.673 | 0.760 | budget/privacy/tool_auth 1.00，order 0.75，deadline 0.06 |
| tpl_ho | 0.634 | 0.731 | 同上，order 0.70，deadline 0.04 |
| tool_ho | 0.614 | 0.711 | 同上，order 0.72，deadline 0.01 |

它的计划与金标最小改动计划的一致率为 **0**（dev/tpl_ho 的 E 和 N 都是 0）。所以 faithful 指标能区分它，而 safe_success 区分不了。

---

## 6. 问题分级与待修清单（队列结束后由我修，现在不改）

| 级别 | ID | 问题 | 位置 | 修法 |
| --- | --- | --- | --- | --- |
| **blocker** | T1 | safe_success 可以被不看约束的保守规划器拿到 0.61–0.67，执行级指标无法把功劳归给编译 | `src/eval_exec.py` L29–48（record_outcome）、summarise | 新增 **faithful_success**（E/I：安全且改动数等于金标计划；N：安全且不偏离默认计划），作为执行级主指标；把保守规划器加为参考档；recompute 脚本同步 |
| **blocker** | T2 | 强模型 PE 与 few-shot 臂缺失 | design §5.1 P1–P3 | 写 `src/run_pe_e1.py`（复用 v4 prompt、strict_parse、score、eval_exec），在服务器或本机通过 API 跑；不占 GPU，可以在队列运行期间开发和跑（只新增文件，不改训练文件） |
| **blocker** | T3 | I 版可恢复性和 N 无约束性没有人工/oracle 验证 | — | oracle：≥2 家强模型在看不到 gold 的条件下恢复约束；人工：≥250 条，2–3 人，报 κ/AC1 |
| high | T4 | POLICY_CARD 泄漏 test 池 PII 字段短语 | `src/dataset_v4_spec.py` L172–183（L178） | 示例只保留 train 池字段，或只给类定义；改完后要重训（会影响 prompt） |
| high | T5 | tool_ho 结构同构，只换了名字 | `src/dataset_v4_spec.py` L71–150 | 新增结构不同的 held-out 世界（阶段数和配对模式不同），或把 tool_ho 改名为 name-held-out，并同步收窄论文措辞 |
| high | T6 | I 版 order/tool_auth 模板的提及顺序存在位置伪影 | `src/dataset_v4_spec.py` L465 起（order I）、tool_auth I | 每种 hint_type 内部平衡先提 before/after 的模板数，验证器加一条位置分布检查 |
| high | T7 | 统计：单 seed | — | 0.6B/1.7B 补 seed 43/44（排在队列之后） |
| medium | T8 | 验证器 V6 对 privacy 的显式检查是空操作 | `src/verify_dataset_v4.py` L154–155 | 检查数据类可读名是否出现在 span 中 |
| medium | T9 | 模板池小（每类每池 E 8 条、I 6 条、N 4 条） | `src/dataset_v4_spec.py` | 扩池，加改写 OOD 子集（注意 LIFT 的教训 Q74：改写模型可能会去"执行"约束） |
| medium | T10 | tool_auth/order 的 difficulty 只是名义标签 | `src/build_dataset_v4.py` L177 | 论文里只按 budget/deadline/privacy 报难度分层，或为 tool_auth/order 设计真正的多步依赖线索 |
| medium | T11 | loss 极快饱和，3 epoch 过量 | 训练配置 | 下一轮记录 tpl_ho 学习曲线（中间 checkpoint 评测），按 dev 早停；本轮不动 |
| low | T12 | 零样本 N 版 safe 接近 1 来自"不可用约束被丢弃" | `src/eval_exec.py` | 报告中把 unusable 比例和 malformed 比例单列 |

**以下 4 条来自 `reports/design_v4_independent_recheck.md`**：该文件 23:44 出现在仓库，不是本会话创建，我未改动。每条都已由我复核成立。

| 级别 | ID | 问题 | 复核结果 | 位置 | 修法 |
| --- | --- | --- | --- | --- | --- |
| high | T13 | "记录全对"不要求 evidence_span | 删掉 dev-00000-I 金标的全部 evidence_span 之后，record_exact_match 仍为 1.0，evidence_exact_rate 为 0，safe 仍为 1.0 | `src/run_e1.py` 的 constraint_key / score | 把现有指标更名为"结构键全对"，另加"含原文 span 的全对率"和"span 是 query 子串"的召回率 |
| high | T14 | E1-exec 只消费 type+params，scope/state/severity/span 不影响执行 | 设计如此 | `src/trust_env.py` normalize_constraint | 论文口径写成"类型与参数的执行效用"；要主张 scope 的价值，需要另设消费 scope 的下游并做消融 |
| medium | T15 | 全部输出乱码时总体 safe_success 仍有 1/3（N 版回退默认计划即安全）；paired_compare 按 sample_id 取交集，McNemar 按记录而非按组计数 | 全乱码时总体 safe = 0.3333 | `src/eval_exec.py` L136–155 | 主表只报受约束 safe/faithful；比较前断言两臂 ID 全覆盖；McNemar 和 bootstrap 以组为单位 |
| medium | T16 | 旧 `run_qwen_max_e1.py` 默认用 processed_v2，续跑不核验数据或 prompt 指纹 | 默认路径确为 processed_v2 | `src/run_qwen_max_e1.py` L236 | 强模型 PE 改用新脚本（T2），输出到新目录，续跑前校验数据 sha 和 prompt hash |

此外，该复核指出：E2 若对同一 query 下所有轨迹施加相同的漏检罚，GRPO 的组内中心化会把它抵消。这一点成立，记入 E2 设计义务：漏检罚必须随轨迹变化，例如只在计划实际违反时触发。

---

## 7. 下一步优先级

1. **（不碰训练文件，现在就能做）** 新增 `src/run_pe_e1.py` 和 oracle 脚本，用可用的 API 跑强模型 PE（零样本 + few-shot）和 I 版可恢复性 oracle。只新增文件，不影响队列。
2. 队列中 0.6B trained 完成后（预计 00:40–01:00），按 §5.2 的口径拉回 metrics，并补算 faithful 和 per-difficulty。
3. 三个模型全部跑完后，按 §6 修 T1、T4、T6、T8，重新生成 v4.1 并重跑。T5 先改口径，再决定是否加结构外世界。
4. 人工盲审包（T3）与 2 个补充 seed（T7）。

---

## 附录 A：已核验引文（116 条，全部脚本回原文定位）

见下表。生成脚本为 `outputs/_lit/quotes.py`，结果为 `outputs/_lit/quotes_verified.json`。

| ID | 论文 | fulltext 路径 | 行号 | 原文（≤40 词，脚本逐条回原文定位） |
| --- | --- | --- | --- | --- |
| Q1 | BeyondReAct | `literature/extracted/library/00_base/2511.10037_BeyondReAct/2511.10037_BeyondReAct_fulltext.txt` | L413-414 | "we pair our Planner with GPT-4o as the executor." |
| Q2 | BeyondReAct | `literature/extracted/library/00_base/2511.10037_BeyondReAct/2511.10037_BeyondReAct_fulltext.txt` | L600-601 | "The Qwen3-0.6B(SFT+RL) variant is excluded due to training instability." |
| Q3 | ATLAS | `literature/extracted/library/01_constraint_compiler/2509.25586_ATLAS/2509.25586_ATLAS_fulltext.txt` | L170-171 | "constraints (𝐶𝐼) are not explicitly given but stem from commonsense domain rules and physical realities" |
| Q4 | ATLAS | `literature/extracted/library/01_constraint_compiler/2509.25586_ATLAS/2509.25586_ATLAS_fulltext.txt` | L167 | "explicitly stated or implied by 𝑄, such as budget limits" |
| Q5 | ConstraintsOfThought | `literature/extracted/library/01_constraint_compiler/2510.08992_ConstraintsOfThought/2510.08992_ConstraintsOfThought_fulltext.txt` | L774-775 | "Const-o-T depends on accurate constraint extraction; when LLMs misinterpret user input or produce incomplete symbolic constraints, the search may be guided toward suboptimal solutions." |
| Q6 | ImplicitIntelligence | `literature/extracted/library/01_constraint_compiler/2602.20424_ImplicitIntelligence/2602.20424_ImplicitIntelligence_fulltext.txt` | L40-41 | "the capacity to identify, reason about, and satisfy requirements users expect but never explicitly state" |
| Q7 | ImplicitIntelligence | `literature/extracted/library/01_constraint_compiler/2602.20424_ImplicitIntelligence/2602.20424_ImplicitIntelligence_fulltext.txt` | L22-23 | "Evaluating 16 frontier and open-weight models across 205 scenarios" |
| Q8 | PRefine | `literature/extracted/library/01_constraint_compiler/2604.17886_PRefine/2604.17886_PRefine_fulltext.txt` | L484-486 | "Human validation of the cost and party-size preferences yielded 89.7% and 97.4% agreement (Fleiss’ κ = 0.701 and 0.880; 19 annotators)" |
| Q9 | AdaPlanBench | `literature/extracted/library/01_constraint_compiler/2606.05622_AdaPlanBench/2606.05622_AdaPlanBench_fulltext.txt` | L1054-1056 | "Our evaluation relies on LLM judges for constraint checking and rubric scoring, which may introduce model-specific preferences or systematic bias." |
| Q10 | AdaPlanBench | `literature/extracted/library/01_constraint_compiler/2606.05622_AdaPlanBench/2606.05622_AdaPlanBench_fulltext.txt` | L23-24 | "AdaPlanBench is built on 307 household tasks" |
| Q11 | CARL | `literature/extracted/library/01_constraint_compiler/2607.04854_CARL/2607.04854_CARL_fulltext.txt` | L30-33 | "CARL introduces a constraint-aware reward by comparing the model’s output distributions under constrained and unconstrained inputs" |
| Q12 | PolicyGuide | `literature/extracted/library/01_constraint_compiler/2608.19861_PolicyGuide/2608.19861_PolicyGuide_fulltext.txt` | L28-30 | "POLICYGUIDE instead compiles each domain policy into a workflow graph and invokes a proactive verifier at user-turn boundaries." |
| Q13 | PolicyGuide | `literature/extracted/library/01_constraint_compiler/2608.19861_PolicyGuide/2608.19861_PolicyGuide_fulltext.txt` | L60-61 | "domain-specific fine-tuning is often unavailable or impractical" |
| Q14 | Sapien | `literature/extracted/library/01_constraint_compiler/2610.00797_Sapien/2610.00797_Sapien_fulltext.txt` | L139-141 | "an automaton-based engine that synthesizes policies from trusted user prompts and enforces them over tool calls" |
| Q15 | NOMOS | `literature/extracted/library/01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt` | L21-22 | "NOMOS, a four-pass compiler, turns a natural-language policy into a deterministic tool-call gate" |
| Q16 | NOMOS | `literature/extracted/library/01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt` | L2969 | "The system also presupposes that a written policy exists" |
| Q17 | NOMOS | `literature/extracted/library/01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt` | L29-30 | "a 26B on-premise compilation is not significantly worse than hand-written or frontier-compiled rules." |
| Q18 | LangNCO | `literature/extracted/library/01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt` | L607-608 | "selecting its targets so that the original high-quality solution violates the new requirement." |
| Q19 | LangNCO | `literature/extracted/library/01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt` | L627-629 | "Our evaluation focuses on constraint-type and compositional breadth rather than systematic robustness to paraphrasing." |
| Q20 | SCA | `literature/extracted/library/01_constraint_compiler/2610.25552_SCA/2610.25552_SCA_fulltext.txt` | L1111-1113 | "they cannot detect omissions, where the agent never makes a necessary call." |
| Q21 | CASEL | `literature/extracted/library/01_constraint_compiler/2610.36570_CASEL/2610.36570_CASEL_fulltext.txt` | L36 | "In a controlled simulation over 20 seeds" |
| Q22 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L23 | "uses an LLM to turn the request into goals," |
| Q23 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L425-426 | "evidence spans ϵi in the user’s messages" |
| Q24 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L810-812 | "Confidence intervals use 10,000 task-level bootstrap resamples, paired by task for differences between methods" |
| Q25 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L1030-1031 | "authorization, privacy, and the decision whether an action is appropriate remain the application’s job" |
| Q26 | CIRCE | `literature/extracted/library/01_constraint_compiler/2610.41089_CIRCE/2610.41089_CIRCE_fulltext.txt` | L1079-1081 | "It does not cover the problems where inferring constraints is part of the reasoning process." |
| Q27 | SafeOrchestrate | `literature/extracted/library/01_constraint_compiler/2611.09364_SafeOrchestrate/2611.09364_SafeOrchestrate_fulltext.txt` | L848-850 | "because its tasks are largely single-rule with an empty constraint set C, the SMT layer’s cross-rule and safety-constraint enforcement is shown only on the worked example" |
| Q28 | ConstrainedGRPO | `literature/extracted/library/02_objective_factorization/2602.05863_ConstrainedGRPO/2602.05863_ConstrainedGRPO_fulltext.txt` | L35-37 | "scalarizing rewards before normalization introduces shared-denominator coupling, so that changing one multiplier alters not only the emphasis on its corresponding constraint" |
| Q29 | ConstrainedGRPO | `literature/extracted/library/02_objective_factorization/2602.05863_ConstrainedGRPO/2602.05863_ConstrainedGRPO_fulltext.txt` | L522-523 | "directly optimizing a multiplicative hard-gated objective can lead to sparse learning signals and unstable optimization" |
| Q30 | ToolRLA | `literature/extracted/library/02_objective_factorization/2603.01620_ToolRLA/2603.01620_ToolRLA_fulltext.txt` | L36-39 | "Ablation studies show the multiplicative reward design accounts for 7 percentage points of improvement over additive alternatives." |
| Q31 | SEVerA | `literature/extracted/library/02_objective_factorization/2603.25111_SEVerA/2603.25111_SEVerA_fulltext.txt` | L146-148 | "SEVerA achieves provably zero constraint violations while outperforming state-of-the-art agents in task performance" |
| Q32 | InteractiveCritiqueRevision | `literature/extracted/library/02_objective_factorization/2605.08327_InteractiveCritiqueRevision/2605.08327_InteractiveCritiqueRevision_fulltext.txt` | L612-613 | "TaxCalcBench TY24 provides synthetic U.S. federal tax-form instances with ground-truth Form 1040 outputs produced by a deterministic tax engine." |
| Q33 | PARPO | `literature/extracted/library/02_objective_factorization/2605.23382_PARPO/2605.23382_PARPO_fulltext.txt` | L688-689 | "Ours significantly outperforms the strongest baseline, SkillRL, under the paired t-test (p < 0.005)" |
| Q34 | AgentLTL | `literature/extracted/library/02_objective_factorization/2607.02599_AgentLTL/2607.02599_AgentLTL_fulltext.txt` | L23-24 | "a single specification drives two usages." |
| Q35 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L500 | "Therefore: penalize commission, never omission." |
| Q36 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L870-872 | "our penalties were manually identified based on domain rules. Automating the discovery of penalizable constraints directly from an environment’s affordances remains an open challenge." |
| Q37 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L1302 | "chain 0.6B/1.7B (too weak)" |
| Q38 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L1236 | "Benefit appears only past a reachability threshold" |
| Q39 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L441-442 | "This holds across five seeds at 4B and generalizes from 1.7B to 8B models" |
| Q40 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L1521-1522 | "folding the same rule rewards into the scalar return doubles the episodes to threshold." |
| Q41 | STAIF | `literature/extracted/library/02_objective_factorization/2607.22649_STAIF/2607.22649_STAIF_fulltext.txt` | L1362-1363 | "Testing results in Section 6 are based on single-run." |
| Q42 | PRISM | `literature/extracted/library/02_objective_factorization/2607.29246_DontMixRewards/2607.29246_DontMixRewards_fulltext.txt` | L56-57 | "do not mix rewards, mix policies." |
| Q43 | AMRP | `literature/extracted/library/02_objective_factorization/2609.00213_AggregationRewardHacking/2609.00213_AggregationRewardHacking_fulltext.txt` | L25-26 | "static projection aliases qualitatively different reward profiles into a single scalar" |
| Q44 | CC-OPD | `literature/extracted/library/02_objective_factorization/2609.27421_CounterfactualConstraintDistill/2609.27421_CounterfactualConstraintDistill_fulltext.txt` | L1398-1401 | "non-inline constraint formats such as structured fields or programmatic templates may require a different counterfactual prompt construction." |
| Q45 | DAGent | `literature/extracted/library/02_objective_factorization/2609.39154_DAGent/2609.39154_DAGent_fulltext.txt` | L516 | "The closure is a structural proxy for contribution rather than a causal attribution" |
| Q46 | DAGent | `literature/extracted/library/02_objective_factorization/2609.39154_DAGent/2609.39154_DAGent_fulltext.txt` | L2950-2951 | "the RL rows are means across three independent training seeds." |
| Q47 | CM-DPO | `literature/extracted/library/02_objective_factorization/2610.09219_CM-DPO/2610.09219_CM-DPO_fulltext.txt` | L747-749 | "Budget violations account for the largest share of TravelPlanner errors (36.8%), suggesting that implicit arithmetic remains a bottleneck for longer plans." |
| Q48 | CALIF | `literature/extracted/library/02_objective_factorization/2610.19525_RewardHackingVerifiableIF/2610.19525_RewardHackingVerifiableIF_fulltext.txt` | L19-20 | "frontier models can receive full credit for responses with little substantive answer content." |
| Q49 | TAG | `literature/extracted/library/02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt` | L32-33 | "then gates auxiliary credit on anchor satisfaction." |
| Q50 | TAG | `literature/extracted/library/02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt` | L514-515 | "Under GRPO no single weight is safe across a prompt population that contains hard prompts (small ρ)" |
| Q51 | TAG | `literature/extracted/library/02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt` | L940-941 | "low policy drift does not guarantee alignment with the unknown true reward." |
| Q52 | TAG | `literature/extracted/library/02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt` | L2204 | "Held-out noise is about ±0.02." |
| Q53 | ShortcutsBoundaries | `literature/extracted/library/02_objective_factorization/2611.12865_ShortcutsBoundaries/2611.12865_ShortcutsBoundaries_fulltext.txt` | L27-29 | "The same contextual checks supply a simple binary penalty that supports joint capability and compliance gains and partially mitigates acquired violations." |
| Q54 | StateAlign | `literature/extracted/library/02_objective_factorization/2611.16304_StateAlign/2611.16304_StateAlign_fulltext.txt` | L1179-1181 | "StateAlign is trained on five types of constructed task states through short interactions with recorded feedback." |
| Q55 | SOTERIA | `literature/extracted/library/02_objective_factorization/2611.17880_SOTERIA/2611.17880_SOTERIA_fulltext.txt` | L1012-1014 | "SOTERIA requires a set of formalized specifications as inputs, which are currently obtained through a semi-automated workflow that combines LLM-based auto-formalization with manual validation." |
| Q56 | RECAST | `literature/extracted/library/03_paired_benchmark/2505.19030_RECAST/2505.19030_RECAST_fulltext.txt` | L1046-1047 | "we use the Hard Constraint Satisfaction Rate (HSR) as the primary metric, quantifying the model’s ability to satisfy all specified constraints in an instruction simultaneously." |
| Q57 | MOSAIC | `literature/extracted/library/03_paired_benchmark/2603.03205_MOSAIC/2603.03205_MOSAIC_fulltext.txt` | L20-21 | "MOSAIC structures inference as a plan, check, then act or refuse loop" |
| Q58 | Firefly | `literature/extracted/library/03_paired_benchmark/2605.17558_Firefly/2605.17558_Firefly_fulltext.txt` | L1150-1151 | "tasks that passed the judge satisfy all three binary criteria 78.0% of the time, compared with 38.0% for rejected candidates" |
| Q59 | MatchingMatters | `literature/extracted/library/03_paired_benchmark/2606.21140_MatchingMatters/2606.21140_MatchingMatters_fulltext.txt` | L1994-1996 | "The preservation gate rejects explicit changes to public task semantics but cannot formally prove natural-language equivalence." |
| Q60 | NormWorldsCF | `literature/extracted/library/03_paired_benchmark/2607.03957_NormWorldsCF/2607.03957_NormWorldsCF_fulltext.txt` | L550-551 | "the Qwen3-4B GRPO study averages three independent seeds" |
| Q61 | NormWorldsCF | `literature/extracted/library/03_paired_benchmark/2607.03957_NormWorldsCF/2607.03957_NormWorldsCF_fulltext.txt` | L364 | "Splits are by root family" |
| Q62 | ExecutionFirst | `literature/extracted/library/03_paired_benchmark/2607.29175_ExecutionFirst/2607.29175_ExecutionFirst_fulltext.txt` | L523-525 | "The Basic task explicitly specifies the operational intent and required entities, the Intermediate task omits some execution details that must be inferred from context" |
| Q63 | ExecutionFirst | `literature/extracted/library/03_paired_benchmark/2607.29175_ExecutionFirst/2607.29175_ExecutionFirst_fulltext.txt` | L516-517 | "This validation is performed using the same LLM used to generate the trace." |
| Q64 | ToolLoop | `literature/extracted/library/03_paired_benchmark/2609.09072_ToolLoop/2609.09072_ToolLoop_fulltext.txt` | L1156-1158 | "the verifier achieves 94% agreement with human annotations on a random sample of 100 instances" |
| Q65 | ANCHOR | `literature/extracted/library/03_paired_benchmark/2610.16859_ANCHOR/2610.16859_ANCHOR_fulltext.txt` | L48-49 | "A five-engineer audit of constraints from 50 instances reports 94% feasibility, 94% repository consistency, and 96% realism." |
| Q66 | ANCHOR | `literature/extracted/library/03_paired_benchmark/2610.16859_ANCHOR/2610.16859_ANCHOR_fulltext.txt` | L752-753 | "Gwet’s AC1 ranges from 0.91 to 0.97." |
| Q67 | AM-Bench | `literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt` | L24-25 | "Each task includes a fully specified reference and six variants spanning ambiguous or missing goals, context, and constraints." |
| Q68 | AM-Bench | `literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt` | L215-217 | "KM: Relevant restrictions or authorization requirements are unstated." |
| Q69 | AM-Bench | `literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt` | L242-243 | "S checks the same fully specified task constraints across conditions, including undisclosed requirements." |
| Q70 | AM-Bench | `literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt` | L296-297 | "GPT-5.6-Sol assisted in drafting the variants using a construction skill, and the authors reviewed them." |
| Q71 | DPG-HiddenCoop | `literature/extracted/library/03_paired_benchmark/2610.26359_DiscoveryProbabilityGraph/2610.26359_DiscoveryProbabilityGraph_fulltext.txt` | L105-106 | "Cooperative tasks can only be completed by two agents, a requirement that remains unknown to the agents until they attempt them." |
| Q72 | LIFT | `literature/extracted/library/03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt` | L302 | "holding topic, outline, and constraint content fixed" |
| Q73 | LIFT | `literature/extracted/library/03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt` | L316 | "We evaluate 17 models on the 10 released splits." |
| Q74 | LIFT | `literature/extracted/library/03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt` | L1188-1189 | "the rewriting model occasionally treated the task’s constraints as instructions addressed to itself and complied with them" |
| Q75 | AgentProofBench | `literature/extracted/library/03_paired_benchmark/2610.34634_AgentProofBench/2610.34634_AgentProofBench_fulltext.txt` | L72-73 | "connects paired tests of a frozen acceptance rule to execution from identical saved openings" |
| Q76 | EffectWorld | `literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt` | L1769-1770 | "template utterances (paraphrases generated by a larger language model are not yet used)" |
| Q77 | EffectWorld | `literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt` | L1783 | "The intervals in Tables 12 and 13 measure task sampling only." |
| Q78 | ToolTurns | `literature/extracted/library/03_paired_benchmark/2611.14925_ToolTurns/2611.14925_ToolTurns_fulltext.txt` | L69-70 | "blind human annotation prefers the revised message in 63.3% of 120 sampled pairs" |
| Q79 | TIDE | `literature/extracted/library/04_credit_assignment/2605.03327_TIDE/2605.03327_TIDE_fulltext.txt` | L34-36 | "a critic-free RL framework that reinterprets distribution deviation as a guiding signal rather than a rigid penalty." |
| Q80 | GACA | `literature/extracted/library/04_credit_assignment/2609.12424_GranularityAdaptiveCredit/2609.12424_GranularityAdaptiveCredit_fulltext.txt` | L443-444 | "each selected checkpoint receives three stochastic evaluations, summarized by their mean and population SD." |
| Q81 | SHARPO | `literature/extracted/library/04_credit_assignment/2610.00838_SHARPO/2610.00838_SHARPO_fulltext.txt` | L397-398 | "We report the mean and sample standard deviation over three independent runs." |
| Q82 | CATS | `literature/extracted/library/04_credit_assignment/2610.29292_ContrastiveAttributionTopology/2610.29292_ContrastiveAttributionTopology_fulltext.txt` | L490 | "Attribution credits have not been validated against human judgments." |
| Q83 | HyperAgent-SE | `literature/extracted/library/05_review_queue/2409.16299_HyperAgent-SE/2409.16299_HyperAgent-SE_fulltext.txt` | L177-178 | "HYPERAGENT is the first system designed to work off-the-shelf across diverse SE tasks in multiple programming languages without task-specific adaptations." |
| Q84 | HyperAgent-Hypergraph | `literature/extracted/library/05_review_queue/2510.10611_HyperAgent-Hypergraph/2510.10611_HyperAgent-Hypergraph_fulltext.txt` | L63-64 | "on GSM8K, HyperAgent achieves 95.07% accuracy while reducing token consumption by 25.33%" |
| Q85 | OrchDAG | `literature/extracted/library/05_review_queue/2510.24663_OrchDAG/2510.24663_OrchDAG_fulltext.txt` | L558-559 | "our method remains limited in that it does not yet address multi-turn scenarios involving implicit dependencies" |
| Q86 | HyperAgents(DGM-H) | `literature/extracted/library/05_review_queue/2603.19461_HyperAgentsSurvey/2603.19461_HyperAgentsSurvey_fulltext.txt` | L441-442 | "For each experiment, we run each method 5 times. We report medians with 95% bootstrap confidence intervals computed from 1,000 resamples" |
| Q87 | AgentGym-RL | `literature/extracted/papers/AgentGym-RL_2509.08755/AgentGym-RL_2509.08755_fulltext.txt` | L522-523 | "We leverage Qwen-2.5-3B and Qwen-2.5-7B [83] as our primary backbone models." |
| Q88 | ReAct | `literature/extracted/papers/ReAct_2210.03629/ReAct_2210.03629_fulltext.txt` | L32-33 | "ReAct outperforms imitation and reinforcement learning methods by an absolute success rate of 34% and 10% respectively" |
| Q89 | rStar2-Agent | `literature/extracted/papers/rStar2-Agent_2508.20722/rStar2-Agent_2508.20722_fulltext.txt` | L855-856 | "We then run large-scale agentic reinforcement learning using GRPO-RoC, with a learning rate of 1e-6 and a batch size of 512 prompts." |
| Q90 | ToolRL | `literature/extracted/papers/ToolRL_2504.13958/ToolRL_2504.13958_fulltext.txt` | L723-725 | "we sample a batch of 512, and generate 4 responses per query, training for 15 epochs in total" |
| Q91 | papers/ATLAS_2605.16668 (错装) | `literature/extracted/papers/ATLAS_2605.16668/ATLAS_2605.16668_fulltext.txt` | L6-7 | "GraViti: Graph-Level Variational Autoencoders with Relaxed Permutation Invariance" |
| Q92 | papers/CARL_2505.23300 (错装) | `literature/extracted/papers/CARL_2505.23300/CARL_2505.23300_fulltext.txt` | L6-7 | "FACTORIZATIONS FOR VARIABLE EXPONENT MUCKENHOUPT WEIGHTS" |
| Q93 | papers/Hermes-Agents_2605.10477 (错装) | `literature/extracted/papers/Hermes-Agents_2605.10477/Hermes-Agents_2605.10477_fulltext.txt` | L6 | "Kaonic Copper and Fluorine Absolute Yields Measurement" |
| Q94 | papers/Instructed-Use-Tools_2605.13596 (错装) | `literature/extracted/papers/Instructed-Use-Tools_2605.13596/Instructed-Use-Tools_2605.13596_fulltext.txt` | L6-7 | "Creativity Bias: How Machine Evaluation Struggles with Creativity in Literary Translations" |
| Q95 | papers/LANG-NCO_2603.07613 (错装) | `literature/extracted/papers/LANG-NCO_2603.07613/LANG-NCO_2603.07613_fulltext.txt` | L6 | "Inverse Robin Spectral Problem for the p-Laplace Operator" |
| Q96 | papers/NCP-Benchmark_2605.04826 (错装) | `literature/extracted/papers/NCP-Benchmark_2605.04826/NCP-Benchmark_2605.04826_fulltext.txt` | L6 | "Faster Algorithms for Shortest Unique or Absent Substrings" |
| Q97 | papers/RLVP_2510.07896 (错装) | `literature/extracted/papers/RLVP_2510.07896/RLVP_2510.07896_fulltext.txt` | L7 | "ATTRIBUTION-CONTROLLED KNOWLEDGE EDIT" |
| Q98 | papers/TAG_2508.09112 (错装) | `literature/extracted/papers/TAG_2508.09112/TAG_2508.09112_fulltext.txt` | L7-9 | "Tracing large-scale structure morphology with multiwavelength line intensity maps" |
| Q99 | papers/ARMA_2502.06849 (错装) | `literature/extracted/papers/ARMA_2502.06849/ARMA_2502.06849_fulltext.txt` | L6 | "Model Fusion via Neuron Transplantation" |
| Q100 | LogiSafetyBench | `literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt` | L117-120 | "Safety Masking, which converts these traces into natural language instructions that omit mandatory safety steps, forcing LLMs to infer implicit constraints from context" |
| Q101 | LogiSafetyBench | `literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt` | L741-745 | "the LLM is initialized with a system prompt containing the Tool Schema (Dapi), the Raw Regulatory Document (Ptxt), and the User Instruction (I) where explicit safety requirements are removed." |
| Q102 | LogiSafetyBench | `literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt` | L1298-1300 | "limiting our ability to analyze the safety of specific function arguments (e.g., verifying that a transfer amount is within a safe limit" |
| Q103 | LogiSafetyBench | `literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt` | L626-628 | "the first evaluation suite designed to rigorously measure implicit regulatory compliance in LLM tool calling." |
| Q104 | LogiSafetyBench | `literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt` | L26 | "comprising 240 human-verified tasks" |
| Q105 | ToolPrivacyBench | `literature/extracted/library/06_web_supplement_20261121/2606.28061_ToolPrivacyBench/2606.28061_ToolPrivacyBench_fulltext.txt` | L16-18 | "The benchmark contains 2,150 cases, including 1,150 fully synthetic privacy-sensitive business workflows and 1,000 cases adapted from existing multi-tool and function-calling benchmarks." |
| Q106 | ToolPrivacyBench | `literature/extracted/library/06_web_supplement_20261121/2606.28061_ToolPrivacyBench/2606.28061_ToolPrivacyBench_fulltext.txt` | L101-104 | "The policy knowledge base is not supplied to the baseline agent as an execution-time defense. It is used only for post-execution audit." |
| Q107 | ToolPrivacyBench | `literature/extracted/library/06_web_supplement_20261121/2606.28061_ToolPrivacyBench/2606.28061_ToolPrivacyBench_fulltext.txt` | L1437-1439 | "This is a sampled reliability study and does not imply that the full benchmark was independently re-annotated." |
| Q108 | SiLR | `literature/extracted/library/06_web_supplement_20261121/2609.04629_SiLR/2609.04629_SiLR_fulltext.txt` | L862-864 | "With B concurrent violation branches, a count-based reward takes at most B+1 distinct values." |
| Q109 | LowerPrivileges | `literature/extracted/library/06_web_supplement_20261121/2606.20023_LowerPrivileges/2606.20023_LowerPrivileges_fulltext.txt` | L875-877 | "Starting from the SFT-initialized model, we then optimize the policy with GRPO (Shao et al., 2024) in the simulated multi-turn tool-use environment." |
| Q110 | LowerPrivileges | `literature/extracted/library/06_web_supplement_20261121/2606.20023_LowerPrivileges/2606.20023_LowerPrivileges_fulltext.txt` | L893-895 | "premature risk-tool use is penalized most strongly when it occurs without prior standard-tool attempts." |
| Q111 | PlanBench-XL | `literature/extracted/library/06_web_supplement_20261121/2606.22388_PlanBenchXL/2606.22388_PlanBenchXL_fulltext.txt` | L19-20 | "inferring implicit subgoals" |
| Q112 | PeakBench | `literature/extracted/library/06_web_supplement_20261121/2608.24509_PeakBench/2608.24509_PeakBench_fulltext.txt` | L120 | "execution-order perturbation recovers prerequisite and concurrency structure used by both benchmark dimensions." |
| Q113 | LangNCO | `literature/extracted/library/01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt` | L342-343 | "do not verify semantic agreement with the natural-language requirement." |
| Q114 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L356-359 | "CGAP takes these rules as application-supplied modeling inputs; automatically inducing them from natural-language descriptions is outside our scope." |
| Q115 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L544 | "to zero success on every seed) is isolated separately in the ungamability sweep" |
| Q116 | NOMOS | `literature/extracted/library/01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt` | L678 | "majority vote at the (type, predicate, tool) granularity." |

