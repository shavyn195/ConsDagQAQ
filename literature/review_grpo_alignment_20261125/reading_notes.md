# 原文核验笔记（2026-11-25）

范围是承重主张核验，非逐篇全章节复现。下列位置是原文定位，结论只限定于已检查内容。摘要级条目明确分开。完整中文研究裁决见 `reports/clip_grpo_literature_audit_20261125.md` 和 `reports/parser_planner_diffusion_review_20261125.md`。

## 后训练及对比学习

### SFT or RL? — 2504.11468v1

- 原文：https://arxiv.org/abs/2504.11468v1
- 核验：实验Table3及相邻结果解释。
- 对象：视觉语言模型，多模态推理蒸馏与后训练。
- Inst 7B：32.5→19.8，下降12.7个百分点，而非普适平均下降12.7%。
- Base 7B：30.7→25.7，下降5个百分点。
- 支持：特定SFT数据/初始化会影响后续RL。
- 不支持：所有任务SFT和GRPO不兼容；本项目只需格式冷启动。
- 未复现其训练，不以其具体收益估计本项目成本或效果。

### Difficulty-Distinguish View — 2511.06722v1

- 原文：https://arxiv.org/abs/2511.06722v1
- 核验：PISM/CMAB难度分层定义及GRPO-only对照结论。
- 支持：该视觉设置里训练题难度与训练范式交互。
- 不支持：一字段近失配负例天然是中等难题；删除全部困难题。
- AAAI2026来自arXiv注释；本轮出版页访问失败，不称独立出版全文核验。

### It Takes Two: Your GRPO Is Secretly DPO — 2510.00977v3

- 原文：https://arxiv.org/abs/2510.00977v3
- 会场记录：https://openreview.net/forum?id=evlIZKNVt7
- 核验：Definition3.1、Proposition3.2、2-GRPO实验统计。
- 关键对象：序列策略概率的广义对比结构，命题使用二元奖励条件。
- 支持：较小组的可行性值得测量；报告保留97.6%性能、12.5%rollout、21%时间。
- 不支持：与CLIP的表示InfoNCE恒等；手工离线负例就是on-policy样本。
- G=2的二元混合组概率2p(1−p)，p接近1时学习信号稀少。
- 会场为NeurIPS Efficient Reasoning Workshop Spotlight，不是主会。

### SupGRPO — 2609.07081v1

- 原文：https://arxiv.org/abs/2609.07081v1
- 核验：文本定位/识别任务和Eq.9。
- 方法：GRPO与匹配后坐标token监督相加，−J_GRPO+λL_SFT-coordinate。
- 支持：联合监督与RL可以形成任务特定互补。
- 不支持：损失相加必然不稳定、advantage混合必然更优。
- 不将视觉定位/识别分工直接替换成约束绑定/规划分工。

### Why Does RL Generalize Better Than SFT? — 2602.10815v1

- 原文：https://arxiv.org/abs/2602.10815v1
- 正式页：https://openaccess.thecvf.com/content/CVPR2026/html/Lu_Why_Does_RL_Generalize_Better_Than_SFT_A_Data-Centric_Perspective_CVPR_2026_paper.html
- 核验：§4–5、Tables1–2。
- G=8按采样成功数区分难度，全错定义hard。
- 7B hard-only ImageNet-R下降14.07pp，中难SFT的平均OOD比GRPO高0.93pp。
- 支持：难度和有效采样组是重要控制变量。
- 不支持：难负例的字符串相似度就是采样难度；hard在所有任务都应删除。
- 任务优势为零不排除KL/辅助损失梯度。

### LAPO — 2605.20555v3

- 原文：https://arxiv.org/abs/2605.20555v3
- 核验：冻结与可训练策略的logit平均、训练概率比及推理方式。
- 生成与更新对应混合策略，而非只替换一个参考KL项。
- 主要评测也使用混合策略；单模型需要额外蒸馏。
- 不支持：两模型logit平均能免费保留SFT能力、无额外推理开销。

### AMIR-GRPO — 2601.03661v1

- 原文：https://arxiv.org/abs/2601.03661v1
- 核验：GRPO结合组内偏好对比正则的方法。
- 是“对比偏好＋GRPO”的直接近邻。
- 不等于CLIP双塔，但足以否定仅靠两个名称组合主张首次。
- 本项目若继续，须解释新的监督对象、语义正确性和可归因收益。

