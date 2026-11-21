# 实验台账（v2 证据战役）

逐日记录关键决策、产物指纹与实验状态，供论文写作时回溯证据链。

### 2026-11-21 01:15 CST 远端 scope-context 诊断复验启动
- 依据 `comprehensive_audit_2026-11-21.md`，继续 E1 的受限诊断实验；E2/GRPO 仍未启动，原因是独立任务成功 checker、信息权限定义和 exploit tests 尚未闭合。
- 远端硬件：NVIDIA RTX 4080 SUPER 32GB；代码目录 `/root/consdag`；数据目录 `data/processed_v2`。四个数据文件哈希与本地冻结版一致：train `4358c60d...391091`、dev `143619f3...4423df`、test_tpl_ho `44083a84...cf003`、test_tool_ho `363b3f0b...62241`。
- 运行目录：远端 `outputs/gpu_e1_scope_context_20261121/Qwen3-0.6B-seed42-bf16/`；独立于旧 `outputs/e1/Qwen3-0.6B`。代码为当前 `src/run_e1.py` 的 scope-context prompt 版本，远端 runner SHA256 `a284a53a...0e1b7`。
- 配置：Qwen3-0.6B，seed 42，BF16，3 epochs，LoRA `r=16/alpha=32`，lr `2e-4`，gradient accumulation 4，sequence length 1024，generation length 384，eval batch 16；使用同一 v3 scorer。scope-context 额外提供任务空间节点元数据（cost/duration/recipient/data classes/terminal），用于检验旧运行中 scope 错误是否由输入信息不足造成。
- 预检：2-step smoke 通过，首步 loss `1.7202147245407104`，return code 0。正式训练 PID `16095` 已启动并保持运行，显存约 5.2 GiB；队列协调器随后被停止，因此 1.7B/4B 不会自动启动。当前结果状态为 `running`，训练完成后必须人工检查 adapter、predictions、metrics 和同一 v3 scorer 重算。
- 解释边界：这是合成 v2 数据上的 scope-context 诊断，不是新主表、不是多 seed 复制，也不能证明真实隐式语用理解、校准拒判或创新点①已成立。原始 scope-free/oracle 数字仍按审计中的诊断口径保留。

## 2026-11-20

### 2026-11-20 21:45 CST 强模型提示词复核与 GPU 状态
- DashScope `qwen-max` 鉴权复核：用户提供的凭据在 `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` 返回 HTTP 401；未生成任何强模型预测，不能作为 E1 P 臂结果。
- 远程服务器环境变量只做存在性检查，未读取或写入凭据；交互环境没有可用 DashScope key。强模型提示词实验仍待有效 key，不能用本地 0.6B CPU pilot 代替。
- 方法口径：qwen-max 可以作为 GPT-4o 的代表性闭源强模型对照，但论文中应明确写实际使用的模型、版本/日期、提示词、温度、token 上限和调用成本；不能把 qwen-max 结果称为 GPT-4o 结果。
- 远程 GPU：RTX 4080 SUPER 32GB，Qwen3-4B E1 PID 3942，约 7,300/9,000 optimizer steps，显存约 22,670/32,760 MiB，利用率约 44%，日志未见异常。
- 本机 GPU：RTX 4060 Laptop 8GB，Qwen3-1.7B E1 PID 63284 仍存活，显存约 7,802/8,188 MiB，利用率约 42%；训练后 adapter、预测和最终 metrics 尚未落盘。

### 环境
- 本机 RTX 4060 8GB（桌面占用后 ~5GB 可用），base Python 3.12.6 + torch 2.12.0+cu126 + transformers 4.57.6 + peft 0.19.1。
- 决策：仅跑 <4B 模型（0.6B/1.7B），4B/8B 等多余算力再补。

