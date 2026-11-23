# ConsDAG 逐题数据和运行文件索引

本地已归档的实验数据、配置和结果文件共 374 个。可按目录、模型名或实验名搜索。[查看带解释的实验总表](consdag_experiments_overview.md)。

JSONL 每行是一条记录，JSON 通常保存汇总或运行设置。历史快照可能与后续归档重复。文件数不能用作独立运行数。

| 类别 | 文件数 | 内容 |
|---|---:|---|
| 部署与推理开销 | 17 | 冻结权重、原生输入输出 token、单条请求耗时、完整编译正确性、固定长度生成和逐 token 解码对照。 |
| 基准数据及程序化核查 | 15 | 冻结的四份数据、执行见证、数据构造分布和质量核查。人工审查题包另行提供。 |
| E1 训练与同底座零示例 | 21 | 三个冻结适配器的各切分原始回答与评分。metrics.json 中有训练与零示例两个分支。 |
| E1 强提示词与字段指标 | 19 | 独立 API 调用得到的强模型逐题回答、配对差值与字段诊断。 |
| 证据改写 | 23 | 逐题原句、改写、无关标签和去引号复测。primary 为前后同时全对。 |
| 逐题新措辞 | 7 | 三个条件下在相同输入上比较小模型和强提示词，同时保留每条原始生成。 |
| 审批歧义 | 8 | 44 对澄清句、执行计划证书、模型原始回答与每题评分。 |
| E2 训练与规划 | 153 | 开发探针、训练失败与种子对照、冻结留出、交叉干预及全量执行细目。 |
| 历史数据和早期实验 | 117 | 早期版本、诊断与本地归档的快照。版本不同，数值请结合对应台账阅读。 |

## 部署与推理开销

**outputs/compiler_efficiency_v1**

[1.7B-env.json](../outputs/compiler_efficiency_v1/1.7B-env.json) · [1.7B.jsonl](../outputs/compiler_efficiency_v1/1.7B.jsonl) · [4B-env.json](../outputs/compiler_efficiency_v1/4B-env.json) · [4B.jsonl](../outputs/compiler_efficiency_v1/4B.jsonl) · [api0-warm.json](../outputs/compiler_efficiency_v1/api0-warm.json) · [api0.jsonl](../outputs/compiler_efficiency_v1/api0.jsonl) · [api10-warm.json](../outputs/compiler_efficiency_v1/api10-warm.json) · [api10.jsonl](../outputs/compiler_efficiency_v1/api10.jsonl) · [fixed-generation.json](../outputs/compiler_efficiency_v1/fixed-generation.json) · [protocol.json](../outputs/compiler_efficiency_v1/protocol.json) · [results.json](../outputs/compiler_efficiency_v1/results.json) · [逐 token 解码协议](../outputs/compiler_efficiency_v1/decode-interval/protocol.json) · [逐 token 解码结果](../outputs/compiler_efficiency_v1/decode-interval/result.json)


## 基准数据及程序化核查

**outputs/dataset_audit/dev-replay-v1**

[1.7B.jsonl](../outputs/dataset_audit/dev-replay-v1/1.7B.jsonl) · [4B.jsonl](../outputs/dataset_audit/dev-replay-v1/4B.jsonl) · [scores.json](../outputs/dataset_audit/dev-replay-v1/scores.json)

**outputs/dataset_audit/privacy-card-v1**

[config.json](../outputs/dataset_audit/privacy-card-v1/config.json) · [no_field_examples.jsonl](../outputs/dataset_audit/privacy-card-v1/no_field_examples.jsonl) · [original.jsonl](../outputs/dataset_audit/privacy-card-v1/original.jsonl) · [scores.json](../outputs/dataset_audit/privacy-card-v1/scores.json)

**outputs/dataset_audit**

[v4-all-pairs-recheck.json](../outputs/dataset_audit/v4-all-pairs-recheck.json) · [v4-recheck-explicit-privacy.json](../outputs/dataset_audit/v4-recheck-explicit-privacy.json)

**data/processed_v4**

[dev.jsonl](../data/processed_v4/dev.jsonl) · [generation_report.json](../data/processed_v4/generation_report.json) · [test_tool_ho.jsonl](../data/processed_v4/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../data/processed_v4/test_tpl_ho.jsonl) · [train.jsonl](../data/processed_v4/train.jsonl) · [verification_report.json](../data/processed_v4/verification_report.json)


## E1 训练与同底座零示例

**outputs/e1/Qwen3-0.6B-v4**

[metrics.json](../outputs/e1/Qwen3-0.6B-v4/metrics.json)

**outputs/e1/Qwen3-0.6B-v4/trained_predictions**

