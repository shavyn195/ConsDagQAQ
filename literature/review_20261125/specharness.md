# SpecHarness：独立编译器与记录审计已有近邻

核验日期：2026-11-25（北京时间）。状态：新下载16页全文，读过方法、实验、消融及Appendix A.1–A.2。
题名：Who Holds the Pen? Let Specifications, Not Agents, Sign Off。
作者：Haiqing Li、Xin Ma、Yinhao Wu、Wenliang Zhong、Feng Jiang、Thao M. Dang、Xiao Hu、Hehuan Ma、Yuzhi Guo、Junzhou Huang。
来源：[arXiv:2609.29921](https://arxiv.org/abs/2609.29921)，2026-09-24；未核实正式venue。
全文缓存：`cache/2609.29921.pdf`、`cache/2609.29921.txt`（不提交；抽取文本搜索需rg -a）。
PDF SHA-256：`d99614c4a91e3a44ae763bfa0d31dd7eedb434fbd88ff50aa3493813c3005457`。

## 机制重合

- 将代理可见规格编译成有来源的obligations，由独立证据资格和版本状态管理执行与完成许可。
- 编译器独立选择后冻结；主观或歧义要求保留为advisory/residual，而非伪造确定判定。
- 已有source-linked记录、独立编译阶段、编译器评测、执行级独立检查。
- 因而“首次独立评测编译器／首次审计约束记录／记录轴真空”均不能保留。
- 它研究运行时规格权威与完成宣告；我们的合成DAG检查器不构成同等真实运行时保证。

## 编译器评测（Appendix A.1，约1318–1502行）

- 七候选编译器使用相同可见输入、schema与解码设置。
- 任务不重叠的14条开发任务，65个source units，81个预先标注的directions。
- 按开发覆盖率选编译器，随后冻结；test官方检查和运行结果不参与选择。
- Table8：GPT-5.6 Sol覆盖77/81=95.1%，Valid Rec.97.6%；DeepSeek-V4覆盖65/81=80.2%，Valid Rec.93.5%。
- Coverage以标注方向为分母，Valid Rec./Accounted以提取记录为分母，UnitMap以source units为分母。
- 记录有效率不是完整语义准确率，不能把它和我们的strict F1直接相比。
- 未实现项需进入residual并保留审计；不能只在模型预测约束上计分而漏掉FN。

## 下游与消融

- SkillsBench87任务提取509方向，另有GuideBench1042任务。
- 官方测试在构造与选择之外保留，构造后对应审计分broad573/585与fine406/585。
- broad对应不是完整语义召回，不能拿接近98%代表所有金标可靠。
- 各臂获得同一个冻结验证器的只读访问；方法区别包括如何利用结果管理运行时状态。
- 主指标官方Pass；诊断gap之外另报raw-pass preservation，以揭示过度拒绝。
- Table5 full Pass85.1%、preservation96.8%；去blocking qualification后79.3%/90.3%。
- 单独减小gap不一定改善成功；方法可能更频繁拒绝本可通过的任务。
- 论文明确承认消融未在匹配轨迹／计算条件下单独隔离commitment机制（约1181–1185行）。

## ConsDAG还能研究什么

- 训练小模型完成语义编译，E/I/N配对及工具／结构留出，字段错误与训练seed诊断。
- 记录字段是否被消费者使用要明示；被忽略字段不影响faithful是构造事实。
- 具体错误规模、跨seed稳定性和更换组件后的影响才是需测量的结果。
- 不把上述组合未经全面检索就写成全球首次；不以形式有效替代语言金标有效性。
- E2输入公平性、E3同投影、N过约束及API消费者交叉实验仍必要，不能由引用取代。
