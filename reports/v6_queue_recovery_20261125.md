# v6 队列恢复与 E2 接力记录

日期：2026-11-25（北京时间）。本记录只覆盖远端队列状态恢复，不更改 v6 已封存的代码、配置或数据。

## 当前运行

- 12:12 CST 只读快照：公开输入 E2 在 `/root/ConsDagSubmissionReview` 运行，PID 204883，已到 8,100/9,000 optimizer steps；82 条 loss 记录全部有限，最新 loss 为 0.0000121。未见 NaN、OOM 或异常退出标志。
- RTX 4080 SUPER 32GB 利用率 51%，显存 21,214/32,760 MiB。E2 仍占用 GPU；本轮没有中断、并行启动或抢占 GPU 作业。
- 恢复监督进程 PID 189623 是 E2 的父进程，已在持有 GPU 锁的同一流程中执行公开输入对照；E2 子进程退出后会继续进入 v6 队列。

## 发现并修复的接力阻塞

v6 原队列账本因 `ValueError: Release file inventory differs from the locally sealed inventory` 标记为 `failed`，但没有活动任务预留。该失败发生在队列完整性检查，不能当作训练失败，也不能直接忽略。恢复前重新执行了隔离发布目录的封存校验：155 个文件均与封存清单匹配，封存 SHA-256 为 `7711bfe8cf6345310ffe8c61ca58fe1ea4f12cf601382cfda1795304d19204fa`。

还重新验证了已完成的 Qwen3-1.7B seed42 和 seed43 产物：两者的 provenance 指纹、预测覆盖、指标、适配器和完成标记均通过 `validate_artifacts`。seed42 校验 14 个产物文件，seed43 校验 9 个。原失败时累计 GPU 预算使用量为 19,899.383 秒；30 小时总预算为 108,000 秒，剩余 88,100.617 秒。

在保留原账本完整快照并先追加审计记录后，只把队列状态从 `failed` 恢复为 `ready`，累计预算和 `last_job` 均未改变，活动预留仍为空。服务器审计原件已回收到 [账本原始快照](../outputs/submission/followup_20261125/server_audit_20261125/v6_queue_state_before_manual_resume.json) 与 [恢复审计记录](../outputs/submission/followup_20261125/server_audit_20261125/v6_queue_manual_resume.jsonl)。未改动封存文件、训练代码、E2 文件或 GPU 上的进程。

## 接下来

E2 尚未完成，现阶段没有最终 E2 指标。PID 189623 在 E2 退出后应启动隔离根目录的 `run_v6_relay.py`；队列从 1.7B seed44 接续，并验证已有 seed42/43 后再跳过它们。下一次检查需要确认 E2 是否完成、监督进程是否已启动 `run_v6_relay.py`，以及新训练日志是否有限且向前推进。若进程或账本与上述条件不符，先保全日志并停止自动追加实验，不声称队列已接力。
