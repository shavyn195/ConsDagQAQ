# ATLAS：约束管理、定向消融与成本报告

核验日期：2026-11-25（北京时间）。状态：读过方法、§4.1–4.3及Appendix D.7；未宣称复现。
题名：ATLAS: Constraints-Aware Multi-Agent Collaboration for Real-World Travel Planning。
作者：Jihye Choi、Jinsung Yoon、Jiefeng Chen、Somesh Jha、Tomas Pfister。
来源：[arXiv:2509.25586](https://arxiv.org/abs/2509.25586)，2025-09-29；本条引用预印本，未核实正式 venue。
本地全文：`literature/extracted/library/01_constraint_compiler/2509.25586_ATLAS/2509.25586_ATLAS_fulltext.txt`。
网页元数据及哈希：同目录 `source_verification.json`。

## 问题与机制

- 处理旅游规划中的显式、隐式及多轮更新约束。
- Constraint Manager 维护约束，Plan Critic 检查，Interleaved Search 补足信息。
- 已有专门的约束管理阶段；不能把“先提取约束再规划”当作我们的首创。
- 论文不是针对小模型 SFT 的 E/I/N 配对留出编译评测；两者研究对象不完全相同。

## 实验如何支撑主张

- §4.1（全文约650–680行）：所有方法最多120次工具调用；ATLAS设K=3、L=10。
- 底座包括Gemini-2.5-Pro和Claude-Sonnet-4；工具调用上限不代表token或延迟完全匹配。
- 去掉Constraint Manager后，macro hard constraint pass下降14.4个百分点（675–676行）。
- 对检查次数、搜索次数做曲线，分别对应组件的具体机制，而非只堆一个总消融表。
- 真实搜索及多轮场景的评判包含LLM judge；不能和我们确定性合成世界直接拼数值。
- Appendix D.7/Table11给运行时与输出token的25/50/75分位数。
- 3日旅行子组：ReAct中位1.41分钟、1.07k输出token；ATLAS为4.07分钟、9.52k。
- 输出token包括系统各模块，不能只计算最后一条答复。
- D.7叙述中的约6分钟与Table11的4.07分钟不是同一个聚合，引用时保留具体子组。

## 对ConsDAG的实际影响

- 重合：约束提取／管理、结构化规划、消融证明组件作用。
- 差异候选：独立训练的小编译器、控制表达与角色留出、同时审计记录和执行。
- 本篇未给出这些组合，不等于已证明所有文献都没有。
- E3每臂应说明改变了什么信息或监督信号，且完整基线按同一字段投影评分。
- N行的过度约束与非法输出必须保留；不能通过删掉失败提高效果。
- 成本应报告全系统用量和分布；多模块可以提高质量同时更慢，不预设速度优势。

## 可写／不可写

- 可写：ATLAS已显示专门管理约束具有价值，本文转向独立训练接口与受控错误诊断。
- 不可写：过去只做功能规划、没有约束管理；拆分自然更快、更便宜。
- 本轮不重跑ATLAS：任务、工具与判分不相同；它提供设计参照，不是已完成实验基线。
