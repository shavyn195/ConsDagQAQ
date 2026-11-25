# ②编译错误传导门控：近邻核验与修正

核验日期：2026-11-26。目标是判断候选机制的重叠，不是声称穷尽文献或确认录用潜力。

## 裁决

存在直接机制重叠。语义一致性核验、采样一致性、不确定性校准和接受/拒绝的组合已被SCP-NL2TL明确提出。不能把“编译噪声此前无人处理”或“语义证据＋一致性＋拒绝”写成新颖性主张。原建议须收窄。

仍可研究但未确立的新问题：在已有计划上，结合请求级约束证据与实际编辑后果，决定是否触发干预。必须超越仅检测翻译错误的强基线；将误差指标改成执行损害，或将已有门控迁移到DAG，单独都不自动构成方法创新。

## 直接近邻

### SCP-NL2TL

- 标识：https://arxiv.org/abs/2608.05439v1 ，2026-08-05；本轮核对官方摘要页及下载的v1原文。
- 作者：Yixuan Wang, Licheng Luo, Yu Fu, Kaidi Xu, Yue Dong, Mingyu Cai。
- 题名：Selective Conformal Prediction with Semantic Verification for Natural Language to Temporal Logic Specifications。
- 阅读范围：摘要、引言、§2–3（含式4–11、定理1）、实验设置相关段落；不是全文逐页复核。
- §3.1：回译后由LLM判断原指令一致性，结合按语义等价聚类的多次翻译一致性。
- §3.2：以校准阈值接受或拒绝；错误依据金标公式语义等价性，部署评分不读取金标。
- 风险定义是全输入流上“接受且翻译错误”的联合概率，不是接受样本中的条件错误率。
- 保证明确依赖同组校准/测试交换性，且为对校准及测试抽样取期望的保证，不能转述为任意OOD或每次运行保证。
- 还设有指令级OOD筛查；不能声称已有方法完全不处理分布变化。
- 影响：直接覆盖上一轮候选②的语义证据＋一致性＋校准拒绝部分。
- 区别候选：已读机制按公式翻译错误计损失；我们可以探索实际计划干预损害，但该区别尚未形成已验证的新算法。
- 发表状态：按arXiv预印本引用，未核正式会场。

### ConformalNL2LTL

- 标识：https://arxiv.org/abs/2504.21022v2 ，v2日期2026-02-20。
- 作者：David Smith Sundarsingh, Jun Wang, Jyotirmoy V. Deshmukh, Yiannis Kantaros。
- 题名：ConformalNL2LTL: Translating Natural Language Instructions into Temporal Logic Formulas with Conformal Correctness Guarantees。
- 阅读范围：官方摘要、原文摘要及引言、算法概述。
- 迭代构造LTL；主模型重复采样、共形预测集；不确定时咨询辅助模型，必要时咨询用户。
- 已直接指出错误形式化会使机器人计划偏离原始自然语言要求。
- 影响：“编译不可靠时再问或调用其他模型”已有直接先例。
- 发表状态：本轮按预印本引用。

### KnowNo

- 标识：https://arxiv.org/abs/2307.01928v2 。
- 题名：Robots That Ask For Help: Uncertainty Alignment for Large Language Model Planners。
- 本轮核验官方摘要及原文摘要、引言和框架示意。
- 共形预测驱动规划器何时寻求人类帮助，目标兼顾任务完成与减少帮助。
- 影响：规划端不确定性门控与追问并非新问题；不能仅靠改称“可信度”获得新颖性。

### QuickXplain

- 原文：https://cdn.aaai.org/AAAI/2004/AAAI04-027.pdf 。
- Ulrich Junker，QUICKXPLAIN: Preferred Explanations and Relaxations for Over-Constrained Problems，AAAI 2004。
- 本轮读取摘要、引言及最小冲突示例。
- 明确讨论建模错误、冲突解释、偏好松弛和分治加速，使用通用CP/SAT/DL求解器。
- 影响：删约束重求解、冲突子集及相应剪枝不能直接作为新方法。
- 注意：冲突定位不等于自然语言语义错误归因；可满足的错误约束也可能损害计划。

## 仓库既有近邻复核

- SOTERIA：https://arxiv.org/abs/2611.17880 ，§2.1明确LLM自动形式化后人工逐条核验；其限制承认形式化质量与工具契约假设。不是“不知道约束会编错”，而是采用人工验证处理这一前提。
- ATLAS：https://arxiv.org/abs/2509.25586v1 ，§3.3区分规划失败和检索信息不足，并基于请求、约束、域及失败历史诊断。不能声称“其他方法都把失败归因于规划”；未据此声称它已经解决请求级编译错误门控。

## 应如何检验剩余差异

最少包含：始终接受、置信度门控、语义核验与一致性融合门控（SCP-NL2TL思想适配）、冲突诊断门控、加入计划影响信息的候选方法。各臂报告复核预算、接受/执行覆盖、真实约束满足、必要修复收益、无约束误改和总成本。

若计划影响信息不优于相同预算的语义门控，不能把它立为方法主贡献。若收益仅来自更多拒绝或丢弃难题，同样不成立。部署决策不得读取金标safe、金标约束或witness；事后评价可用金标。

## 检索记录

- 在线来源：arXiv官方摘要/PDF、AAAI原文、OpenAlex、Crossref。
- OpenAlex查询：natural language formal specification semantic validation uncertainty；natural language temporal logic translation uncertainty conformal。
- Crossref核回Reiter 1987书目信息（10.1016/0004-3702(87)90062-2），未读取原文，未据元数据展开机制结论。
- QuickXplain的Crossref标题搜索未返回原始2004条目，随后直接核对AAAI原文，未误引2021后续论文为原始工作。
- 原始响应和PDF/文本缓存保存在本目录但不入Git；它们供复核，不作为额外论文贡献。
- 此次是目标近邻检索。尚不能得出“无完全相同方法”或“新颖性无冲突”。
