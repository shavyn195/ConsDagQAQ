# 可复用研究方法

2026-11-26。用户提供的研究方法已经整理为五个独立技能，均带`agents/openai.yaml`并通过技能结构校验。技能是研究流程，不是文献事实或录用保证；“90%顶会论文如此”等未经统计的说法未写入规则。

| 技能 | 用途 | 文件 |
|---|---|---|
| 从实验发现问题 | 历史逐题数据、竞争解释、最小判别实验 | [experiment-driven-discovery](C:/Users/19371/.codex/skills/experiment-driven-discovery/SKILL.md) |
| 原文核查创新边界 | 阅读问题/方法/假设/实验/附录后才判断重叠，记录未读范围 | [fulltext-novelty-audit](C:/Users/19371/.codex/skills/fulltext-novelty-audit/SKILL.md) |
| 针对真实缺陷改进 | 缺陷→原因→针对性修正→受控验证，区分算法和实现问题 | [boundary-driven-improvement](C:/Users/19371/.codex/skills/boundary-driven-improvement/SKILL.md) |
| 场景适配建模 | 由真实场景要求推导建模、部署约束和公平对照 | [scenario-grounded-modeling](C:/Users/19371/.codex/skills/scenario-grounded-modeling/SKILL.md) |
| 简化与效率 | 控制质量与覆盖，衡量全部训练/推理/复核成本 | [simplification-efficiency-research](C:/Users/19371/.codex/skills/simplification-efficiency-research/SKILL.md) |

本项目固定为可信数据空间；机器人/具身论文只提供可迁移机制。①本地类型化解析、②具体可靠性改进、③E/I/N配对评测要共同回答真实的数据使用控制问题。相同组件既不是整体撞车的证明，也不能仅靠换场景就变成新方法。

当前应用实例：[历史逐题审计](history_and_edit_impact_readout_20261126.md)、[隐私与授权分层及下一项实验](trusted_space_family_audit_20261126.md)。新实验必须保留负结果、全种子和旧协议，原文核查与资源相称的可证伪小实验可以共同推进。
