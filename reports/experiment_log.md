# 实验台账（v2 证据战役）


## 2026-11-22 11:45 CST：同分轨迹的违规身份诊断

复用服务器上已保存的 32 组多约束样本，逐条重算原检查结果。189 对同任务且都完成的轨迹中，100 对违反的约束数相同，其中 18 对违反不同约束，分布在 8/32 个组。例 train-02338-E 中授权与先后顺序各错一项。成对计数共享轨迹，不能当独立样本；该发现说明总分会丢失违规身份，不证明节点归因改善训练。证据 outputs/e2_v4/multiconstraint-gate-opportunity-v1/equal-score-different-constraints.json。下一步，同一预热适配器、同一检查器和预算，比较同总额的轨迹级/责任动作级信用；全局约束不能唯一归因时保留轨迹级处理。
逐日记录关键决策、产物指纹与实验状态，供论文写作时回溯证据链。

### 2026-11-21 22:15 CST v3 判定不合格 -> dataset v4 + E1-exec，服务器三模型队列重启
- **审计结论**（全量复算，详见 `reports/design_v4_ccfb.md` §1）：
  - v3 的 N 版 query 等于 goal，5000/5000；E/I 版全部是"goal + 额外句"，10000/10000，存在句子数量捷径。
  - 17,574/17,574 条约束已被唯一默认计划满足，约束完全不起约束作用。
  - severity 是 type 的常函数；I 线索有 1930/8787 含指令或顺序词。
  - 0.6B v3 在 dev/tool_ho 上 strict F1 = 1.0000，属于背模板。
  - v3 全部 E1 数字降级为 legacy 诊断，不进任何表。
- **处置**：
  - 停止服务器 v3 队列：1.7B-v3 在 step 5600/9000、loss 约 1e-5 时停止，结果作废。
  - v3 队列日志已追加停止记录。
- **v4**（commit `5f8fcd6` 和 `f63c727`）：
  - 可执行任务世界，每阶段 1–3 个备选工具，另有审批、脱敏、校验插入步骤。
  - 约束 100% 咬合，且逐条必要（全量复核）。
  - E/I/N 最小三元组，N 版用同主题近似干扰句。
  - I 版无指令词；d2/d3 需要算术或字段映射，且不含金标数值（含尾数捷径）。
  - held-out 工具名不进训练输入。
  - 策略卡随 prompt 给出，删掉恒定的 confidence/description。
- **v4 规模与验证**：
  - 15,000 条：train 12,000 / dev 900 / tpl_ho 1,050 / tool_ho 1,050。
  - V1–V9 全部 PASS。
  - SHA256（LF）：train `eaabe109…`、dev `e7ff77f1…`、tpl_ho `04de746c…`、tool_ho `23e8b9b6…`。
  - 服务器从 GitHub 拉同一提交后重新生成，哈希逐一相同。
  - 首次比对不一致，原因是本地 Windows 写 CRLF；已改为显式写 LF。
- **评测**：
  - e1_score_v5：新增核心键 F1、记录全对、N 误报率。
  - e1_exec_v1：编译输出交给最小改动规划器，再由独立检查器判 safe_success。刻度：none 档在 E/I 上为 0、在 N 上为 1，gold 档为 1。另有 group bootstrap CI、配对 McNemar。
  - 本地 53 个测试全部通过。
- **训练配置变更**：max_seq_len 1024 改为 1280。v4 prompt 最长约 1060 token，原设置会静默丢样本；现在打印丢弃数，smoke 中 12000/12000 保留。其余超参不变：bf16、seed 42、LoRA r16/α32/0.05、lr 2e-4、3 epoch、grad-accum 4、max_new_tokens 384。
- **服务器**：
  - 目录 `/root/ConsDagQAQ`，经 `source /etc/network_turbo` 浅克隆加稀疏检出 GitHub 仓库；models 软链到旧目录。
  - 队列 `scripts/run_e1_queue_v4.sh` 于 22:10 启动：每个模型先跑 2 步 smoke，再跑完整流程；状态记在 `outputs/e1_v4_queue_manifest.jsonl`。
  - 0.6B smoke 通过，首步 loss 0.683；正在做 zero-shot 评测，eval batch 为 48/32/16。
- **未完成**：
  - 强模型 PE 臂、I 版 oracle 可恢复性、人工盲审、改写 OOD、外部 OOD（ToolPrivacyBench）、E2/GRPO。
  - 新检索到的 LogiSafetyBench 2601.08196、ToolPrivacyBench 2606.28061 等只核实到摘要层，全文待入库。

### 2026-11-21 17:05 CST C-LEAK-1 修复：v2 跨 split query 泄漏定位与 v3 重造
- **泄漏发现**：v2 数据 dev 301/900、test_tool_ho 353/1050 的 query 与 train 完全相同（gold 同步相同）；train 内部另有 3,429 条重复 query。根因：N 变体 query=task_goal 原文，而 goal 模板池仅 10×10×6=600 组合，train 4,000 组随机采样将池子抽穿，dev/tool_ho 的 goal 100% 在 train 出现过。tpl_ho 因使用 held-out goal 模板池保持零重叠（该子集的 v2 指标不受污染）。
- **责任**：既有验证清单（witness/角色泄漏/模板 id/E-I 配对/组切分）全部通过但未包含"跨 split 文本级重复"检查项，属检查清单设计失误。
- **v2 结果处置**：所有 v2 上的 E1 数字（0.6B-bf16 dev F1 1.0000 / tpl_ho 0.9288 / tool_ho 0.9918 等）降级为受污染预实验；唯一可信读数为 tpl_ho（模板+goal 双 held-out）。dev/tool_ho 的高分含背题成分，不得进入论文主表。
- **v3 修复**（commit `24493d8`）：goal 模板 10→20/池、DATASETS 10→30、TEAMS 6→12（组合空间 600→7,200）；生成器加全局 `used_goals` 硬约束（跨 split 共享，goal 唯一 ⇒ N 版 query 唯一 ⇒ E/I query 以 goal 为前缀全局唯一）；deadline hours 采样 1-5→1-8。输出 `data/processed_v3`（seed 42，15,000 条，五类 3.0k-3.8k 均衡，0 生成失败）。
- **v3 审计全绿**：query 跨 split 重复 dev/tpl_ho/tool_ho 均 0；task_goal 出现在 train 均 0；train 内部重复 0；group 跨 split 0；verify PASS（witness 0 失败）；17/17 回归测试通过。残余记录：E 约束句后缀在 train 模板池出现率 ~39%（模板族内复用，goal 前缀唯一使背整句 query 不可能；泛化主读数为 tpl_ho）；金标参数组合与 train 某条全同率 ~40%（数值参数空间所致，query 唯一无作弊面）。均列为 limitations，不阻塞。
- **v3 队列**：服务器 v2 队列（1.7B-bf16 训练至 ~42%）与半成品已终止；`run_e1_queue_v3.sh` 以 `--data-dir data/processed_v3 --precision bf16 --seed 42` 串行重跑 Qwen3-0.6B→1.7B→4B，输出隔离至 `outputs/e1/${M}-v3`。数据 md5 与本地一致（dev `ec716769...`），代码含 used_goals 修复。17:04 启动，0.6B 已加载 311 权重、GPU 96%。
- **定位口径**：论文框架表述为 domain-agnostic 约束编译器；可信数据空间（61 角色、五类约束）为实验案例域（与 CARL/ATLAS/NOMOS 同构：机制通用、单域实例化）。

### 2026-11-21 01:15 CST 远端 scope-context 诊断复验启动（v2 数据，已被 C-LEAK-1 修复取代）
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

## 2026-11-21 12:39 服务器三模型 bf16 接力启动（受控 scaling 线）

- 队列脚本: /root/consdag/run_e1_queue.sh（bash for 循环串行, PID 34452）
- 顺序: Qwen3-0.6B -> Qwen3-1.7B -> Qwen3-4B, 全部 bf16 seed 42, 同一代码(MD5 8265ed7b 与本地/git 一致), 同一服务器(RTX 4080S 32GB)
- 输出目录: outputs/e1/{model}-bf16/, 各自 metrics.json + adapter + predictions
- 与旧结果关系: 旧 0.6B(本机fp16)/4B(服务器fp16,非受控)保留为历史; 本轮构成首个同代码同环境同精度的受控 scaling 对照
- 已知偏差(记录, 不阻塞): 数据规模 5k 任务 vs 蓝本 7-10k; 文本拼接语病率 5-6%(the the/entry entry, 金标一致性不受影响); P 臂(qwen-max PE)与 S6 oracle 阻塞于有效 API key
- git: 7e8259a 已推送 GitHub(dc47c08..7e8259a)
- 预计: 0.6B 约 2h -> 1.7B 约 4h -> 4B 约 4h, 全部完成约 10h 后(今晚 22:30 前后)

## 2026-11-22 01:33 CST：冻结 v4，0.6B 完成

服务器 /root/ConsDagQAQ 的队列记录显示 0.6B 于 00:46:39 完成，1.7B 于 00:47:15 接力。01:33 时 1.7B 到 2000/9000 步，最近 loss 3.495e-5；4B 等待。qwen-max 零样本已有 1356/3000 条响应，few-shot 尚未接力。未重启。

服务器 CPU 复评分文件已取回 outputs/e1_v4_side/trained-0.6B.json，三个评测文件的哈希均与本地冻结 v4 一致。对照取自相邻的 zero-0.6B.json；模型 seed 42。

| 子集 | 样本数（其中有约束） | strict F1 训练后 | 有约束 faithful_success：零样本 → 训练后 | 有约束含证据整条全对：训练后 |
|---|---:|---:|---:|---:|
| dev | 900（600） | 0.9704 | 7.33% → 97.33% | 95.33% |
| 模板留出 | 1050（700） | 0.7034 | 6.71% → 82.29% | 58.14% |
| 工具名留出 | 1050（700） | 0.4425 | 10.29% → 75.57% | 31.43% |

单 seed 的训练增益在三个子集上方向一致。工具名留出执行成功率高于完整契约准确率，当前结果不能说明证据或 scope 单独提高了执行成功率。下一步：在 1.7B 和 PE 完成后核对相同 ID 及数据指纹，做按组配对对照，不等待 4B。

## 2026-11-22 02:38 CST

1.7B 已到 6700/9000 步，最近 loss 为 1.48e-6。qwen-max 零样本臂已保存 2772/3000 条，dev 与模板留出采集完毕。服务器 CPU 用两臂原始响应按完整 ID 对齐，复算 0.6B 训练相对同底座零样本的有约束 faithful_success 差值。每组保留配对的 E/I 两条记录，以任务组为单位有放回抽样 10000 次，seed 42。dev 提高 90.00 个百分点（95% 区间 87.17–92.67），模板留出提高 75.57（71.43–79.43），工具名留出提高 65.29（60.86–69.57）。区间反映测试组抽样波动。带输入哈希、逐侧成功数的结果存于 outputs/e1_v4_side/paired-0.6B-faithful-constrained.json。

## 2026-11-22 03:34 CST：两尺寸与强模型零样本对照

1.7B 在 03:27:02 完成，4B 于 03:27:42 接力。qwen-max 零样本 3000 条全部评分完成，few-shot 已采集 1326/3000。用服务器 CPU 检查三个臂的冻结数据、预测哈希和 ID 全覆盖后，对受约束样本重算。每组 E/I 配对抽样 10000 次，seed 42。

| 子集 | 0.6B faithful_success | 1.7B faithful_success | qwen-max 零样本 faithful_success | 1.7B 减 qwen-max（百分点，95% 组配对区间） |
|---|---:|---:|---:|---:|
| dev | 97.33% | 100% | 90.50% | +9.50 [7.17, 11.83] |
| 模板留出 | 82.29% | 95.71% | 87.43% | +8.29 [5.43, 11.29] |
| 工具名留出 | 75.57% | 81.00% | 86.86% | −5.86 [−9.86, −1.86] |