### 模型（避免旧任务污染，全部重新下载）
- 来源：ModelScope `Qwen/Qwen3-0.6B`、`Qwen/Qwen3-1.7B`，下载到 `models/`。
- `models/Qwen3-0.6B/model.safetensors` SHA256: `F47F71177F32BCD101B7573EC9171E6A57F4F4D31148D38E382306F42996874B`。
- `models/Qwen3-1.7B/model-00001-of-00002.safetensors` SHA256: `169AD53EC313C3A34B06C0809216E4FC072CCE444A5D4FF2B59690D064130ED5`。
- `models/Qwen3-1.7B/model-00002-of-00002.safetensors` SHA256: `912BECFF8D60672AA8628EF08C05898D9ADF17C2AD4AE3CAF99B065622FDEFF9`。

### API key 实测（PE 实验准备）
- 用户提供的 DashScope 凭据在阿里 compatible-mode 返回 HTTP 401 `Incorrect API key`；没有成功的 qwen-max/qwen-plus 调用，也没有生成 PE 结果。
- 已检查可用的现有模型中转路由，未找到 qwen-max/qwen-plus；未把其他模型或本地模型冒充该 P 臂。
- 用户决策：先跑本地 T/Z 臂，PE 臂与 S6 oracle 后补（需要有效的强模型 API）。

### 数据 v2（S1-S8，可信数据空间背景）
- 领域化：工具池 61 角色（7 个训练子系统 + 3 个 held-out 专属子系统 trace/qos/fl），
  映射 docs/rules 的数据资产/权限/工作流/沙箱/服务组合/钱包/分析产出规则。
- 约束五类带 severity + scope 绑定：budget(钱包/QoS 花费)、deadline(QoS 时限)、privacy(PII 不出本地)、
  tool_auth(审批前置)、order(工作流先后)。
- 规模：5,000 组 x E/I/N 三版 = 15,000 条（train 12,000 / dev 900 / test_tpl_ho 1,050 / test_tool_ho 1,050）。
- E/I 配对：同 DAG + 同约束集 + 同信息面；I 版线索三类型(consequence/fact/convention) x 难度 1-3；
  模板池 train/test 严格分池（每类每版每池 >=8 变体）。
- 约束类型分布：budget 3770 / order 3582 / deadline 3668 / tool_auth 3444 / privacy 3206。
- 数据 sha256：train `4358c60d...391091` / dev `143619f3...4423df` / test_tpl_ho `44083a84...3cf003` /
  test_tool_ho `363b3f0b...362241`（全量见 `data/processed_v2/generation_report.json`）。
- S5 witness 复查 0 失败、S7 泄漏检查（工具 2-子集 0、模板 0、证据句 3-gram Jaccard 0.047）。
- 修正记录：首版 tool_ho 组的 budget 约束注入了 train 付费角色（DAG 混入非 held-out 角色）；
  修正为 held-out 专属付费角色 `create_fl_round`（FL 算力配额），重新生成后 tool_ho DAG 100% held-out
  （train/dev/tpl_ho 指纹不受影响，仅 test_tool_ho 更新）。
- 生成前配置冻结：`configs/dataset_v2.yaml`（seed 42，可复现）。
- 数据 sha256 记录于 `data/processed_v2/generation_report.json`。
- 已知局限（如实写入论文 limitations）：纯合成模板语料；confidence 全为构造期 1.0（无校准目标）；
  无歧义/拒判样本（I 版红线所致）；test_tool_ho 无 tool_auth 约束（held-out 无授权惯例对）。

### E1（T/Z 臂）启动
- 臂定义：Z = 基座 zero-shot 结构化抽取；T = LoRA（r16 a32 lr2e-4，3 epochs，bs1 ga4，seq<=1024）。
- 评测：dev(in-domain) / test_tpl_ho / test_tool_ho 三子集分列；指标 = 三态准确、约束 micro P/R/F1、
  per-type、I 版难度分桶(d1/d2/d3)、evidence span 精确率、JSON 解析率。