[dev.jsonl](../outputs/e1/Qwen3-0.6B-v4/trained_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-0.6B-v4/trained_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-0.6B-v4/trained_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-0.6B-v4/zeroshot_predictions**

[dev.jsonl](../outputs/e1/Qwen3-0.6B-v4/zeroshot_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-0.6B-v4/zeroshot_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-0.6B-v4/zeroshot_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-1.7B-v4**

[metrics.json](../outputs/e1/Qwen3-1.7B-v4/metrics.json)

**outputs/e1/Qwen3-1.7B-v4/trained_predictions**

[dev.jsonl](../outputs/e1/Qwen3-1.7B-v4/trained_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-1.7B-v4/trained_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-1.7B-v4/trained_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-1.7B-v4/zeroshot_predictions**

[dev.jsonl](../outputs/e1/Qwen3-1.7B-v4/zeroshot_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-1.7B-v4/zeroshot_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-1.7B-v4/zeroshot_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-4B-v4**

[metrics.json](../outputs/e1/Qwen3-4B-v4/metrics.json)

**outputs/e1/Qwen3-4B-v4/trained_predictions**

[dev.jsonl](../outputs/e1/Qwen3-4B-v4/trained_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-4B-v4/trained_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-4B-v4/trained_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-4B-v4/zeroshot_predictions**

[dev.jsonl](../outputs/e1/Qwen3-4B-v4/zeroshot_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-4B-v4/zeroshot_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-4B-v4/zeroshot_predictions/test_tpl_ho.jsonl)


## E1 强提示词与字段指标

**outputs/e1_v4_side/deepseek-v4-pro-0813-few**

[config.json](../outputs/e1_v4_side/deepseek-v4-pro-0813-few/config.json) · [dev.jsonl](../outputs/e1_v4_side/deepseek-v4-pro-0813-few/dev.jsonl) · [full-paired.json](../outputs/e1_v4_side/deepseek-v4-pro-0813-few/full-paired.json) · [full-scores.json](../outputs/e1_v4_side/deepseek-v4-pro-0813-few/full-scores.json) · [panel-scores.json](../outputs/e1_v4_side/deepseek-v4-pro-0813-few/panel-scores.json) · [test_tool_ho.jsonl](../outputs/e1_v4_side/deepseek-v4-pro-0813-few/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1_v4_side/deepseek-v4-pro-0813-few/test_tpl_ho.jsonl)

**outputs/e1_v4_side**

[discordance-tool-1.7B-P0-P10.json](../outputs/e1_v4_side/discordance-tool-1.7B-P0-P10.json) · [main-v4-0.6B-1.7B-PE-zero-PE-10.json](../outputs/e1_v4_side/main-v4-0.6B-1.7B-PE-zero-PE-10.json) · [main-v4-0.6B-1.7B-PE-zero.json](../outputs/e1_v4_side/main-v4-0.6B-1.7B-PE-zero.json) · [paired-0.6B-faithful-constrained.json](../outputs/e1_v4_side/paired-0.6B-faithful-constrained.json) · [supplement-4B-paired.json](../outputs/e1_v4_side/supplement-4B-paired.json) · [trained-0.6B.json](../outputs/e1_v4_side/trained-0.6B.json) · [trained-4B.json](../outputs/e1_v4_side/trained-4B.json) · [zero-0.6B.json](../outputs/e1_v4_side/zero-0.6B.json) · [zero-4B.json](../outputs/e1_v4_side/zero-4B.json)

**outputs/e1_v4_side/public-scope-v1**

[scores.json](../outputs/e1_v4_side/public-scope-v1/scores.json)

**outputs/e1_v4_side/qwen-max-few**

[scores.json](../outputs/e1_v4_side/qwen-max-few/scores.json)

**outputs/e1_v4_side/qwen-max-zero**

[scores.json](../outputs/e1_v4_side/qwen-max-zero/scores.json)


## 证据改写

**outputs/evidence_edits_v1/0.6B**

[audit.json](../outputs/evidence_edits_v1/0.6B/audit.json) · [catalog_scope_diagnostic.json](../outputs/evidence_edits_v1/0.6B/catalog_scope_diagnostic.json) · [inference.json](../outputs/evidence_edits_v1/0.6B/inference.json) · [paired_scores.json](../outputs/evidence_edits_v1/0.6B/paired_scores.json) · [placebo_errors.json](../outputs/evidence_edits_v1/0.6B/placebo_errors.json) · [raw.jsonl](../outputs/evidence_edits_v1/0.6B/raw.jsonl) · [summary.json](../outputs/evidence_edits_v1/0.6B/summary.json)

**outputs/evidence_edits_v1/1.7B**

[audit.json](../outputs/evidence_edits_v1/1.7B/audit.json) · [catalog_scope_diagnostic.json](../outputs/evidence_edits_v1/1.7B/catalog_scope_diagnostic.json) · [inference.json](../outputs/evidence_edits_v1/1.7B/inference.json) · [paired_scores.json](../outputs/evidence_edits_v1/1.7B/paired_scores.json) · [placebo_errors.json](../outputs/evidence_edits_v1/1.7B/placebo_errors.json) · [raw.jsonl](../outputs/evidence_edits_v1/1.7B/raw.jsonl) · [summary.json](../outputs/evidence_edits_v1/1.7B/summary.json)

**outputs/evidence_edits_v1**

[panel.jsonl](../outputs/evidence_edits_v1/panel.jsonl) · [panel_audit.json](../outputs/evidence_edits_v1/panel_audit.json) · [protocol.json](../outputs/evidence_edits_v1/protocol.json) · [scope_other_groups.json](../outputs/evidence_edits_v1/scope_other_groups.json)

**outputs/evidence_edits_v1/unquoted_followup/0.6B**

[raw.jsonl](../outputs/evidence_edits_v1/unquoted_followup/0.6B/raw.jsonl) · [summary.json](../outputs/evidence_edits_v1/unquoted_followup/0.6B/summary.json)

**outputs/evidence_edits_v1/unquoted_followup/1.7B**

[raw.jsonl](../outputs/evidence_edits_v1/unquoted_followup/1.7B/raw.jsonl) · [summary.json](../outputs/evidence_edits_v1/unquoted_followup/1.7B/summary.json)

**outputs/evidence_edits_v1/unquoted_followup**

[protocol.json](../outputs/evidence_edits_v1/unquoted_followup/protocol.json)


## 逐题新措辞

**outputs/authored_wording_v1**

[ambiguity_sensitivity.json](../outputs/authored_wording_v1/ambiguity_sensitivity.json) · [paired.json](../outputs/authored_wording_v1/paired.json) · [panel.jsonl](../outputs/authored_wording_v1/panel.jsonl) · [pe.jsonl](../outputs/authored_wording_v1/pe.jsonl) · [protocol.json](../outputs/authored_wording_v1/protocol.json) · [scores.json](../outputs/authored_wording_v1/scores.json) · [sft.jsonl](../outputs/authored_wording_v1/sft.jsonl)


## 审批歧义

**outputs/approval_wording_v1**

[certificates.json](../outputs/approval_wording_v1/certificates.json) · [panel.jsonl](../outputs/approval_wording_v1/panel.jsonl) · [pe-by-id.json](../outputs/approval_wording_v1/pe-by-id.json) · [pe.jsonl](../outputs/approval_wording_v1/pe.jsonl) · [protocol.json](../outputs/approval_wording_v1/protocol.json) · [scores.json](../outputs/approval_wording_v1/scores.json) · [sft-by-id.json](../outputs/approval_wording_v1/sft-by-id.json) · [sft.jsonl](../outputs/approval_wording_v1/sft.jsonl)


## E2 训练与规划

**outputs/e2_v4/action-credit-1.7B-pilot-v1/action-s42**

[config.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/action-s42/config.json) · [dev-scores.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/action-s42/dev-scores.json) · [dev.jsonl](../outputs/e2_v4/action-credit-1.7B-pilot-v1/action-s42/dev.jsonl) · [done.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/action-s42/done.json) · [progress.jsonl](../outputs/e2_v4/action-credit-1.7B-pilot-v1/action-s42/progress.jsonl) · [rollouts.jsonl](../outputs/e2_v4/action-credit-1.7B-pilot-v1/action-s42/rollouts.jsonl)

**outputs/e2_v4/action-credit-1.7B-pilot-v1**

[cache-ready.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/cache-ready.json) · [compiler.jsonl](../outputs/e2_v4/action-credit-1.7B-pilot-v1/compiler.jsonl) · [credit-replay-action-s42.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/credit-replay-action-s42.json) · [paired-dev-s42.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/paired-dev-s42.json) · [paired-dev-s43.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/paired-dev-s43.json) · [paired-dev-s44.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/paired-dev-s44.json) · [panel.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/panel.json) · [prevention-train-v1.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/prevention-train-v1.json) · [rechecked-original-42-43-44.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/rechecked-original-42-43-44.json) · [train-sampling-coverage-v1.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/train-sampling-coverage-v1.json)

**outputs/e2_v4/action-credit-1.7B-pilot-v1/preventive-comparison-v1**

[comparison.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/preventive-comparison-v1/comparison.json) · [decision.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/preventive-comparison-v1/decision.json) · [protocol.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/preventive-comparison-v1/protocol.json) · [rechecked-prevention-42-43-44.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/preventive-comparison-v1/rechecked-prevention-42-43-44.json) · [rechecked-prevention-42.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/preventive-comparison-v1/rechecked-prevention-42.json)

**outputs/e2_v4/action-credit-1.7B-pilot-v1/trace-s42**

[config.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/trace-s42/config.json) · [dev-scores.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/trace-s42/dev-scores.json) · [dev.jsonl](../outputs/e2_v4/action-credit-1.7B-pilot-v1/trace-s42/dev.jsonl) · [done.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/trace-s42/done.json) · [progress.jsonl](../outputs/e2_v4/action-credit-1.7B-pilot-v1/trace-s42/progress.jsonl) · [rollouts.jsonl](../outputs/e2_v4/action-credit-1.7B-pilot-v1/trace-s42/rollouts.jsonl)

**outputs/e2_v4/action-credit-1.7B-pilot-v1/warm**

[dev-scores.json](../outputs/e2_v4/action-credit-1.7B-pilot-v1/warm/dev-scores.json) · [dev.jsonl](../outputs/e2_v4/action-credit-1.7B-pilot-v1/warm/dev.jsonl)

**outputs/e2_v4/failure-interventions-2x2-v1**

[protocol.json](../outputs/e2_v4/failure-interventions-2x2-v1/protocol.json) · [results.json](../outputs/e2_v4/failure-interventions-2x2-v1/results.json) · [rows.jsonl](../outputs/e2_v4/failure-interventions-2x2-v1/rows.jsonl)

**outputs/e2_v4/frozen-planner-swap-panel-v1**

[config.json](../outputs/e2_v4/frozen-planner-swap-panel-v1/config.json) · [paired-audit.json](../outputs/e2_v4/frozen-planner-swap-panel-v1/paired-audit.json) · [samples.jsonl](../outputs/e2_v4/frozen-planner-swap-panel-v1/samples.jsonl) · [scores.json](../outputs/e2_v4/frozen-planner-swap-panel-v1/scores.json)

**outputs/e2_v4/frozen-planner-transfer-v1**

[function-42.json](../outputs/e2_v4/frozen-planner-transfer-v1/function-42.json) · [function-42.jsonl](../outputs/e2_v4/frozen-planner-transfer-v1/function-42.jsonl) · [function-43.json](../outputs/e2_v4/frozen-planner-transfer-v1/function-43.json) · [function-43.jsonl](../outputs/e2_v4/frozen-planner-transfer-v1/function-43.jsonl) · [function-44.json](../outputs/e2_v4/frozen-planner-transfer-v1/function-44.json) · [function-44.jsonl](../outputs/e2_v4/frozen-planner-transfer-v1/function-44.jsonl) · [paired.json](../outputs/e2_v4/frozen-planner-transfer-v1/paired.json) · [protect-42.json](../outputs/e2_v4/frozen-planner-transfer-v1/protect-42.json) · [protect-42.jsonl](../outputs/e2_v4/frozen-planner-transfer-v1/protect-42.jsonl) · [protect-43.json](../outputs/e2_v4/frozen-planner-transfer-v1/protect-43.json) · [protect-43.jsonl](../outputs/e2_v4/frozen-planner-transfer-v1/protect-43.jsonl) · [protect-44.json](../outputs/e2_v4/frozen-planner-transfer-v1/protect-44.json) · [protect-44.jsonl](../outputs/e2_v4/frozen-planner-transfer-v1/protect-44.jsonl) · [protocol.json](../outputs/e2_v4/frozen-planner-transfer-v1/protocol.json) · [rechecked-failures.json](../outputs/e2_v4/frozen-planner-transfer-v1/rechecked-failures.json) · [trace-42.json](../outputs/e2_v4/frozen-planner-transfer-v1/trace-42.json) · [trace-42.jsonl](../outputs/e2_v4/frozen-planner-transfer-v1/trace-42.jsonl) · [trace-43.json](../outputs/e2_v4/frozen-planner-transfer-v1/trace-43.json) · [trace-43.jsonl](../outputs/e2_v4/frozen-planner-transfer-v1/trace-43.jsonl) · [trace-44.json](../outputs/e2_v4/frozen-planner-transfer-v1/trace-44.json) · [trace-44.jsonl](../outputs/e2_v4/frozen-planner-transfer-v1/trace-44.jsonl)

**outputs/e2_v4/frozen-record-choice-v1**

[choice-audit.json](../outputs/e2_v4/frozen-record-choice-v1/choice-audit.json) · [config.json](../outputs/e2_v4/frozen-record-choice-v1/config.json) · [samples.jsonl](../outputs/e2_v4/frozen-record-choice-v1/samples.jsonl) · [scores.json](../outputs/e2_v4/frozen-record-choice-v1/scores.json)

**outputs/e2_v4**

[missed-core-coverage-dev.json](../outputs/e2_v4/missed-core-coverage-dev.json) · [missed-credit-train.json](../outputs/e2_v4/missed-credit-train.json)

**outputs/e2_v4/multiconstraint-gate-opportunity-v1**

[config.json](../outputs/e2_v4/multiconstraint-gate-opportunity-v1/config.json) · [equal-score-different-constraints.json](../outputs/e2_v4/multiconstraint-gate-opportunity-v1/equal-score-different-constraints.json) · [samples.jsonl](../outputs/e2_v4/multiconstraint-gate-opportunity-v1/samples.jsonl) · [scores.json](../outputs/e2_v4/multiconstraint-gate-opportunity-v1/scores.json)

**outputs/e2_v4/planner-warmup-1.7B-v1**

[audit.json](../outputs/e2_v4/planner-warmup-1.7B-v1/audit.json) · [base.jsonl](../outputs/e2_v4/planner-warmup-1.7B-v1/base.jsonl) · [config.json](../outputs/e2_v4/planner-warmup-1.7B-v1/config.json) · [loss.jsonl](../outputs/e2_v4/planner-warmup-1.7B-v1/loss.jsonl) · [scores.json](../outputs/e2_v4/planner-warmup-1.7B-v1/scores.json) · [warm.jsonl](../outputs/e2_v4/planner-warmup-1.7B-v1/warm.jsonl)

**outputs/e2_v4/reachability-format-v2**

[config.json](../outputs/e2_v4/reachability-format-v2/config.json) · [samples.jsonl](../outputs/e2_v4/reachability-format-v2/samples.jsonl) · [summary.json](../outputs/e2_v4/reachability-format-v2/summary.json)

**outputs/e2_v4/reachability-v1**

[fence-rescore.json](../outputs/e2_v4/reachability-v1/fence-rescore.json) · [samples.jsonl](../outputs/e2_v4/reachability-v1/samples.jsonl) · [summary.json](../outputs/e2_v4/reachability-v1/summary.json)

**outputs/e2_v4/semantic-disagreement-dev-v1**

[cases.jsonl](../outputs/e2_v4/semantic-disagreement-dev-v1/cases.jsonl) · [protocol.json](../outputs/e2_v4/semantic-disagreement-dev-v1/protocol.json) · [results.json](../outputs/e2_v4/semantic-disagreement-dev-v1/results.json)

**outputs/e2_v4/shared-candidate-selection-dev-v1**

[cases.jsonl](../outputs/e2_v4/shared-candidate-selection-dev-v1/cases.jsonl) · [protocol.json](../outputs/e2_v4/shared-candidate-selection-dev-v1/protocol.json) · [results.json](../outputs/e2_v4/shared-candidate-selection-dev-v1/results.json) · [selection-replay.json](../outputs/e2_v4/shared-candidate-selection-dev-v1/selection-replay.json)

**outputs/e2_v4/shared-candidate-selection-transfer-v1**

[cases.jsonl](../outputs/e2_v4/shared-candidate-selection-transfer-v1/cases.jsonl) · [protocol.json](../outputs/e2_v4/shared-candidate-selection-transfer-v1/protocol.json) · [results.json](../outputs/e2_v4/shared-candidate-selection-transfer-v1/results.json) · [selection-replay.json](../outputs/e2_v4/shared-candidate-selection-transfer-v1/selection-replay.json)

**outputs/e2_v4/strict-witness-paired-audit-v1**

[exceptions.jsonl](../outputs/e2_v4/strict-witness-paired-audit-v1/exceptions.jsonl) · [results.json](../outputs/e2_v4/strict-witness-paired-audit-v1/results.json)

**outputs/e2_v4/temperature-coverage-1.7B-train-v1**

[protocol.json](../outputs/e2_v4/temperature-coverage-1.7B-train-v1/protocol.json) · [results.json](../outputs/e2_v4/temperature-coverage-1.7B-train-v1/results.json)

**outputs/e2_v4/verified-missing-stage-v1**

[protocol.json](../outputs/e2_v4/verified-missing-stage-v1/protocol.json) · [raw.jsonl](../outputs/e2_v4/verified-missing-stage-v1/raw.jsonl) · [replay.jsonl](../outputs/e2_v4/verified-missing-stage-v1/replay.jsonl) · [results.json](../outputs/e2_v4/verified-missing-stage-v1/results.json)

**outputs/e2_v4/verified-one-edit-confirmation-v1**

[cases.jsonl](../outputs/e2_v4/verified-one-edit-confirmation-v1/cases.jsonl) · [empty-route.json](../outputs/e2_v4/verified-one-edit-confirmation-v1/empty-route.json) · [independent-replay.json](../outputs/e2_v4/verified-one-edit-confirmation-v1/independent-replay.json) · [normalized-symbolic.json](../outputs/e2_v4/verified-one-edit-confirmation-v1/normalized-symbolic.json) · [protocol.json](../outputs/e2_v4/verified-one-edit-confirmation-v1/protocol.json) · [raw.jsonl](../outputs/e2_v4/verified-one-edit-confirmation-v1/raw.jsonl) · [results.json](../outputs/e2_v4/verified-one-edit-confirmation-v1/results.json)

**outputs/e2_v4/verified-one-edit-confirmation-v1/compiler-swap**

[results.json](../outputs/e2_v4/verified-one-edit-confirmation-v1/compiler-swap/results.json) · [rows.jsonl](../outputs/e2_v4/verified-one-edit-confirmation-v1/compiler-swap/rows.jsonl)

**outputs/e2_v4/verified-one-edit-depth-pair-v1**

[mandatory.jsonl](../outputs/e2_v4/verified-one-edit-depth-pair-v1/mandatory.jsonl) · [optional.jsonl](../outputs/e2_v4/verified-one-edit-depth-pair-v1/optional.jsonl) · [protocol.json](../outputs/e2_v4/verified-one-edit-depth-pair-v1/protocol.json) · [results.json](../outputs/e2_v4/verified-one-edit-depth-pair-v1/results.json)

**outputs/e2_v4/verified-one-edit-full-holdouts-v1**

[cases.jsonl](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/cases.jsonl) · [empty-route.json](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/empty-route.json) · [normalized-symbolic.json](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/normalized-symbolic.json) · [oracle-neighborhood.json](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/oracle-neighborhood.json) · [paired-summary.json](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/paired-summary.json) · [protocol.json](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/protocol.json) · [raw.jsonl](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/raw.jsonl) · [results.json](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/results.json)

**outputs/e2_v4/verified-one-edit-full-holdouts-v1/compiler-swap**

[protocol.json](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/compiler-swap/protocol.json) · [results.json](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/compiler-swap/results.json) · [rows.jsonl](../outputs/e2_v4/verified-one-edit-full-holdouts-v1/compiler-swap/rows.jsonl)

**outputs/e2_v4/verified-one-edit-full-order44-v1**

[empty-route.json](../outputs/e2_v4/verified-one-edit-full-order44-v1/empty-route.json) · [normalized-symbolic.json](../outputs/e2_v4/verified-one-edit-full-order44-v1/normalized-symbolic.json) · [oracle-neighborhood.json](../outputs/e2_v4/verified-one-edit-full-order44-v1/oracle-neighborhood.json) · [protocol.json](../outputs/e2_v4/verified-one-edit-full-order44-v1/protocol.json) · [replicated-summary.json](../outputs/e2_v4/verified-one-edit-full-order44-v1/replicated-summary.json) · [replication.json](../outputs/e2_v4/verified-one-edit-full-order44-v1/replication.json) · [results.json](../outputs/e2_v4/verified-one-edit-full-order44-v1/results.json)

**outputs/e2_v4/verified-repair-sft-1.7B-orders-v1**

[all-orders.json](../outputs/e2_v4/verified-repair-sft-1.7B-orders-v1/all-orders.json) · [independent-replay.json](../outputs/e2_v4/verified-repair-sft-1.7B-orders-v1/independent-replay.json) · [protocol.json](../outputs/e2_v4/verified-repair-sft-1.7B-orders-v1/protocol.json)

**outputs/e2_v4/verified-repair-sft-1.7B-orders-v1/order-43**

[paired.json](../outputs/e2_v4/verified-repair-sft-1.7B-orders-v1/order-43/paired.json)

**outputs/e2_v4/verified-repair-sft-1.7B-v1**

[independent-replay.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/independent-replay.json) · [paired.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/paired.json) · [panel.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/panel.json) · [train-pairs.jsonl](../outputs/e2_v4/verified-repair-sft-1.7B-v1/train-pairs.jsonl) · [training.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/training.json)

**outputs/e2_v4/verified-repair-sft-1.7B-v1/one-edit-replay**

[protocol.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/one-edit-replay/protocol.json) · [repair.jsonl](../outputs/e2_v4/verified-repair-sft-1.7B-v1/one-edit-replay/repair.jsonl) · [results.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/one-edit-replay/results.json) · [uniform.jsonl](../outputs/e2_v4/verified-repair-sft-1.7B-v1/one-edit-replay/uniform.jsonl) · [warm.jsonl](../outputs/e2_v4/verified-repair-sft-1.7B-v1/one-edit-replay/warm.jsonl)

**outputs/e2_v4/verified-repair-sft-1.7B-v1/repair**

[budget.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/repair/budget.json) · [cases.jsonl](../outputs/e2_v4/verified-repair-sft-1.7B-v1/repair/cases.jsonl) · [results.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/repair/results.json) · [steps.jsonl](../outputs/e2_v4/verified-repair-sft-1.7B-v1/repair/steps.jsonl)

**outputs/e2_v4/verified-repair-sft-1.7B-v1/uniform**

[budget.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/uniform/budget.json) · [cases.jsonl](../outputs/e2_v4/verified-repair-sft-1.7B-v1/uniform/cases.jsonl) · [results.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/uniform/results.json) · [steps.jsonl](../outputs/e2_v4/verified-repair-sft-1.7B-v1/uniform/steps.jsonl)

**outputs/e2_v4/verified-repair-sft-1.7B-v1/warm**

[cases.jsonl](../outputs/e2_v4/verified-repair-sft-1.7B-v1/warm/cases.jsonl) · [results.json](../outputs/e2_v4/verified-repair-sft-1.7B-v1/warm/results.json)


## 历史数据和早期实验

**outputs/_server_ro/Qwen3-0.6B-v4/zeroshot_predictions**

[dev.jsonl](../outputs/_server_ro/Qwen3-0.6B-v4/zeroshot_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/_server_ro/Qwen3-0.6B-v4/zeroshot_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/_server_ro/Qwen3-0.6B-v4/zeroshot_predictions/test_tpl_ho.jsonl)

**outputs/_tmp_schema_rich_predictions**

[dev.jsonl](../outputs/_tmp_schema_rich_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/_tmp_schema_rich_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/_tmp_schema_rich_predictions/test_tpl_ho.jsonl)

**outputs**

[analysis_e1_0.6b.json](../outputs/analysis_e1_0.6b.json) · [analysis_e1_0.6b_scope_audit_20261120.json](../outputs/analysis_e1_0.6b_scope_audit_20261120.json) · [analysis_e1_4b_scope_audit_20261120.json](../outputs/analysis_e1_4b_scope_audit_20261120.json) · [counterfactual_e1_0.6b.json](../outputs/counterfactual_e1_0.6b.json) · [counterfactual_e1_4b.json](../outputs/counterfactual_e1_4b.json) · [dataset_text_quality_20261120.json](../outputs/dataset_text_quality_20261120.json) · [quality_recheck.json](../outputs/quality_recheck.json) · [quality_recheck_20261121.json](../outputs/quality_recheck_20261121.json)

**outputs/dataset_metadata_verified**

[dataset-metadata.json](../outputs/dataset_metadata_verified/dataset-metadata.json)

**outputs/e1/Qwen3-0.6B**

[metrics.json](../outputs/e1/Qwen3-0.6B/metrics.json) · [metrics_e1_score_v2_recomputed.json](../outputs/e1/Qwen3-0.6B/metrics_e1_score_v2_recomputed.json) · [metrics_e1_score_v3_recomputed.json](../outputs/e1/Qwen3-0.6B/metrics_e1_score_v3_recomputed.json) · [metrics_zero_shot_e1_score_v3.json](../outputs/e1/Qwen3-0.6B/metrics_zero_shot_e1_score_v3.json)

**outputs/e1/Qwen3-0.6B/trained_predictions**

[dev.jsonl](../outputs/e1/Qwen3-0.6B/trained_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-0.6B/trained_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-0.6B/trained_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-0.6B/zeroshot_predictions**

[dev.jsonl](../outputs/e1/Qwen3-0.6B/zeroshot_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-0.6B/zeroshot_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-0.6B/zeroshot_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-0.6B-seed43/zeroshot_predictions**

[dev.jsonl](../outputs/e1/Qwen3-0.6B-seed43/zeroshot_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-0.6B-seed43/zeroshot_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-0.6B-seed43/zeroshot_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-0.6B-seed43_smoke**

[smoke.json](../outputs/e1/Qwen3-0.6B-seed43_smoke/smoke.json)

**outputs/e1/Qwen3-1.7B**

[metrics_zero_shot_e1_score_v3.json](../outputs/e1/Qwen3-1.7B/metrics_zero_shot_e1_score_v3.json)

**outputs/e1/Qwen3-1.7B/zeroshot_predictions**

[dev.jsonl](../outputs/e1/Qwen3-1.7B/zeroshot_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-1.7B/zeroshot_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-1.7B/zeroshot_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-4B**

[metrics.json](../outputs/e1/Qwen3-4B/metrics.json) · [metrics_e1_score_v3_recomputed.json](../outputs/e1/Qwen3-4B/metrics_e1_score_v3_recomputed.json) · [metrics_zero_shot_e1_score_v3.json](../outputs/e1/Qwen3-4B/metrics_zero_shot_e1_score_v3.json)

**outputs/e1/Qwen3-4B/trained_predictions**

[dev.jsonl](../outputs/e1/Qwen3-4B/trained_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-4B/trained_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-4B/trained_predictions/test_tpl_ho.jsonl)

**outputs/e1/Qwen3-4B/zeroshot_predictions**

[dev.jsonl](../outputs/e1/Qwen3-4B/zeroshot_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/e1/Qwen3-4B/zeroshot_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/e1/Qwen3-4B/zeroshot_predictions/test_tpl_ho.jsonl)

**outputs/e1_preflight/Qwen3-0.6B-seed43-bf16**

[smoke.json](../outputs/e1_preflight/Qwen3-0.6B-seed43-bf16/smoke.json)

**outputs/gpu_error_v3/outputs/predictions**

[prompt_abstaining.jsonl](../outputs/gpu_error_v3/outputs/predictions/prompt_abstaining.jsonl) · [prompt_structured.jsonl](../outputs/gpu_error_v3/outputs/predictions/prompt_structured.jsonl)

**outputs/gpu_snapshot_20261120/Qwen3-4B**

[metrics_partial_recomputed.json](../outputs/gpu_snapshot_20261120/Qwen3-4B/metrics_partial_recomputed.json) · [metrics_zero_shot_e1_score_v3.json](../outputs/gpu_snapshot_20261120/Qwen3-4B/metrics_zero_shot_e1_score_v3.json)

**outputs/gpu_snapshot_20261120/Qwen3-4B/remote_trained_final/trained_predictions**

[dev.jsonl](../outputs/gpu_snapshot_20261120/Qwen3-4B/remote_trained_final/trained_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/gpu_snapshot_20261120/Qwen3-4B/remote_trained_final/trained_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/gpu_snapshot_20261120/Qwen3-4B/remote_trained_final/trained_predictions/test_tpl_ho.jsonl)

**outputs/gpu_snapshot_20261120/Qwen3-4B/zeroshot_predictions**

[dev.jsonl](../outputs/gpu_snapshot_20261120/Qwen3-4B/zeroshot_predictions/dev.jsonl) · [test_tool_ho.jsonl](../outputs/gpu_snapshot_20261120/Qwen3-4B/zeroshot_predictions/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../outputs/gpu_snapshot_20261120/Qwen3-4B/zeroshot_predictions/test_tpl_ho.jsonl)

**outputs/gpu_v4/outputs**

[pilot_run.json](../outputs/gpu_v4/outputs/pilot_run.json)

**outputs/gpu_v4/outputs/predictions**

[prompt_abstaining.jsonl](../outputs/gpu_v4/outputs/predictions/prompt_abstaining.jsonl) · [prompt_structured.jsonl](../outputs/gpu_v4/outputs/predictions/prompt_structured.jsonl) · [trained_lora.jsonl](../outputs/gpu_v4/outputs/predictions/trained_lora.jsonl)

**outputs/gpu_v5/outputs**

[pilot_run.json](../outputs/gpu_v5/outputs/pilot_run.json)

**outputs/gpu_v5/outputs/predictions**

[prompt_abstaining.jsonl](../outputs/gpu_v5/outputs/predictions/prompt_abstaining.jsonl) · [prompt_structured.jsonl](../outputs/gpu_v5/outputs/predictions/prompt_structured.jsonl) · [trained_lora.jsonl](../outputs/gpu_v5/outputs/predictions/trained_lora.jsonl)

**outputs/independent_writer_materials**

[group-map.json](../outputs/independent_writer_materials/group-map.json)

**outputs/prompt_pilot_v2_0.6B_cpu**

[metadata.json](../outputs/prompt_pilot_v2_0.6B_cpu/metadata.json) · [results.json](../outputs/prompt_pilot_v2_0.6B_cpu/results.json)

**outputs/prompt_pilot_v2_0.6B_cpu/predictions**

[baseline.jsonl](../outputs/prompt_pilot_v2_0.6B_cpu/predictions/baseline.jsonl) · [improved.jsonl](../outputs/prompt_pilot_v2_0.6B_cpu/predictions/improved.jsonl)

**outputs/prompt_qwen_max_e1**

[metadata.json](../outputs/prompt_qwen_max_e1/metadata.json) · [metadata_smoke.json](../outputs/prompt_qwen_max_e1/metadata_smoke.json) · [results.atlas_adapted.json](../outputs/prompt_qwen_max_e1/results.atlas_adapted.json) · [results.e1_original.json](../outputs/prompt_qwen_max_e1/results.e1_original.json) · [results_smoke.atlas_adapted.json](../outputs/prompt_qwen_max_e1/results_smoke.atlas_adapted.json) · [results_smoke.e1_original.json](../outputs/prompt_qwen_max_e1/results_smoke.e1_original.json)

**outputs/prompt_qwen_max_e1/predictions**

[dev.atlas_adapted.jsonl](../outputs/prompt_qwen_max_e1/predictions/dev.atlas_adapted.jsonl) · [dev.e1_original.jsonl](../outputs/prompt_qwen_max_e1/predictions/dev.e1_original.jsonl) · [dev_smoke.atlas_adapted.jsonl](../outputs/prompt_qwen_max_e1/predictions/dev_smoke.atlas_adapted.jsonl) · [dev_smoke.e1_original.jsonl](../outputs/prompt_qwen_max_e1/predictions/dev_smoke.e1_original.jsonl) · [test_tool_ho.atlas_adapted.jsonl](../outputs/prompt_qwen_max_e1/predictions/test_tool_ho.atlas_adapted.jsonl) · [test_tool_ho.e1_original.errors.jsonl](../outputs/prompt_qwen_max_e1/predictions/test_tool_ho.e1_original.errors.jsonl) · [test_tool_ho.e1_original.jsonl](../outputs/prompt_qwen_max_e1/predictions/test_tool_ho.e1_original.jsonl) · [test_tool_ho_smoke.atlas_adapted.jsonl](../outputs/prompt_qwen_max_e1/predictions/test_tool_ho_smoke.atlas_adapted.jsonl) · [test_tool_ho_smoke.e1_original.jsonl](../outputs/prompt_qwen_max_e1/predictions/test_tool_ho_smoke.e1_original.jsonl) · [test_tpl_ho.atlas_adapted.jsonl](../outputs/prompt_qwen_max_e1/predictions/test_tpl_ho.atlas_adapted.jsonl) · [test_tpl_ho.e1_original.jsonl](../outputs/prompt_qwen_max_e1/predictions/test_tpl_ho.e1_original.jsonl) · [test_tpl_ho_smoke.atlas_adapted.jsonl](../outputs/prompt_qwen_max_e1/predictions/test_tpl_ho_smoke.atlas_adapted.jsonl) · [test_tpl_ho_smoke.e1_original.jsonl](../outputs/prompt_qwen_max_e1/predictions/test_tpl_ho_smoke.e1_original.jsonl)

**outputs/prompt_qwen_max_schema_rich**

[metadata_smoke.json](../outputs/prompt_qwen_max_schema_rich/metadata_smoke.json) · [results_smoke.schema_rich.json](../outputs/prompt_qwen_max_schema_rich/results_smoke.schema_rich.json)

**outputs/prompt_qwen_max_schema_rich/predictions**

[dev_smoke.schema_rich.jsonl](../outputs/prompt_qwen_max_schema_rich/predictions/dev_smoke.schema_rich.jsonl) · [test_tool_ho_smoke.schema_rich.jsonl](../outputs/prompt_qwen_max_schema_rich/predictions/test_tool_ho_smoke.schema_rich.jsonl) · [test_tpl_ho_smoke.schema_rich.jsonl](../outputs/prompt_qwen_max_schema_rich/predictions/test_tpl_ho_smoke.schema_rich.jsonl)

**outputs/prompt_qwen_max_schema_rich_v2**

[metadata.json](../outputs/prompt_qwen_max_schema_rich_v2/metadata.json) · [metadata_smoke.json](../outputs/prompt_qwen_max_schema_rich_v2/metadata_smoke.json) · [metrics_e1_score_v3_recomputed.json](../outputs/prompt_qwen_max_schema_rich_v2/metrics_e1_score_v3_recomputed.json) · [results.schema_rich.json](../outputs/prompt_qwen_max_schema_rich_v2/results.schema_rich.json) · [results_smoke.schema_rich.json](../outputs/prompt_qwen_max_schema_rich_v2/results_smoke.schema_rich.json)

**outputs/prompt_qwen_max_schema_rich_v2/predictions**

[dev.schema_rich.jsonl](../outputs/prompt_qwen_max_schema_rich_v2/predictions/dev.schema_rich.jsonl) · [dev_smoke.schema_rich.jsonl](../outputs/prompt_qwen_max_schema_rich_v2/predictions/dev_smoke.schema_rich.jsonl) · [test_tool_ho.schema_rich.errors.jsonl](../outputs/prompt_qwen_max_schema_rich_v2/predictions/test_tool_ho.schema_rich.errors.jsonl) · [test_tool_ho.schema_rich.jsonl](../outputs/prompt_qwen_max_schema_rich_v2/predictions/test_tool_ho.schema_rich.jsonl) · [test_tool_ho_smoke.schema_rich.jsonl](../outputs/prompt_qwen_max_schema_rich_v2/predictions/test_tool_ho_smoke.schema_rich.jsonl) · [test_tpl_ho.schema_rich.jsonl](../outputs/prompt_qwen_max_schema_rich_v2/predictions/test_tpl_ho.schema_rich.jsonl) · [test_tpl_ho_smoke.schema_rich.jsonl](../outputs/prompt_qwen_max_schema_rich_v2/predictions/test_tpl_ho_smoke.schema_rich.jsonl)

**data/processed**

[test.jsonl](../data/processed/test.jsonl) · [train.jsonl](../data/processed/train.jsonl) · [validation_report.json](../data/processed/validation_report.json)

**data/processed_v2**

[dev.jsonl](../data/processed_v2/dev.jsonl) · [generation_report.json](../data/processed_v2/generation_report.json) · [test_tool_ho.jsonl](../data/processed_v2/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../data/processed_v2/test_tpl_ho.jsonl) · [train.jsonl](../data/processed_v2/train.jsonl) · [verification_report.json](../data/processed_v2/verification_report.json)

**data/processed_v3**

[dev.jsonl](../data/processed_v3/dev.jsonl) · [generation_report.json](../data/processed_v3/generation_report.json) · [test_tool_ho.jsonl](../data/processed_v3/test_tool_ho.jsonl) · [test_tpl_ho.jsonl](../data/processed_v3/test_tpl_ho.jsonl) · [train.jsonl](../data/processed_v3/train.jsonl) · [verification_report.json](../data/processed_v3/verification_report.json)

