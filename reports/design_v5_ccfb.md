# ConsDAG v5：基于论文与 v4 实测重新设计的可立足方案（面向 CCF-B）

日期：2026-11-24。会话：`b3f1c2a4-5d6e-4f7a-8b9c-0d1e2f3a4b5c`。

**证据纪律**：
- 对相关工作的每条断言都以 `[ID]` 引用。ID 对应的论文、fulltext 路径、行号和英文原句见**附录 A**；这些引文全部由 `tools/verify_quotes_v5.py` 回原文定位（51/51 找到，0 条超过 40 词，结果在 `reports/design_v5_quotes.json`）。
- 查不到原文的断言一律写"无原文支撑"。
- 本项目自己的数字分三类标注：【已定】是用户给定、本文不再复核的事实；【复算】是本轮只读重算的结果；【新数据】是本轮生成的 v5 数据。

---

## 0. 结论先行

| 问题 | 回答 |
| --- | --- |
| 新方案值不值得重跑？ | **值得，但只重跑必要的部分。** v4 上的三个缺陷（N 版 2 条歧义模板、名称级 tool_ho、策略卡泄漏 PII 别名）都会直接削弱论文主张，而且都只能靠重新生成数据加重训来修；修完后能回答 v4 回答不了的问题（结构 OOD、无泄漏的隐私推断、训练方差）。不重跑的话，只能按 v4 的收窄口径投稿。 |
| 最小重跑代价 | **约 19.3 GPU 小时**（RTX 4080 SUPER，1.7B 与 4B 各 3 个种子），外加 3 个强模型 PE 臂约 12,150 次 API 调用（不占 GPU）。完整版加上 0.6B 三个种子，约 **26.9 GPU 小时**。估算依据见 §7。 |
| 三个创新点 | ① **改写**：不再主张"胜过强模型"，改为"训练式可审计逐请求编译器 + 等精度下的部署成本"，主张以非劣效检验为准。② **删除** GRPO 信用分配这一算法贡献，**改写**为"约束解释与候选搜索的交叉干预诊断"。③ **保留并加强**：新增结构 OOD、子类型化 N 近似对照与歧义门槛、faithful 主指标和保守规划器下限。 |
| 本轮已完成 | v5 规范层、生成器、验证器（V1–V14）、评测器升级（faithful 主指标 + 保守参考档）、PE 与队列脚本、预注册分析脚本、v4 只重算分析。本地 71 个测试全部通过；v5 数据 16,050 条，验证 PASS，哈希见 §4.4。 |

---

## 1. 现状事实（v5 设计的输入）

### 1.1 已定事实（来自用户，不再复核）

**E1 v4 seed42 主表**（受约束记录的 faithful execution）：

| 系统 | dev | tpl_ho | tool_ho |
| --- | ---: | ---: | ---: |
| 0.6B LoRA | 97.33 | 82.29 | 75.57 |
| 1.7B LoRA | 100.00 | 95.71 | 81.00 |
| 4B LoRA | 100.00 | 95.86 | 99.86 |
| Qwen-Max 零样本 | 90.50 | 87.43 | 86.86 |
| Qwen-Max 十样本 | 88.17 | 85.00 | 89.14 |
| DeepSeek 十样本 | 99.33 | 99.00 | 100.00 |

本轮复算了三个训练臂，逐格与上表一致（584/576/529、600/670/567、600/671/699）。这说明本轮对 `trust_env` / `eval_exec` 的改动没有改变 v4 结果。

**E2**：
- 1,400 道受约束题，重排 682 → 一次验证式局部修复 1,144，+33.0pp，95% CI [30.0, 36.1]，464 胜 2 负；
- 另一训练顺序 756 → 1,199，合并 +32.32pp；
- 原 GRPO 三臂三种子的净变化为 +1 / −3 / −6（分母 80），**不成立**。

**seed43 复现**：0.6B、1.7B 已完成，4B 正在服务器上做最终评测。1.7B 的 tpl_ho state 错误数从 seed42 的 122 变为 seed43 的 143，训练方差明显。

**49 条公共错误**：五个训练 run 的公共错误集合有 49 条，全部是 variant=none。

**边界**：
- tool_ho 只是名称级 held-out；
- 策略卡泄漏测试集 PII 字段别名；
- 4B tool_ho 执行 699/700，但含证据的完整记录只有 552/700；
- CCFA 概念分 ① 4.13、② 4.18、③ 4.28，均为 revise。

### 1.2 本轮复算（只读，代码 `src/analyze_v4_nearmiss.py`，输出 `outputs/v4_reanalysis/nearmiss.json`）

**(a) N 版公共误判的来源**

v4 有两条 N 模板，提到他方规则却没有说明"不适用于本任务"：
- `test:tool_auth:N:2`："Only the partner account gates {required} behind {approval}."
- `test:deadline:N:2`："A {hours}-hour window exists for the other lane only."

用词法门槛 G1（§3.1）可以把它们逐字挑出来；在全部 40 条 v4 N 模板（5 类 × 2 池 × 4 条）中，只有这两条不通过 G1。

只看 tpl_ho 的 N 记录：

| 系统 | 全部 N 误报 | 剔除含上述两条模板的组后 |
| --- | ---: | ---: |
| 0.6B LoRA | 166/350 | 103/282 |
| 1.7B LoRA | 99/350 | 36/282 |
| 4B LoRA | 68/350 | **0/282** |
| DeepSeek 十样本 | 35/350 | **0/282** |

dev 与 tool_ho 的 N 误报在 0–2/350 之间。

