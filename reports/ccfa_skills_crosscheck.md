# CCFA-Skills 对照审查：ConsDAG 0.6B pilot

审查日期：2026-11-19  
CCFA-Skills 来源：`mikubaka88/CCFA-Skills` main，README 标注 v0.12.1。  
范围：只审查当前 ConsDAG pilot 的证据边界、实验纪律和研究工程记录；不把第三方竞赛任务或外部数据集纳入本实验。

## 已取得的对照材料

已从仓库 raw 文件下载到 `literature/ccfa_skills_v0.12.1/`：

- `ccf-common`：任务模式、证据/隐私、工件契约、评审输出规范；
- `ccf-humanization`：实验纪律；
- `ccf-idea-reviewer`：严格思路评审、六维 rubric、calibration、expert panel；
- `ccf-literature-searcher` 与 `ccf-literature-monitor`；
- `ccf-experiment-designer`：evidence design；
- `ccf-research-engineer`。

仓库 GitHub API/整仓 zip 在本机受到匿名请求限制，因此没有把整个仓库伪装成“已下载”；本次审查所需的原文文件均已逐个取得并保留 URL 来源。当前 `literature/innovation1_audit/pdf/2607.04854.pdf` 是一次失败下载留下的 0-byte 残片，不作为论文证据。

## 当前 pilot 的可复核事实

- `python src/validate_pilot.py`：201 条记录、67 个组、`valid: true`；
- `python -m pytest -q`：5 passed；
- 历史 GPU 日志 `outputs/gpu_v5/consdag-constraint-compiler-0-6b-pilot.log`：运行时检测到 2× Tesla T4，每卡约 14.56 GiB；CPU preflight pass；
- `outputs/gpu_v5/outputs/pilot_run.json`：Qwen/Qwen3-0.6B，150 train / 51 test，seed 42，75 optimizer steps；
- prompt-structured：constraint F1=0，implicit/none 状态识别为 0；
- prompt-abstaining：constraint F1=0，状态准确率 0.373；
- trained LoRA：状态准确率、constraint micro P/R/F1、exact accuracy、JSON parse rate 均为 1.0，evidence exact rate=0.961。

这些数字可支持“在这套透明、合成、同模板分布的 pilot 上，短 LoRA 训练能拟合该输出契约，而零样本提示词基线没有学会”的管道信号结论。它们不能支持校准、拒判能力、自然语言隐式约束恢复、跨模板/工具组合泛化，或 planner 下游收益。

## 按 CCFA 规则的审查结论

### 可以保留

1. **问题—机制链条是可检查的。** 当前数据固定 task goal、graph、witness 和 role vocabulary，只改变 E/I/N query rendering；schema 检查 exact evidence span、scope、severity、pair integrity 和 witness feasibility。这满足一个小型机制 pilot 的可审计性要求。
2. **pilot 目标写得足够克制。** `README.md` 和 `reports/pilot_dataset_protocol.md` 已明确说明 synthetic-only、无独立 oracle/人工复核、无 group-held-out、无 calibration/abstention claim。该边界符合 `ccf-idea-reviewer` 的“区分概念判断与经验验证”和 `ccf-experiment-designer` 的“planned result 不冒充 finding”。
3. **比较对象至少包含同底座 prompt 条件。** 这使“训练信号是否产生可学习增益”成为一个可回答的 pilot 问题，但仍只是同一 base model、同一窄分布上的比较。

### 必须降级或暂不宣称

1. **不能把 1.0 F1 称为创新点①成立。** 训练集和测试集都是手写合成样本，role graph/措辞模板在 split 间复用；没有独立 oracle、人工 agreement 或 unseen template/tool-combination。最合理措辞是“pipeline feasibility / learning-signal pilot”。
2. **不能把 implicit=1.0 称为语用推理。** 当前 implicit 文本由固定模板生成，且 gold confidence 全部为 1.0；没有恢复性准入判据，也没有对隐式线索是否唯一指向约束的人工/强模型审查。
3. **不能把 abstain 或 confidence 称为已验证能力。** 当前样本没有 ambiguity/abstention-required cases；`abstain_accuracy` 只是在没有拒判需求的集合上测量。confidence 是构造期常数，不是校准目标。
4. **不能把 evidence span=0.961 作为忠实度结论。** span 是生成器写入并由 schema 做 exact substring 检查；这验证了标签/解析契约，不验证真实用户语句中的证据边界。
5. **不能支持 planner-agnostic、下游约束满足或外置信用门控。** 当前没有 planner、执行环境、constraint-anchored reward、节点归因或 RL 训练；这些属于后续实验，不应从 compiler-only pilot 外推。

## 最小后续证据包

按 `ccf-experiment-designer/references/evidence-design.md` 的“最小充分证据”原则，下一轮优先级如下：

1. **先修数据测量面。** 新增训练/测试互斥的措辞模板池和工具组合池；保留同 DAG + 同约束集的 E/I 对，N 作为对比臂。至少给 implicit 版做分层 oracle 恢复抽检，并记录人工 agreement。
2. **再复测编译器。** 0.6B 先做 ≥3 个种子；报告 per-type、E/I/N 分桶、parse fail、evidence span、scope、severity，以及 abstain coverage-risk。保留当前 prompt baseline 作为 sanity baseline，并补一个简单规则/结构化 oracle 上界。
3. **最后才进入②。** 在 ① 的输出冻结后，以同一执行检查器比较 vanilla、加法混标量和完整版门控奖励；先做小规模可达性/方差预诊断，避免把无梯度类别误报成机制失败。当前 pilot 不应提前生成②的结果表。

## 审查判定

**概念层：revise，创新点①值得继续但需先修正机制缺口。** 其“独立编译器 + typed 输出 + evidence/scope 字段”在概念上清楚；当前材料不足以证明训练形态、隐式恢复和校准拒判的经验优势。  
**实验层：pilot pass，论文证据未达标。** 现有 run 可以作为内部管道里程碑和负基线记录，不能作为“近两年无人匹敌”或“创新点已被验证”的依据。下一步应优先扩大独立测量面，而不是直接跑 4B/8B。

## 可追溯文件

- [项目 README](../README.md)
- [pilot 数据协议](pilot_dataset_protocol.md)
- [pilot 结果](../outputs/gpu_v5/outputs/pilot_run.json)
- [GPU 日志](../outputs/gpu_v5/consdag-constraint-compiler-0-6b-pilot.log)
- [CCFA-Skills 镜像](../literature/ccfa_skills_v0.12.1/)
