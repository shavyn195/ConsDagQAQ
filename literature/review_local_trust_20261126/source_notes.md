# 本地部署与可信约束：来源核验记录

日期：2026-11-26。此轮为目标段落精读和概念核验，不宣称新增论文均已逐页精读，也不是穷尽新颖性检索。沿用仓库已有原文，不重复下载PDF。

## Beyond ReAct

- 标识：[2511.10037v2](https://arxiv.org/abs/2511.10037v2)。官方摘要页题名、作者已在线确认；正式会场未独立核查。
- 原文：`literature/paper_texts/Beyond-ReAct_2511.10037.txt`。
- 定位：第2页贡献列表，文本行124–140；实验设置GPT-4o执行器行402；RQ3行931–955。
- 方法：planner-centric plan–execute，DAG节点工具选择与边依赖建模；SFT后RL。
- 数据：ComplexTool-Plan分级训练/规划评测；StableToolBench外部端到端评测。
- 作者把系统实验效果明确列为一条贡献，支持“方法＋基准＋实证”的组织方式。
- 范围修正：RQ3承认DTA-Llama成功率更高；非迭代规划及2.29次决策轮次是其强调的效率维度。不能推广为所有范式成功率最佳。
- 不支持：完全本地推理链、强模型不适合可信场景、我们的新方法已经成立。

## ATLAS

- 标识：[2509.25586v1](https://arxiv.org/abs/2509.25586v1)。官方摘要页题名、作者已在线确认。
- 原文：`literature/paper_texts/ATLAS_2509.25586.txt`；已有BibTeX在`literature/review_20261125/verified.bib`。
- 读取：约束形式化、代理分工及附录D.2 Table5(a)。
- 代理：检索、约束管理、规划、检查、检索建议。
- 消融条件以表格说明为准：TravelPlanner validation，Gemini-2.5-pro，5次检查、10次交错检索。
- 有/无约束管理器：Hard Constraint Macro 74.44%/60.00%，Final Pass44.44%/30.00%。
- 适用解释：支持特定强模型旅行规划中的约束管理机制作用；不是全场景理论保证。
- 后续：若做本地DAG适配，说明信息接口和迭代次数变化，不能将适配结果冒充官方复现。

## Access control for Data Spaces

- 标识：[2504.13767](https://arxiv.org/abs/2504.13767)。作者Nikos Fotiou、Vasilios A. Siris、George C. Polyzos与原文及官方摘要页一致。
- 原文：`literature/trusted_constraints/2504.13767.txt`；读取摘要、引言、§II。
- 核心机制：上下文代理中的细粒度访问控制，持续评估和撤销，对对象类型、对象及属性控制Read/Write/Subscribe。
- 扩展：允许数据所有者维护政策管理点，使用Verifiable Credentials。
- 支持本项目授权、对象范围、政策所有权动机。
- 该文的离线/不可达情形涉及访问控制可用性，不能转换成所有LLM推理必须离线的论据。
- 本次不援引未复核的性能数字。既有报告的ICIN DOI未在本轮独立核查；新增BibTeX明确按预印本记录。

## Dr.Aid

- 标识：[2110.01056v1](https://arxiv.org/abs/2110.01056v1)；沿用先前核验条目。
- 原文：`literature/review_grpo_alignment_20261125/2110.01056v1.txt`。
- 已有笔记及本轮复核定位：数据治理义务、数据流与规则流结合，§3.2.1–3.2.2。
- 核心区分：义务不止访问许可；多输入/多输出变换可能传播、修改或删除政策关联。
- 因此“约束传播从未有人做过”不成立。
- 支持治理约束及后续规则语义选择；不证明现有五类已覆盖全部义务与传播语义。
- BibTeX沿用`literature/review_grpo_alignment_20261125/references.bib`，不新增重复条目。

## Styx

- 标识：[2604.04082](https://arxiv.org/abs/2604.04082)。官方摘要页作者/题名与本地原文一致。
- 原文：`literature/trusted_constraints/2604.04082.txt`，读取摘要及引言。
- 方法：TEE保护的语言运行时/中间件沙箱，与sticky policies联合实施数据政策。
- 范围：使用中数据、数据生命周期及派生输出、动态多方协作。
- 引言明确讨论AWS/GCP/Azure云机密计算，不能据此主张可信场景一律排除云。
- 本项目没有该执行机制；只能借用治理需求的动机，不能借用其安全保证。
- 没有迁用其效果数字或声称复现。正式会场未独立核查。

## W3C ODRL

- 官方标准：[ODRL Information Model 2.2](https://www.w3.org/TR/odrl-model/)；在线获取成功，选段保存在`odrl_source_check.json`。
- 核对§2.5 Constraints、§2.6 Rule/Permission/Prohibition/Duty。
- Permission可以附带必须先完成的Duty；Constraint使用操作数与关系运算符；同一规则上的多个Constraint按合取解释。
- 标准是语义参考，不是证明规划算法有效的论文；ODRL约束语义不等于本项目解析器当前schema。
- 用途：避免随意发明“可信约束官方五类/七类”的说法。使用某些概念不等于完整实现ODRL标准。

## 收集日志与限制

| 来源 | 核验状态 | 本次动作 |
|---|---|---|
| Beyond ReAct | arXiv元数据＋指定全文段落 | 新增本轮BibTeX；明确SOTA范围和云执行器 |
| ATLAS | 已有条目，在线复核＋Table5(a) | 沿用原BibTeX；条件按表格的10次交错检索记录 |
| Access control for Data Spaces | arXiv元数据＋原文概念段 | 新增预印本BibTeX；不扩展成本地LLM强制要求 |
| Dr.Aid | 既有全文核验，本轮复查相关概念 | 沿用原BibTeX；不重复下载 |
| Styx | arXiv元数据＋摘要/引言 | 新增预印本BibTeX；明确未实现TEE |
| ODRL | 官方标准页面 | 新增标准条目与选段缓存 |

初次arXiv API请求超时，之后官方摘要页请求成功；没有将超时当作论文不存在。原文SHA256与线上元数据保存在`source_check.json`。本轮未系统检索全部本地Agent、机密计算、计划修复文献，不支持“首个”“无冲突”断言。