- Token 预算实测：prompt max 394、completion max 324（p99 279），1024/384 足够。
- 管线冒烟：0.6B zero-shot 8 条 dev 解析率 0.75、F1 0.0（符合预期，弱模型复制枚举语法）。
- 队列：原计划 `scripts/run_e1_queue.ps1` 串行 0.6B -> 1.7B。
- 2026-11-20 01:14 用户曾指示暂停 1.7B 自动接力；随后用户最新决定恢复队列：0.6B 完成后自动运行 1.7B，无需再次确认。当前队列 watcher 已重启，0.6B 主任务不受影响。
- E2/E3 前置修正（GPT 对照指出的单点阻塞）：门控奖励求和域从 `Ĉ` 改为 `C* ∪ Ĉ`，
  对 `C* \ Ĉ`（漏检）显式 `-λ_miss`，对 `Ĉ \ C*`（误拦）`-λ_block`；实现排入 E2/E3。

### 待办
- S6 oracle 可恢复性准入（I 版恢复集 ⊇ 金标且无金标外新约束；N 版抽样恢复须空集）——等强模型 API。
- E1 P 臂（qwen-max/qwen-plus x ATLAS/CARL 式提示词）——等有效 DashScope key。
- E2 六臂同预算对照 + E3 消融链（A 去编译器 / B 去绑定 / C 对称罚 / D 去拒判 / E 去外部锚）。
- E5 校准拒判（v2 数据无校准目标，需另行构造或如实降级）。

### 2026-11-20 CPU 复核与运行状态
- 运行中的任务：`python src/run_e1.py --model models/Qwen3-1.7B --eval-batch-size 8`，本机 RTX 4060 独占；日志已进入 LoRA 训练阶段，计划 9,000 optimizer steps。未启动并行 GPU 任务。
- 独立数据复核：`python src/verify_dataset_v2.py --data-dir data/processed_v2`，15,000 条记录；witness 重放失败 0、schema 失败 0、E/I/N 配对失败 0、工具二元组合泄漏 0、模板泄漏 0，证据句 3-gram train/test Jaccard 0.0471，判定 `PASS`。
- 代码语法复核：`src/*.py` 已逐文件编译检查；本次 PowerShell 通配符调用方式不兼容，未将该次报错作为代码失败，后续以逐文件编译结果为准。
- 下一步：1.7B 结束后使用同一评测输出和 `src/analyze_e1_errors.py` 生成 type/state/params/scope/evidence 分解，再决定第二 seed 或 scope 消融；不把当前单 seed 结果写成稳定结论。
- 0.6B 反事实字段修复诊断（`src/counterfactual_e1.py`；结果见 `outputs/counterfactual_e1_0.6b.json`）：只把预测 scope 替换为对应金标，strict F1 从 dev 0.729→0.979、template-held-out 0.630→0.834、tool-held-out 0.303→0.838；只修 params 时分别为 0.746、0.667、0.347。该诊断是 oracle 上界分解，不是模型结果。当前证据指向工具留出主要瓶颈为角色 scope 泛化，下一步优先补充角色语义/结构输入并做受控消融。
- 远程 GPU 接入（19:40 更正）：SeetaCloud 服务器已连通，RTX 4080 SUPER 32GB、Ubuntu 22.04、Python 3.12.3、torch 2.12.1+cu130；代码与 15,000 条数据已同步到 `/root/consdag`，Qwen3-4B 权重下载完整，4B E1 已按 0.6B/1.7B 同一配置启动（seed 42、LoRA r16/a32、3 epoch、9000 steps）。密码仅通过环境变量传递，未写入仓库。
- 4B zero-shot（服务器，运行时初报）：dev 900 条完成，约束 F1 0、三态准确率 0.3533；当时 test_tpl_ho/test_tool_ho 仍在生成。之后用统一 v3 评分器重算三子集，state accuracy 为 0.3511/0.3838/0.3724，F1 均为 0（见 `metrics_zero_shot_e1_score_v3.json`）。
- 1.7B 进度（本机 4060）：训练 2700/9000 步，约 30%，近期约 14–15 秒/步，预计 2026-11-21 完成。
- GRPO/E2 状态：仓库目前没有 planner rollout 环境、奖励实现或 GRPO trainer；只有实验方案。未把 E1 LoRA 训练误报为 GRPO，也未伪造 E2 启动。