结论：
- 4B 与 DeepSeek 在 tpl_ho N 上的误报**全部**来自这两条歧义模板；
- 0.6B / 1.7B 剩下的误报（103、36）是真实的"否定、豁免句泛化不足"；
- 上一轮"训练模型普遍过拟合 N 措辞"的说法对 4B 不成立，予以撤回。

注意：这个门槛是看过结果之后才制定的，所以剔除后的数字**只能作为事后敏感性分析**，不能改写冻结主表。

**(b) 保守规划器下限**

一个不看约束的规划器（每阶段选本地且最便宜的工具，并插入全部可选步骤），在 v4 受约束记录上：

| | dev | tpl_ho | tool_ho |
| --- | ---: | ---: | ---: |
| safe_success | 0.673 | 0.634 | 0.614 |
| faithful_success | 0 | 0 | 0 |

所以 safe_success 可以被保守策略刷高，faithful 不能。这一点正是 faithful 必须作为主指标的依据。

**(c) E2 中的 N 记录**

在同一 E2 输出（`outputs/e2_v4/verified-one-edit-full-holdouts-v1/results.json`）中，局部修复只在 23/350（tpl_ho）和 24/350（tool_ho）条 N 记录上保持了默认计划；只编辑默认计划的臂为 257/350 和 349/350。

也就是说，+33pp 的收益**只在受约束题上**；神经规划器会大量改动无约束任务。这一点必须写进论文。

**(d) 强模型十样本的调用量**

DeepSeek 十样本 3,000 次请求的平均输入为 8,739 token，其中 8,539 被缓存，平均输出 92 token。本地编译器的输入约 725 token（`reports/compiler_efficiency_v1.md`）。这里只能比较 token 量，**没有实测价目**，不写"更便宜多少钱"。

---

## 2. 三个创新点：保留 / 改写 / 删除

### 2.1 决策表

| 项 | 决策 | 理由（文献与证据） | 论文里的新表述 |
| --- | --- | --- | --- |
| ① 训练式可审计逐请求约束编译器 | **改写** | ① 的各个组件都已有先例：用 LLM 把请求转成目标与 evidence span [C1][C2]；从可信 prompt 合成可执行策略 [C5]；编译书面 policy，且本机 26B 不显著劣于前沿编译 [C6]；显式/隐式二分 [C9]。DeepSeek 十样本在留出集上不输于训练臂【已定】，所以"优于强模型"不成立，"本机部署"本身也已被 [C6] 覆盖。仍可守的是：**逐请求、类型化、参数化**的约束记录，由**专门训练的小模型**产出，并在执行层验收。[C1][C2] 解析的是 operation/goal，授权与隐私留给应用 [C3]；[C6][C7] 以书面 policy 存在为前提。 | "A compact trained compiler that emits typed, parameterized, evidence-bearing constraint records per request; at matched faithful execution it uses an order of magnitude fewer input tokens than ten-shot prompting." 胜负按 §6.3 的 H2 非劣效检验判，不写"优于"。 |
| ② 约束锚定的 GRPO 信用分配 | **删除**（作为算法贡献） | 三种子净变化 +1/−3/−6【已定】，不成立。相关机制已被占据：锚门控 [R1][R2]、逐动作可验证罚 [R3]、标准化与加权的耦合 [R6]、DAG 拓扑信用 [R7]、计数奖励坍塌 [R8]。 | 写进附录作为负结果，并报告"同一 query 常数罚被组内中心化抵消"的诊断。 |
| ②′ 约束解释 vs 候选搜索的交叉干预诊断 | **改写后保留**（分析型贡献） | 有直接证据：+33.0pp、2×2 交叉【已定】。邻近工作做的是执行验证器重排 [X1]、邻居枚举式语义评测 [X2]、唯一可修复参数的修复 [X3]、工作流补救 [X6]，都**没有**把"编译器 × 候选生成器"交叉替换来区分两类失败。缺陷要如实报告：符号求解器 1,149 与修复 1,144 持平；修复在 N 记录上大量改动默认计划（§1.2c）。 | "We separate interpretation failures from search failures by crossing compilers and candidate generators over an enumerable edit space with an oracle-reachable upper bound." |
| ③ E/I/N 可执行配对基准 | **保留并加强** | LogiSafetyBench 自称首个隐式合规工具评测 [B1]，但它的隐式来自系统提示中的法规全文 [B3]，且自认无法处理参数级约束 [B2]。AM-Bench 的缺失档不陈述约束 [B4]，评测仍按完整约束判 [B5]，所以缺失档的 gold 无法从输入恢复。ExecutionFirst 改变的是执行细节显式度 [B6]。LIFT 的约束全部显式 [B7]。"让参考解违反约束"的构造有先例 [B8]，结构 OOD 也有先例 [O1][O2][O3]。可守的组合是：参数级约束 + 请求内可恢复的隐式线索 + 带歧义门槛的 N 近似对照 + 逐条必要的咬合 + 训练集 + faithful 执行刻度与保守下限 + 结构不相交的 OOD。 | 不写"首个"。写"to our knowledge, within the verified corpus (Appendix A) no benchmark combines…"。 |
| 新增（并入③）：N 近似对照与误拦测量 | **新增** | 误拦/过度拒绝已被确认为真实失败模式：[N3] 过度拒绝良性请求；[N4] DPO 后 8% 过度拒绝；[X4] 误报使 agent 重试合法调用；[N1] 正例沿线索迁移而非沿标签迁移；[N2] 有专门的"否定/条件逻辑"错误类别。但读过的论文中，没有在 E/I/N 最小三元组里用近似否定句测"约束编译器误报 → 计划被无谓改动"的执行后果（**组合层面的空白，无原文支撑"无人做过"**）。§1.2a 已显示这能区分模型（4B 0/282，1.7B 36/282，0.6B 103/282）。 | 作为③的一个测量维度报告，按子类型（waiver / revoked / other_party / permission）分列。 |
| 新增（并入③）：faithful 主指标 + 保守下限 | **新增** | 联合指标 J=T×S 是已有做法 [B5]，但 §1.2b 证明不看约束的保守规划器能拿到 0.61–0.67 的 safe_success。faithful（安全且改动数等于金标最小计划）把它压到 0。 | 主表一律报 faithful；safe 作为辅助指标，并附保守下限。 |

