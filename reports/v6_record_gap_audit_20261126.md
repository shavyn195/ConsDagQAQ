# v6 4B记录差距：三seed逐字段核对

2026-11-26。在服务器两项健康作业继续运行时，分析已回收的4B seed42/43/44预测，不生成新模型输出或计划。复用冻结`constraint_key`和`core_key`，全部15个seed×切分的strict/core F1、record exact、解析率与原保存指标重新计算一致；冻结数据SHA和逐题ID对齐通过。执行评分器没有重跑。

**工具、结构留出的记录差距大多来自scope字段，不是type/params错误。** 这延伸了v4/v5已经记录的公开scope映射问题，并非一个全新发现，也不能因此宣布语义问题解决。

| 切分 | 预测次数（三seed合计） | 完整记录匹配 | 仅元数据不匹配 | 核心type/params不匹配 | core正确但query_state不匹配 | 无效输出 |
|---|---:|---:|---:|---:|---:|---:|
| dev | 2700 | 2700 | 0 | 0 | 0 | 0 |
| 模板留出 | 3150 | 3017 | 11 | 103 | 15 | 4 |
| 工具留出 | 3150 | 2453 | 681 | 16 | 0 | 0 |
| 结构留出 | 3150 | 2345 | 752 | 53 | 0 | 0 |
| 组合留出 | 3150 | 3146 | 4 | 0 | 0 | 0 |

这些是重复任务上三份模型的预测次数，不是3150个独立任务。互斥分类依次判断无效输出、核心不匹配、query_state不匹配、元数据不匹配；核心或query_state不匹配行也可能同时含元数据错误。元数据类要求core集合和query_state均正确，故没有把核心错误隐藏进去。

工具留出681/697=97.70%的记录不匹配、结构留出752/805=93.42%的记录不匹配，均仅由scope引起。对应不匹配条目按类型计数：工具privacy561、budget159；结构privacy390、budget430、order1。一个请求可含多个条目，条目数不能与请求数直接相加比较。模板的11次元数据问题均是约束state，涉及budget9、privacy2；因此scope不是所有切分的通解。

示例：seed44的`test_tool_ho-00003-E`正确提取employee_pii不出域参数，却把privacy scope写成`approve_partner_access/sync_to_partner_hub`，参考scope为公开目录中的三个外发角色。结构`test_struct_ho-00003-E/I`也正确保留隐私参数，却混入审批节点并漏掉外发节点。这里描述的是记录映射错误；当前消费者主要使用type/params，不能仅靠修scope声称执行更安全。

代码已有`src/public_scope_binding.py`，公开目录即可确定budget/ privacy等scope，不读取隐藏task、gold或witness，也不补缺约束或改语义参数。旧对照见`reports/v4_optimization_results.md`及`reports/v5_binding_progress_20261124.md`。先复用该基线，不能再发明一个同义模块或把相同旧基线改名为②。

另一个指标边界：当前strict键**不包括evidence_span**，evidence单独评分。因此“记录匹配”不代表证据文本完全正确。本轮无重复core键导致的未确定配对；审计器遇到重复键会保留歧义，不按任意顺序归因。四项测试覆盖scope顺序、证据字段独立性、语义参数错误、无效输出和重复键处理。

下一步继续等待完整绑定复核的同预算三臂结果；不把scope可确定性修正的缺口当作训练新复核器的理由。值得检验的仍是合法目标错绑、漏约束和N误报，并需要独立请求确认。当前不更改冻结评分器、v5/v6主表或正在运行的提示。

产物：`outputs/v6_4b_record_gap_20261126/summary.json`含15面板、源码/输入SHA；`cases.jsonl`保留全部1639次记录不匹配及局部字段。代码`audit_record_metadata.py`仅分析原始缓存，没有模型调用、求解或后处理生成。

来源检查曾因Windows自动写入CRLF、Git保存LF而失败；未在失败状态提交。首次字节保留于`first_pass_bytes.zip`，分析写出改为明确LF后重新运行，15面板及全部病例内容一致，最终暂存字节SHA检查通过。详见`newline_audit.json`，没有改变冻结预测或评分口径。
