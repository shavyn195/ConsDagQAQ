# 计划修复文献补查记录

日期：2026-11-26。范围为已有近邻的追溯式补查，不是穷尽检索，不能据此保证创新“无冲突”。

| 来源 | 核验程度 | 对本项目的约束 |
|---|---|---|
| [Plan Stability: Replanning versus Plan Repair](https://strathprints.strath.ac.uk/2776/) | 机构库全文已下载；摘要、§3–5.1等指定段落已读；页码未核实 | 计划保留、局部编辑和稳定性/代价权衡已有经典方法。详见独立阅读笔记。 |
| [HTN Plan Repair Algorithms Compared](https://doi.org/10.1609/icaps.v35i1.36131) | Crossref题名、五位作者、ICAPS 2025卷35(1)、297–305页和摘要已核对；出版页及PDF返回520，未读全文 | SHOPFIXER、IPYHOPPER、REWRITE有不同问题定义及搜索空间；不能把修复范围变化笼统称新。不能根据摘要断言具体方法缺少某功能。 |
| [ATG](https://arxiv.org/abs/2607.01942v1) | 沿用前次元数据和§4.3原文核查 | 受影响区域、冻结其余节点、接口保持和局部编辑已有直接先例。 |
| [Replan, Repair, or Edit?](https://arxiv.org/abs/2609.19654v1) | 沿用前次指定全文段落；本轮复核笔记与IPyHOPPER描述 | 分层修复、局部编辑、全局重规划及成功/保留/成本对比已有工作。 |

OpenAlex三条查询为 `IPyHOPPER hierarchical plan repair`、计划稳定性查询、动态CSP最小变化查询；实际完整查询与结果保存在 `repair_prior_art_search.json`。候选进入阅读不等于已核实全文。

下载成功/失败及实际URL保存在 `repair_prior_art_fetch.json`；HTN的Crossref响应保存在 `htn_2025_crossref.json`。机构库BibTeX导出另返回429，未密集重试；其网页的异常页码不照抄。PDF和抽取文本留作本地缓存，仓库只同步笔记、来源元数据与明确标记的书目条目。

新增书目：`fox2006planstability`（正文与主要书目核验，页码/DOI待补）；`zaidins2025htnrepair`（DOI注册元数据核验，最终原文核对待补）。ATG和Replan沿用 `literature/review_grpo_alignment_20261125/references.bib`，不新增重复键。

【研究裁决】本次实验有效性与方法新颖性分开判断。收益为正也不推翻先例；全局边界摘要、影响域和扩域若要作为新机制，必须先给出精确定义，并与已有增量/层级修复方法作有针对性的差异和实证比较。
