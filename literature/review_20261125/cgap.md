# CGAP：公开输入公平、计算预算与编译边界

核验日期：2026-11-25（北京时间）。状态：读过方法、§3、Limitations及Appendix D/E相关实验。
题名：Capability-Grounded Agentic Planning。
作者：Shikha Shrestha、William Yeoh、Ning Zhang、Yevgeniy Vorobeychik。
来源：[arXiv:2610.41040](https://arxiv.org/abs/2610.41040)，2026-10-29；未核实正式 venue。
本地全文：`literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt`。
网页元数据及哈希：`source_verification.json`。

## 问题与机制

- 工具目录确定性编译为PDDL；LLM把用户请求变成目标；经典规划器求计划。
- 运行时补实体级调用，检查来源与依赖，另由LLM核实请求结果是否交付。
- 同时包含请求解析、证据来源与scope语义；不能将其缩成“只编译目录”。
- 正确性保证限于编译后的抽象模型，不等于自然语言解析正确。
- Limitations承认尚未全面审计请求解析错误、错误证据绑定及验证器误接受。

## 实验设计

- 四组任务：120 ToolSandbox、250 ComplexFuncBench、200 BFCL多轮、114 tau2零售。
- 三种底座：gpt-oss-20b、Qwen3-32B、GPT-5-mini。
- 每任务每配置运行三次；二元结果按多数票，部分分数取均值（806–810行）。
- 这是推理重复，不是三个训练seed；不能照搬其方差解释。
- 任务级配对bootstrap，10000次；不可把其多数票分数直接比单次榜单。
- 信息对照给普通代理相同公开dependency notes。
- 计算对照的自检次数与token上限先在留出任务校准后冻结。
- 三个基准实际token与CGAP相差不超过5%；零售没有校准集，反而多17%，论文明确披露。
- LLM规划器消融获得同一规划问题、允许一次修复，其余执行机制保持一致（849–853行）。
- 强GPT-5-mini下符号对LLM规划的增益较小，仅ToolSandbox的差值区间排除零；不支持“符号必胜”。

## 成本与边界

- Table9只报gpt-oss-20b的平均token：plain 61.7/104.3/128.6k，compute-matched 92.8/152.3/160.0k，CGAP 97.6/146.2/164.7k。
- 顺序为ToolSandbox／ComplexFuncBench／BFCL；这些不是我们任务的推理成本。
- 相同公开信息与相同计算预算是两个不同对照维度，不能互相替代。

## 对ConsDAG的行动

- 完整单体需要政策、显示名称、数据类别、任务结构与工具属性；原不完整输入E2只作诊断。
- 完整公开输入E2已单独排队；不更改运行中的旧臂或追认原始预注册。
- 同训练行、epoch、LoRA配置只能称同配方，需单独披露prompt和答案token。
- 同一编译输出交给不同消费者，才是可解释的消费者比较；不额外给某一臂隐藏gold。
- 本文可能贡献在受训练的语义接口及字段／seed诊断，不在“首次神经符号分离”。
- CGAP承认未做某种审计，只能证明其自身范围，不能推出全领域空白。
