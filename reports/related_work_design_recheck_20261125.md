# 近邻论文复核：对 ConsDAG 贡献与实验设计的影响

日期：2026-11-25。范围：在已有近邻复核基础上，回读 CARL、CIRCE、SOTERIA、LogiSafetyBench 和 ToolPrivacyBench 的方法、数据质控、实验设计和局限；核验五篇 arXiv 页面元数据；新增 E3 结果重放工具的代码审查。不是全库精读或系统性全网查新完成声明。

## 结论

继续完成已排队的 ConsDAG 对照有价值，但当前不能宣称编译—规划分离已经胜出，也不能说整套实验足以支撑一个稳固的 CCF-B 结论。新增核验的 SCHEDBench 已做同实例语言表述变化与求解器评测；DisasterBench 已做类型化工具工作流、专家复核和首错归因；ICSE-NIER 2026 也已有规格到工具验证的架构先例。结合 CARL、CIRCE、SOTERIA、SafeOrchestrate、LogiSafetyBench、ToolPrivacyBench 与 NormWorlds-CF，ConsDAG 不能主张首次解耦、配对可执行评测、隐式约束基准、工具失败归因或安全规格执行门控。当前候选增量只可具体写为同一构造任务 E/I/N 呈现、类型化约束记录与固定规划器 faithful execution 的联合评测，以及记录字段错误如何跨切分/seed 映射到执行结果；这仍未证明自然语言语义有效。

## 近邻对照

