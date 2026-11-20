# 实验台账（v2 证据战役）

逐日记录关键决策、产物指纹与实验状态，供论文写作时回溯证据链。

## 2026-11-20

### 环境
- 本机 RTX 4060 8GB（桌面占用后 ~5GB 可用），base Python 3.12.6 + torch 2.12.0+cu126 + transformers 4.57.6 + peft 0.19.1。
- 决策：仅跑 <4B 模型（0.6B/1.7B），4B/8B 等多余算力再补。

### 模型（避免旧任务污染，全部重新下载）
- 来源：ModelScope `Qwen/Qwen3-0.6B`、`Qwen/Qwen3-1.7B`，下载到 `models/`。
- `models/Qwen3-0.6B/model.safetensors` SHA256: `F47F71177F32BCD101B7573EC9171E6A57F4F4D31148D38E382306F42996874B`。
- `models/Qwen3-1.7B/model-00001-of-00002.safetensors` SHA256: `169AD53EC313C3A34B06C0809216E4FC072CCE444A5D4FF2B59690D064130ED5`。
- `models/Qwen3-1.7B/model-00002-of-00002.safetensors` SHA256: `912BECFF8D60672AA8628EF08C05898D9ADF17C2AD4AE3CAF99B065622FDEFF9`。

### API key 实测（PE 实验准备）
- 用户提供的 key `sk-xRHK...QsNa`：在阿里 DashScope compatible-mode 实测返回 `Incorrect API key`。
- 同一 key 实为 geekspace.cloud 中转 key（与 `~/.codex/config.toml` 的 ANTHROPIC_AUTH_TOKEN 一致），
  该中转仅有 gpt-5.5/5.6-sol/5.6-terra/6-astra，无 qwen-max/qwen-plus。
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
- 4B zero-shot（服务器）：dev 900 条完成，约束 F1 0、三态准确率 0.3533，与 0.6B/1.7B 同样为 schema 提示照抄退化；test_tpl_ho/test_tool_ho 仍在生成。
- 1.7B 进度（本机 4060）：训练 2700/9000 步，约 30%，近期约 14–15 秒/步，预计 2026-11-21 完成。
- GRPO/E2 状态：仓库目前没有 planner rollout 环境、奖励实现或 GRPO trainer；只有实验方案。未把 E1 LoRA 训练误报为 GRPO，也未伪造 E2 启动。
