# 投稿补充实验执行状态报告（2026-11-24）

执行依据：`reports/submission_plan_emnlp2027.md`（用户定稿，未做任何修改）。
授权：用户指令「这次破例，你来完成」，由助手本人执行方案 §4 补充实验清单。

## 1. 素材核查结论（只读）

方案「核心数字速查」中的数字与仓库/服务器素材逐项核对，全部对上：

| 方案数字 | 素材位置 | 核对结果 |
| --- | --- | --- |
| v5 主表 faithful（受约束） | `outputs/v5_analysis/main.json`、v5 各 run `metrics.json` | 一致 |
| 2×2：编译器救回 112/118 | `outputs/v5_analysis/` 2×2 协议产物 | 一致 |
| 2×2：规划器救回 47/138 | 同上 | 一致 |
| DeepSeek 行 1255/1292 | `outputs/e1_v4_side/deepseek-v4-pro-0813-few/` | 一致 |
| 符号规划器 1149/1400 | `symbolic_env` 复算 | 一致 |
| 裂缝 699/700 vs 552/700 | v5_analysis 裂缝诊断 | 一致 |

E1 回放管线自校验（口径可信度）：

- 用 DeepSeek 编译器预测回放符号规划器 + 检查器，精确复现 2×2 协议 p0_c1 = 1255/1400 = 0.8964；
- 用 0.6B 编译器预测回放，精确复现 safe = 1144/1400 = 0.8171；
- 说明 E1 回放口径与历史协议 100% 一致，网格数字可直接进论文。

## 2. E1 插拔网格（已完成，纯 CPU，零 GPU 成本）

面板：v4 tpl_ho + tool_ho 共 2100 条（1400 受约束 + 700 N），冻结缓存回放，编译器 4 轴 × 规划器 3 轴。
faithful 列为受约束行口径（faithful_constrained）；safe 列为全面板 safe_success；bootstrap 10000 次（seed 20261124，按 group 重采样）。

| 编译器 \ 规划器 | SFT-order42 | SFT-order44 | symbolic |
| --- | --- | --- | --- |
| 0.6B-SFT | 0.2514 / 0.8776 | 0.2607 / 0.9043 | 0.7893 / 0.8767 |
| 1.7B-SFT | 0.2657 / 0.8990 | 0.2786 / 0.9190 | 0.8836 / 0.9267 |
| 4B-SFT | 0.2793 / 0.9229 | 0.2886 / 0.9390 | 0.9786 / 0.9857 |
| prompted-compiler(skill-style, DeepSeek 10-shot) | 0.2814 / 0.9305 | 0.2950 / 0.9486 | 0.9950 / 0.9967 |

结论（支撑贡献 C2，不越已死主张红线）：

- 符号规划器行随编译器质量单调上升（0.7893 → 0.8836 → 0.9786 → 0.9950），且 DeepSeek 行超过 4B：编译输出接口可被任何消费者复用，「接口任何人可接」成立；
- SFT 规划器两行全线平坦在 0.25-0.30，与编译器质量无关；safe 0.88-0.95 而 faithful 0.25-0.30，差距即过编辑（0.6B 格 over_edited=792、under_edited=0），过编辑是下游瓶颈而非编译质量；
- 4B × symbolic 的 tool_ho 为 0.999，为当前架构上限参考。

产物：`outputs/submission/e1_grid/results.json`；脚本 `src/sub_e1_grid.py`、`scripts/submission/summarise_e1.py`。

## 3. GPU 排期与队列状态

服务器 `/root/ConsDagV5`（RTX 4080 SUPER 32GB）当前状态（2026-11-24 11:16 UTC）：

- v6 主表队列（PID 175052，`run_v6_relay.py --mode queue`）运行中：1.7B seed42 已完成（11072 GPU 秒），seed43 训练中；30h 预算已用 11072 秒，剩余约 96928 秒，不 kill、不干扰；
- 投稿接力队列已启动（PID 181081，`scripts/submission/run_submission_queue.sh`，nohup），正在等待 v6 队列结束 → GPU 显存 <2000MiB 后自动执行：
  1. E2 B1 单体对照（1.7B，同底座同数据同预算，预注册判定 mono ≥ pipe−1pp 且 CI 跨 0 ⇒ 架构主张死，约 8.5 GPU 时）；
  2. E3 A 系字段消融（0.6B seed42，顺序 A3 → A4 → A2 → A1，各约 2-3 GPU 时）；
- 推送方式：SFTP + SHA-256 双侧校验（服务器 git pull 不通），四个文件哈希已验证一致。

## 4. 已完成 / 阻塞 / 下一步

已完成：

- 方案落档 `reports/submission_plan_emnlp2027.md`；
- 素材只读核查（§1）；
- E1 网格 12 格 + 口径自校验（§2）；
- E2/E3 脚本编写、本地与服务器语法/参数冒烟通过；
- GPU 接力队列推送并启动（§3）。

阻塞：

- 无硬阻塞。E2/E3 结果需等 v6 主表队列让出 GPU（预计 v6 三种子完成后开始，v6 剩余预算约 27h，足够 seed43/seed44 收尾）。

下一步：

- v6 结束后接力队列自动跑 E2 → E3，日志落 `outputs/submission/queue_launch.log` 与各臂日志；
- 结果出来后：汇总 H 系列判定（E2 架构主张预注册判定、E3 四臂下游/记录轴对照），负结果如实报，五轴分列；
- 全部完成后回收服务器产物（SHA-256 校验），追加台账并 commit（push 由用户决定）。