工具名留出中 1.7B / qwen-max 的 strict F1 为 0.5593 / 0.3619，含正确证据的受约束整条全对率为 40.43% / 30.43%。两项结构指标和执行指标给出不同排序。此处为单训练种子、合成数据、强模型零样本对照。完整数值及数据指纹见 outputs/e1_v4_side/main-v4-0.6B-1.7B-PE-zero.json。下一轮按相同方法纳入 few-shot 臂。

## 2026-11-22 04:35 CST 主对照四臂齐全

qwen-max 十示例对照三子集各 900、1050、1050 条。服务器 CPU 从四臂原始预测核对数据与响应哈希、完整 ID，并以 seed 42 按任务组配对 bootstrap 10000 次。有约束 faithful_success 如下。

| 子集 | 0.6B | 1.7B | PE 零样本 | PE 十示例 | 1.7B 减十示例，百分点 [95% CI] |
|---|---:|---:|---:|---:|---:|
| dev | 97.33% | 100.00% | 90.50% | 88.17% | +11.83 [9.33, 14.50] |
| 模板留出 | 82.29% | 95.71% | 87.43% | 85.00% | +10.71 [7.71, 13.71] |
| 工具名留出 | 75.57% | 81.00% | 86.86% | 89.14% | −8.14 [−12.29, −4.00] |

工具名留出十示例 PE 对 1.7B 净多成功 57 条，其中显式净多 46/350，隐式净多 11/350。strict F1 在此子集也由十示例 PE 领先，0.6164 对 0.5593。范围为一个训练种子的冻结合成基准；配对区间描述任务抽样。归档 outputs/e1_v4_side/main-v4-0.6B-1.7B-PE-zero-PE-10.json 和 discordance-tool-1.7B-P0-P10.json。服务器 4B 到 1300/9000，最近 loss 4.47e-6。下一轮可做 E2 漏检罚组内信用诊断。

## 2026-11-22 05:37 CST E2 训练前漏检罚检查

在服务器 CPU 读取冻结 v4 训练集的 4000 个任务组。每次从金标集合移除一条约束，生成两条均完成目标、均满足剩余约束的脚本轨迹，分别核实原 witness 满足遗漏项、放宽后的计划恰好违反遗漏项。五类约束共得到 6237 对。每对都扣固定 1 分时，组内中心化后的信号均为 0。仅实际违反时扣 1 分，6237 对均得到履约 +0.5、违约 −0.5。按类型分别为预算 864、期限 1075、隐私 1406、授权 1250、顺序 1642 对。两条轨迹都完成任务，所以该测试只覆盖锚成立时的单项漏检。真实策略能采到多少有效轨迹、实际训练收益及与加法臂的差异仍待测。脚本 src/check_e2_missed_credit.py，结果 outputs/e2_v4/missed-credit-train.json。4B 为 4800/9000，最近 loss 6.76e-6。

## 2026-11-22 06:36 CST：E2 漏检罚的开发集覆盖率

服务器 CPU 按完整 sample_id 对齐 dev 原始预测并验证数据与响应哈希。以 type+params 多重集定义缺失（包括参数错配造成的缺项），900 条样本中 600 条有约束，共 972 个金标约束。训练后 1.7B 无缺项，因而不论执行轨迹如何，此 dev 切分不能检验“针对漏检”的增量收益。训练后 0.6B 有 14 条样本共缺 19 项；按其输出做符号规划后，10 条完成任务但违反了至少一个缺项。此为真实编译输出配符号规划器的触发诊断，不是 GRPO rollout 或训练效果。后续预注册单独的注入漏检条件，保持天然条件独立；基策略 rollout 方差另测，不用测试集调奖励。结果：outputs/e2_v4/missed-core-coverage-dev.json。4B 到 8200/9000 步，最近 loss 6.80e-7，当时尚无最终指标。

## 2026-11-22 07:39 CST：4B 补充对照验收

服务器 manifest 在 07:26:23 记录 4B 完成和 queue_end。训练前、后评分文件已取回，服务器 CPU 已按原始预测、样本 ID、数据及响应哈希复核。4B 的有约束 faithful_success：dev 600/600，模板留出 671/700，工具名留出 699/700。相对 1.7B，模板留出独赢/独负为 23/22，差值 +0.14 个百分点（组配对 95% CI −1.86 至 +2.29）；工具名留出为 133/1，差值 +18.86（+15.57 至 +22.29）。相对 qwen-max 十示例，工具名留出为 76/1，差值 +10.71（+8.43 至 +13.00）。4B 在工具名留出上结构 strict F1 为 0.8548，有约束含证据整条全对为 552/700。此为单 seed、冻结合成世界和符号规划器上的补充对照。记录：outputs/e1_v4_side/supplement-4B-paired.json。07:39 实查 GPU 利用率 0%，E1 队列已结束。下一项为 E2 基策略的真实采样可达性检查；尚未启动 GRPO 训练。

## 2026-11-22 08:37 CST：E2 未微调规划器采样诊断

同批输出已额外在服务器 CPU 重评：只剥除完整包住回答的一层 Markdown 围栏，6 条受影响；合法角色列表从 1/40 增至 7/40，完成任务从 0 增至 4/40，全部约束满足且完成仍为 0/40。见同目录 fence-rescore.json，其 raw SHA256 与下载的 samples.jsonl 一致。严格评测保留原数值。

在服务器空闲 GPU 上运行 Qwen3-1.7B 原始底座；冻结的 v4 train 中每类取一个显式、一个隐式查询（10 个不同任务组），每个独立采样 4 条。用户查询、工具环境入 prompt；金标仅在执行后计分。seed 42，temperature 0.8，top_p 0.95，160 新 token。40 条中仅 1 条严格解析为仅含合法角色的 JSON 列表；完成目标 0，安全完成 0，出现“已完成且一条履约、一条违规”的组为 0/10。6 条输出以 Markdown 代码围栏开头。不得由此推断模型不能规划，也不可把这些样本冒充训练效果。保存 outputs/e2_v4/reachability-v1/{summary.json,samples.jsonl} 与 src/probe_e2_planner_v1.py。此配置没有观察到足以训练的锚定奖励差异；不启动长 GRPO。后续先对同一批 raw 做围栏剥离的独立重评，检验格式与功能的贡献，再固定所有臂共享的输出接口，用新训练组测可达性。

## 2026-11-22：跨家族 PE 完成；数据、适配器与 E2 核查

- DeepSeek 十示例使用与 qwen-max 十示例相同的冻结输入。服务器全量 3,000 条 ID、请求哈希和响应覆盖检查通过，3,000 条正常结束，无空文本。带约束 faithful_success 分别 596/600、693/700、700/700；模板留出无约束 322/350。工具名留出含证据整条全对 655/700，4B 为 552/700。完整对照及范围见 [本轮报告](v4_results_and_claims.md)；原始响应、面板、全量分数、按组配对置信区间分别归档在 outputs/e1_v4_side/deepseek-v4-pro-0813-few/。
- 强化显式隐私证据、重复 ID/变体、元数据数量、切分文件标签与跨切分检查后，服务器对冻结 15,000 条全量重验通过。1.7B 在 89 组隐私字段题上移除提示示例前后，参数恢复均为 88/89。1.7B/4B 分别重新加载并在同批 27 条 dev 上逐字重现原响应。见 outputs/dataset_audit/。
- 另选与 v1 不重叠的 10 个 train 组，每组 4 次、两臂共享工具表与编号表。在严格 JSON 输出下，工具名：合法 1/40、完成 1/40、安全 0/40；整数编号：三项均 0/40；均无履约与违规并存的已完成轨迹组。见 outputs/e2_v4/reachability-format-v2/。截至本轮，GRPO 未训练。

## 2026-11-22：公开规则绑定、1.7B 规划示范预热与门控诊断

详见 [本轮优化报告](v4_optimization_results.md)。服务器同规则复算六个 E1 系统，各 3,000 条；工具名留出 4B 的含证据整条正确从 552 升至 649/700，六个系统执行成败均无变化。另从 train 的 128 个独立任务组训练 64 步，仅更新规划器 LoRA；在独立 20 个单约束组上，严格结构下任务完成 0→80/80，安全完成 0→19/80。原环境口径分别为 4→80、1→19；均由原始响应重算。新取 32 个多约束组（128 次采样），127 次完成、9 次完全合规；对本次明确定义的两种 oracle 标量奖励，32 组均无标准化后的差异。保留共享初始化和负结果；未启动 GRPO。原 v4 主表未改。

## 2026-11-22 12:46 CST：冻结编译器换规划器，首次配对面板

同一冻结 4B 编译器（公开 scope 绑定）、同一冻结 1.7B 预热规划器；每个留出按金标约束数量 1/2/3 各取 5 组并保留 E/I/N。90 条查询 × 原文、原文附预测对象、原文附金标对象，共 270 次贪心生成，三个输入臂均保留完整查询；按 ID 逐条重新解析和检查。受约束查询严格结构安全完成（原文/预测/金标）：模板留出 4/30、4/30、4/30；工具名留出 12/30、9/30、9/30。两种附加输入相对于原文的各自配对变化在模板集均为 0 胜 0 负，在工具名集均为 0 胜 3 负。N 臂 30/30 均严格完成，但不说明计划一定等于默认计划。相同面板下符号 planner 的预测约束臂在原环境安全完成 26/30、30/30，金标臂均为 30/30；其空集输入不等同于神经 planner 阅读原文。N 中有 1 条相同输入哈希的预测/金标回答不同（均完成），存在小的确定性限制。

该面板是对既有测试分割的探索性复核，不是泛化失败的普遍证明。当前附加对象协议未显示收益，金标不能救回严格安全完成；优先在 train 内验证神经规划器的约束消费，保留原文和等信息文本对照，不在这个面板调整提示。真实输出、配置及配对审计：outputs/e2_v4/frozen-planner-swap-panel-v1/。脚本 src/probe_planner_swap.py、src/audit_planner_swap.py。

## 2026-11-22：冻结规划器读取约束，训练集内二选一诊断

从与预热示范及前置诊断不重叠的 60 个 train 单约束组中选择五类 × E/I 各 6 组。逐题验证两条候选都完成、恰有一条合规；三种输入共享原文、工具世界和候选，将两条计划交换位置各测一次。按 A/B 单 token 分数判定，严格相等计错。三臂各有 120 个位置观测，原文、附金标 type+params JSON、附等义英文分别有 60、52、60 个正确；两种位置都答对分别为 0、2、7/60。仅原文时 118/120 选择 B，2 次平分。英文表示也没有提升平均位置准确率。本实验只反映该模型和该二选一接口，不是开放生成效果或表达形式胜负的确认性结论。原始 logits 与 360 个 (id,arm,order) 覆盖已在服务器复核，输出 outputs/e2_v4/frozen-record-choice-v1/。下一步需单独校准判别接口（如中性题与位置平衡对照），或训练共有的约束消费接口后回到自由生成；本轮未启动 GRPO。

## 2026-11-22 13:38 CST：E2 策略训练已接力

13:29 服务器 GPU 空闲；已缓存 0.6B 在 128 个训练组的真实输出。1.7B 预热起点在 160 条 dev 上全部完成，显式/隐式安全完成为 15/60、9/60，无约束保持默认计划为 5/40。13:36:24 开始 seed 42 的四臂对照，13:38:38 整轨迹计分臂已运行 71/128 组，40 次参数更新；尚无训练后比较。服务器已配置逐臂保存、重评分及按训练信号覆盖率接力第二、第三个种子。见[实验协议与运行目录](e2_action_credit_pilot.md)。

## 2026-11-22 13:45 CST：E2 首个种子的动作归因与逐题对照