### 2.2 为什么不另起一个新的独立创新点

对照文献，唯一同时满足"现有数据能支撑"和"一次重跑可以加强"的空白，是 N 近似对照的误拦测量（上表倒数第二行）。它和 ③ 共用同一套数据与执行刻度，单独成为第四个贡献会显得单薄，所以并入 ③。②′ 作为分析型贡献，比继续投入 GRPO 更可守：后者需要新机制、多种子、同预算的正向结果，而 [R1]–[R8] 已经覆盖了主要设计空间。

---

## 3. 五个具体缺陷与修法

### 3.1 N 版 49 条公共误判

**诊断**：§1.2a。歧义来自"他方规则 + 缺少不适用条款"的模板写法，不是模型能力问题。

**修法（v5 已实现）**：
- `src/dataset_v5_spec.py` 的 `NEAR_MISS` 改为 4 个子类型 × 2 条 = 每类每池 8 条（v4 为 4 条）。
- 每条模板都要通过两道词法门槛：
  - **G1**：提到他方（another/other/partner/separate/different/archive…）时，必须含"不适用于本任务"的条款（does not apply/cover、not on this…、not ours、has no such…）；
  - **G2**：必须锚定本任务（this task/engagement/request/…、here、ours），并带豁免、否定或许可标记。
- 策略卡写明："rules that belong to another team, lane or project and are said not to apply here, do not count"。

**可验证判据**：
1. V10 规范层 G1/G2 全过，子类型覆盖每类每池至少 2 条，数据层的子类型标签与模板一致（已通过）。
2. **外部有效性门槛（预注册 H4）**：v5 上 DeepSeek 十样本在每个 N 子类型的误报率 ≤ 5%。不满足的子类型**标为歧义并单列报告，但不从主表删除**。
3. 指标口径：主表报 N 误报率（按子类型）与 N faithful（不偏离默认计划）。v4 冻结主表不改，只在附录给"剔除 G1 失败模板"的敏感性分析（§1.2a）。

### 3.2 tool_ho 只是名称级 held-out

**修法（v5 已实现）**：
- 保留 `test_tool_ho`，并明确改名为"名称级 held-out"。验证器 V12 主动检查它的结构签名与 train 世界相同；如果不同，反而会报错。
- 新增 `test_struct_ho`（350 组 / 1,050 条）。它有 6 个阶段（train 为 3–5）、单阶段 4 路备选（train 为 3）、3 步 finish 块（train 为 2，规划器因此要在 6 个排列中选择）、锚定在 finish 步上的审批对（train 没有），时长分布右移，工具名与 train/heldout 两个世界都不重叠（V7）。措辞使用 train 池，只改变结构。
- 文献依据：按结构族划分 OOD [O1]、无结构对应物的迁移组 [O2]、不共享名称/参数/实体类型的未见域 [O3]；后者也发现效率能迁移而行为纪律只部分迁移 [O4]。

**可验证判据**：
- V12：struct 每组的签名 `(6,3,4,True)` 不在 train 可能签名集合 `{(3|4|5,2,3,False)}` 内（已通过：350/350）。
- 预注册 H3：同一臂在 tool_ho 与 struct 上的 faithful 下降，95% CI 上界 ≤ 5pp 判为"迁移"，下界 ≥ 10pp 判为"不迁移"，其余为"无定论"。

### 3.3 策略卡泄漏 PII 字段别名

**修法（v5 已实现）**：
- 策略卡只给数据类定义（"any field that identifies an individual customer"等），不列任何字段别名。
- V11 检查两点：卡内不含任何池的别名；test 池别名只出现在 tpl_ho 的输入中（已通过）。

**影响**：tpl_ho 上 privacy 的 d2/d3 题从"查表"变回"把未见字段名归入数据类"的推断。它会降低模型分数，这本身就是要测的东西。v4 已有一个小诊断：在 1.7B 上移除卡片示例后，89 题中隐私参数恢复为 88/89 对 88/89【已定，见 `reports/v4_results_and_claims.md`】。

### 3.4 单 seed 方差

**定口径（预注册）**：
- 训练臂统一 3 个种子（42、43、44），报告逐种子值、均值和样本标准差。
- 臂间差值用**层次 bootstrap**：按任务组重采样，同组 E/I 一起；每次重采样内先对训练臂的各种子取平均，再与对照臂相减；10,000 次，固定种子 20261124（`src/analyze_v5_main.py`）。
- 主张"差异"需要 95% CI 不含 0，并且三个种子方向一致。

**依据**：同类工作用 3 个训练种子报告 RL 结果 [S1]；也有工作明确说明自己的区间只覆盖任务采样 [S2]；单次运行被作者列为局限 [S7]。

### 3.5 强模型十样本在留出集上不输

**改主张**：不比"谁更强"，改为非劣效加成本。