| 工作 | 已做的方法和实验 | 对 ConsDAG 的约束 |
|---|---|---|
| [SCHEDBench](https://aclanthology.org/2026.findings-emnlp.852/) | Findings of EMNLP 2026。1,132 个来自六类调度源的实例，覆盖模板/实体/领域/释义/约束顺序表述变化；以求解器检查可行性和目标值，测试 13 个模型。两位专家独立核验 100 条分层实例，协商分歧后报告零语义错误。 | 直接先例已覆盖同一问题表述变化与约束忠实度。ConsDAG 不能声称表述配对或求解器约束验证新颖；差异应限于 E/I/N 状态和 typed record—固定 planner 的执行联动。它的双专家审核也构成比 ConsDAG generator-only witness 更强的数据质量参照。 |
| [DisasterBench](https://aclanthology.org/2026.findings-emnlp.1665/) | Findings of EMNLP 2026。233 个灾害响应任务、26 个开放工具；评测工具选择、参数绑定、依赖关系，并用 First-Point-of-Failure 定位首个根因。任务—工作流对经过四位相关领域 PhD 两轮审核。 | 类型化工具工作流基准、参考计划专家审核和一般失败归因已有先例。ConsDAG 应聚焦约束编译记录字段对固定规划器 faithful execution 的影响，而不是声称首次做 tool-constraint benchmark 或 failure diagnosis。 |
| [Towards Verifiably Safe Tool Use for LLM Agents](https://doi.org/10.1145/3786582.3786839) | ICSE-NIER 2026，页 201–205。Crossref 确认正式出版信息；本轮 ACM 正文返回 403，方法细节参考项目先前笔记并列为待核原文。 | 安全需求形式化、工具规格及验证已有架构先例；不应把规格—执行分层泛称新。投稿前需要重新取得并逐段核对正文，尤其不要依赖当前未存档的细节。 |
| [SafeOrchestrate](https://arxiv.org/abs/2611.09364) | 自然语言意图拆成原子目标，生成 LTL-style 规格，按角色映射到运行时 MCP affordances，并以 SMT guardrail 检查候选动作；在 smart home/greenhouse/industrial 仿真上与直接 LLM→MCP 比较。论文说明多数评测任务是单规则且空约束集，跨规则与安全约束 enforcement 主要用 worked example 展示。 | 系统层面已出现 intent→specification→grounding→runtime check 链条，故编译/执行分离不能单独称新架构。区别只能落在 ConsDAG 的受训逐请求 typed record、E/I/N 配对诊断和真实量化约束压力测试；不要把它的高动作准确率写成强约束验证证据。 |
| [NormWorlds-CF](https://arxiv.org/abs/2607.03957) | solver-verified executable normative worlds，输出证明/反证证书、support/status 与 paired-world change record；270 个 root families、1080 个 canonical-to-variant pairs，按 root family split，并在 4B GRPO 做三 seed 分析。 | 配对可执行世界、机器评分结构记录、按组切分与多 seed post-training 均有先例。它不从自然语言 E/I/N query 编译约束供规划器消费；ConsDAG 应把差异说成任务定义和字段接口的具体组合，不泛称“paired benchmark/solver verified labels”新颖。 |
| [AdaPlanBench](https://arxiv.org/abs/2606.05622) | 307 个 household tasks；用户与世界约束在多轮交互中渐进披露，违规动作后反馈并重规划；比较十个模型。论文披露约束检查与 rubric 依赖 LLM judge。 | 隐式/渐进披露约束和约束下规划已有基准，但其交互重规划与本项目单轮编译任务不同；它也提醒 judge-based 标注和确定性执行 oracle 是不同效度维度。 |
| [LogiSafetyBench / LogiSafetyGen](https://arxiv.org/abs/2601.08196) | LTL 监管 oracle、逻辑引导 fuzzing、可执行轨迹和隐式约束遮蔽；240 个金融、医疗和智能家居任务（120 个配对样本），13 个模型评测。作者报告对监管公式三轮独立审查，oracle 候选总接受率 73.9%；指令／遮蔽候选接受率 70.6%。 | 已有可执行隐式约束/合规基准和人审，不得宣称这类基准首次出现。它的隐含监管步骤与 Python/tool 轨迹不同于 ConsDAG 的 typed record 和 E/I/N 三态；但它使 ConsDAG 缺少语义核验成为核心局限。 |
| [ToolPrivacyBench](https://arxiv.org/abs/2606.28061) | 2,150 个案例：1,150 合成业务流、1,000 条从 tau-bench/API-Bank/BFCL/AppWorld 改造；模拟后端记录多工具参数与信息流。215 案例、21,994 个私有原子—工具对双人复标，原始一致率 93.1%、Cohen's κ=0.86，仲裁改动 499 项。 | 任务不同，不是语言约束编译器；但它给出强的数据质量参照：合成控制之外，加入公开任务结构、分层复标、一致率及仲裁。ConsDAG 目前这些独立语义可靠性证据均缺。 |
| [CARL](https://arxiv.org/abs/2607.04854) | 约束／去约束输入上的输出分布差作为训练信号，GRPO 为主，也测 PPO/DPO。BlocksWorld、TravelPlanner、T-Eval 三类任务；T-Eval 的隐式约束由 GPT-4o 抽取，128/553 用于训练。默认 Qwen3-8B、8 张 A100、64 查询批次、每题 8 rollout；分任务报告准确率、hard-constraint pass rate、P/R/F1。 | 约束奖励和隐式约束规划是直接先例；原 GRPO 创新不能恢复。我们自己的 E2 是分离系统对单体的条件比较，不可与 CARL 的大模型 RL 收益直接比较。模型辅助标签也不等于人类语义验证。 |
| [CIRCE](https://arxiv.org/abs/2610.41089) | LLM 提取变量／约束 CIR，再确定性编译为图，用于估计七个基准、四个模型上的解题正确率。每基准 200 个评测问题，三种数据切分 seed、GNN 四个 seed。全量检查可规则核验的结构；其余四个基准各人工抽查20例。 | 中间表示、抽取—编译分层、表示可靠性评测都已有先例。它预测难度，不进行约束规划，任务目标不同。其核验设计说明 ConsDAG 的 witness 证明世界内可行性，不证明自然语言金标语义正确。 |
| [SOTERIA](https://arxiv.org/abs/2611.17880) | 以形式化领域政策与工具合同验证分层计划，运行时拦截违规。207 个 Airline/Retail/Toolathlon 任务、4 个模型；对比无 guardrail、NeMo、AgentSpec、ABC；同时报告任务成功、违规和每任务成本；报告规格下零违规。规格从政策文档半自动生成，之后由作者人工验证并逐条做覆盖检查。 | 不能声称形式规格检查或执行安全新颖。它假设经过验证的领域规格；ConsDAG关注逐请求话语到类型记录的编译。我们的合成检查器在可信请求语义上不等价于 SOTERIA 的真实工具/政策验证。 |
| [SpecHarness](https://arxiv.org/abs/2609.29921) | 独立对比七个编译器的覆盖率、记录有效性和来源映射；从 agent 可见输入抽取 source-grounded obligation。 | 不声称首次单测约束记录；差异只能是数据结构、消费者合同、切分和失败分析的具体组合。 |
| [ATLAS](https://arxiv.org/abs/2509.25586)、[CGAP](https://arxiv.org/abs/2610.41040) | 分别含显隐式约束管理、规划检查，以及请求解析、证据/scope 与符号规划。 | 不能把“先解析再规划”“显隐式约束”“带证据 IR”说成空白。已在 `literature/review_20261125/` 留有细读笔记。 |

## 数据与实验的判定

v5/v6 数据的本机逐项复核结果见 [`dataset_quality_recheck_20261125.md`](dataset_quality_recheck_20261125.md)：两个版本的内部验证器与分片哈希均通过，v5 的 E/I/N 组、任务和 E/I 核心金标对齐；但自然语言隐式约束和 N 负例仍没有独立语义验证。这里的 PASS 仅指生成器/检查器规则通过。

- 当前 v5 每条约束由模板生成，并通过 witness/确定性检查器确认“生成世界里存在安全计划”。这是构造期正确性；尚无人类或独立来源验证自然语言请求与隐式约束是否语义对应。
- LogiSafetyBench 对规则 oracle 和具体任务做人工审核；ToolPrivacyBench 对代表案例检查并对分层子集复标，报告 kappa 和仲裁；SCHEDBench 由两位专家独立核验 100 条分层实例、协商分歧并报告零语义错误；DisasterBench 对参考任务—工作流做两轮专家审核。因此语义/标签可靠性不是可轻描淡写的 limitation，而是 C1 的直接证据缺口。现有 witness、schema 和配对完整性只能支持生成器内部自洽。
- v5 采用模板与工具组合留出、多模型规模和三训练 seed，有利于测受控泛化和优化方差；这些切分仍来自同一合成生成器，不等同于跨来源／真实任务 OOD。
- 受约束 faithful 同时要求约束安全与金标最小改动。必须与 safe success、记录 strict/core、invalid output 和 N 版 false alarm 并列；不能用单个 faithful 或 strict F1 代表整体语义能力。
- CARL 与 SOTERIA 的模型、数据和算力规模远超本项目，不能只拿结果表做数值优劣对比。应比较问题设定和方法假设；本项目内部的架构优劣只能来自完成的、输入信息完整的 E2，且须分别呈现监督 token、输入 token、运行时与失败样本。

## 当前执行状态及本轮代码

已同步的 A3 完整 metrics 文件时间为 2026-11-25 03:59:58（北京时间）；其 seed42 faithful 为 dev/tpl/tool/struct 0.9917/0.9257/0.4029/0.4271，完整基线同投影为 0.9867/0.9129/0.6429/0.7171。A3 在 tool/struct 上分别低 24/29 pp，并有 24–25% 无效输出；因此它是三态消融的初步单 seed 信号，同时存在契约格式混杂，尚无逐样本文件可运行配对 bootstrap。较早的服务器快照 03:34:32 仍记录 A3 训练中，之后 A4/A2/A1 状态未核实。2026-11-25 本轮非交互 SSH 两把本机密钥均认证失败，不能将旧 GPU 利用率当成当前状态；本轮未接触远端任务。

新增 `scripts/submission/analyse_e3_ablation.py`：只在四个 arm 已完成后，对每个 seed42 消融臂与完整基线使用原 E3 执行读取器重放；核对数据／源码／基线预测哈希、四切分 ID 一致性、E/I/N 成组完整性、同投影记录分数；给出按 E/I 同组 bootstrap 的探索性配对差值及逐 arm 成本。无 GPU调用，不会改动训练、预测、冻结分数或 v5 主表；区间仅条件于 seed42，不作跨 seed 推断或等价性声明。测试使用具有解析期望值的合成配对，四项通过。

本机没有 PyTorch，因此本轮不能在 Windows 上运行原有的 GPU 依赖 E3 测试；该套代码此前已按提交记录在服务器 CPU 上通过。本轮只新增的分析测试在本机全通过。启动真实分析前仍需拿到四个完整 metrics 与预测文件；当前 E3 结果尚未齐，故未提前计算或改写实验结论。

## 搜索范围与残余风险

新增 arXiv API 组合检索若干，部分 TLS 握手成功、部分失败；成功结果主要重遇已知直接近邻。另从本地已下载全文中识别出 LogiSafetyBench 和 ToolPrivacyBench 并逐篇核读。查询和错误记在 `literature/review_20261125/search_log.json`；五篇新增/复核论文的元数据和全文哈希在 `source_verification.json`。所有新增引用只按 arXiv 预印本处理；未独立核验的 venue 不写成正式发表。

**目前明确的差距**：完整公开输入 E2 仍待跑；外部规划器结果暴露当前消费者约束执行失败，不支持任意消费者可替换或无衰减；E3 其余三个消融臂未核实，A3 只有单 seed 且缺逐样本预测；自然语言金标语义尚未独立验证；外部任务/多源基准仍缺。C1 的基准范式已有更直接近邻，贡献需收窄到 E/I/N 三态、typed record 与固定 planner 的联合评测协议，并补独立语义证据；否则只能定位为受控合成分析。恢复实时监控后仍只按既有监督队列推进，依据公平 E2、E3 实际结果决定 C2 是否仅保留为参考架构。不要用新提示在 test 上反复调分，不要为填满 GPU 而另起同设计训练。
