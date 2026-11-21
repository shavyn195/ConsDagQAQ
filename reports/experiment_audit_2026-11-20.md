# 实验设计与结果审查（2026-11-20）

## 运行更新（2026-11-20 23:20 CST）

- Qwen-max 原始 E1 prompt 臂已补齐先前失败的 `test_tool_ho-00013-N`，三子集均有完整 1:1 预测。统一 `e1_score_v3` 严格约束 F1 为 `0.000 / 0.000 / 0.000`（dev / template-held-out / tool-combination-held-out）；JSON parse rate 为 `0.987 / 0.983 / 0.968`。这只能作为 qwen-max 的原始 schema prompt 对照，不能写成 GPT-4o 结果。
- ATLAS-inspired 适配 prompt 正在运行，已完成 dev，严格 F1 为 `0.000`；该臂是将 ATLAS 的枚举原则翻译到本项目 JSON 契约的适配实现，不是 ATLAS 原文逐字复现。template/tool 两个子集尚未完成，当前不汇总为最终对照。
- schema-rich qwen-max 控制臂已通过 smoke，正在跑完整三子集。它单独测试“显式给出参数键和 scope 规则”能否修复原始 prompt 的契约错配，不与原始 P 臂合并。
- Qwen3-4B LoRA E1 已完成；统一 v3 严格 F1 为 `0.4523 / 0.3207 / 0.0670`，训练日志到 9000 步且未见 NaN。该结果不支持单调 scaling，工具组合留出退化明显。
- Qwen3-1.7B 训练在 step 4400 进入 NaN，step 4500 后无有效训练产物；只保留 zero-shot 结果，不能计入 trained scaling 或主表。
- 本轮代码与评测回归：`23 passed, 2 skipped`。

## 最新运行复核（2026-11-20 21:45 CST）

- 强模型提示词对照仍未完成：DashScope `qwen-max` 鉴权返回 HTTP 401；远程交互环境没有可用 DashScope 凭据。没有生成强模型预测，也没有把 CPU 0.6B pilot 计入 P 臂。
- qwen-max 可在方法上替代 GPT-4o 作为闭源强模型对照，但必须按实际模型名和调用日期报告，并保持同一 v2 数据、提示词、温度 0、384-token 上限与 v3 scorer；qwen-max 结果不能标为 GPT-4o 结果。
- 远程 RTX 4080 SUPER 32GB 的 Qwen3-4B E1 PID 3942 已推进到约 7,300/9,000 步，显存约 22.7/32.8 GiB、利用率约 44%，未见异常。本机 RTX 4060 的 Qwen3-1.7B PID 63284 仍在运行，显存约 7.8/8.2 GiB、利用率约 42%。
- 两个训练进程均未停止或重启；训练后产物出现后，仍需用同一 v3 scorer 重算三子集并检查 adapter、predictions 和 metrics 完整性。

## 审查结论

当前证据只支持一个较窄、但可复核的结论：在合成的 v2 数据上，0.6B LoRA 能学会结构化约束输出契约；模板留出仍有可用性能，工具组合留出明显退化。这个结果是 E1 的单 seed feasibility 证据，不足以证明真实隐式语用理解、校准拒判、planner 下游收益或创新点 ①/② 已经成立。

E2/GRPO 目前没有可运行实现，不能启动或写成已有结果。当前最重要的工作不是继续扩大模型，而是修正测量面并把 E2 的奖励信息源和外部锚定义清楚。

## 证据与运行状态

| 项目 | 状态 | 可采信口径 |
| --- | --- | --- |
| v2 数据 | 15,000 条，E/I/N 配对、witness/schema/基本泄漏检查通过 | 支持合成编译器 E1；不等于隐式语义已被人工或 oracle 证明 |
| 评测器 | `e1_score_v3` 已加入长度检查、一对一匹配、证据对齐、空集指标、难度 FP，并将无效 JSON 计为错误；S6 oracle 已加 fail-closed 解析 | 22 个测试通过；统一重算文件已单独保存 |
| 0.6B E1 | seed 42，9,000/9,000 optimizer steps，已完成 | 单 seed、合成数据 feasibility |
| 1.7B E1 | 本机 RTX 4060，训练日志在 step 4400 进入 NaN，step 4500 后停止 | 训练失败；仅 zero-shot 可用，无 trained adapter/正式 trained 指标 |
| 4B E1 | 远程 RTX 4080 SUPER 32GB，9000/9000 已完成 | trained 结果已用 v3 统一重算；工具组合留出明显退化 |
| qwen-max 原始 P 臂 | API 三子集均已完成，单条断点失败已恢复 | 严格 F1=`0/0/0`；可作为 qwen-max 原始 schema prompt 对照，不能称 GPT-4o |
| ATLAS-inspired P 臂 | dev 已完成，template/tool 仍在运行 | 适配实现，不是 ATLAS 原文逐字复现；未完成前不汇总 |
| schema-rich P 控制臂 | smoke 通过，完整三子集运行中 | 单独控制参数契约错配，不与原始 P 臂合并 |
| E2/GRPO | 未实现 planner、rollout 环境、checker、reward 或 trainer | 不启动、不报告结果 |