### 2026-11-20 实验设计与结果审查
- 新增 `reports/experiment_audit_2026-11-20.md`，按证据等级区分已证实、进行中和不可采信结果。
- 当前可引用的最强结果仍是 0.6B seed 42 的合成数据 feasibility：dev/template-ho/tool-combination-ho strict F1 = 0.7291/0.6299/0.3030；scope 反事实替换只是诊断上界。
- 4B 已完成 zero-shot，核查时远程 LoRA 日志约 900/9000；1.7B 本机日志约 3200/9000。两者均未形成训练后结果（状态核查时间：2026-11-20 20:06 Asia/Shanghai）。
- 远程卡核查为 RTX 4080 SUPER 32GB，约占用 21.4 GiB、利用率 57%；此为单次状态快照。
- 评测器 v3 和 S6 oracle fail-closed 检查共通过 22 个测试；无效 JSON 不再计为状态/空集正确，S6 恢复/判定解析失败按不通过计。strict F1 匹配 `type/state/severity/scope/params`，不含 description/evidence；evidence exact rate 仅在已匹配约束上计。旧 0.6B `metrics.json` 和 `metrics_e1_score_v2_recomputed.json` 仅保留作历史口径，正式比较只使用 `metrics_e1_score_v3_recomputed.json`、`metrics_zero_shot_e1_score_v3.json` 等统一 v3 文件。
- 审查确认：I 版隐式语义、校准/拒判、完整工具泛化、E2/GRPO 和 planner 下游收益都尚未被当前实验验证；E2 先解决 `C*` 漏检信号权限与外部锚完成性。

### 2026-11-20 20:36 CST 运行与测量面复核
- 本机 RTX 4060：Qwen3-1.7B E1 PID `63284` 仍在运行，日志到 `3500/9000` optimizer steps；未发现异常/OOM，尚无训练后 adapter、predictions 或最终 metrics。
- 远程 RTX 4080 SUPER 32GB：Qwen3-4B E1 PID `3942` 仍在运行，日志到 `2900/9000`；单次核查约 `22668/32760 MiB` 显存、GPU 利用率约 `42%`；未发现异常/OOM，尚无训练后 adapter、predictions 或最终 metrics。此前保存的 4B v3 数字仍只代表 zero-shot。
- 增加测量面审查：extractable JSON、schema-valid、query-state/constraint-contract-valid 与 strict F1 分开报告；可解析 JSON 不能作为契约或语义正确的替代指标。
- 将 I 版模板构造效度提升为 P0：90 模板单人初审为 direct/infer-candidate/ambiguous 共 73/8/9；budget 12/2/4、deadline 9/4/5、privacy 16/2/0、tool_auth 18/0/0、order 18/0/0。tool_auth/order 当前无通过初审的隐式模板。该统计不是双人盲审结论。现有 implicit F1 仅可称 `synthetic I-template split score`；在双人盲审、过滤统计和 agreement 之前，不写成真实隐式语用理解。
- DashScope qwen-max 凭据返回 HTTP 401 `Incorrect API key`；PE 强模型结果未取得。旧 v1 `run_pilot.py` 不作为 v2 E1 对照；另行运行的 CPU prompt pilot 会单独标记为本地 0.6B 诊断。
- 本轮仍保持本机 1.7B 与远程 4B 主训练进程，不启动 E2/GRPO。
- 继续保持两个 E1 进程，不启动 E2/GRPO。训练完成后必须用同一 v3 评分器重算三子集，并检查 `metrics.json`、trained predictions、adapter 是否完整落盘。