- **H2 非劣效**：训练臂减 DeepSeek 十样本的 faithful 差值，95% CI 下界大于 −3pp，判为非劣效。dev、tpl_ho、tool_ho、struct 分列，不合并成一个数。
- **成本轴**：只报实测量——每请求输入/输出 token（§1.2d）、同卡解码延迟与显存（`reports/compiler_efficiency_v1.md`：1.7B 37.38 ms/token、3.36 GiB；4B 48.75 ms/token、7.72 GiB）。
- **部署动机**：可信数据场景中，请求本身可能含敏感上下文。本机编译避免把请求外发，这与 CGAP 把隐私留给应用 [C3]、NOMOS 支持本机编译 [C6] 一致。这是动机，不是实验结论。
- **正面回答的实验**：如果 H2 在 struct 或 tpl_ho 上不成立，照实报告"训练小模型在 X 上劣于强模型 PE"，不改口径。

---

## 4. 数据集 v5 规格与验证门槛

### 4.1 规格

| 切分 | 组数 | 条数 | 工具世界 | 措辞池 | 测什么 |
| --- | ---: | ---: | --- | --- | --- |
| train | 4,000 | 12,000 | train | train | — |
| dev | 300 | 900 | train | train | 同分布 |
| test_tpl_ho | 350 | 1,050 | train | test（goal、背景、E/I/N 模板、PII 别名） | 措辞 OOD |
| test_tool_ho | 350 | 1,050 | heldout（名称级） | train | 名称 OOD |
| test_struct_ho | 350 | 1,050 | struct（结构不相交） | train | 结构 OOD |

【新数据】分布：
- 约束数 1/2/3 = 2,830/1,983/537；
- 隐式难度 d1/d2/d3 = 2,565/3,313/2,529；
- N 子类型 waiver/revoked/other_party/permission = 2,643/2,662/2,562/2,714；
- 干扰槽比例 0.406；生成失败 0；
- struct 的约束类型为 order 141、tool_auth 144、deadline 105、privacy 98、budget 93。

### 4.2 验证门槛（`src/verify_dataset_v5.py`，任一失败即 FAIL 并非零退出）

| 门槛 | 内容 | v5 结果 |
| --- | --- | --- |
| V1–V9 | 沿用 v4：schema、witness 执行、咬合、逐条必要（全量）、三元组与最小对、证据子串与指令词、跨 5 个切分两两零重叠、未见工具名不泄漏、相邻重复词、下游刻度 | PASS |
| V10 | N 模板 G1/G2；子类型覆盖；数据层子类型标签一致 | PASS |
| V11 | 策略卡无别名；test 别名只在 tpl_ho | PASS |
| V12 | struct 签名与 train 不相交；tool_ho 签名与 train 相同（如实标为名称级） | PASS（350/350） |
| V13 | order/tool_auth 的 E、I 模板先提哪个角色严格平衡 | PASS（E 4/4，I 3/3） |
| V14 | 保守规划器在受约束记录上的 faithful ≤ 0.05 | PASS（各切分为 0；safe 为 0.644–0.673，struct 0.554） |

### 4.3 生成与校验命令

```bash
python src/build_dataset_v5.py                      # 读 configs/dataset_v5.yaml，seed 42，写 data/processed_v5/
python src/verify_dataset_v5.py                     # V1–V14，全量必要性复核，约 25 秒
python tools/verify_quotes_v5.py                    # 本文引文核验
python -m pytest -q tests                           # 71 passed（本地）
```

### 4.4 哈希（LF，跨平台一致）

| 文件 | sha256 |
| --- | --- |
| train | `5334504af4397fe0acc087c87c04eb0789200b4a314be415792c28a142e3d413` |
| dev | `f614a32adc74ca7708a286c0f97e0d2befbd226cc696c2db5b2a34126600b24a` |
| test_tpl_ho | `40d891221b4411a4e7736588a78a3a3a90952c3e3180ef285d713a586b33f8f7` |
| test_tool_ho | `c5310f7859a06c22997a69edd62a59fb4ec1a4faf5cf8fd6f766ef02e97140e7` |
| test_struct_ho | `25f073cdcafef92d3318d8932f53ab1544929b5a58254f73cc245208c2460da3` |

Token 长度（Qwen3 tokenizer）：输入最长 909，输入加金标输出最长 1,154，都在 `max_seq_len` 1280 以内，0 条被截断；金标输出最长 259，在 384 以内。

---

## 5. 代码改动（本轮已完成，本地 71 个测试通过）

| 文件 | 改动 | v4 回归 |
| --- | --- | --- |
| `src/trust_env.py` | finish 块从"原序/反转"推广为全排列，改动数按逆序对计 | v4 全部 5,000 个 witness 重现，mismatch 0 |
| `src/eval_exec.py` | `e1_exec_v2`：新增 faithful_success（总体/受约束/分 variant + CI）和保守参考档；子集自动发现 struct | v4 三个训练臂主表逐格一致 |
| `src/run_e1.py` | `spec_version=v5` 的记录用 v5 策略卡（v4 记录的 prompt 字节不变，有单测）；评测子集自动发现 | 同上 |
| `src/rescore_v4_side.py` | 新增 `--data`，子集自动发现 | 默认仍为 v4 |
| `src/verify_dataset_v4.py` | `verify()` 参数化切分、未见角色组和可读名函数；默认参数即 v4 口径 | v4 全量重验 PASS |
| 新增 `src/dataset_v5_spec.py`、`build_dataset_v5.py`、`verify_dataset_v5.py` | §3–§4 | — |
| 新增 `src/run_pe_v5.py` | v5 强模型 PE（零/十样本），请求指纹缓存，输出 `outputs/e1_v5_side/` | — |
| 新增 `src/analyze_v5_main.py` | 预注册判定 H1–H4 与层次 bootstrap；用合成臂做过端到端自检 | — |
| 新增 `src/analyze_v4_nearmiss.py` | §1.2a–b 的只重算分析 | — |
| 新增 `scripts/run_e1_queue_v5.sh` | §8 的服务器队列 | — |
| 新增 `tests/test_dataset_v5.py` | 13 项，包括 v4 prompt 不变、struct 不相交、保守规划器拿不到 faithful、验证器能抓到篡改 | — |