远程 4B 的数据哈希与本地 v2 数据一致，启动配置为 seed 42、3 epochs、lr `2e-4`、LoRA `r=16/alpha=32`、gradient accumulation 4、sequence length 1024、generation length 384、eval batch 16。21:44 CST 核查时训练日志约为 `7300/9000`，RTX 4080 SUPER 显存约 `22.7/32.8 GiB`、利用率约 44%；没有发现 OOM 或训练异常。GPU 快照和日志位于 `outputs/gpu_snapshot_20261120/Qwen3-4B/`，本地快照只含训练前 zero-shot 预测，不能作为当前训练进度。

## 已有结果

### 三个尺寸的 zero-shot 对照

| 模型 | dev F1 | template-held-out F1 | tool-combination-held-out F1 | JSON parse rate 范围 |
| --- | ---: | ---: | ---: | ---: |
| Qwen3-0.6B | 0 | 0 | 0 | 0.793–0.818 |
| Qwen3-1.7B | 0 | 0 | 0 | 0.678–0.720 |
| Qwen3-4B | 0 | 0 | 0 | 0.968–0.980 |

4B 的 JSON parse rate 较高，但 0.6B/1.7B 并非随规模单调变化；三个尺寸都没有在严格结构匹配上命中约束。它只说明当前 zero-shot schema 提示基线较弱；不构成对强模型 prompt engineering 基线的胜出证据。1.7B 与 4B 的训练后结果仍在运行中。

解析层级不能混用。对保存的 zero-shot 输出做了额外契约检查，得到如下比例（extractable JSON / schema-valid / query-state-and-constraint-contract-valid）：

| 模型 | 子集 | 可提取 JSON | schema 合规 | 状态/约束契约合规 |
| --- | --- | ---: | ---: | ---: |
| Qwen3-0.6B | dev / template-ho / tool-ho | 0.8178 / 0.8143 / 0.7933 | 0.2267 / 0.2410 / 0.1933 | 0.2044 / 0.2314 / 0.1771 |
| Qwen3-1.7B | dev / template-ho / tool-ho | 0.6822 / 0.7200 / 0.6781 | 0.6189 / 0.6962 / 0.6267 | 0.5733 / 0.6210 / 0.5762 |
| Qwen3-4B | dev / template-ho / tool-ho | 0.9756 / 0.9676 / 0.9800 | 0.9556 / 0.9629 / 0.9657 | 0.8622 / 0.8876 / 0.8819 |

这些是 zero-shot 的格式与契约诊断，不是严格约束 F1；格式可解析也不能替代一对一的语义匹配。

### 0.6B trained（seed 42）

| 子集 | strict constraint F1 | implicit F1 | state accuracy | JSON parse rate |
| --- | ---: | ---: | ---: | ---: |
| dev | 0.7291 | 0.7199 | 0.9978 | 0.9978 |
| template-held-out | 0.6299 | 0.6144 | 0.9324 | 1.0000 |
| tool-combination-held-out | 0.3030 | 0.2791 | 0.9962 | 0.9962 |

只把预测的 scope 替换为对应金标的反事实诊断，将 F1 从 `0.7291/0.6299/0.3030` 提高到 `0.979/0.834/0.838`（dev/template/tool）。这是 oracle 上界分解，不是完整模型结果。随后从原始预测独立按忽略 scope 的匹配键重算，`strict_without_scope` 恰为 `0.979/0.834/0.838`；因此这组数可以作为“忽略 scope 字段的宽松结构指标”报告，但必须和完整 strict F1、oracle 诊断分栏，不能写成约束编译器已经达到该分数。它提示 scope/role binding 错误可能占当前工具组合留出误差的很大部分，值得优先做受控表示或消融，但不能据此作因果证明。

`strict constraint F1` 的一对一匹配键是 `type/state/severity/scope/params`；`description` 和 `evidence_span` 不参与 TP 匹配。evidence exact rate 只在结构键已匹配的约束上计算，因此是条件指标，不能替代全量 evidence-span 召回/忠实度。

错误分解显示类型差异很大：dev 上 deadline strict F1 约 `0.070`，而 privacy/order/tool_auth 分别约 `0.995/0.998/0.913`；工具组合留出上 budget 为 `0`、deadline 约 `0.014`、privacy 约 `0.996`、order 约 `0.321`。因此总 F1 会掩盖约束类型和组合的明显不均衡，后续主表必须保留 per-type 指标和分层样本数。

