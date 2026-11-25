# 检索和来源日志

日期：2026-11-25。检索用于近邻核查，不是穷尽系统综述。原始API/HTML/PDF缓存留在本机，Git保存紧凑元数据、本文、笔记和来源哈希。

## 第一阶段：CLIP/SFT/GRPO主张

针对用户提供的标题与数字，使用arXiv Atom API、OpenReview、Crossref、CVF以及项目文档核对。

- SFT or RL?：Table3核对32.5→19.8，修正百分点/相对比例和领域外推。
- It Takes Two：arXiv版本与OpenReview记录比对，确认workshop层级，核对对比目标的适用条件。
- SupGRPO、DC-SFT、LAPO、AMIR-GRPO、S-GRPO、PRISM：逐项核对承重方法和相关消融。
- OpenClaw-Combine精确名称未定位可确认原文，不能据此宣称不存在。
- AAAI出版页访问520；CVF正式DC-SFT出版页可用。
- 工程主张核对TRL GRPO/vLLM及PEFT DeepSpeed文档。
- 微信最初返回验证页；用户后续粘贴全文后，定位Rufus-Air 2609.29421v2并核验原文。

## 第二阶段：解析器、传播与Qwen命名工作

- 在本地库查ATLAS、CGAP、LangNCO、CONSTRAINER、GRAFT、GNNVerifier等。
- ATLAS的约束管理器消融是“前置解析器”直接先例。
- arXiv查询 `all:"Dr.Aid"` 得到2110.01056与2109.00838；前者HTML404，改用PDF并成功提取方法。
- 获取CaMeL 2503.18813v2，阅读capabilities、dataflow及policy enforcement段落。
- 查询IMR-LLM、GraphPlanner获得匹配元数据；它们的会场信息未全部独立核验。
- GFlow查询存在大量其他领域同名结果；VECO-GNN、Grapheon RL、ACT、CLM没有完成精确对应，不作为核心论据。

## 第三阶段：具身扩散与DAG

原始结果：`diffusion_search_20261125.json`（本地缓存）。每个查询最多20条，按相关性排序，存在召回限制。

1. `all:diffusion AND (all:workflow OR all:tool-planning OR all:agentic)`
2. `ti:LayerDAG OR ti:DAGDiff OR (all:diffusion AND ti:acyclic)`
3. `ti:"Diffusion Policy" OR ti:"Planning with Diffusion" OR ti:"Motion Planning Diffusion"`
4. `all:diffusion AND ti:planning AND (all:constraint OR all:safe)`

重点选取直接威胁宽泛新颖性主张的工作，未仅选支持本项目的文献：

- DiG-Plan：扩散工具集合提案＋依赖预测。
- CoDA：扩散期间施加工具/参数/信息流策略。
- Plan-and-Patch：生成和局部修复。
- LayerDAG：分层离散扩散生成DAG。
- Diffuser、Diffusion Policy、LTLDoG：具身规划方法依据。
- The Bitter Lesson：摘要级失败证据，提醒不能把并行生成等同实际agent优势。

原文获取记录在`diffusion_fulltext_retrieval.json`；结构化题名/作者/日期在`architecture_diffusion_sources.json`。固定HTML版本与API返回的最新版本分开记录，不把最新摘要自动当成旧版全文内容。引用以实际读取版本为准。

## 限制与后续

没有网页搜索连接器，本轮通过公开原始API/论文页面和本地全文开展核查。对若干会场仅有作者arXiv注释；未写独立确认发表。没有查全“首个可信数据空间数据集”的证据，不作首次主张。

未来若实际实施扩散试点，需进一步核对DiG-Plan、CoDA、Plan-and-Patch的代码、许可、复现条件和适配基线；当前阅读确认的是机制近邻，未运行这些官方实现。

## 第四阶段：多模态设想的快速近邻筛查

用户提出多模态工作流后，检索视觉/多模态agent与隐私、约束、安全及工具规划的交集，另查VisualAgentBench/OSWorld等任务。原始查询在`multimodal_search_20261125.json`本地缓存，核心条目元数据另存`multimodal_sources.json`。

选取TRACER、MMA-SafetyBench、Penny Wise Pixel Foolish、DWIM和PriMobiBench，仅核对摘要；前四篇获取全文与章节目录，不称已经精读方法。未运行其代码。API结果中首次公开日期晚于2026-11-25的条目剔除，不用未来条目建立新颖性结论。

用户随后澄清唯一目标是CCF-B。此次快速筛查用于避免凭“多模态”标签盲目转向，不构成启动新训练、求职优化或机器人任务的决定。

## 第五阶段：Qwen局部图修复设想核验

2026-11-25，在本地全文库搜索 `graph repair|plan repair|local repair|局部修复|图编辑|minimal.*repair|minimum.*repair`，找到2609.19654；复核既有Plan-and-Patch的Related Work，沿其参考文献定位Atomic Task Graph，再读取ATG原文§4.1/§4.3/§7。不是依据二手论文断言ATG的方法。

两次arXiv API `id_list`查询分别为`2610.10786,2609.19654`和`2607.01942`。返回元数据已保存到`outputs/architecture_20261125/local_graph_repair_source_check.json`；固定版本与全文分别匹配。ATG HTML获取成功，原文缓存不随本次提交上传。阅读笔记为`local_graph_repair_notes.md`，研究裁决为`reports/local_graph_repair_review_20261125.md`。

| 条目 | 核验状态 | 裁决/更正 |
|---|---|---|
| arxiv260701942 | arXiv-only；作者、题名、日期及指定方法段已核验 | ATG已覆盖影响区域定位、冻结其余图、替换/插入/改依赖及接口保持；不能声称Qwen提出的通用流程无人做过。 |
| arxiv260919654 | arXiv-only；元数据与本地全文核验 | 重规划/修复/编辑、稳定性与成本组合已有直接比较；不另行宣称本项目首次定义这些维度。 |
| arxiv261010786 | 既有条目复核 | 局部补全近邻保持成立；本次补上其引用的更直接图修复工作ATG。 |

当前结论没有证明任何更窄机制不存在先例，也没有把十例手工成功认定为方法成立。服务器访问本次受认证阻塞；文献核验不等于新GPU实验已启动。