---

## 6. 实验矩阵

### 6.1 主表（E1-v5，全部在冻结的 v5 数据上）

| 臂 | 模型 | 种子 / 次数 | 用途 |
| --- | --- | --- | --- |
| T | Qwen3-1.7B、4B LoRA（必做）；0.6B LoRA（完整版） | 42/43/44 | 主臂 |
| Z | 同底座零样本 | 1 次（贪心解码，确定性） | 训练增益 H1 |
| P1 | DeepSeek-v4-pro 十样本 | 1 次（temperature 0） | 非劣效对照 H2；N 门槛外部检验 H4 |
| P2/P3 | Qwen-Max 零样本 / 十样本 | 各 1 次 | 第二家强模型 |
| R | none / gold / 保守规划器 | 确定性 | 指标刻度与下限 |

指标逐列报告，不合并：
- **主指标**：受约束 faithful；
- 辅助：safe、N 误报（按子类型）、N faithful；
- 含证据的整条全对，以及证据片段召回（与执行分开报，见 4B 的 699 vs 552【已定】）；
- 严格/核心 F1 与解析率（只作诊断）；
- 每请求 token 与延迟。

### 6.2 对照与消融

| 编号 | 内容 | 回答的问题 | 代价 |
| --- | --- | --- | --- |
| A1 | 保守规划器下限 | faithful 能否被刷高 | CPU，已内置 |
| A2 | v4 → v5 同模型比较（仅描述，数据不同不做配对） | 修 N 与卡片之后的变化 | 只重算 |
| A3 | 卡片示例有/无（v4 已做 89 题诊断【已定】）；v5 默认无示例 | 别名泄漏的影响 | 已有 |
| A4 | N 子类型分列 | 误拦来自哪类否定 | 只重算 |
| A5 | E2 交叉干预在 struct 上复跑（沿用 v4 的 1.7B 规划器权重，只做推理） | ②′ 是否跨结构成立 | **可选**，GPU 时长未实测，需先用 20 组面板计时 |

### 6.3 预注册判胜条件（写在 `src/analyze_v5_main.py`，看结果前固定）

| 编号 | 假设 | 判定 |
| --- | --- | --- |
| H1 | 训练增益 | 训练臂（3 种子均值）减同底座零样本，层次 bootstrap 95% CI 下界 > 0，且三个种子方向一致 |
| H2 | 对 DeepSeek 十样本非劣效 | 95% CI 下界 > −3pp；按切分逐一判定 |
| H3 | 结构迁移 | tool_ho − struct 的下降：CI 上界 ≤ 5pp 为迁移，下界 ≥ 10pp 为不迁移，其余为无定论 |
| H4 | N 控制有效 | DeepSeek 十样本在每个 N 子类型、每个切分上的误报 ≤ 5%；不满足的子类型标为歧义并单列，不删数据 |
| H5 | 证据保真 | 不设胜负，只报含证据整条全对，并与 faithful 并列 |

### 6.4 统计口径

- 所有比较都在同一测试集上配对，以任务组为单位（同组 E/I 一起重采样）。
- 训练随机性用种子间标准差表示，**不能**用任务 bootstrap 代替。
- E2 沿用 v4 已有的 10k 次按切分分层 bootstrap【已定】。
- 多重比较：H1/H2 在 4 个切分 × 2 个尺寸上，主张"全部切分成立"时用 Holm 校正，其余按切分分别报告。
- 发散或 NaN 的运行单列计数，不静默剔除（`run_e1.py` 的 NaN 防护仍在）。

---

## 7. 最小重跑清单与 GPU 时长

估算依据是 v4 实测 `metrics.json` 里的 `train_seconds`（含零样本评测）：0.6B 2.59 h、1.7B 2.66 h、4B 3.98 h。v5 多出 struct 一个评测集，评测时间按 4/3 推算；非 42 种子跳过零样本评测。

| 类别 | 内容 | 预计 |
| --- | --- | --- |
| **必须重训** | 1.7B × seed 42/43/44 | 2.84 + 2 × 2.48 ≈ **7.8 GPU-h** |
| **必须重训** | 4B × seed 42/43/44 | 4.44 + 2 × 3.51 ≈ **11.5 GPU-h** |
| 推荐重训 | 0.6B × seed 42/43/44 | ≈ 7.6 GPU-h |
| 必须重跑（API） | DeepSeek 十样本、Qwen-Max 零样本/十样本 × 4,050 条评测 | 共 12,150 次调用，不占 GPU；DeepSeek 十样本按 §1.2d 约 3,500 万输入 token（大部分为缓存命中） |
| 只需重算（CPU） | v4 的 N 敏感性与保守下限（已完成）；v5 主表与 H1–H4（训练后运行 `analyze_v5_main.py`） | 分钟级 |
| 不重跑 | E2 v4 结果（作为 ②′ 主证据，已有两个顺序的复现）；GRPO（删除） | 0 |
| 可选 | A5：E2 在 struct 上复跑 | 未实测，先计时 |

- **最小重跑**：约 19.3 GPU-h。
- **完整重跑**：约 26.9 GPU-h。

以上都是按 v4 时长线性推算的估计，不是实测值。

---

## 8. 论文主张清单