这些结果不能被写成多 seed 稳定泛化。原始 `outputs/e1/Qwen3-0.6B/metrics.json` 仍是旧评分格式；正式汇报应使用 `outputs/e1/Qwen3-0.6B/metrics_e1_score_v3_recomputed.json`，它由保存的 prediction 用当前 v3 评分器统一重算。

### Scope 口径复核（原始预测，seed 42）

| 子集 | 完整 strict F1（含 scope） | strict_without_scope F1 | oracle scope 替换 F1 |
| --- | ---: | ---: | ---: |
| dev | 0.7291 | 0.9794 | 0.9794 |
| template-held-out | 0.6299 | 0.8339 | 0.8339 |
| tool-combination-held-out | 0.3030 | 0.8382 | 0.8382 |

本次运行 `src/analyze_e1_errors.py` 独立重算前三个指标中的前两列；输出保存在 `outputs/analysis_e1_0.6b_scope_audit_20261120.json`。`strict_without_scope` 通过删除 scope 匹配条件得到，是模型预测的宽松评分；oracle 列则把已匹配约束的 scope 替换为 gold，属于诊断上界。两者在这份数据上碰巧相同，不可混称。

条件于 type+state 匹配的字段准确率（分母为相应已配对数；这是条件指标）：dev 的 scope/params/evidence 为 0.749/0.983/0.992，模板留出为 0.766/0.957/0.975，工具组合留出为 0.348/0.841/1.000；severity 均为 1.000。工具组合留出 type+state F1 为 0.997，而完整 strict F1 为 0.303。它支持“主要误差集中在 scope”这一诊断方向，但这是单 seed 合成分布上的条件分析，不能推出自然语言语用理解已泛化。
### 4B zero-shot（训练前基线）

| 子集 | strict constraint F1 | state accuracy | none empty-set accuracy | JSON parse rate |
| --- | ---: | ---: | ---: | ---: |
| dev | 0 | 0.3511 | 0.0633 | 0.9756 |
| template-held-out | 0 | 0.3838 | 0.1400 | 0.9676 |
| tool-combination-held-out | 0 | 0.3724 | 0.1314 | 0.9800 |

保存的 4B 快照只到训练 step 1；21:44 CST 远程日志约到 `7300/9000`。因此上述数字只代表训练前 zero-shot，不能解释为 4B 训练失败，也不能称为完整 E1 结果。v3 复算文件位于 `outputs/gpu_snapshot_20261120/Qwen3-4B/metrics_zero_shot_e1_score_v3.json`。

## 设计与测量风险

### P0：E2 漏检惩罚的信息源未闭合

公式对真实约束集 `C*` 与编译器输出 `Ĉ` 的差集计漏检罚，但训练时必须获得 `C*`。需要在实验协议中固定：`C*` 来自独立环境 checker、构造金标还是人工信号；所有对照臂是否拥有同一信息权限；以及为什么完整方法仍然需要编译器。否则会出现信息泄漏，或让对照不公平。建议第一版只实现 vanilla、加法约束奖励、完整版三臂，并记录相同 rollout/token/GPU 时间预算。

### P0：外部锚的“可执行”不等于任务完成

仅检查计划结构合法，可能让空计划或合法但未完成任务领取约束信用。锚至少应要求独立验证的任务成功和执行合法性，并加入四个攻击用例：空计划、合法但未完成、完成但违反约束、完成且满足约束。

### P0：I 版的构造效度尚未成立

对 90 个 I 模板的单人初审（不是双人盲审或最终标签）得到：budget 12 个直接陈述、2 个可推断候选、4 个歧义；deadline 9/4/5；privacy 16/2/0；tool_auth 18/0/0；order 18/0/0。合计 73 个直接陈述、8 个可推断候选、9 个歧义。尤其 tool_auth 与 order 当前没有通过初审的隐式模板。直接陈述或强线索不能作为“约束未被陈述、需要情境推断”的测量面；S6 oracle 恢复通过也不能修复这个构造问题。现有 implicit F1 必须标为“synthetic I-template split score”，不能写成真实隐式语用理解。下一步先冻结版本、逐模板双人盲审并报告过滤数与 Krippendorff α，再决定哪些模板进入主表。

### P1：强模型提示词基线尚未取得

DashScope 请求返回 HTTP 401 `Incorrect API key`，没有成功的 qwen-max 调用或可报告的 PE 结果。旧 `src/run_pilot.py` 使用 v1 数据和独立评分器，不可与 v2 E1 横比。本地 0.6B CPU prompt pilot 只是低成本诊断：它不等价于强模型基线、不证明训练优于提示工程，也不替代 v2 的 3,000 条正式 PE 评测。

