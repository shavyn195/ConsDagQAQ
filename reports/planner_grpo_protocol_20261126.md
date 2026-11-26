# 原请求/预测约束输入 × 规划器后训练的GRPO对照

2026-11-26。研究目标是在已有匹配SFT的基础上，实测GRPO及其与结构化约束输入的交互，不将标准GRPO当创新。真实场景保持可信数据空间；当前环境为阶段有序计划，不泛称通用并行DAG。

## 已锁定比较

| 因素 | SFT对照 | GRPO两臂 |
|---|---|---|
| 共同起点 | shared-planner-learning-v2 final | 完全同一adapter |
| 输入 | raw / raw+冻结预测契约 | raw / raw+同一预测契约 |
| train | 32完整新组96行 | 同96行、同基础顺序与seed42 |
| 监督 | 验证过的最少改动witness；N默认计划 | 金标验证faithful_success，包含最少改动与N保持 |
| 更新 | 每4样本一步，一轮24步 | 每8提示G4采样，每批复用2次，12批24步 |
| 评测 | 两模型×两输入×144行 | 同样真实重新生成576条 |
| 选择 | 最后一轮 | 最后固定24步 |

同更新数和train任务数不是同计算预算。SFT每臂96个目标，GRPO每臂384个采样、每样本反向2次；记录训练/采样/token/推理/缓存编译全部成本。上游缓存训练编译96次356.77秒是历史成本，依赖部署次数摊销，不能既忽略也重复算作本轮GPU时间。评测缓存调用费用按每条流水线归属单列。

## 实现审计

采用token级PPO clipped surrogate、completion长度均值后样本等权、组内人口标准差优势（epsilon1e-4）、k3 KL到冻结SFT参考。旧策略在每批采样到两次更新结束期间固定，不以current.detach伪装跨更新旧概率。参考为同一SFT parent，不能把禁用adapter后的原始基座当同一参考。reference切换后显式冻结，最终逐张量检查不变。

为排除sampling/log-prob不一致，temperature1、top_p1、top_k0，禁用dropout，计入EOS、排除EOS后padding、保留达到长度上限的样本并报告。首个更新前每批old/current最大概率比偏移阈值0.05，超出立即报错，不静默截断log ratio。双次更新验证clipping真的有可作用的策略偏移；非零KL在离开parent后产生。

固定lr1e-5、AdamW weight_decay.01、grad norm1、beta.04、clip.2；底座bf16、LoRA同parent rank16/alpha32/qkvo、非重入梯度检查点。SFT原lr2e-4/dropout.05，这些是不同训练算法配方的一部分；不是loss-only单变量实验。

服务器已有torch2.12.1+cu130/transformers5.23.0/peft0.22.0/accelerate1.16.0，无TRL和datasets；未在线改动健康任务的依赖。参考归档`outputs/planner_grpo_reference_20261126/grpo_trainer.py.txt`来自官方仓库，SHA及URL在source.json；核读3226—3342行旧策略、clipping、KL和归一化代码，采用原始grpo风格。此实现不是该官方完整trainer的复现。

## 判定与边界

主指标E/I faithful，另报safe、严格结构合法、N保持、每约束类型、1/2/3约束组；完整E/I/N为bootstrap单位。只在全部配对完成后算差异。对GRPO标量奖励恒定的组原样保留，不过滤成好看的训练集；不把N的高成功率混成E/I提升。

若raw/contract GRPO均无提升：先按奖励非零组、每类违反、KL和截断分析，不立即宣布GRPO无效或改换研究场景。若contract有正向交互：接着补匹配generic/PE对照、多seed和独立留出。逐项奖励、预算/拉格朗日、POLPO等先作为已有基线，改进要针对实际未解决的边界。当前matched-SFT的deadline35/38违反只是动机，不是新方法结论。

每臂训练1800秒、评测1200秒；整体6600秒；超时保留半成品、不缩臂或偷改token上限。实际启动、进度和完成结果以status/receipt/completion为准。