### 8.1 可写（前提是相应实验跑出来）

- 训练式小编译器在同底座零样本上有显著的 faithful 增益（H1，3 种子）。
- 在 dev/tpl_ho 上对 DeepSeek 十样本非劣效（只有 H2 成立时才写），并且输入 token 少一个数量级、可本机运行（§1.2d，实测）。
- faithful 指标不可被保守规划器刷高，safe 可以（已证）。
- N 近似对照能区分模型的误拦，按子类型给出（§1.2a 为 v4 证据，v5 是预注册复测）。
- 交叉干预能把失败分成"候选空间内无解"和"有解未选中"两类，在固定候选空间里 +33.0pp【已定】；同时报告符号求解器持平和 N 上的过度改动。
- 结构 OOD 的结论按 H3 的三种判定原样写。

### 8.2 禁写

- "首个隐式约束 / 隐式合规工具基准"（[B1] 已这样自称）、"首次约束编译""首次 scope 绑定"。
- "训练小模型优于强模型"（与【已定】矛盾）；任何以美元计的成本优势（未测价目）。
- "GRPO 信用分配有效 / 抗 reward hacking"（三种子 +1/−3/−6）。
- 把 tool_ho 写成结构泛化；把 v4 剔除歧义模板后的数字写进主表。
- 用解析 F1 或 safe_success 代替 faithful 作为执行级主指标；把执行成功说成证据保真。
- "人类可以恢复全部隐式约束"（独立盲审尚未完成）。
- 使用中期报告的任何实验数字。

---

## 9. 服务器启动清单（供直接执行）

**前提**：
- 不触碰正在运行的 4B seed43 评测（`/root/ConsDagQAQ`），也不在该目录 pull；
- v5 使用**新目录** `/root/ConsDagV5`；
- 队列脚本会等同机所有 `src/run_e1.py` 进程结束后才开始训练。

### 9.1 本地（由你执行推送）

```bash
cd <本地仓库>
python -m pytest -q tests && python src/verify_dataset_v5.py >/dev/null && python tools/verify_quotes_v5.py >/dev/null
git push origin main          # 本轮只做了本地提交；GitHub 同步由你决定何时推
```

### 9.2 服务器：新目录同步与校验

```bash
cd /root
source /etc/network_turbo
for i in 1 2 3 4 5 6; do rm -rf ConsDagV5; git clone --depth 1 --filter=blob:none --no-checkout https://github.com/shavyn195/ConsDagQAQ.git ConsDagV5 && break; sleep 10; done
cd ConsDagV5
git sparse-checkout set --no-cone '/src/' '/tests/' '/scripts/' '/configs/' '/tools/' '/data/processed_v5/' '/.gitignore'
for i in 1 2 3 4 5; do git checkout main && break; sleep 10; done
git log --oneline -1                                   # 记录提交号
ln -sfn /root/consdag/models models
PY=/root/miniconda3/bin/python
$PY src/build_dataset_v5.py > /tmp/gen_v5.json          # 服务器重新生成
$PY - <<'EOF'
import json, hashlib
want=json.load(open('data/processed_v5/generation_report.json'))['sha256']
got={s:hashlib.sha256(open(f'data/processed_v5/{s}.jsonl','rb').read()).hexdigest() for s in want}
print('SHA_MATCH' if got==want else ('SHA_MISMATCH', got))
EOF
git checkout -- data/processed_v5/generation_report.json   # 恢复已提交版本，供队列再校验
$PY src/verify_dataset_v5.py | tail -3                  # 期望 "verdict": "PASS"
```

### 9.3 服务器：启动队列（会自动等 4B seed43 结束）

```bash
cd /root/ConsDagV5
nohup bash scripts/run_e1_queue_v5.sh > outputs/e1_v5_queue_master.log 2>&1 &
# 只跑最小清单：
# PLAN="Qwen3-1.7B:32:42 Qwen3-4B:16:42 Qwen3-1.7B:32:43 Qwen3-4B:16:43 Qwen3-1.7B:32:44 Qwen3-4B:16:44" nohup bash scripts/run_e1_queue_v5.sh > outputs/e1_v5_queue_master.log 2>&1 &
```

### 9.4 运行中只读检查

```bash
cat outputs/e1_v5_queue_manifest.jsonl
grep optimizer_step outputs/e1/Qwen3-1.7B-v5-seed42.log | tail -3
ls outputs/e1/*-v5-seed*/training_failure.json 2>/dev/null   # 应为空
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader
```

### 9.5 PE 臂（有 `DASHSCOPE_API_KEY` 的机器上执行，不占 GPU）

```bash
python src/run_pe_v5.py --model deepseek-v4-pro-0813 --style few
python src/run_pe_v5.py --model qwen-max --style zero
python src/run_pe_v5.py --model qwen-max --style few
```

### 9.6 全部完成后

```bash
python src/analyze_v5_main.py          # 写 outputs/v5_analysis/main.json，打印 H1–H4 判定
```

---

## 附录 A：本文引文（51 条，`tools/verify_quotes_v5.py` 逐条回原文定位）

