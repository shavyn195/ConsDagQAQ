# E2 informed 单体对照读数

日期：2026-11-25（北京时间）。远端结果文件：`outputs/submission/e2_monolithic_informed/metrics.json`。模型为 Qwen3-1.7B，LoRA，seed 42，bf16，12,000 条训练行；`elapsed_s=7792.5` 包含初始化、训练和评测，不能称纯训练时间。

| split | constrained faithful | safe success | planned | N faithful |
|---|---:|---:|---:|---:|
| dev | 0.8833 | 0.9567 | 0.9989 | 1.0000 |
| tpl_ho | 0.8300 | 0.9324 | 1.0000 | 0.7771 |
| tool_ho | 0.2814 | 0.5343 | 0.9010 | 1.0000 |
| struct_ho | 0.0586 | 0.3686 | 0.5667 | 0.9657 |

## 判读

- 这是输入信息对齐后的单体对照，不是旧版“单体看不到任务结构”的不公平对照。
- 该单体在 tool_ho 和尤其 struct_ho 明显退化；因此当前结果不支持“单体和分离架构等价”，也不支持单凭 E2 宣称分离架构已经胜出。需要和同协议编译器、同切分、同 seed 的结果以及 token/延迟成本一起做预注册的配对比较。
- `planned`、`safe_success`、`faithful`、`faithful_constrained` 和 N faithful 必须同时报告。struct_ho 的低 faithful 不是单一解析 F1 可以替代的结论。
- 该结果不能证明结构 OOD 的失败来自架构本身：它可能来自单体训练目标、提示长度、规划输出契约或优化方差。后续应以冻结的同输入、同预算、同消费者对照分析原因，不在测试集上调参。

本结果不改变已排队的 E3 消融，也不触发新的 GPU 训练；A3 已完成，A4 正在按既定队列运行。