同一冻结 dev，整轨迹扣分与责任动作扣分均严格完成 160/160。120 道有约束题上，预热 24、整轨迹 29（显式 18、隐式 11）、责任动作 30（显式 18、隐式 12）。逐 ID 核对后，责任动作臂独对 3、独错 2、共同对 27、共同错 88；无约束保持默认计划为 5/40、3/40、2/40（预热、整轨迹、动作）。尚不能认定位置归因改善了合规。

服务器 CPU 运行 src/audit_e2_action_rollouts.py --arm action，从完整生成重新解码，核对 128 个训练组、512 条轨迹、预测对象、实际违规角色、词元位置以及归因前后整条平均信用守恒。38 个组确有罚分转移，共 97 项（先后关系 44、授权 41、隐私 12）；这 38 组在同轨迹重放中与错位信用均可区分。这证明干预发生，不证明下游获益。首次调用时第二臂尚未写满，ID 齐全断言拒绝部分数据；在 128 条写齐后重放通过，无训练重跑。归档 outputs/e2_v4/action-credit-1.7B-pilot-v1/credit-replay-action-s42.json。13:44:59 服务器自动启动错位臂；仍待功能臂及后续种子。

## 2026-11-22 14:00 CST：E2 四臂首轮完成，预防动作对照与双盲审题包准备

首轮 120 道受约束开发题：预热 24，功能奖励 25，整轨迹奖励 29，责任动作 30，错位 27。无约束默认路径保持数依次为 5、5、3、2、5（各 40 题）；动作归因比错位 8 胜 5 负，比整轨迹 3 胜 2 负。正式比较见 outputs/e2_v4/action-credit-1.7B-pilot-v1/paired-dev-s42.json。关闭源预测未纳入本次四臂，不作编译器端到端因果效用断言。

原实验 s43、s44 保持不变，14:00:22 s43 动作臂到第 92/128 组。服务器 CPU 另对 s42 整轨迹臂的 512 条真实训练轨迹做单动作反事实复查：移除一个可选动作或替换一个同阶段工具，仍须严格完成目标、只新增违反一条预测约束且其他约束判定不变；仅在唯一责任位置、同组有完成但违约的轨迹时转移正信用。查到 87 项（预算 9、先后 21、授权 30、期限 20、隐私 7），有 42/128 组的真实位置与错位处理不同。此为训练机会数，不是评测收益。脚本 src/audit_e2_prevention.py；哈希和结果见同目录 prevention-train-v1.json。

13:59 已在服务器锁定第二开发面板（120 个与第一面板不重叠的组，90 约束、30 无约束）及后续作业。启动规则是在看到 s42 后确定的工程决策，不是原实验事前判胜规则：若任一种子正确位置不优于整轨迹或错位，或三种子对整轨迹的中位净增不超过 6/120，按 s42–44 分别训练“给避免违规的动作正信用”和“仅把该正信用错位”两臂。原负信用、初始化、训练数据和预算固定；同面板还评原 action、trace。新增至多 6 次短训练及 12 次面板推理，按当前速度约半卡时。结果无论方向均留存；不能视为完全未知领域外测。协议见同目录 preventive-comparison-v1/protocol.json。

③已在服务器自冻结两个测试切分抽取 350 个不同组（250 I、50 E、50 N），两位审阅者各见完整查询、公共目录和统一公开策略卡，各自随机编号；不见金标或同组三版。盲审包 outputs/dataset_audit/v4-implicit-human-review-v1/reviewer-{A,B}/；目前无人工回收和一致性结果。样本按类型分层，不代表自然流量。检查器和抽取器对合成环境的支持范围仍按 v4_results_and_claims.md，不宣称自然语义唯一、跨结构泛化或 CCF-B 录用。

## 2026-11-22 14:44 CST：E2 原版三种子重评，预防动作首个种子

服务器完成 42、43、44 三个种子的原版训练；src/report_e2_panels.py 从十二个臂各 160 条 dev 原始响应重算。按种子顺序，原版同一面板的有约束安全完成数（分母 120）为：只奖功能 25/24/21，整轨迹 29/26/28，责任动作 30/26/27，错位 27/24/26。责任动作对整轨迹净增 +1/0/−1，平均 0 个百分点；整轨迹对只奖功能 +4/+2/+7，平均 +3.61 个百分点。三种子共享的任务组在 E/I 内配对重采样 10,000 次；条件于这些种子，两个差的 95% 区间分别为 [−3.89, +3.61]、[+0.28, +7.22] 个百分点。不能据此宣称任意训练随机性下显著或抗投机。

改进版 14:30:23 起自动执行。独立于原面板的 90 道受约束 dev 题，s42 预防动作 22、仅把正信用错位 20、原责任动作 21、整轨迹 22；30 道无约束默认计划保持数分别为 3、3、2、4。原面板和新面板不可横比。14:42:15 接力 s43。

训练阶段另经 src/audit_e2_sampling_support.py 在服务器 CPU 完成全部十二臂回放，每臂仅统计 96 个有约束组 × 4 次。44 至 57 个组从未采到完全合规的完成轨迹；32 至 46 组同时采到合规完成与违规完成的轨迹。对这些实际采样的二值安全完成标志，预测对象与训练金标检查未见分歧，不表示参数、证据和范围字段全部正确。缺少全合规轨迹不等于缺少部分满足的奖励梯度。若改进版不稳定，先检验同预算下如何获得可比较轨迹，不按已有 dev 输赢继续扫罚系数。结果在 outputs/e2_v4/action-credit-1.7B-pilot-v1 下的 rechecked-original-42-43-44.json、train-sampling-coverage-v1.json 及 preventive-comparison-v1/rechecked-prevention-42.json。

## 2026-11-22 15:19 CST：改进版三种子结束，采样诊断完成，启动冻结留出评测

15:06:21 改进版队列结束。服务器重新解析全部原始响应。在第二开发面板每个种子同样的 90 个受约束组上，预防动作正信用臂安全完成 22/23/18，整轨迹臂 22/21/20，原负信用动作臂 21/19/17，错位正信用臂 20/19/17。改进版对整轨迹差 0/+2/−2，平均 0 个百分点，按组重采样、条件于三种子的区间为 [−4.81,+4.45] 个百分点。不能据此宣称动作归因优于整轨迹。复核文件 preventive-comparison-v1/rechecked-prevention-42-43-44.json。

15:15 GPU 实查空闲，随后用预热 1.7B 在 48 个独立 train 组（E/I，各约束数 1/2/3 均衡）每臂每题抽样四次。冻结温度 0.8→1.1 时，至少一条安全完成的组从 14/48 到 10/48；同时出现安全与违规完成的组从 12/48 到 7/48；严格任务完成从 181/192 到 135/192，解析失败 2→24。实际生成 token 5285→5443。该单面板不支持升温，未调训练参数。产物：outputs/e2_v4/temperature-coverage-1.7B-train-v1/results.json。

15:19 验证新的冻结评测已写入首批 64 个响应。模型为原 function、trace、改进 protect 各三个既有权重；同一 240 个留出任务组（两种切分各 80 约束 + 40 无约束，排除早期 E6 面板），合计 2160 次贪心推理。主要比较 trace−function，次要为 protect−trace。E1 已用这两个切分，不作为新外部盲测；不使用成绩修改训练。目录 outputs/e2_v4/frozen-planner-transfer-v1/，脚本 src/eval_e2_transfer_frozen.py。

## 2026-11-22 15:45 CST：冻结训练结果与四候选推理对照完成

冻结权重的 2,160 条响应全部完成。三个种子（42/43/44）整轨迹奖励相对只奖功能的受约束安全完成净增（各 80 道）：模板留出 0/+1/+3，工具名留出 +1/−1/+1；预防动作信用相对整轨迹分别为 −1/+4/−1、0/+1/−2。工具名留出的整轨迹臂每种子 16–18 道安全完成，58–59 道完成但违规，3–6 道未完成。该臂在三种子下均为 0/40 无约束题保持默认路径；改变默认路径不必然意味着不安全。源数据与逐题复核：outputs/e2_v4/frozen-planner-transfer-v1/{paired.json,rechecked-failures.json}。

独立于奖励训练的推理对照：冻结预热 1.7B 每题生成四条候选，同一批候选分别以“首个功能完成”“0.6B 预测约束”“金标约束”选择；最后一种只用于诊断候选上限。独立符号求解器用与预测选择器相同的约束，但可另构计划，不是同候选预算的选择器。下表均为受约束题的安全完成数：

| 面板 | 首个功能完成 | 用预测约束选择 | 金标选择上限 | 预测约束 + 符号求解 | 四条均无安全完成 | 有安全完成但预测未选到 |
|---|---:|---:|---:|---:|---:|---:|
| 已用开发面板，90 题 | 22 | 40 | 40 | 85 | 50 | 0 |
| 新措辞，40 题 | 9 | 16 | 19 | 31 | 21 | 3 |
| 新工具名，40 题 | 8 | 12 | 12 | 34 | 28 | 0 |

后两个面板共 120 个任务组（80 受约束、40 无约束），与前两个 E2 留出面板排重，但切分曾用于 E1。受约束题逐题配对 11 胜、0 负；选择器在 79/80 道成功完成功能，预测约束只让其中 28 道同时合规。无约束默认路径：功能选择 4/40、预测选择 3/40、符号求解 33/40；不把无约束结果算入 11 胜。抽样一次/一个种子，开发面板已使用；该证据支持编译输出在推理时有用，不证明 GRPO 动作归因或抗奖励投机。对两个面板逐条重新解析四个候选并复验摘要哈希、ID 顺序、所选索引和安全标记。原始响应、协议、统计与重放见 outputs/e2_v4/shared-candidate-selection-{dev,transfer}-v1/；开发面板原生成代码保留为 generator-dev.py。

下一轮优先检验生成器能否提出更多可执行且合规的候选：仅在 train 构造并验证合规示范/修复，和同底座、同任务、相同训练及推理 token 预算的普通 SFT 对照。主要报告受约束安全完成、四候选覆盖和无约束默认路径保持；固定候选重排与符号求解器保留。使用新面板，不用以上留出题选参；不追加无假设的温度、罚系数扫描。

## 2026-11-22：1.7B 经执行验证的修复示范，等预算对照

服务器接力运行 warm、普通 SFT、修复动作加权 SFT。两训练臂只用相同的 256 道 train 题（96 E、96 I、64 N）：用户输入、目标 token、初始适配器、样本顺序、128 次更新、学习率和生成上限完全配对。对合规示范做同阶段替换、移除可选动作、颠倒两收尾动作，经执行器确认仍完成功能且出现违规后，才标记对应的目标动作。共 192 道有标记，378 项反事实；草案与金标不进入推理提示。改进臂将标记的工具名 token 损失权重设为 3，并按每题权重和归一化；普通臂统一为 1。训练使用 bf16、梯度裁剪及逐步有限性检查。这是 SFT 的机制实验，不是 GRPO 或抗奖励投机证据。

初次预检因部分原始 witness 允许两收尾动作之间插入质检而中止于更新前。保留原失败日志；现仅重排不符合规划器严格结构的训练示范，并重新验证完成和全部约束，没有删题或修改测试分数。新面板 120 个组（每种留出各 20 E、20 I、20 N），与前三个 E2 留出面板按组排重；它们仍属于 E1 用过的切分。每题四候选，固定抽样种子 91011、同温度与 160 token 上限，另记实际生成 token。warm 基线 80 道有约束题四候选覆盖 23，编译器选择后安全完成 21；40 道无约束默认保持 2。另在首轮改进臂评测完成前固定两种训练顺序（43/44）接力；固定初始化和抽样种子，不称作三次独立模型种子。

协议与结果位置：outputs/e2_v4/verified-repair-sft-1.7B-v1 及 verified-repair-sft-1.7B-orders-v1。训练脚本 src/train_repair_sft.py，评测与复核分别为 src/eval_repair_sft.py、src/replay_repair_sft.py。