### S-GRPO — 2604.16557v2

- 原文：https://arxiv.org/abs/2604.16557v2
- 核验：有条件的专家完成注入机制。
- 支持：外部正确样本与RL结合有明确先例。
- 不支持：任意手写样本可直接当作旧策略iid rollout。
- 混合采样必须说明真实概率、目标与估计方式。

### PRISM — 2604.28123v4

- 原文：https://arxiv.org/abs/2604.28123v4
- 核验：分阶段SFT/判别对齐/RLVR和AppendixB联合控制。
- 联合61.4，串行66.2，SFT→GRPO61.8，是该论文配置的结果。
- 更新预算匹配不等于FLOPs匹配。
- 不支持：联合必然优于串行；也不支持相反的一般结论。

### Rufus-Air — 2609.29421v2

- 原文：https://arxiv.org/abs/2609.29421v2
- 来源：用户随后粘贴的微信文章定位到原论文。
- 核验：摘要、§2阶段顺序、SFT与难度筛选段落、结论。
- 106B总参数、12B激活MoE，SFT后接七个RL阶段。
- 作者明确认为SFT建立能力基础，不只教格式。
- 难度筛选基于采样，可靠奖励与系统基础设施是配方的重要部分。
- 不支持：本项目4B直接复制八阶段即可获益；阶段顺序具有普适最优性。
- 未复现大规模多节点训练。

## 解析、传播与工作流架构

### ATLAS — 2509.25586v1

- 原文：https://arxiv.org/abs/2509.25586v1
- 本地全文在既有 `literature/extracted/library/01_constraint_compiler/2509.25586_ATLAS/`。
- 核验：§3.1–3.2、Fig.3及AppendixTable5a。
- ConstraintManager从请求/工具结果提取显式和隐式要求，接Planner/Checker。
- 有/无管理器消融，特定TravelPlanner开发配置硬约束宏观通过率60.00→74.44%。
- 不把其implicit commonsense等同本项目I模板。
- 直接限制“前置解析器提升CSR”的新颖性主张；不是小模型训练的同一实现。

### Dr.Aid — 2110.01056v1

- 原文：https://arxiv.org/abs/2110.01056v1
- 另有框架摘要：https://arxiv.org/abs/2109.00838v1
- HTML不可用，PDF下载并提取全文，核验§3.2.1–3.2.2及相关工作。
- data rules：attributes、obligations、validity binding和activation condition。
- flow rules：propagate、edit、delete，针对输入输出端口处理规则。
- 允许多输入多输出数据处理与派生数据的规则变化。
- 其相关工作还讨论IFC、Meta-code、CamFlow等，传播并非2026年新空白。
- 不等同从自然语言训练编译器，也不自动解决本项目五类联合规划。

### CaMeL — 2503.18813v2

- 原文：https://arxiv.org/abs/2503.18813v2
- 核验：§5.3–5.4和工具执行前策略检查。
- 对数据值记录来源、允许读者；计算依赖图。
- STRICT模式将控制条件纳入块内变量依赖。
- 工具调用前检查输入及其依赖；拒绝或在部署场景要求授权。
- 重点是抵抗不可信数据/提示注入，不是学习最优DAG。
- 直接否定“agent没有信息流/约束传播工作”。
- 作者也说明不可回滚副作用等限制；不能说整个真实系统无条件安全。

### 其他近邻的证据等级

- CGAP：https://arxiv.org/abs/2610.41040v1；既有方法段记录，目录转PDDL、语言请求转目标/约束、求解和执行检查。
- LangNCO：https://arxiv.org/abs/2610.23190v1；既有方法段记录，语言规则、动作mask、未来完成条件。
- CONSTRAINER：https://arxiv.org/abs/2611.10627v1；既有方法段记录，约束算子图、GNN及求解条件化。
- GNNVerifier：https://arxiv.org/abs/2603.14730v2；既有方法段记录，请求条件图验证和局部修复。
- GRAFT：https://arxiv.org/abs/2605.11706v1；既有方法段记录，图工具表示、后继关系学习。
- IMR-LLM：https://arxiv.org/abs/2603.02669v1；本轮仅元数据与摘要，析取图、确定性求解、程序生成；不确认ICRA发表。
- GraphPlanner：https://arxiv.org/abs/2604.23626v1；本轮仅元数据与摘要，图记忆增强路由，不根据名称推断它完整解决约束传播。