### 2026-11-20 20:45 CST 结果与命名复核
- 评测与 oracle 回归测试：`23 passed`。当前统一口径仍是 v3 scorer；旧 v1 prompt pilot 不纳入 v2 主表。
- 强模型提示词对照：DashScope qwen-max 凭据返回 HTTP 401，未取得可报告的强模型结果；不能用本地模型或旧 v1 结果冒充 P 臂。
- 已启动本机 Qwen3-0.6B CPU 配对 prompt pilot：v2 三个子集各抽 5 个完整 E/I/N 组，共 45 条；baseline 与逐字段 improved prompt 使用同一 v3 scorer，结果目录为 `outputs/prompt_pilot_v2_0.6B_cpu/`。该运行仅为低成本诊断，不等价于 qwen-max。
- 用户要求的命名清理已完成：远程快照目录改为 `outputs/gpu_snapshot_20261120/`；遗留 Kaggle 试跑产物已删除。当前主训练进程未被触碰。
- scope 反事实 `0.979/0.834/0.838` 明确登记为 oracle 上界；不得直接写成普通 `strict_without_scope` 模型结果，后者必须从原始预测独立重算。
- 已从原始 0.6B trained predictions 运行 `src/analyze_e1_errors.py`，独立得到 `strict_without_scope` F1 `0.9794/0.8339/0.8382`（dev/template/tool）；它与 scope oracle 替换分数数值相同但计算含义不同，报告已分栏。工具组合留出 type+state F1 `0.9971`，完整 strict F1 `0.3030`；条件 scope 准确率仅 `0.3485`（分母 1211 个 type+state 匹配对），支持 scope 是主要错误来源的诊断，但不能视为因果或跨 seed 证据。
- 本机 CPU 提示词 pilot 完成（Qwen3-0.6B，v2 固定配对样本 45 条，3 子集各 5 个 E/I/N 组，贪心解码、max_new_tokens 384，同一 v3 scorer）：baseline 约束 micro F1/state accuracy/JSON parse rate = `0.000/0.3556/0.7778`，耗时 `1413.6 s`；逐字段 improved prompt = `0.000/0.2889/0.8444`，耗时 `2080.9 s`。提升的仅是 parse rate（+6.7pp），strict F1 无改善，state accuracy -6.7pp；改进臂的 implicit/none state accuracy 均为 0。它是每子集 5 组的等距抽样诊断，不是 qwen-max 对照，不支持对一般提示工程或训练优越性的结论。原始预测、metadata、结果均在 `outputs/prompt_pilot_v2_0.6B_cpu/`。
- 强模型提示词 P 臂仍未完成：DashScope qwen-max 返回 HTTP 401 `Incorrect API key`，没有可比较的强模型预测；待有效凭据后再跑同 v2 数据与 v3 scorer 的正式对照。
- 21:37 CST 运行状态复核：本机 1.7B PID `63284` 前进到 `3800/9000`（日志时间 21:26:10）；远程 4B PID `3942` 前进到 `6500/9000`（日志时间 21:31:57）。两进程均存活、未见异常；没有停止或重启训练。

### 2026-11-20 22:10 CST qwen-max P 臂已启动
- 新 DashScope key 已用 compatible-mode 最小请求验证成功（HTTP 200）；密钥只通过临时进程环境变量传递，不写入仓库、metadata、预测文件或日志。
- 新增 `src/run_qwen_max_e1.py`：复用 `run_e1.py` 的原始 E1 prompt、`extract_json`、`normalise_prediction` 和 `score`（`e1_score_v3`）；逐样本保存原始响应、解析预测、请求状态、模型名、端点和时间戳，支持成功行断点续跑，并在请求失败时阻止生成可报告的汇总分数。
- 9 条 smoke（dev/template-ho/tool-combination-ho 各 1 个完整 E/I/N 组）已成功。原始 prompt 的 smoke 严格约束 F1 = 0；state accuracy = 0.667/0/0.333，JSON parse rate = 1.0/0.667/0.667。样本量仅用于链路验收，不作模型结论。
- 正式原始 E1 P 臂已启动：`qwen-max`、temperature 0、max_tokens 384、4 个 API worker；输出目录 `outputs/prompt_qwen_max_e1/`，日志 `run_e1_original.log`。启动后 dev 已完成前 50/900，未见请求错误。
- ATLAS-inspired P 臂按原文“枚举显式与可推断约束”原则改写到同一 E1 JSON schema；不称为 ATLAS 原 prompt 逐字复现。其 smoke 通过后自动启动全量 3,000 条评测，输出 `atlas_adapted` 文件名。CARL 原文是约束删除/查询简化 prompt，不与此 JSON F1 直接冒充同类复现。
- 远端 SeetaCloud SSH 本轮公钥认证未通过；API 评测不占 GPU，故回退本机执行，未触碰本机 4060 上的 Qwen3-1.7B 训练或远程 4B 训练。
# 2026-11-20 23:20 CST

