# 2026-11-25近邻精读与核验记录

范围：针对当前C2编译—规划分离与C3记录／执行诊断，复核四篇最直接近邻。不是全库精读完成声明，也不是系统性最新检索完成声明。

| 论文 | URL | 本轮阅读记录 | 对当前工作最重要的约束 |
|---|---|---|---|
| ATLAS | https://arxiv.org/abs/2509.25586 | [笔记](atlas.md)；已有本地PDF，回读方法、实验及成本附录 | 已有显隐式约束管理；多模块不自动更快 |
| CGAP | https://arxiv.org/abs/2610.41040 | [笔记](cgap.md)；已有本地PDF，回读方法、对照、消融、局限 | 相同公开信息与匹配计算预算是两个独立要求 |
| Coordination Tax | https://arxiv.org/abs/2610.37700 | [笔记](coordination_tax.md)；新取16页全文 | 3.22倍不是我们的方法成功门槛；已有异构角色对照 |
| SpecHarness | https://arxiv.org/abs/2609.29921 | [笔记](specharness.md)；新取16页全文 | 已比较七个独立编译器的覆盖与记录有效性 |

四篇arXiv页面均实际返回成功，作者、题名、日期由页面citation元数据核验；当前只引用为预印本，不编造会议或CCF等级。原始元数据、检查UTC时间及所读PDF／文本SHA-256保存在 `source_verification.json`，参考条目见 `verified.bib`。ATLAS、CGAP沿用仓库PDF，另两篇缓存不提交；公开URL足以重新获取，版本漂移时以哈希识别。

本轮另尝试OpenAlex的两个组合检索：`constraint compilation agent planning evidence intermediate representation`、`typed constraint extraction compiler tool planning`。两次均在SSL握手超时，记录见 `search_log.json`；没有把失败检索当成“没有相关论文”。未完成全覆盖的新文献查漏。

当前论文主张的修改及实验行动见 `reports/literature_architecture_recheck_20261125.md`。原投稿方案作为历史材料保留，工作草稿按本轮事实收紧。

新增成本分析不依赖论文数字：服务器CPU从12,000条冻结训练数据重放真实提示与target，见 `outputs/submission/audit_20261125/training_token_budget.json`。所用历史编译器源码从Git提交 `0487907c7dd2e9191416a6787b46ebf0b61d5ee4` 找回，与原run的SHA-256完全相同；不是按当前代码猜测旧提示。tokenizer历史哈希未保存，因此只确认当前部署同模型tokenizer的重放计数。