首轮普通/加权 SFT 实际输入与监督 token 的逐题哈希完全相同；训练示范 7/256 条重排，均通过结构和约束验证。严格四候选覆盖 36/80 对 37/80，差 +1.25 个百分点，按题配对重采样区间 [−6.25,+8.75]；编译器选后安全完成 35/80 对 36/80。选后分切分为 20→24、15→12；N 默认保持 2/40 对 1/40。首轮环境原生完成与严格结构两种评分在此主指标相同。快照及逐题回放见 verified-repair-sft-1.7B-v1/independent-replay.json。

额外推理诊断在同一批四候选上进行：若无候选通过预测约束、但有功能完成者，对各完成候选枚举同阶段替换、插删可选工具或交换收尾顺序；只接受预测约束全部通过的一个编辑，找不到则退回原选择。排序、搜索与接受都不用金标，需额外的环境检查。已用面板上加权臂从 36 到 63/80（两切分各 +12、+15，零回退），哈希选邻居为 38/80，符号求解为 66/80；默认路径不因这一改法变好。这是事后推理诊断，不是奖励学习的证据。另锁定同规模、与之前四个 E2 面板按组不重合的留出评测，固定普通 SFT；比较原重排、单动作修复、同邻域哈希对照、仅从默认计划修一步以及不受一步限制的符号求解器。后两个基线没有神经候选生成开销。协议：outputs/e2_v4/verified-one-edit-confirmation-v1/protocol.json。

三种训练顺序的普通 vs 加权：四候选安全覆盖 36→37、44→41、44→38；编译器选后安全完成 35→36、43→40、43→37（每组分母 80）。覆盖差平均 −3.33 个百分点，按题在切分及表达状态内成对重采样 95% 区间 [−7.50,+0.42]，条件于这三种顺序及固定抽样种子。均完成；不支持继续增加动作损失权重。outputs/e2_v4/verified-repair-sft-1.7B-orders-v1/independent-replay.json。

新面板同一普通 SFT 的四候选：受约束安全完成数，原重排 42/80、约束指导单动作修复 71/80、同邻域哈希选取 43/80、从默认计划修一步 50/80、完整符号求解器 67/80。修复按模板/工具名分别 37/40、34/40（原重排 26/40、16/40）；单次小面板不作优于符号规划的一般性断言。独立回放核验了实际编辑合法、金标后判分、原始响应哈希；保存的四候选只取前 1/2/4 条，修复后安全完成分别为 58/69/71（分母 80），评估有效邻居合计 1265/1921/2865。无约束 40 题原重排和修复均未保持默认计划。事后加入“结构有效、状态为 none、约束为空且未标拒判才走公开默认计划”规则，默认保持 0→28/40，受约束 71→71；此项须从全量验证误路由。产物：outputs/e2_v4/verified-one-edit-confirmation-v1/{results,independent-replay,empty-route}.json。

数据审计：按环境执行金标 15,000/15,000 全部完成且合规；训练、开发、两测试中分别 304/26/30/30 个原示范不满足额外的严格收尾格式（390 个样本、195 个任务组），仅重排收尾后逐条检查通过 15,000/15,000。原始数据和既有成绩未改。outputs/e2_v4/strict-witness-paired-audit-v1/results.json。

服务器已经接力固定普通 1.7B 的 2,100 条全量 E/I/N 评估（700 个任务组、共 8,400 候选），保留每题预测、实际 token、验证邻居及默认/符号对照，另排空集路由复算。目录 outputs/e2_v4/verified-one-edit-full-holdouts-v1；这批包含前面的面板，不是新外部数据。未完成前不据其推断总体效果。

全量首轮已完成。1,400 道受约束题上，0.6B 编译输出指导的四候选重排安全完成 682 道，同一批计划允许验证并修一个动作后完成 1,144 道，逐题 464 胜、2 负。两留出各有 350 组，每组 E/I 一起抽样 10,000 次，差 +33.00 个百分点，条件于本次权重与解码种子的 95% 区间 [+30.00,+36.07]。模板留出 410→608/700，工具名留出 272→536/700。首轮修复后仍失败的 256 题中，10 道无严格完成候选，128 道有完成候选但一步邻域无安全计划，25 道原候选中有安全解，另 93 道在一步邻域存在安全解但部署规则没有选到。见 verified-one-edit-full-holdouts-v1/{results,paired-summary,oracle-neighborhood}.json。

符号对照按其原环境合同评为 1,149/1,400；若直接施加神经规划器的额外收尾格式仅为 1,092。给予符号计划不看金标且经预测约束验证的收尾重排后，严格分恢复为 1,149（模板 619、工具名 530），与神经候选修复的 1,144 接近。先前确认面板的同一修正将符号对照 67→71/80，和修复 71/80 持平。论文应使用规范化符号对照。两种方法有不同的搜索及推理开销。

加入明确空集走默认的分支，0.6B 有约束安全完成 1,142/1,400（2 道合成措辞被错误判空），无约束保默认从 47/700 升到 536/700。同四候选、同路由的缓存 PE 对照，有约束安全完成/无约束保默认分别为 qwen-max 零示例 1,169/1,400 与 289/700，qwen-max 十示例 1,134 与 411，DeepSeek 十示例 1,255 与 667。使用既有请求缓存，未产生新 API 调用。见 verified-one-edit-full-holdouts-v1/{normalized-symbolic,empty-route}.json 及 compiler-swap/results.json。

流程深度压力测试中，公开目录相同，将可选复核步骤设为新的必做收尾前阶段，安全完成从 70 降到 9/80，严格功能完成从 79 降到 11/80。根据公开流程补一个遗漏阶段，再按原规则验收，同一批候选从 9 恢复到 70/80，规范化符号对照 71/80。另在冻结的 96 道开发题上构造处于流程中间、可二选一的全新阶段，64 道受约束题从 54 提到 57，规范化符号对照 64。两项只说明合成流程深度改变时的行为，未完成人类盲测。见 verified-one-edit-depth-pair-v1/results.json 和 verified-missing-stage-v1/results.json。

## 2026-11-22 两份规划器权重复核及投稿取舍

第二份普通 SFT 权重全量评测完成，1,400 道受约束题的安全完成由重排 756 提高至修复 1,199。两份权重平均配对增益为 32.32 个百分点，按 700 个 DAG 在切分内配对重采样的区间为 [29.61,35.11]，条件于固定训练顺序及共同抽样种子。

开发集区分性计划提示试验在 900 道中发现 192 道两种预测约束可区分。直接判、随机计划、区分性计划、固定 0.6B 分别忠实执行正确 750、771、765、884。完整 2×2 交叉回放使用固定候选预算与单编辑修复，第一份权重配 0.6B/DeepSeek 得 1,144/1,255，第二份为 1,199/1,292，分母均为 1,400。对初始失败中的 118 道可达题，固定候选改用强编译器救回 112 道。另 138 道不可达题在更换候选后救回 47 道。归档在 outputs/e2_v4/semantic-disagreement-dev-v1、failure-interventions-2x2-v1 及 verified-one-edit-full-order44-v1。投稿范围见 [贡献取舍](contributions_submission_decision.md)。


## 2026-11-22 固定任务的证据改写，服务器 GPU

48 个双表达任务组，96 对有效编辑。0.6B、1.7B 各 384 次主实验推理，分别追加 192 次去引号复测，冻结权重。参数跟踪 79、86 对，全记录正确 27、56 对，区分性计划判定 68、83 对，分母均为 96。按公共目录推导 scope 后完整记录升到 45、76 对。在本面板之外 652 条工具名留出原问句上完整记录从 213→483、267→502，措辞留出两模型均无变化。去引号后，可解析率上升但无关标签两侧全对仅为 1/96、34/96。原始生成、两份独立计分检查、环境与权重哈希均已归档。[实验报告](evidence_edits_gpu_v1.md)。

## 2026-11-22 独立于原模板的措辞对照与中文作者试读

20 组，60 个请求，两臂均在租用服务器发起并完成。1.7B 完整编译 37/60，DeepSeek 十示例 59/60。仅历史或示例条件下，1.7B 有 8/20 条误提、1 条解析失败。材料由 AI 另写，外部人类措辞确认待收集。见[逐题改写对照](authored_wording_v1.md)。中文作者试读 A001–A003 的原始回答已保留。原始英文 “No sign-off is attached to …” 描述审批未附，是否豁免存在第二种解读。模板影响措辞留出 44 条（含 30 条空集、14 条带其他有效约束），等待独立复审。
## 2026-11-22 作者试读与审批歧义复测

根据 A003 的作者反馈，全量取出措辞留出中所有含有“No sign-off is attached to … here.”的 44 条请求，覆盖 30 个任务组。每条只替换该句，得到明确豁免和明确须批两版。1.7B 和 DeepSeek 各完成 88 次推理，目标授权两版同时正确 43/44、44/44，整条两版均对 33/44、39/44。40 条有目标工具获批和未批的两份可行证书，可单独评估执行。原基准未改。作者中文试读 A004–A006 已记录。A004 提问带顺序提示，按引导试读记录。[数据与解释总表](consdag_experiments_overview.md) · [服务器逐题结果](../outputs/approval_wording_v1/scores.json)。

## 2026-11-22 单请求部署测量

同台服务器、同 30 条请求，1.7B、4B、DeepSeek 零示例与十示例各测 30 次。完整记录正确为 17/20/17/29 条（每臂分母 30），中位延迟为 2.93/3.45/1.65/2.65 秒。1.7B、4B 在加载前禁止进程创建 IPv4/IPv6 套接字仍完成推理，PyTorch 峰值已分配显存为 3.36/7.72 GiB。在两本地模型固定 512+64 token 的生成对照中，中位耗时为 2.395/3.117 秒。[部署测量、协议与原始结果](compiler_efficiency_v1.md)。

## 2026-11-23 v5 seed42 结果回收与复算

- v5 数据集共 16,050 条、5,350 个任务组；`data/processed_v5/verification_report.json` verdict 为 `PASS`。本地测试 71 项通过。
- 已回收并核对 1.7B 和 4B seed42 的 `metrics.json` 与四个评测子集预测；训练均为 BF16，未发现 NaN 或非有限值记录。0.6B v5 训练主臂尚未落盘。
- CPU 复算写入 `outputs/v5_analysis/main.json`。受约束 faithful_success：1.7B 为 dev 98.50%、template-HO 96.71%、tool-name-HO 91.71%、structure-HO 95.86%；4B 为 100.00%、97.43%、91.00%、99.71%。同底座零样本分别为 17.17%/19.14%/13.43%/25.86% 和 51.50%/53.00%/56.71%/57.57%。
- 这些是单训练 seed 的 v5 结果。相对 DeepSeek 十示例，1.7B/4B 在结构留出分别低 4.00/0.14 个百分点和低 8.00/8.71 个百分点（按子集见 `outputs/v5_analysis/main.json`）；不能写成强模型非劣效已成立。
- 远端队列当前不抢占；在 0.6B v5 和 seed43/44 完成前，不启动新的训练或 E2 GRPO。

## 2026-11-23 20:02 CST v5 队列只读复核

- 远端 `/root/ConsDagV5` 只读检查确认 RTX 4080 SUPER 32GB 正在运行 `Qwen3-1.7B` v5 seed43；约 7,100/9,000 optimizer steps，最近日志 loss 为有限值，未触发 NaN/非有限保护。
- 当次 GPU 查询为约 21,144/32,760 MiB、利用率 53%；队列脚本仍保持 seed43/44 后接力 0.6B 的原登记顺序，没有抢占或重复启动。
- 本地 `python -m pytest -q` 复核通过 71 项（7.79s）。远端结果未在 seed43 完成前回收；下一次只读检查优先拉取 metrics、预测、manifest 并校验 SHA-256。

## 2026-11-24 13:00 CST v5 队列收口与 4B seed44 回收