| ID | 论文 | fulltext 路径 | 行号 | 原文 |
| --- | --- | --- | --- | --- |
| C1 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L23 | "uses an LLM to turn the request into goals," |
| C2 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L425-426 | "evidence spans ϵi in the user’s messages" |
| C3 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L1030-1031 | "authorization, privacy, and the decision whether an action is appropriate remain the application’s job" |
| C4 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L1022-1023 | "CGAP uses 1.3–1.6 times the plain agent’s tokens per task with gpt-oss-20b" |
| C5 | Sapien | `literature/extracted/library/01_constraint_compiler/2610.00797_Sapien/2610.00797_Sapien_fulltext.txt` | L139-141 | "an automaton-based engine that synthesizes policies from trusted user prompts and enforces them over tool calls" |
| C6 | NOMOS | `literature/extracted/library/01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt` | L29-30 | "a 26B on-premise compilation is not significantly worse than hand-written or frontier-compiled rules." |
| C7 | NOMOS | `literature/extracted/library/01_constraint_compiler/2610.11030_NOMOS/2610.11030_NOMOS_fulltext.txt` | L2969 | "The system also presupposes that a written policy exists" |
| C8 | PolicyGuide | `literature/extracted/library/01_constraint_compiler/2608.19861_PolicyGuide/2608.19861_PolicyGuide_fulltext.txt` | L60-61 | "domain-specific fine-tuning is often unavailable or impractical" |
| C9 | ATLAS | `literature/extracted/library/01_constraint_compiler/2509.25586_ATLAS/2509.25586_ATLAS_fulltext.txt` | L167 | "explicitly stated or implied by 𝑄, such as budget limits" |
| C10 | BeyondReAct | `literature/extracted/library/00_base/2511.10037_BeyondReAct/2511.10037_BeyondReAct_fulltext.txt` | L413-414 | "we pair our Planner with GPT-4o as the executor." |
| C11 | LangNCO | `literature/extracted/library/01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt` | L342-343 | "do not verify semantic agreement with the natural-language requirement." |
| C12 | ConstraintsOfThought | `literature/extracted/library/01_constraint_compiler/2510.08992_ConstraintsOfThought/2510.08992_ConstraintsOfThought_fulltext.txt` | L774-775 | "Const-o-T depends on accurate constraint extraction; when LLMs misinterpret user input or produce incomplete symbolic constraints, the search may be guided toward suboptimal solutions." |
| R1 | TAG | `literature/extracted/library/02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt` | L32-33 | "then gates auxiliary credit on anchor satisfaction." |
| R2 | TAG | `literature/extracted/library/02_objective_factorization/2610.21404_TAG/2610.21404_TAG_fulltext.txt` | L514-515 | "Under GRPO no single weight is safe across a prompt population that contains hard prompts (small ρ)" |
| R3 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L500 | "Therefore: penalize commission, never omission." |
| R4 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L870-872 | "our penalties were manually identified based on domain rules. Automating the discovery of penalizable constraints directly from an environment’s affordances remains an open challenge." |
| R5 | RLVP | `literature/extracted/library/02_objective_factorization/2607.07435_RLVP/2607.07435_RLVP_fulltext.txt` | L441-442 | "This holds across five seeds at 4B and generalizes from 1.7B to 8B models" |
| R6 | ConstrainedGRPO | `literature/extracted/library/02_objective_factorization/2602.05863_ConstrainedGRPO/2602.05863_ConstrainedGRPO_fulltext.txt` | L35-37 | "scalarizing rewards before normalization introduces shared-denominator coupling, so that changing one multiplier alters not only the emphasis on its corresponding constraint" |
| R7 | DAGent | `literature/extracted/library/02_objective_factorization/2609.39154_DAGent/2609.39154_DAGent_fulltext.txt` | L516 | "The closure is a structural proxy for contribution rather than a causal attribution" |
| R8 | SiLR | `literature/extracted/library/06_web_supplement_20261121/2609.04629_SiLR/2609.04629_SiLR_fulltext.txt` | L862-864 | "With B concurrent violation branches, a count-based reward takes at most B+1 distinct values." |
| R9 | SOTERIA | `literature/extracted/library/02_objective_factorization/2611.17880_SOTERIA/2611.17880_SOTERIA_fulltext.txt` | L1012-1014 | "SOTERIA requires a set of formalized specifications as inputs, which are currently obtained through a semi-automated workflow that combines LLM-based auto-formalization with manual validation." |
| X1 | LEVER | `literature/supplement_execution_semantics/LEVER/LEVER.txt` | L21-24 | "we train verifiers to determine whether a program sampled from the LLMs is correct or not based on the natural language input, the program itself and its execution results." |
| X2 | DistilledTestSuites | `literature/supplement_execution_semantics/Distilled-test-suites/Distilled-test-suites.txt` | L149-150 | "neighbor queries (Section 3.1), which are generated by modifying one aspect of the gold query." |
| X3 | SCA | `literature/extracted/library/01_constraint_compiler/2610.25552_SCA/2610.25552_SCA_fulltext.txt` | L1111-1113 | "they cannot detect omissions, where the agent never makes a necessary call." |
| X4 | SCA | `literature/extracted/library/01_constraint_compiler/2610.25552_SCA/2610.25552_SCA_fulltext.txt` | L720-721 | "since a false alarm makes an agent retry a valid call." |
| X5 | CGAP | `literature/extracted/library/01_constraint_compiler/2610.41040_CGAP/2610.41040_CGAP_fulltext.txt` | L810-812 | "Confidence intervals use 10,000 task-level bootstrap resamples, paired by task for differences between methods" |
| X6 | PolicyGuide | `literature/extracted/library/01_constraint_compiler/2608.19861_PolicyGuide/2608.19861_PolicyGuide_fulltext.txt` | L28-30 | "POLICYGUIDE instead compiles each domain policy into a workflow graph and invokes a proactive verifier at user-turn boundaries." |
| B1 | LogiSafetyBench | `literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt` | L626-628 | "the first evaluation suite designed to rigorously measure implicit regulatory compliance in LLM tool calling." |
| B2 | LogiSafetyBench | `literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt` | L1298-1300 | "limiting our ability to analyze the safety of specific function arguments (e.g., verifying that a transfer amount is within a safe limit" |
| B3 | LogiSafetyBench | `literature/extracted/library/06_web_supplement_20261121/2601.08196_LogiSafetyBench/2601.08196_LogiSafetyBench_fulltext.txt` | L741-745 | "the LLM is initialized with a system prompt containing the Tool Schema (Dapi), the Raw Regulatory Document (Ptxt), and the User Instruction (I) where explicit safety requirements are removed." |
| B4 | AM-Bench | `literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt` | L215-217 | "KM: Relevant restrictions or authorization requirements are unstated." |
| B5 | AM-Bench | `literature/extracted/library/03_paired_benchmark/2610.18090_AM-Bench/2610.18090_AM-Bench_fulltext.txt` | L242-243 | "S checks the same fully specified task constraints across conditions, including undisclosed requirements." |
| B6 | ExecutionFirst | `literature/extracted/library/03_paired_benchmark/2607.29175_ExecutionFirst/2607.29175_ExecutionFirst_fulltext.txt` | L523-525 | "The Basic task explicitly specifies the operational intent and required entities, the Intermediate task omits some execution details that must be inferred from context" |
| B7 | LIFT | `literature/extracted/library/03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt` | L302 | "holding topic, outline, and constraint content fixed" |
| B8 | LangNCO | `literature/extracted/library/01_constraint_compiler/2610.23190_LangNCO/2610.23190_LangNCO_fulltext.txt` | L607-608 | "selecting its targets so that the original high-quality solution violates the new requirement." |
| B9 | ImplicitIntelligence | `literature/extracted/library/01_constraint_compiler/2602.20424_ImplicitIntelligence/2602.20424_ImplicitIntelligence_fulltext.txt` | L40-41 | "the capacity to identify, reason about, and satisfy requirements users expect but never explicitly state" |
| O1 | NormWorldsCF | `literature/extracted/library/03_paired_benchmark/2607.03957_NormWorldsCF/2607.03957_NormWorldsCF_fulltext.txt` | L365-367 | "OOD uses held-out structural family types (e.g., priority chains and distractor-conflict variants), not merely new roots of the same type mix." |
| O2 | AgentLTL | `literature/extracted/library/02_objective_factorization/2607.02599_AgentLTL/2607.02599_AgentLTL_fulltext.txt` | L668-669 | "no-coverage (no structural counterpart in training)." |
| O3 | EffectWorld | `literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt` | L485-486 | "None of them shares a name, an argument or an entity type with the workspace tools, and no commerce trajectory is used in training." |
| O4 | EffectWorld | `literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt` | L38-39 | "Efficiency transfers to unseen tools out of the box; effect discipline does so only partly" |
| N1 | EffectWorld | `literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt` | L87-88 | "Positives transfer along their cue rather than their label" |
| N2 | ANCHOR | `literature/extracted/library/03_paired_benchmark/2610.16859_ANCHOR/2610.16859_ANCHOR_fulltext.txt` | L4056 | "Negation or conditional logic error -- misread "do not X" or "only if Y then X" type instructions" |
| N3 | MOSAIC | `literature/extracted/library/03_paired_benchmark/2603.03205_MOSAIC/2603.03205_MOSAIC_fulltext.txt` | L79 | "over-refuse benign requests when safety is treated implicitly." |
| N4 | ToolRLA | `literature/extracted/library/02_objective_factorization/2603.01620_ToolRLA/2603.01620_ToolRLA_fulltext.txt` | L527-528 | "Initial DPO produced 8% over-refusal" |
| S1 | DAGent | `literature/extracted/library/02_objective_factorization/2609.39154_DAGent/2609.39154_DAGent_fulltext.txt` | L2950-2951 | "the RL rows are means across three independent training seeds." |
| S2 | EffectWorld | `literature/extracted/library/03_paired_benchmark/2610.35981_EffectWorld/2610.35981_EffectWorld_fulltext.txt` | L1783 | "The intervals in Tables 12 and 13 measure task sampling only." |
| S3 | LIFT | `literature/extracted/library/03_paired_benchmark/2610.28819_LIFT/2610.28819_LIFT_fulltext.txt` | L316 | "We evaluate 17 models on the 10 released splits." |
| S4 | ToolPrivacyBench | `literature/extracted/library/06_web_supplement_20261121/2606.28061_ToolPrivacyBench/2606.28061_ToolPrivacyBench_fulltext.txt` | L1437-1439 | "This is a sampled reliability study and does not imply that the full benchmark was independently re-annotated." |
| S5 | PRefine | `literature/extracted/library/01_constraint_compiler/2604.17886_PRefine/2604.17886_PRefine_fulltext.txt` | L484-486 | "Human validation of the cost and party-size preferences yielded 89.7% and 97.4% agreement (Fleiss’ κ = 0.701 and 0.880; 19 annotators)" |
| S6 | ANCHOR | `literature/extracted/library/03_paired_benchmark/2610.16859_ANCHOR/2610.16859_ANCHOR_fulltext.txt` | L752-753 | "Gwet’s AC1 ranges from 0.91 to 0.97." |
| S7 | STAIF | `literature/extracted/library/02_objective_factorization/2607.22649_STAIF/2607.22649_STAIF_fulltext.txt` | L1362-1363 | "Testing results in Section 6 are based on single-run." |

正文直接引用 37 条；其余 14 条（B9、C4、C8、C10–C12、R4、R5、R9、S3–S6、X5）是写作相关工作和统计口径时的备用原文，同样经过定位核验，正文没有逐条标注。
