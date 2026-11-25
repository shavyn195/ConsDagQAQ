# v6 队列恢复与 E2 接力记录

日期：2026-11-25（北京时间）。本记录只覆盖远端队列状态恢复，不更改 v6 已封存的代码、配置或数据。

## 12:12 CST 初始快照

- 12:12 CST 只读快照：公开输入 E2 在 `/root/ConsDagSubmissionReview` 运行，PID 204883，已到 8,100/9,000 optimizer steps；82 条 loss 记录全部有限，最新 loss 为 0.0000121。未见 NaN、OOM 或异常退出标志。
- RTX 4080 SUPER 32GB 利用率 51%，显存 21,214/32,760 MiB。E2 仍占用 GPU；本轮没有中断、并行启动或抢占 GPU 作业。
- 恢复监督进程 PID 189623 是 E2 的父进程，已在持有 GPU 锁的同一流程中执行公开输入对照；E2 子进程退出后会继续进入 v6 队列。

## 发现并修复的接力阻塞

v6 原队列账本因 `ValueError: Release file inventory differs from the locally sealed inventory` 标记为 `failed`，但没有活动任务预留。该失败发生在队列完整性检查，不能当作训练失败，也不能直接忽略。恢复前重新执行了隔离发布目录的封存校验：155 个文件均与封存清单匹配，封存 SHA-256 为 `7711bfe8cf6345310ffe8c61ca58fe1ea4f12cf601382cfda1795304d19204fa`。

还重新验证了已完成的 Qwen3-1.7B seed42 和 seed43 产物：两者的 provenance 指纹、预测覆盖、指标、适配器和完成标记均通过 `validate_artifacts`。seed42 校验 14 个产物文件，seed43 校验 9 个。原失败时累计 GPU 预算使用量为 19,899.383 秒；30 小时总预算为 108,000 秒，剩余 88,100.617 秒。

在保留原账本完整快照并先追加审计记录后，只把队列状态从 `failed` 恢复为 `ready`，累计预算和 `last_job` 均未改变，活动预留仍为空。服务器审计原件已回收到 [账本原始快照](../outputs/submission/followup_20261125/server_audit_20261125/v6_queue_state_before_manual_resume.json) 与 [恢复审计记录](../outputs/submission/followup_20261125/server_audit_20261125/v6_queue_manual_resume.jsonl)。未改动封存文件、训练代码、E2 文件或 GPU 上的进程。

## 接下来

在这一历史检查点，E2 尚未完成，现阶段没有最终 E2 指标。PID 189623 在 E2 退出后应启动隔离根目录的 `run_v6_relay.py`；队列从 1.7B seed44 接续，并验证已有 seed42/43 后再跳过它们。下一次检查需要确认 E2 是否完成、监督进程是否已启动 `run_v6_relay.py`，以及新训练日志是否有限且向前推进。若进程或账本与上述条件不符，先保全日志并停止自动追加实验，不声称队列已接力。

## 2026-11-25 13:07 CST 后续状态

完整公开输入 E2 已结束，配对结果和逐条独立复算见 `reports/e2_public_contract_readout_20261125.md`。恢复监督进程已继续启动隔离发布目录的 v6 relay，没有并行创建新训练。

13:07 CST 只读快照：RTX 4080 SUPER 利用率 63%、显存 17,420/32,760 MiB；既有 v6 队列 PID 208814/208832 运行 Qwen3-1.7B seed44，训练日志到 2,200/9,000 optimizer steps，最近 loss `8.97858444659505e-06`，队列状态为 `running`，活动预算预留 88,100.617 秒。没有向运行进程发信号、修改队列账本或启动其他 GPU 工作。

13:26 CST 再次只读检查：同一 v6 seed44 进程继续运行，日志到 3,600/9,000，最近记录 loss `3.1263273285730975e-06`；RTX 4080 SUPER 利用率 67%、显存 17,420/32,760 MiB，queue 状态仍为 `running`。本次检查没有启动、停止或抢占作业。

13:37 CST 只读检查：队列仍为 `running`，同一 seed44 作业推进到 4,400/9,000；日志中已观察到的 45 条 loss 均有限，最新值 `1.6764878409958328e-06`。RTX 4080 SUPER 利用率 65%、显存 17,420/32,760 MiB。metrics 和 completion 标记尚未出现；本次只查看状态，没有触碰训练或队列。快照记录在 `outputs/submission/followup_20261125/server_snapshot_continuation.json`。