- 服务器 `/root/ConsDagV5` 队列运行正常：1.7B/4B 三种子与 0.6B seed42/43 已完成，0.6B seed44 训练中；GPU 19,698 MiB / 40%，无 NaN、OOM 或异常退出。
- 4B seed44 于 06:54 CST 完成，`metrics.json` 已回收本地，SHA-256 `1391b9d2...bf476f`，与服务器一致；五个数据文件哈希与 `metrics.json` 内 `data_sha256` 逐一相同。
- 受约束 faithful_success：4B seed42 为 100.00/97.43/91.00/99.71，seed43 为 99.83/92.86/95.86/97.00，seed44 为 100.00/99.71/74.14/93.57（dev/tpl_ho/tool_ho/struct_ho，%）。三种子均值 ± 样本标准差为 99.94±0.10、96.67±3.49、87.00±11.40、96.76±3.08。
- 4B 相对 DeepSeek 十示例均值差为 +0.61/−2.62/−12.71/−3.10pp。tool_ho 即使 seed44 记为 100%，均值上界仅 95.62%，仍低 4.10pp；原 H2 的 −3pp 门槛在该切分不可能通过。
- 0.6B seed42/43 受约束 faithful 为 dev 98.67/97.67、tpl 91.29/90.57、tool 64.29/66.57、struct 71.71/74.14（%），seed44 待完成，仅用于方差报告。
- 独立审查脚本发现的 `eval_exec.py` 解析失败 fail-open（空约束走默认计划，N 记录可能判 faithful）在当前五组训练 run 的 N 输出中未触发；`oracle_check.py` 的 format 花括号缺陷未修复。两项均未改动代码，待批准。
- 审查附件 `reports/_audit_work_20261124/metrics_per_record.json`（17.1 MB）已移出仓库到本地临时目录，其余报告与汇总 JSON 保留。

## 2026-11-24 v6 本地实现与数据冻结

- 设计见 `reports/design_v6_ccfb.md`。定位为合成基准与评分审计；不宣称新编译器架构、人工语义验证完成或 CCF-B 达标。v5 数据、保存的预测和历史执行评分保持原样；`oracle_check.py` 的 JSON 花括号插值缺陷已修复。
- `data/processed_v6/` 共 17,100 条、5,700 组：train 12,000，dev 900，四个测试切分各 1,050。`privacy + tool_auth` 及其所有超集从其他切分排除，composition 测试仅有精确二类型组合；筛选会改变任务构成，不解释为因果组合干预。
- 独立 verifier 为 PASS：六切分之间 45 项 query/goal/group 重叠全部为 0；E/I/N 对齐、可完成的正例与反事实 witness、保留约束、空集 no-op 和 SHA-256 检查通过。相同种子在临时目录二次生成，六个 JSONL 字节哈希完全一致。全量金标 CPU 复算无解析或 faithful 失败；这些是参考自洽检查，不是模型性能。
- v6 执行评分对解析失败 fail-closed，N 分别统计解析失败、非空约束和状态错误。strict/core F1、record exact、evidence exact、safe/faithful 分开报告。H1 改为每种子配对任务组区间；训练均值须三种子完整；H3 沿用命名切分的独立组重采样；H4 固定 DeepSeek 十示例为模型诊断臂，不判定标签真假。
- 队列含 32 GB GPU 检查、源码/数据/模型/环境 provenance、完成标记、预测与 adapter 哈希、失败日志保留、禁止覆盖未完成 smoke/run、NaN 中止和累计 30 小时预算（包含 smoke 与失败任务）。PE 请求按模型、参数、完整输入与数据指纹缓存，只从环境读取 key。
- 两位盲审者材料已导出到 `data/review_v6_seed20261125_n5/`，共 250 条唯一请求；协议在 `reports/v6_human_review_protocol.md`。尚未人工审阅，`human_validation_status=pending`。
- 完整 `python -m pytest -q -rs`：116 passed、2 skipped；两项跳过原因是本机无 torch。Python 编译与 Git Bash 语法检查通过。
- 远程只读认证检查：环境未配置 `SEETA_PASSWORD` 或 `DASHSCOPE_API_KEY`，绕开无效 SSH 配置后，密钥认证仍被拒绝。没有修改服务器文件，没有启动 v6 GPU smoke/训练或 PE；不能报告任何 v6 模型结果。未 commit、未 push。

## 2026-11-24 19:16 CST 投稿补充实验接力队列启动

- 执行依据 `reports/submission_plan_emnlp2027.md`（用户定稿）；授权为用户指令「这次破例，你来完成」。方案「核心数字速查」与素材逐项核对全部一致（主表 faithful、2×2 的 112/118 与 47/138、DeepSeek 行 1255/1292、符号规划器 1149/1400、裂缝 699/700 vs 552/700）。
- E1 插拔网格（编译器 4 轴 × 规划器 3 轴，v4 tpl_ho+tool_ho 2100 条冻结回放，纯 CPU）完成，产物 `outputs/submission/e1_grid/results.json`。符号规划器行随编译器质量单调：0.7893/0.8836/0.9786/0.9950，DeepSeek 行超 4B，接口可被任意消费者复用；SFT 规划器行平坦在 0.25-0.30 且 safe 0.88-0.95，过编辑为下游瓶颈（0.6B 格 over_edited=792）。回放口径自校验：DeepSeek 编译器复现 p0_c1=1255/1400=0.8964，0.6B 编译器复现 safe=1144/1400=0.8171，与 2×2 协议一致。
- E2（B1 单体，1.7B）与 E3（A 系消融 A3/A4/A2/A1，0.6B）脚本经本地与服务器语法/参数冒烟后 SFTP 推送（SHA-256 双侧一致）；GPU 接力队列 PID 181081 已 nohup 启动，先等 v6 主表队列结束且显存 <2000MiB 再依次执行，日志落 `outputs/submission/`。v6 队列（PID 175052）未受干扰：1.7B seed42 完成（11072 GPU 秒），seed43 训练中，30h 预算剩余约 96928 秒。
- 详细状态见 `reports/submission_execution_20261124.md`。E2/E3 结果未产生前不作任何结论；预注册判定（E2：单体 faithful_constrained ≥ 管线−1pp 且配对 bootstrap CI 跨 0 ⇒ 架构主张死）不变。

## 2026-11-24 深夜 投稿方案 v3 第一波（零 GPU）执行

- seed 方差机制分解完成（R3 必做项）：脚本 `scripts/submission/seed_variance_decomposition.py`，产物 `outputs/v5_analysis/seed_variance_decomposition_20261125.json`，报告 `reports/seed_variance_analysis_20261125.md`。回放 faithful 与 v5 主表单 seed 逐项一致（1.7B tool_ho 91.71/75.71/71.86、struct_ho 95.86/75.29/77.57；4B 91.00/95.86/74.14、99.71/97.00/93.57），口径可信。
- 发现 A（行为轴）：三 seed 共杀率 1.7B tool_ho 仅 15/700=2.1%、struct_ho 6/700、4B tool_ho 4/700、struct_ho 0/700；规划器实际消费的 params 字段错误跨 seed IOU 0.01-0.08，实例为预算值 100→1000、required_role 写错角色。执行级 seed 方差=params 训练噪声，非样本系统性难度。
- 发现 B（记录轴）：scope 绑定错误规模最大（每 seed 300-420 条）且 1.7B/4B-struct_ho 上三 seed IOU 0.629-0.810 属系统性缺陷，但规划器不消费 scope，执行级完全不可见；4B tool_ho 的 scope 错误率 seed 间在飘（67→309→446），系统性结论按切分分别陈述。两轴可分离，双轴评测设计获实证支撑（C3 延伸）。
- 4B seed44 预测自服务器拉回本地后并入分析；字段比对经实例抽查确认真实差异（`scripts/submission/diag_field_mismatch_samples.py`）。
- 写作层修正落地 `reports/paper_wording_negative_results_20261125.md`：GRPO 按 R3 口径改为「本设计功效（3 seed、配对 bootstrap ±1-2pp）内未检出稳定效应」，不声称证明为零；symbolic 单调行定位为「接口无衰减验证」，核心证据句改为 DeepSeek 行 0.9950 > 4B 行 0.9786 的接口非特化性 + SFT 规划器列对编译器质量全平的反向证据。含 seed 方差段配套英文措辞与限定词。
- 第二波（E2/E3/v6）仍等 GPU 队列；本波未改任何代码口径、未动服务器。

## 2026-11-25 11:30 CST E3 四臂回收与 E2 实况

- 使用用户先前授权的 SeetaCloud 登录信息只读连接 `connect.westc.seetacloud.com:40958`。11:17 快照：RTX 4080 SUPER 54%利用率、21,214/32,760MiB 显存；完整公开输入 E2 PID 204883 正在服务器隔离目录 `/root/ConsDagSubmissionReview` 训练。11:19日志为4,400/9,000步，loss有限，未见NaN/OOM/Traceback；之后没有在本地推测新的步数。
- 远端 `queue2.log` 记录 A3、A4、A2、A1 均按序完成（A3 03:47、A4 06:01、A2 08:13、A1 10:19，北京时间），每臂 9,000 步、12,000样本、0长度丢弃。逐日志检查每臂91条loss均有限；代码哈希均为 `5e0c0514...1635ce16`。未更改或中断任何远端运行。E2 后续由既有 recovery supervisor 持 GPU 锁接入 v6；远端 v6 queue_state 的原始 `status=failed` 仍需新快照验证恢复结果。
- 四臂 metrics、逐题预测与0.6B seed42基线预测经SFTP回收；按SHA-256校验并保留原始服务器输出。分析前将配对分析脚本和测试上传到隔离CPU目录 `/root/consdag_audits/e3_followup_20261125_1120`，不覆盖训练仓库。CPU回归测试7项通过；配对复算核验样本ID/E-I-N完整组、每臂源码/数据哈希、baseline预测哈希，并复现训练端已存执行与记录指标。
- 受约束 faithful 相对同字段投影基线（dev/tpl/tool/struct，%）：A1差−0.50/−5.86/−13.43/−18.14；A2 +0.17/+4.29/−14.43/−36.29；A3 +0.50/+1.29/−24.00/−29.00；A4 +1.00/+2.57/+0.57/+7.00。区间为10,000次配对任务组bootstrap、只条件于seed42、点态且未经多重校正。A2/A3的tool/struct无效输出率25%上下；A3 tpl_ho N false alarm 71/350=20.29%；A4去scope后struct faithful反而高7pp，要求删掉“所有字段对执行都必要”的主张。
- 解释限制：单seed、训练token量各臂不同（监督completion 0.894M–2.521M）、A1结构不再等价字段F1；prompt/schema/target一起变化，不对单字段作因果归因。A4也不能说明scope提高了执行，因为当前符号执行器本就不消费scope。完整读数及解释见 `reports/e3_ablation_readout_20261125.md`；配对输出、远端快照和双侧哈希清单在 `outputs/submission/followup_20261125/`。
- 11:32 CST 新鲜只读快照：完整公开输入 E2 到 5,200/9,000 步，累计53条日志loss均有限，GPU 81%、显存21,214/32,760MiB；recovery PID189623仍等待既有E2 supervisor退出，v6旧queue_state仍为inventory错误后的`failed/active=null`，尚未恢复到新作业。快照 `outputs/submission/followup_20261125/server_snapshot_latest.json`。
- 论文草稿§5.6已填入实际消融与限定，摘要仍等公平完整输入E2/v6；本轮未改v5主结果。下一步先等待E2完成，按冻结协议做公平配对和成本复算；随后核验恢复进程是否续上v6，再决定是否用额外种子复测A3/A4。数据语义仍是生成器构造条件，未被独立人工验证。

## 2026-11-25 11:52 CST v6 接力账本恢复与 E2 进度