## 具身与离散扩散

### Diffuser — 2205.09991v2

- 原文：https://arxiv.org/abs/2205.09991v2
- 核验：摘要、§3规划方法。
- 轨迹分布经去噪采样，目标引导/inpainting构成规划条件。
- 可借鉴将生成与规划联合、条件补全的思想。
- 非离散工具图，不证明本项目checker可直接求梯度。
- 不据机器人结果宣称工作流规划更快。

### Diffusion Policy — 2303.04137v5

- 原文：https://arxiv.org/abs/2303.04137v5
- 核验：§1、§3。
- 条件动作扩散表示多峰动作分布，联合动作序列与滚动时域控制。
- 视觉条件特征复用；比较CNN和时间序列Transformer。
- 此文为原RSS论文的扩展版本；本轮不逐表复核全部机器人实验。
- 是视觉运动策略，不将其泛称具有语言输入的VLA。
- 多解不由扩散独占，自回归概率模型也能多峰采样。

### LayerDAG — 2411.02322v2

- 原文：https://arxiv.org/abs/2411.02322v2
- 核验：§3.1–3.4。
- DAG按拓扑层生成，每层节点/边集合通过离散扩散细化。
- 双向消息传递编码，节点去噪用Transformer，边去噪用节点配对。
- 讨论置换不变性及分层去噪步数。
- 已有“GNN＋Transformer＋扩散DAG”先例。
- 无环性不是用户隐私/总预算/权限满足保证。

### DiG-Plan — 2606.05728v1

- 原文：https://arxiv.org/abs/2606.05728v1
- 核验：§3、§4.1–4.5。
- 扩散工具集合提案→AR依赖边→轻量价值选择器。
- 选择器训练目标包含参考ToolF1/EdgeRecall，推理仅用可观察特征。
- 文章注意oracle选择不可部署，并比较AR采样设置。
- 工具结构可执行过滤并非全部用户约束检查；不能把其结果冒充严格safe success。
- 直接近邻：扩散探索多种工具组合，减轻早期承诺。
- 本项目需新的约束干预机制，不能只更换数据。

### CoDA — 2610.15177v1

- 原文：https://arxiv.org/abs/2610.15177v1
- 核验：§4、§5.1–5.2。
- 策略由上游给定，框架重点是去噪过程执行策略。
- 从整段clean proposal定位受约束区域，投影后用于逆转移。
- 支持工具能力、参数、URL、来源、信息流。
- 完整多token值以trie保持组合一致性，不是独立逐token白名单。
- 规则的语义边界和上游提取准确性不能自动保证。
- 不声称CoDA仅管格式；也不声称其完整解决全局DAG资源调度。

### Plan-and-Patch — 2610.10786v1

- 原文：https://arxiv.org/abs/2610.10786v1
- 核验：§4.1–4.3。
- 层级计划表示，执行反馈定位失败区域，保留上下文再填补。
- AR对照也使用FIM，不能只与从头生成比较。
- 训练包括生成与修复，部分参考辅助数据与非参考执行反馈分开。
- 交互评估把修复后的计划从初始环境重放。
- “只修坏的地方”已存在；保留不可逆已执行状态是不同且更严格的任务设定。
- 不宣称改变设定就足够形成新方法。

### LTLDoG — 2405.04235v2

- 原文：https://arxiv.org/abs/2405.04235v2
- 核验：§III。
- 部署时给定LTLf公式，以满足值函数梯度引导逆扩散。
- 约束涉及时序访问与避障，而不只是无碰撞静态安全。
- 符号约束指导扩散并非新概念。
- 离散工具世界需要自己的语义及不可微检查处理。

### The Bitter Lesson of Diffusion Language Models for Agentic Workflows — 2601.12979v3

- 原文：https://arxiv.org/abs/2601.12979v3
- 本轮只读摘要与章节结构，全文已缓存待后续方法核查。
- 摘要报告所测dLLM的长程反馈及严格格式困难。
- 用作风险提示，不作为扩散必然失败的证据。
- arXiv作者注释写ACL2026主会；本轮未做出版页独立核验。

## 不进入事实依据的内容

OpenClaw-Combine、Visual-R1精确身份、Qwen所指GFlow/VECO-GNN/Grapheon RL/ACT/CLM、官方“七类”条款尚未完成定位。未搜到不代表不存在。所有“首次”“无冲突”“成本低一个数量级”主张均未因此成立。
