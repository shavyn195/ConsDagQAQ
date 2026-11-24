# 原始API消费者缓存与严格格式评分

本目录原始 `config.json`、`responses.jsonl`、`outcomes.jsonl`、`paired_analysis.json` 保持原样。

**解释时必须同时读取 `../deepseek_planner_v5_parse_parity/`。** 原评分直接对整个回答做`json.loads`，5339个独立回答中5337个带单个Markdown代码块，因而受约束faithful全零。这个严格格式遵从结果不能被解释为模型没有生成可执行计划；原单体E2的读取规则本来允许括号包裹的数组，二者不对称。

2026-11-25补充公开披露的缓存重评分：

- `strict_json_analysis.json`：复现原始整个回答必须为JSON的成绩。
- `single_fence_analysis.json`：仅允许完整单个代码块包装。
- `e2_shared_analysis.json`：直接复用原单体计划读取器，只传公开task，不传gold、witness或query。

后两者8100个条件的四项执行结果完全相同；没有修改工具、参数、顺序，没有新API请求。原始严格成绩保留；包装兼容成绩是事后公平性修正，不追认为预注册。该零样本、关闭thinking、384输出token的消费者也不代表强模型规划上限。

报告：`reports/consumer_cross_results_20261125.md`。按服务器回收哈希校验原缓存，核验清单 `outputs/submission/audit_20261125/completed_0215_manifest.json`。