- 只读服务器快照：完整公开输入 E2 PID 204883 到 6,600/9,000 步，67 条 loss 均有限，最新 loss 0.001282；RTX 4080 SUPER 利用率64%、显存21,214/32,760MiB。恢复监督进程 PID189623 仍在运行；没有中断或抢占 GPU。
- v6 的 `failed` 状态来自 release inventory 检查，不是训练失败。恢复前确认隔离发布目录 155 个封存文件与清单完全一致，release seal SHA-256=`7711bfe8...d19204fa`；并重新用冻结验证器核验1.7B seed42/43完成标记、provenance及预测/指标/适配器哈希。
- 先在服务器独立审计目录保存了原始队列状态、19,899.383秒累计预算、88,100.617秒剩余预算和原失败原因，再原子恢复状态为 `ready`；累计预算、`last_job` 未变，`active` 仍为空。没有改封存内容、数据或当前 E2。详细记录见 `reports/v6_queue_recovery_20261125.md`；服务器审计原件尚待随下一次结果回收。
- v6 尚未确认重启：E2 仍在运行，PID189623 将等待 E2 退出后通过原 GPU 锁接力。下一次只读快照需确认 E2结束、v6启动/进度和账本状态；之后再回收并公平复算 E2 主结果与成本。

## 2026-11-25 12:12 CST E2 公开输入对照继续推进

- 新鲜只读快照：E2 已到8,100/9,000步，82条loss均有限，最新0.0000121；GPU利用率51%、显存21,214/32,760MiB。恢复监督进程PID189623是E2进程PID204883的父进程，公开输入对照结束后将继续v6流程；未启动并行训练。
- 6项本地协议/公平配对评分测试通过。最终指标尚未生成；等待评测落盘后按样本/任务组配对主表编译器管线，并单独核成本、token与延迟，不把旧informed诊断臂代入主结论。

## 2026-11-25 13:14 CST E2 完成、独立复算与 v6 只读监控

- 完整公开输入 E2 单体已完成。Qwen3-1.7B、bf16、seed42、12,000行、9,000 optimizer steps；同seed编译器+符号规划器四切分 faithful 为 98.50/96.71/91.71/95.86%，单体为 90.67/87.29/38.14/14.29%（dev/tpl_ho/tool_ho/struct_ho）。E/I 配对任务组 bootstrap 10,000次的单体减管线差值为 −7.83/−9.43/−53.57/−81.57pp；CI见 `reports/e2_public_contract_readout_20261125.md`。
- CPU 独立复算覆盖数据/代码哈希、逐条预测与已存评分、E/I/N 完整组和原有配对 bootstrap，四切分和 overall 均完全复现。无模型重跑、API调用或GPU占用。产物：`outputs/submission/followup_20261125/e2_public_contract_independent_audit_v2.json`；脚本与回归测试：`scripts/submission/audit_e2_public_contract.py`、`tests/test_submission_e2_audit.py`。
- 更正旧 `none_false_alarm_rate` 解释：tpl_ho 为 83/350 条有效计划偏离默认值；struct_ho 为 8/350 条无效计划、0条有效偏离。该单体不输出约束，不能把此量称为编译器误报。结构留出59条完整评测输入超过训练长度上限，但评测未截断、训练集无样本丢弃。
- 训练token重放：编译器 prompt/target/total 为26,061,492/2,670,729/28,732,221；单体为35,346,477/1,056,099/36,402,576。两臂更新数相同，但计算量未匹配；单体`elapsed_s=8028.5`包括初始化、训练、评测与分析。不能声称成本或速度优势。
- 13:07 CST 服务器只读快照：RTX 4080 SUPER 利用率63%、显存17,420/32,760MiB；既有 v6 队列 PID208814/208832 正运行 Qwen3-1.7B seed44，日志到2,200/9,000，当前 loss 有限（8.98e-6），队列状态`running`，已预留预算88,100.617秒。没有其他 GPU 作业被中断或抢占。本轮未干预作业。

## 2026-11-25 13:37 CST v6 seed44 只读检查

- 新鲜只读快照：v6 队列状态`running`，活动作业仍是 Qwen3-1.7B seed44；日志推进到4,400/9,000 optimizer steps，已见的45条 loss 记录均有限，最新为`1.67649e-6`。指标和完成标记尚未生成，当前不能报告 v6 结果。
- RTX 4080 SUPER 利用率65%、显存17,420/32,760MiB。现有 relay、队列与训练进程均在运行；未新开、停止、重启或抢占 GPU 作业。只读快照：`outputs/submission/followup_20261125/server_snapshot_continuation.json`。

## 2026-11-25 14:06 CST v6 1.7B 两种子中期复算与 seed44 监控

- seed42/43 的 v6 metrics、provenance、completion、适配器、token coverage 与全部逐题预测从服务器只读回收。按 completion 逐项验证了 seed42 的14项和 seed43 的9项产物哈希，并核验155项冻结源码/数据哈希；v6 独立分析器在 CPU 上重放并复算了全部五个测试切分。没有重训、API调用或额外GPU作业。
- 中期 faithful 均值（仅两种子）：dev 100.00%、tpl_ho 96.43%、tool_ho 98.93%、struct_ho 96.58%、composition_ho 100.00%。tool/struct 的严格记录 F1 为64.51–73.66%、record exact 为69.81–77.14%，明显低于执行轴。模板留出 N 合同警报为8.29%/13.14%，超预登记5%门槛；警报来自非空预测和错误 query_state，不是解析失败。
- 对零样本的配对任务组检查中，两个已完成 seed 的 dev 和 composition_ho 差值、区间下界均为正；正式 H1 仍 pending seed44。两种子在 dev 与 composition_ho 的预测 JSONL 哈希逐字节相同，记录为需解释的稳定输出现象；不视作独立样本证据或无泄漏证明。composition_ho 仅测试已知工具/措辞条件下未见的 privacy+tool_auth 类型对；其 100% 不能外推到结构或真实语义泛化。
- 语义盲审状态仍为 pending，所有 E/I/N 标签仍为生成器构造。完整中期读数：`reports/v6_interim_1p7b_seed42_43_20261125.md`；复算汇总：`outputs/submission/followup_20261125/v6_1p7b_seed42_43_interim_analysis.json`。
- 新鲜服务器只读快照：1.7B seed44 到6,600/9,000步，67条loss均有限、最新 `1.19564e-6`；RTX 4080 SUPER 利用率47%、显存17,420/32,760MiB。未干预队列。快照：`outputs/submission/followup_20261125/server_snapshot_20261125_1405.json`。

## 2026-11-25 14:29 CST v6 同分母交叉诊断与训练续查

- 补记14:11日志审计：seed42/43各91条loss全有限、训练9,000步；seed44为6,900步/70条全有限。原件`server_training_log_audit_20261125_1417.json`按内部UTC时间标注，避免文件名导致时间误读。14:17续查到7,400步/75条全有限；14:29:38到8,300/9,000步/84条全有限，GPU56%、17,420/32,760MiB。metrics/completion尚无；未停止、重启、抢占或追加GPU任务。
- 新增事后诊断`scripts/submission/analyze_v6_seed_diagnostics.py`：只接受冻结验证器认可的完整run，从raw逐题重放评分与执行，复现原metrics并在同一E/I分母计算行为/记录2×2计数和跨seed任务组失败重叠。原训练、评分器、金标、提示和测试集未变；所有数字条件于已完成seed42/43。
- tool_ho：执行faithful为687/700、698/700，但严格记录正确仅383/700（54.71%）、460/700（65.71%）；执行成功而记录不正确为304/238题。struct_ho对应653/700、699/700 versus 434/700、395/700，交叉错误219/304题。旧overall record exact包含N，不可和E/I指标不加说明地比较。
- core匹配条件下的scope错误约束次数：tool合计607（budget282/privacy325），struct546（budget359/privacy187）；scope错误记录Jaccard为.760/.771。执行失败任务组交集/并集则1/14、0/37。前者是重复出现的记录问题，后者提示两seed行为失败敏感性；不能将此写成完整优化机制证明。当前符号规划器不消费scope/state/severity/evidence，不能将记录差异夸大成这些字段的执行因果贡献。
- 本机专项测试11/11通过；服务器独立CPU目录未装pytest，直接调用9个无fixture回归函数均通过。服务器复算JSON与本机逐字节相同（SHA-256 `8ab240c16d339f4730653de7f8fb3f8ccc0fecacaca6d21707be476bd51e0f03`），且10份预测双侧哈希一致。详见`reports/v6_execution_record_diagnostic_20261125.md`及`v6_seed_diagnostic_server_parity.json`。
- 等seed44完成再做三seed聚合。正式H4仍指定DeepSeek，当前小模型N警报不替代H4；v6 PE与语义有效性仍未解决，不能从高执行率宣称CCF-B已具备完整证据。没有重新开启定时任务。
- 同步状态：上述分析及报告已本地提交`5007d4a`，服务器隔离CPU审计目录已同步并复算成功。GitHub推送连续两次失败（连接重置、443端口超时），尚未确认远端分支更新；这是仓库同步阻塞，不影响既有GPU训练。下轮先重试推送，不能将此提交表述为已推送。

## 2026-11-25 16:49 CST v6 1.7B 三种子完成与4B接力

- seed44于15:15:55完成，v6原队列于15:16:10自动启动4B seed42。16:35 GPU98%、30,024MiB；16:47快照确认4B已进入训练700/9,000步，8条loss均有限，GPU95%、17,748MiB。1.7B三seed各91条loss均有限。未干预或额外启动GPU任务；既有30小时累计预算保持不变。
- seed44全部9项完成产物双侧哈希核验；服务器CPU检查224个适配器张量全部有限。冻结汇总器在服务器独立审计目录核验三run的来源/配方/数据/产物后重算五切分；交叉诊断本机再重放，和服务器结果逐字节一致，SHA-256 `2ec9bad92fe64bd2abf3a6014e6d54d0f8639f9be4b7b567c70db1f449e7368c`。没有把低分seed44当NaN坏权重排除。
- 1.7B faithful三seed精确计数均值±sample SD（dev/tpl/tool/struct/composition，%）：98.61±2.41 / 93.86±4.68 / 96.67±4.00 / 91.10±10.04 / 97.67±4.04。冻结分析器因先舍入每run输出tool96.66%，与精确计数仅0.01pp显示差异，原分析器未改。seed44为95.83/88.71/92.14/80.14/93.00%；此前把约55%简写为tool/struct表现，已明确纠正为strict F1约56.6/55.2%，不是执行成功率。
- H1的1.7B部分通过，各seed dev/composition提升区间下界均>0；总体H1等待4B。H3 tool-minus-struct区间[3.95,7.19]pp，按登记规则inconclusive。v6 PE三个完整缓存均missing_pe_config，H2/H4仍pending，不能复用v5数字充当新基线。
- 同分母E/I严格记录正确率tool/struct三seed均值56.05%/53.43%；tpl N broad alarm分别29/350、46/350、7/350。第三seed还有core/证据差错，不能概括为仅scope错误。更新论文草稿§5.7及`reports/v6_1p7b_three_seed_readout_20261125.md`，v5仍为主表。
- Git同步复核发现：用户当前main已是`c3c60a3`且远端main同哈希，包含先前`5007d4a/7b6ad1e`，所以这些工作已由main同步。旧本地codex分支顶端`12416dd`另含111.75MiB适配器，推旧分支被GitHub尺寸上限拒绝；没有改写/删除该历史或权重。当前新增工作在从干净main派生的`codex/v6-three-seed-readout`分支，显式暂存本轮报告、统计及元数据，不包含权重。
- 16:54后续确认：4B seed42到1,100/9,000步，12条loss均有限，GPU72%、21,480/32,760MiB，原队列正常运行。审计报告与统计提交`cf76198`及审计换行保护提交`2f3d740`已成功推送至`origin/codex/v6-three-seed-readout`。新产物在Git中保留原始字节；原适配器文件和旧分支未删除。

## 2026-11-25 17:38 CST v6 强PE正式启动，与GPU队列并行