- 完成 qwen-max 原始 E1 prompt 臂的断点恢复：此前 `test_tool_ho-00013-N` 网络错误已成功补跑；输出 `outputs/prompt_qwen_max_e1/results.e1_original.json`，三子集完整，无请求错误。严格约束 F1（dev / tpl-ho / tool-ho）= `0 / 0 / 0`，parse rate=`0.9867 / 0.9829 / 0.9676`。
- ATLAS-inspired 适配臂继续运行，dev 完成且 F1=0；该实现仅为适配 prompt，不能标作原文复现。
- 启动 schema-rich qwen-max 控制臂 PID 25652，输出目录 `outputs/prompt_qwen_max_schema_rich_v2/`，用于区分参数契约错配与模型抽取能力；结果未完成前不纳入主表。
- 4B trained E1 已完成，统一 v3 严格 F1=`0.4523/0.3207/0.0670`；1.7B 在 step 4400 出现 NaN，无 trained 结果。
- 回归测试 `23 passed, 2 skipped`。

### 2026-11-21 E1 stability replication preregistration
- Research question: does the 0.6B E1 feasibility result persist under a new random seed when training uses explicit BF16 and finite-loss/gradient guards?
- Run: Qwen3-0.6B, seed 43, same v2 train/dev/template-held-out/tool-combination-held-out files, 3 epochs, LoRA r=16/alpha=32, lr=2e-4, gradient accumulation 4, max sequence 1024, max generation 384, greedy evaluation, v3 scorer. Precision is explicitly BF16 because the seed-42 run did not record precision; this is a robustness replication, not an exact reproduction.
- Primary outcome: strict constraint micro-F1 by the three fixed subsets; secondary: variant F1, per-type F1, state accuracy, parse rate, and training failure/NaN status. One seed is a replication check, not a multi-seed significance claim.
- Expected: lower dev/template scores than oracle-free diagnostics, with tool-combination-held-out still weaker; no directional claim is registered for the new seed. A non-finite loss/gradient aborts the run and is recorded as failure, never silently skipped.
- Output: `outputs/e1/Qwen3-0.6B-seed43-bf16/`; preflight smoke output: `outputs/e1_preflight/Qwen3-0.6B-seed43-bf16/`. The running qwen-max API comparisons are independent and do not use the GPU.

