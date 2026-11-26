# 匹配训练的通用分解与PE内容对照

## 问题与固定因素

2026-11-26已完成的raw/contract匹配SFT出现正交互，但它不能单独排除“让规划器训练适应任意有用分析”这个解释。补generic和PE两个匹配训练控制，不改变已有raw/contract结果，不根据新旧胜负选任务。

两臂仍从shared-planner-learning-v2最终adapter起步，用matched-SFT的同32组96行、同verified witness/default目标、同顺序与seed42，分别24次更新。学习率2e-4、rank16/alpha32、dropout.05、qkvo、accum4、bf16、AdamW decay.01、max_seq2048均与已完成matched-SFT配置逐字段核对。改变的是第一阶段分析来源。预算属于独立硬上限，不被称为计算量匹配。

generic严格复用原fixed_planner.summary_messages；PE复用run_e1.chat_messages(public_row)。第一阶段使用原始4B、原compiler wrapper禁用adapter，与旧固定规划器对照一致；不使用共同规划器SFT权重代替第一阶段。192次新的train分析输出全部生成并保存，greedy/384token，截断和错误保持原样，不事后改写或只挑成功缓存。dev的generic/PE/SFT契约沿用同一次原始第一调用缓存。

## 新增六格评测

| 训练辅助输入 | 推理输入 | 新规划次数 |
|---|---|---:|
| generic | raw | 144 |
| generic | generic | 144 |
| generic | SFT预测契约 | 144 |
| PE | raw | 144 |
| PE | PE | 144 |
| PE | SFT预测契约 | 144 |

总864次真实规划。对应输入条件与已有raw/raw、contract/contract构成内容来源比较；三种训练规划器接收完全相同SFT契约的条件进一步区分训练差异与输入信息差异。每条dev循环轮换三个推理条件顺序，不选择效果更好的条件。主指标依然E/I合规且最少修改，另报safe/valid/N/每类型、多约束结果和完整调用成本。

同24更新不等token：generic更长且可能截断。旧第一阶段协议的质量局限如实报告；本次能检验“这些冻结实现下”的内容比较，不能宣称打败了所有通用分解或PE优化方法。已暴露dev、单seed仍为探索，后续独立复验不能省。

## 接力、成本和失败规则

新run仅在当前GRPO完整结束、completion签名匹配、GPU空闲且取得共同锁后启动；不抢占或更改运行中的GRPO。先检查冻结数据、模型/起点/编译器哈希、公开首阶段与所有cached-dev长度；生成train辅助输出后，检查两臂训练长度，再开始任何更新。不能声称生成前已知道实际辅助长度。

预算192次第一阶段调用不超过1800秒，每臂训练300秒、评测1200秒，总5400秒。参考历史generic/PE每144次约1600/800秒，96次合计约1600秒，近第一阶段上限；超时保留并报不完整，不删臂、压token或更换样本凑齐。预计整体约40—60分钟，取决于实际输出长度，不保证结束时刻。

不使用GRPO胜负触发本控制，依赖只用于GPU接力。最终checkpoint固定24步，不看dev选取。部署前本地相关测试、服务器真实tiny-Qwen3+LoRA继续训练检查必须通过。原raw/contract已保存运行代码不改写。