- 服务器155项冻结文件校验通过；两次train接入检查确认官方接口可调用指定DeepSeek/qwen-max模型，temperature=0、max_tokens=384，DeepSeek关闭thinking。接入样本不是评测结果。
- 在独立目录部署并双侧核验`scripts/submission/supervise_v6_pe.py`，17:37:20启动PID216853，按原登记顺序接力DeepSeek十示例→qwen-max零示例→qwen-max十示例，每臂5,100条。仅CPU/API，8并发、CPU低优先级、数学库线程1、GPU不可见；未改冻结runner、数据、提示或评分器。凭据仅通过SSH标准输入与子进程环境传递，不进入代码/配置/实验日志。
- 17:38:05实际核验：DeepSeek进程PID216854，dev缓存56条唯一样本ID、返回模型名一致，尚未全量完成。缓存指纹/响应哈希/完成清单沿用冻结实现；任一臂失败停止后续、保留成功响应。三臂成功后自动运行冻结分析器；不能把部分缓存当完整PE或复用v5替代v6。
- 同时4B seed42推进到3,600/9,000步，37条已记录loss全有限，GPU90%、21,480/32,760MiB。原GPU队列及30小时累计预算未改，继续4B其余seed再接0.6B。未恢复定时任务，未抢占其他作业。
- 启动报告`reports/v6_pe_launch_20261125.md`；预检、train接入、启动和实际进度在`outputs/submission/followup_20261125/v6_pe_*.json`。H2/H4仍等待完整PE；本轮未产生新的正式性能结论。

## 2026-11-25 18:41 CST v6 DeepSeek全量完成、H2/H4落地

- DeepSeek十示例于18:37:08完成5,100条请求，用时3,587.536秒；返回模型名均匹配、finish全为stop。原监督进程自动接力qwen-max零示例，18:38缓存80条，后续十示例仍待队列。完整缓存七文件双侧SHA-256一致，原冻结发布155文件和请求/响应/完成清单验证通过。
- 冻结分析器在服务器CPU完成全量复算，新增独立整数聚合脚本在外部审计目录逐条核验五切分记录、行为与N错误计数，全部匹配；共享原执行谓词，不称独立语义验证。缓存、配置、完成标记已回收，分析`main_after_deepseek.json`与整数审计`v6_pe_deepseek_integer_audit.json`均在`outputs/submission/followup_20261125/`。
- DeepSeek受约束faithful（dev/tpl/tool/struct/composition）为98.00/99.57/97.00/94.71/99.86%。1.7B三seed减DeepSeek的配对95%区间为[−0.56,+1.83]/[−7.33,−4.19]/[−1.76,+1.19]/[−5.81,−1.48]/[−2.95,−1.48]pp。dev/tool/composition满足原−3pp门槛，但tpl/struct未成立，整体H2仍未成立。composition窄幅过线，区间固定观测seed，不能声称稳定追平或小模型更优。
- DeepSeek整体N broad alarm为7/300、0/350、11/350、6/350、7/350；tool_ho permission子型9/150=6%超过H4门槛，其余子型×切分未超。子型允许重叠；门槛失败是样本诊断，不是总体率显著超过5%或金标错误的证明。
- 同E/I分母，DeepSeek严格记录正确率87.83/91.57/83.00/79.43/75.29%。组合留出699/700执行成功、527/700记录正确，172条行为成功但记录错；新增报告及草稿§5.7明确字段不被消费的限制。报告`reports/v6_deepseek_readout_20261125.md`。
- API用量输入44,521,485、输出474,593 token；输入中43,403,008为缓存命中（97.49%）。不把逻辑输入全按未缓存费率计费，不由并发整臂耗时推断解码速度优势。18:38 GPU快照：4B seed42到6,900/9,000，70条loss全有限，GPU94%，原队列及30小时预算未动。
- 18:48续查发现qwen-max零示例已于18:42在346条成功响应后返回HTTP 400，监督器按规则退出，十示例未启动。18:49对首个缺失ID `dev-00125-N`用原冻结请求函数进行一次诊断，返回`Arrearage`（账户欠费）；未改请求或刷重试。原缓存346条及配置双侧哈希通过，已备份但不报告部分性能。账户恢复前这两臂保持blocked，GPU不受影响。18:48 GPU为4B 7,400/9,000、75条loss全有限、97%、21,480/32,760MiB。

## 2026-11-25 19:33–19:43 CST 4B训练完成与记录等价诊断

- 19:33快照：4B seed42完成9,000步，91条loss均有限；trained dev已落盘，完整metrics/completion尚无，GPU59%、21,480/32,760MiB。原relay/队列正常，等待评测结束再接seed43。未新增GPU训练、API请求或定时任务；qwen-max仍因账户欠费阻塞。
- 新增服务器CPU事后诊断，重放DeepSeek与1.7B三seed的五切分，共20个臂×切分；逐条复现已有行为和严格记录计数。分离parse failure、core参考不一致、core相同但其他严格字段不同、strict exact，避免把同一差错重复归因。源码在独立审计目录，封存155文件未变。
- 进一步确认tool_auth/order在冻结检查器中共用前置谓词。DeepSeek组合留出172条行为成功但strict不匹配，120条为同角色tool_auth→order、52条为state/query_state规范差异，全部具有相同冻结谓词。五切分494条行为成功但记录不一致中488条（98.79%）谓词等价；不能当作488次语义失败。谓词一致是新增解释性诊断，未改原strict/core/faithful或H2/H4。
- 小模型同样存在编码差异，但seed44解析失败仍为14/15/20/29/35（E/I，共113/3,400），没有被等价诊断豁免。当前不能凭小模型更高strict分数主张语义超过强模型；报告与草稿方法/§5.7已补充这一限制。
- 本机专项12项通过；服务器直接执行7项分类/谓词真值表检查通过。20组复算完全匹配，双侧产物哈希通过；`v6_pe_record_error_comparison.json` SHA `2eb575da...c3fdd4`，`v6_pe_predicate_equivalence.json` SHA `5d492ab8...6eae93`。完整报告`reports/v6_predicate_equivalence_audit_20261125.md`。后续不根据测试差错改金标、挑seed或调提示，保留GPU原接力。
- 19:43:22续查4B trained dev与test_tpl_ho已完成，GPU55%、21,480/32,760MiB；完整metrics/completion仍未落盘，队列running。对应`v6_status_post_equivalence.json`；不报告局部指标为正式4B结果。

## 2026-11-25 19:46 CST 审计同步与稿件一致性修正

- 13个审计文件提交为`2e2eb00`，已推送到`origin/codex/v6-three-seed-readout`；暂存文件凭据模式和大小检查通过，审计JSON与源码在Git中的原始字节与工作区一致。未提交适配器权重。
- 19:46:29服务器实查：4B seed42完成9,000步，91条loss均有限，trained dev/tpl两个切分完成，整体metrics/completion尚未生成；GPU59%、21,480/32,760MiB。原队列继续，1.7B三seed均已完成。状态存入`v6_status_followthrough.json`。qwen-max账户欠费状态未变，本轮未重试API。
- 对草稿引言、C3贡献和局限作一致性修正：隐式参考记录符合度不能等同语义可恢复性；witness和模型一致率不能代替独立语义验证；C3明确区分参考记录、冻结谓词和执行行为。保留全部原始数值；v5等价编码比例仍待独立计数，不套用v6结果。更新已完成的DeepSeek-planner与v6章节状态，避免把已完成项继续列为缺失。


## 2026-11-25 架构候选复核与服务器CPU四臂试点

- 复核GLM四份材料，核对15篇arXiv和2篇ACL元数据，阅读10篇承重方法段；11组检索记录和引文归档至literature/review_architecture_20261125。GNNVerifier/CONSTRAINER/TTCT覆盖通用图验证、约束图和轨迹对齐；TACL 2013非确定性oracle也覆盖正确动作集合思想。不宣称通用GAT/CLIP/集合监督本身新颖，不给CCF-B录用概率。
- 服务器S0审计256个train组及300个dev组：1698子集，最小改动数与冻结求解器零分歧；全约束任务多解比例68.75%/72%。816个需编辑的重复约束控制均显示留一归因消失；这个控制发生率不是自然数据发生率。源码、监督格和原数据哈希保留。
- 4B v6 seed42全量完成，原评分器核验faithful为100/97/100/99.14/100（dev/tpl/tool/struct/composition）。单seed不作新H2判定；4B seed43自动接力继续。22:04:43服务器GPU86%、30292/32760MiB，未抢占原队列。
- 已实现0.6B冻结对象编码器＋参数量相等的dense/graph指针头，共563920个可训练参数。服务器14项单元测试及20步四臂smoke通过。GPU不可见，2个低优先级CPU线程，四臂各1000更新，21:51启动、8分37秒完成。训练776子集/5526前缀，开发922子集（622有约束、300空约束）。模型不接收未来动作/金标计划作为输入；同结构掩码，所有监督最优计划通过可达性检查。
- seed42原始开发受约束faithful：dense_single87.14%、dense_set91.32%、graph_single86.66%、graph_set89.39%；N失败/额外修改均0。重复约束探针分别78.94/86.98/87.14/80.39。集合相对单解+4.18pp（41胜/15负），任务组描述性bootstrap区间[1.44,7.00]；不是训练seed总体CI。图相对dense_set无独立增益，停止图分支扩规模；仅按预设3–5pp区间补dense两臂seed43，未改数据、学习率或更新数。
- 12份逐题结果及训练源码哈希复核通过，4臂1000步记录均完成且loss/梯度范数有限；完整权重/记录已下载到outputs/architecture_20261125/pilot_dev_v1（未入Git），摘要pointer_pilot_analysis.json。数值/资源组合挑战、无语言编码器和确定性去重基线、外部数据仍待完成；本试点是oracle记录规划，不等于端到端语言泛化或新方法成立。
- 研究审计先提交为1fb1a57。GitHub同步尝试遇到连接重置/443超时，服务器代码已通过SFTP上传并校验；保留本地提交，未改写远端历史。

- 第二seed两臂随后完成（277.73秒）：单解81.19%、集合76.21%，增量−4.98pp，与seed42的+4.18pp翻转；两seed集合均值83.76%，单解84.16%。决定停止集合/图分支扩规模，不加CLIP。输入、评分、代码哈希和语言向量一致，order分项掉分明显。集合臂seed43曾进入替代最优前缀209题、其中69题后续失败，seed42为231/9；这只是覆盖不足线索，不作因果定论。下一步需先用两臂共同的全最优前缀覆盖控制；尚未运行，不能算新创新点。复核记录pointer_seed43_analysis.json、pointer_seed_diagnostic.json，源码已归档。

### 2026-11-25 — 共同前缀覆盖对照及求解器必要性检查

首轮集合监督seed效应翻转后，登记并在服务器CPU启动all-optimal共同训练前缀对照：seed42/43、dense_single/dense_set、1,000更新、2线程nice15，原GPU队列保留。训练前缀由5,526增至8,669；两臂列表和采样随机流完全相同。19项解析/结构/评分测试通过；服务器未安装pytest，使用无fixture的标准库测试入口。首次缺少PYTHONPATH的测试失败记录保留，补上冻结执行器路径后通过，未修改冻结代码。

另完成已有确定性求解器在全部922个开发子集的基线：622个受约束全对、300个N全对，单题求解中位数0.632ms（每题warmup后3次；不含评分）。当前世界没有神经规划头替代求解器的必要性证据。结果`outputs/architecture_20261125/solver_baseline.json`；不扩GAT规模，也不凭此宣称真实语言/环境安全。

追加核验CCTU的数据许可、固定版本、第一行schema及方法中的审核/执行反馈协议；没有执行外部工具代码，没有外部模型结果。后续接口研究仍是待验证候选，不是已确立创新。

共同前缀四次对照完成：seed42单解/集合86.01/86.01%，seed43为88.10/89.71%。两组描述性区间均跨零；N偏离全0；12个结果文件哈希和四个有限训练日志已复核。10次开发训练总计约25分钟CPU墙钟，不扩GPU，不增加CLIP臂。最终报告与`architecture_final_status.json`保留全部结果；①②作为候选方法整体评估，③E/I/N数据资产保留，不称三项创新已成立。