本机 Qwen3-0.6B CPU 配对 pilot 已完成：三个子集各取 5 个完整 E/I/N 组，共 45 条固定样本；两臂均以贪心解码、384-token 上限和同一 `e1_score_v3` 评分。baseline 的约束 micro F1/state accuracy/JSON parse rate 为 `0.000/0.356/0.778`，耗时 `1413.6 s`；逐字段改进提示词为 `0.000/0.289/0.844`，耗时 `2080.9 s`。改进提示词将 JSON parse rate 提高 6.7 个百分点，但 strict 约束 F1 没有命中，state accuracy 下降 6.7 个百分点；隐式版 state accuracy 两臂均为 0，改进版 none state accuracy 也为 0。结果说明该改写改善了格式可解析性，却没有改善约束语义匹配；它还在 none 样本中产生多条约束预测。样本由排序后的 group ID 等距选取、每子集仅 5 组，因此这是单模型小样本诊断，不支持“提示工程普遍失效”或“训练胜过提示工程”。强模型 qwen-max P 臂仍未取得：DashScope 请求返回 HTTP 401 `Incorrect API key`；本 pilot 不是强模型结果。

### P1：S6 oracle 目前可能假通过

`src/oracle_check.py` 旧实现把解析失败按空约束继续处理，并让同一模型负责恢复和判定匹配。现已改为 fail-closed 并记录恢复/判定解析失败；仍需分离恢复与判定、分层 test 抽样和人工盲审，否则 N 版空恢复率仍不充分。

### P1：held-out 名称需要收窄

当前 `tool-held-out` 是特定 DAG 角色组合留出，不是未见角色词汇泛化；held-out 角色仍会出现在训练样本的 `available_roles` 干扰目录中，且该子集没有 `tool_auth`。报告中应使用“tool-combination-held-out”，不要写成完整工具或五类约束泛化。

### P1：校准与拒判没有测量面

gold confidence 全为构造期常数 `1.0`，没有 ambiguity 或 abstention-required 样本。当前不能声称 confidence calibration、abstain learning 或 selective risk 已验证。

### P2：单 seed 与数据规模限制

0.6B 结果只有一个 seed，且数据是模板合成语料。应报告 seed、数据生成版本、哈希和评测器版本，并把当前数字称为 pilot/feasibility，不能直接作为论文主结论。

## 最小后续实验顺序

1. 让当前 1.7B 和远程 4B 完成；对三尺寸保存的原始预测统一用 `e1_score_v3` 重算，并补 `analyze_e1_errors.py` 与 scope 反事实诊断。
2. 清洗 I 版重复冠词和拼接语病并记录过滤数；完成 S6 的 fail-closed 版本和人工抽审，清理或标记直接陈述规范的模板。
3. 为 E2 写最小 toy planner/environment、独立成功 checker 和 exploit tests，预先固定 `C*` 权限、奖励系数、rollout/token/GPU 时间预算。
4. 只跑 vanilla/additive/full 三臂的 smoke 和可达性预诊断；通过后再扩 TAG/RLVP 复刻和消融。
5. 先补 0.6B 或 1.7B 的第二、第三 seed，再决定是否值得继续 4B/更大模型。

6. 有效强模型 API 可用后，按相同 v2 三子集、相同 E1 prompt/schema、温度 0 和 384-token 上限补 qwen-max PE 正式对照；当前 CPU pilot 不得代替该对照。

## 当前禁止的表述

- “创新点①已经验证”或“近两年没有匹敌”；
- “implicit constraint 已证明语用推理”；
- “4B E1 已完成”；
- “GRPO/E2 已启动或已证明下游收益”；
- “confidence/abstention/calibration 已验证”；
- “tool-held-out 证明了未见工具或跨角色词汇泛化”。

## 2026-11-20 22:10 CST 强模型 P 臂状态

- 新 DashScope 凭据已通过 `qwen-max` compatible-mode HTTP 200 验证；此前的 401 记录保留为历史状态，不代表当前 key。
- smoke 已完成且所有请求成功。该结果只证明接口、E1 原始 prompt 和 v3 scorer 链路可运行，不能作为性能结论。
- 正式原始 prompt P 臂正在运行，三子集共 3,000 条，温度 0、384 token 上限、4 并发 worker；逐样本原始响应落盘，失败请求不会生成汇总结果。
- ATLAS-inspired 臂将使用同一数据、预算、解析器和评分器；它是忠实保留“显式+可推断约束枚举”政策的 schema 适配，不是 ATLAS 原文逐字复现。CARL 的约束删除 prompt 不直接纳入本次 JSON 抽取 F1 主表。
- 远端 GPU SSH 公钥认证失败，本轮 API 运行回退本机，不占用 4060 训练进程；远端 4B 训练状态仍需单独通过原连接核查。