### 2026-11-21 01:03 CST E1 seed-43 launch and design gate
- Training environment was corrected after the preflight was initially invoked with a Python installation that had no torch. The verified interpreter is `D:\Programe_Env\Python\Python312\python.exe` with torch `2.12.0+cu126`, CUDA available, transformers `4.57.6`, and peft `0.19.1`.
- The BF16 8-step smoke run passed using Qwen3-0.6B, v2 data, LoRA `r=16/alpha=32`, learning rate `2e-4`, gradient accumulation `4`, sequence length `1024`, seed `43`, and finite-loss/finite-gradient guards. First optimizer-step loss was `2.2899701595306396`; `smoke.json` is in `outputs/e1_preflight/Qwen3-0.6B-seed43-bf16/`.
- Full seed-43 run started in the background as PID `82152`, output `outputs/e1/Qwen3-0.6B-seed43-bf16/`, log `outputs/e1_0.6b_seed43_bf16_run.log`. Zero-shot evaluation is intentionally skipped because it is deterministic for this base model and already exists under the seed-42 baseline; trained predictions will still be scored with the same `e1_score_v3` scorer. A missing or non-finite training result is recorded as failure and is not converted into a metric.
- Current E1 design gate remains **continue with restricted claims**: v2 construction/witness/leakage checks and scorer tests pass, but I-template validity, confidence/abstention calibration, and downstream E2/GRPO are not established. E2 is not launched because the planner rollout environment, independent success checker, and the information permission for the true constraint set `C*` are still unspecified.
- Literature audit changes the novelty wording: innovation 1 must be presented as the learned, auditable combination of typed state/evidence/scope/confidence outputs with a planner-agnostic interface. The extracted nearest-neighbor papers occupy several individual components; no “complete component has zero prior coverage” or “no recent paper matches” claim is allowed without a dated search protocol.
- qwen-max schema-rich control arm is complete under the same v2 data and `e1_score_v3`: strict micro-F1 is `0.03963 / 0.03594 / 0.01005` (dev / template-held-out / tool-combination-held-out), with parse rates `0.9944 / 0.9952 / 0.9943`. It improves formatting/parameter compliance relative to the original prompt but remains weak on implicit and none variants; it is a control arm, not evidence that a strong model solves the task.

### 2026-11-21 GPU queue correction and restart
- The first remote scope-context queue was interrupted after only the dev zero-shot subset was written. It was spending many hours on a duplicate zero-shot pass before training; its partial output remains under `outputs/gpu_e1_scope_context_20261121/` and is not merged into the formal table.
- A new independent queue is running on the remote RTX 4080 SUPER under `outputs/gpu_e1_scope_context_20261121_fast/`. It uses the frozen `processed_v2` hashes, BF16, LoRA `r=16/alpha=32`, lr `2e-4`, 3 epochs, gradient accumulation 4, max sequence 1024, max generation 384, finite-loss/gradient/parameter guards, and per-model effective eval batches 64/32/16 for 0.6B/1.7B/4B. Full runs skip duplicate zero-shot evaluation; this queue is labelled a scope-context input-sufficiency diagnostic and does not overwrite legacy runs.
- At launch the 0.6B smoke passed (2 optimizer steps; first loss `1.7202147245407104`) and full BF16 training reached optimizer step 1 without a non-finite value. The remote GPU process and supervisor were verified alive. The queue manifest is the source of truth for completion and failure.
- The local seed-43 replication did not produce a complete run (no adapter, predictions, metrics, or active training process); it is marked incomplete and is excluded from scaling claims. The prior local 1.7B fp16 NaN run remains failed and excluded.
- Regression suite after the queue change: `24 passed, 2 skipped`.

### 2026-11-21 01:34 CST audit refresh and remote run check
- Local regression suite rerun after the queue and finite-value changes: `26 passed`.
- Independent dataset verifier rerun on `data/processed_v2`: 15,000 records; witness/schema/pair failures 0; tool 2-subset leakage 0; template leakage 0; evidence 3-gram Jaccard 0.0471; verdict `PASS`.
- Text-quality scan rerun: flagged rows remain train 728/12,000, dev 52/900, template-HO 55/1,050, tool-combination-HO 35/1,050. These rows are a validity review queue, not an automatic rejection of the structural dataset checks.
- Remote RTX 4080 SUPER queue is alive under `outputs/gpu_e1_scope_context_20261121_fast/`. Qwen3-0.6B BF16 scope-context diagnostic reached optimizer step 400/9000 with finite losses (latest observed loss 0.0087308), about 10.3 GiB GPU memory, and no failure. The queue manifest remains `status=running`; 1.7B and 4B will start only after the preceding model has a complete adapter, predictions, and metrics.
- Interpretation remains restricted: this prompt exposes graph metadata used by the synthetic scope generator, so the run measures input sufficiency on the synthetic contract. It is not evidence of planner-agnostic deployment, real implicit pragmatics, calibration/abstention, or CCF-B validation.