### 2026-11-25 — 后续对比学习试点与扩散近邻核查

用户进一步授权核查CLIP/GRPO与规划器架构；在冻结0.6B文本特征和oracle候选上，服务器CPU完成BCE/排序/多正例对比三损失×seed42/43，各800更新。参数590,592，192开发请求；BCE准确率63.02/62.50%，排序与对比均66.67/71.35%。逐题预测并不相同，对比相对排序胜负为15:15和13:13。未达到每seed较两基线均高3pp的预登记门槛，停止该冻结头方案扩规模。总墙钟316.585秒，含编码259.690秒；全部30文件哈希一致，训练步检查和事后日志未见非有限值。详见alignment_pilot_readout_20261125.md。不将该检索试点说成端到端编译器或生成式CLIP训练成功。

核对SFT/GRPO原文后，撤销一般化的“SFT有害、联合必优、GRPO等同CLIP、至少两卡”等二手主张。用户提供微信正文后定位Rufus-Air，明确其大模型串行配方不能保证4B收益。发现AMIR-GRPO等联合对比学习近邻，原文、笔记及来源哈希在literature/review_grpo_alignment_20261125。

用户再提出前置解析器、约束传播和借鉴具身扩散。原文核验ATLAS管理器消融、Dr.Aid传播/编辑/删除、CaMeL数据流策略，不能以“传播空白”为新颖性。新增DiG-Plan/CoDA/Plan-and-Patch/LayerDAG/LTLDoG方法核查，扩散工具规划、去噪约束和局部修复均有近邻。研究候选及开发门槛写入parser_planner_diffusion_review_20261125.md；没有新起扩散/GRPO训练，也未修改冻结数据/评分器或测试选择规则。

本阶段最近服务器只读快照为23:01 CST：原v6 4B seed43进程220951运行，23:00 GPU52%、30,292/32,760MiB。此为带时间戳的历史状态，不作为报告发送时实时快照。原30小时接力保留，未抢占他人任务；欠费API臂未盲目重试。


### 2026-11-26 00:39 CST — 旧结果复用与固定规划器后续

恢复服务器访问，原v6队列保留，4B seed43已完成，seed44继续；00:39 GPU97%、26956/32760MiB。seed43完成签名、冻结数据和可获取源码哈希通过；faithful为100/94.57/98.29/97.29/100（dev/tpl/tool/struct/composition），tool/struct strict为0.692/0.683。本轮没有独立重评分其完整预测，不混入v5/H2判定。

新服务器CPU探索回放4050条（dev及三旧测试切分），复用v5 public-contract单体计划和1.7B seed42编译预测，选择过程不读取金标/witness。一步修复faithful分别90.67→94.17、87.29→92.00、38.14→53.29、14.29→27.29%；同触发盲编辑分别90.50/86.57/38.86/15.43%。四个分组探索性CI下界为正，但不包含seed不确定性，旧测试不称新盲测。模板N额外误改9/350，结构无效计划仍多，预测约束＋符号求解仍显著较强。初轮历史字段核对失败保留，v2只修正核对字段。逐样本结果、协议、哈希和局限见local_planning_followup_readout_20261126.md。

已部署独立GPU等待器PID228433：固定4B规划器、v6 dev 48个完整E/I/N组，共144条，直接/通用分解/PE编译/SFT编译四臂及符号诊断。预检PASS，实际状态waiting_for_original_queue；只有原队列complete且同物理GPU锁及空闲检查通过才运行，最多2活动小时，不改原队列。失败/预算耗尽不抢占。原始调用、输入输出token、时间、截断和失败全部记账。七项专项测试和服务器CPU微型PEFT兼容检查通过，真实GPU试点仍待运行。

追加Fox等ICAPS2006计划稳定性指定全文阅读、HTN修复ICAPS2025元数据与摘要核查，保留ATLAS/ATG/Replan近邻限制。普通局部修复、扩域和少改动目标均不能当新发明；报告不宣称CCF-B创新已经成立。未启动GRPO/扩散新训练，未改定时任务。数据与既有正负结果继续复用，方法选择由固定规划器对照决定。


### 2026-11-26 02:04 CST — 历史审计、编辑后果探针与可信场景分层

- 4050条v5输出与三seed编译结果逐ID/分组/哈希审计，恢复全部冻结聚合；strict_parse保留无效输出，不等同空约束。原计划合法且谓词匹配时仍有22/34/117/91次有益修复，否定“正确编译几乎无修复收益”的预期；更正旧文把原非法计划未恢复写成算法保证的错误。
- tpl N新增9条损害均为两类deadline误报；与符号N失败11条重叠9，剩余2属于原83条，集合并集92。不能宣称9个独立语言家族或把失败相加为103。
- 两轮服务器CPU探索完成（2.73s、3.31s；0新增模型/API请求），所有输入与回收SHA一致。第一轮路径元数据分隔符失败保留；第二轮前6臂完整复现第一轮。至少2可用解释的后果/改动成本门控拦截9新增N损害，仍损失12有益E/I修复，相对无门控净+0.33/+0.43/+0.57/−0.57pp；struct区间为[−1.14,−0.14]pp。三编译器总成本不包含在CPU回放时间里。禁止继续旧测试调票数/阈值。
- 本地对已回收产物完成可信场景分层；四切分所有互斥类型组合计数与原聚合匹配。tool含privacy任务84/250→77/250，含tool_auth任务124/214→132/214（11胜3负）；类型集合重叠不可相加。8条跨tool/struct隐私损失均只有一份整记录可用。已核一例：无关order角色写错，连带使正确privacy字段失去支持，必要脱敏编辑被拒。下一项独立开发/确认设计已登记，尚未生成数据或运行；不能静默丢弃unknown义务。
- DRAGO28页、ORSMT41页、MetaAct21页、Certified Harness17页本地全文读完，SAGE外部附录未取得，ReLoop/CLEAT/AMAO仍部分阅读。12篇PDF实际页数和PDF/文本SHA复核，近期五篇BibTeX与覆盖清单落盘；官方方法未复现。
- 五套研究技能均已安装并经结构校验；索引research_skills_index.md。通过工具更新原每小时任务consdag-2，保留ACTIVE、原线程和间隔，固定可信数据空间并同步最新正负证据及独立验证要求；没有新增重复任务。
- 02:04:09只读快照：原30小时队列status=running，active为4B seed44，GPU87%、26956/32760MiB，固定规划器等待器PID228433存活、waiting_for_original_queue。未改运行中code-v2或冻结协议，未新增训练。专项测试7/7通过。
- 完整结果：history_and_edit_impact_readout_20261126.md、trusted_space_family_audit_20261126.md。新机制仍待独立验证，不宣称CCF-B录用或新颖性已成立。

### 2026-11-26 02:15 CST — 局部契约有效性受控探针

保持可信数据空间。先登记partial_contract_probe_protocol_20261126.md，再在新服务器隔离目录partial-contract-20261126-v1生成并运行5机制骨架×E/I/N×0/2/3损坏视角，共45条件。只有受控编译记录，无自然模型输出；不将E/I复制或条件数当独立任务。全程0模型/API调用、单线程nice15、120秒上限，实际符号探针0.0395秒，不含模型成本。

新增5项契约测试通过且逐项内存变异均被捕获，旧7项通过。下载inputs/per_condition/summary三项SHA与服务器匹配，运行清单保存协议及源码SHA。逐条保留能恢复3种正确修复候选；保留unknown后有限补全仅放行1种、其余仍需复核。全部视角损坏时丢弃unknown会放行2种违规提案；一致错误N仍导致多余编辑。因此停止将“逐条保留＋unknown”直接升为②，定位为接口修正和必要基线，不继续调人工例子的规则。

ORSMT p3/6原文已覆盖逐条源契约及unresolved保留undecided；MetaAct类型契约、合取和组合回放不能省略。本项目whole-record实现缺陷不等于其他论文固有缺陷。原文粒度记录partial_contract_granularity.md；未复现官方代码。

02:14:55只读快照：v6 4B seed44继续running、GPU85%、26956/32760MiB，固定规划器仍waiting_for_original_queue。未改code-v2/原队列/预算，下一项为独立自然错误及同预算语义复核，当前未启动。详细读数partial_contract_probe_readout_20261126.md。

### 2026-11-26 02:26 CST — 运行来源补审与真实复合错误

提交c78b5be前源码Git字节检查在run_e1.py失败后仍提交推送，原检查不得追认为通过。本轮七个输入逐项补审：run_e1.py和dataset_v5_spec.py只有CRLF/LF差异，其余五项字节相同；三结果Git对象与服务器回执完全匹配。另存run_source_bytes.zip并逐成员核对实际启动SHA，git_provenance_audit.json记录原失败和解决。未改冻结源码、运行协议或结果，无需重跑探针。

本地仅分析已回收八条隐私损失及三seed原始输出，不生成新计划或模型预测。六个任务组、24份记录均有正确可用privacy谓词，其中16份整体失效；按非互斥标签，14份有目录外角色、2份还绑错另一合法目标、另有缺字段/错误类型等。数据/预测SHA与历史审计匹配，病例计数及整体可用状态复核；独立逐字段检查privacy参数和两个复合误绑案例通过。汇总元数据将independent_task_groups改为task_groups时，验证命令首次因路径分隔符键查找失败，修正键匹配后通过；两次案例文件字节完全相同，未改变任何结果。该问题与原实验无关。

产物natural_privacy_loss_audit_20261126.md及同名outputs目录。不能把“只有first-role错”的受控结果外推为真实错误改进；下一项需同预算核验完整义务绑定，同时保留仅修不合法字段对照。仍不调整旧面板门槛，不扩新训练，固定可信数据空间与CCF-B目标。

### 2026-11-26 09:32 CST — 真模型复核启动、格式故障隔离及完整复测

- 原4B CPU复核已运行1802.85秒，15调用；三臂调用存在的5行中1次被预算截断，仅4行没有活动预算截断。7次上下文复制导致token上限截断，不能当语义方法失败；重新编译E/I成功3/4但唯一N被改坏。真实负结果、全部提示、成本与失败保留；7结果SHA核验、评分和成本重聚合通过。
- 格式对照只增加三臂共同的输出边界，单行三调用212.58秒，3/3解析通过、无截断。没有按任务分数挑提示。随后实际启动18历史请求×三臂完整复测，最多54调用、90分钟活动CPU预算，8线程CUDA隐藏；目录contract-review-4b-envelope-20261126-v1，父进程242847，最长输入2637 tokens，服务器四项测试通过。不是独立新测试，不预报方法成立。
- v6 4B42/43/44已完成并恢复27文件，SHA/数据签名/15预测ID覆盖核对；faithful均值100/96.29/99.38/98.14/100，tool/struct strict为0.755/0.734。未独立重跑执行评分，v6与v5分列。
- 09:31:34服务器GPU38%、17170MiB；原0.6B43已完成，44训练第1200/9000，241982实际占卡；固定规划器228433存活。未改原30小时队列、2小时固定规划器、code-v2或健康作业。
- CLEAT本地34页技术内容及附录读完，补全配对采样、原生PASS、策略刷新、用户模拟器与算力条件；更正“原理相似等于整体重叠”的宽泛措辞。官方代码未复现。原五套研究技能继续复用。

收尾核验：代码/结果提交ab91346已推送。完整复测再次查到子进程242848存活、2/54调用完成且无截断。原consdag-2已通过自动化工具更新为当前运行状态、完成后分析分支及每轮末尾强制动态改写规则；读取TOML确认ACTIVE、每小时、原线程均保留。4220字符提示SHA256为41049c3da986a4af62f7d31f81173366cee4f3ab00bcbd9974b8eb952ba46d84。没有创建重复任务或写入凭据。
