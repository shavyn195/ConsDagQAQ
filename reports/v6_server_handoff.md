# v6 服务器接力交付说明

本交付只准备代码，不连接服务器、不结束 v5 任务、不启动 GPU 实验。
当前训练的自然结束时间以服务器状态为准。

## 同步与启动

同步最终本地发布清单 `configs/v6_release_sha256.json` 列出的所有文件，保留其字节内容。
清单在本地代码、测试、设计完成后生成；**服务器不要重新生成清单**。
同步时不要改写 `data/processed_v5/`、`outputs/e1/`、`reports/v5_*`。
数据、源码、测试、队列计划及配置均须与此清单一致；额外源文件也会触发清单拒绝。

**当前 v5 仍在运行时，不要覆盖它可见的共享 `src/`。** 为了提前挂好接力器，
推荐从原仓库创建独立 worktree，再将发布包解到该目录。已有模型使用只读用途的目录链接，
不复制权重、不改原目录；接力器通过 GPU UUID 锁和进程检查等待旧训练自然结束。
例如（以下是供操作者执行的命令，本次未执行）：

```bash
git -C /root/ConsDagV5 worktree add --detach /root/ConsDagV6_release_20261124 HEAD
# 将 consdag_v6_release_20261124.zip 上传并解压到这个新 worktree，保留字节。
# 确认新 worktree 的 models 路径不存在后，再创建目录链接：
if [ ! -e /root/ConsDagV6_release_20261124/models ] && [ ! -L /root/ConsDagV6_release_20261124/models ]; then
  ln -s /root/ConsDagV5/models /root/ConsDagV6_release_20261124/models
fi
```

模型目录如果已经存在，不运行 `ln`，先核实已有模型；不删除任何目录。
不重新生成 release 清单。若使用独立 worktree，下方命令中的项目路径替换为
`/root/ConsDagV6_release_20261124`；若坚持使用原 `/root/ConsDagV5`，
应在旧任务完全结束后再覆盖共享源码。

在服务器持久会话中运行：

```bash
cd /root/ConsDagV5
mkdir -p outputs/e1_v6
nohup env PY=/root/miniconda3/bin/python PROJECT_ROOT=/root/ConsDagV5 \
  bash scripts/wait_and_run_v6.sh > outputs/e1_v6/relay_console.log 2>&1 < /dev/null &
```

默认每 30 秒轮询一次。启动前必须同时满足：GPU 显存占用低于 5 GiB、
选定 GPU 没有 compute 进程、系统中没有识别到的 Python 训练进程。
接力器连续两次确认空闲后，执行 `scripts/run_v6_queue.sh`。
它不会发送信号给已运行的 v5 进程。
GPU UUID 对应 `/tmp` 下唯一 `flock`，接力器、队列和训练子进程继承同一锁；
不同 checkout 的本接力器也不能同时运行。
任意外部启动器若不遵守该锁，仍须由使用者避免手工另开训练。

直接执行 `bash scripts/run_v6_queue.sh` 只适用于 GPU 已空闲时；忙碌则立即拒绝。
`PY`、`PROJECT_ROOT`、`CUDA_VISIBLE_DEVICES` 可通过环境指定。
`--budget-hours` 允许降低预算，不能超过 30；已存在状态的预算不能改变。
清单不含任何 SSH 凭据，脚本不读取或记录 `RC_PASS`。

## 固定计划与预算

`configs/v6_queue_plan.json` 固定完整顺序：

1. Qwen3-1.7B，seed 42、43、44。
2. Qwen3-4B，seed 42、43、44。
3. Qwen3-0.6B，seed 42、43、44。

全部使用 bf16、rank 16、alpha 32、dropout 0.05、lr 2e-4、epochs 3、
accum 4、max-seq 1280、max-new 384。仅 seed 42 计算同底座零样本。
没有任何短训练或缩小数据运行。
训练前按真实 tokenizer 检查所有数据的 token 覆盖；任何训练截断或目标长度超限都停队列。

30 小时累计预算从本队列的模型子进程启动起计算，包括零样本推理、token 检查、
训练、训练后评估及失败子进程用时；等待 v5 和 CPU 验证/哈希/汇总不计入。
每个子进程由独立 GNU `timeout --signal=KILL` 守住剩余额度，
即使 Python 调度父进程异常消失，看门狗仍然保留。
本调度器超时只杀自己创建的进程组，标记 `incomplete`，不启动下一项。
异常退出/OOM/NaN/校验失败同样停队列并保留证据。
异常监督进程遗留的活动预算在重启时按全部预留时长保守计费，自动重启不会取得新预算。

## 检查结果

- `outputs/e1_v6/queue_manifest.jsonl`：启动 UTC 时间、GPU 名称/UUID、等待状态、逐模型 seed 开始/完成/失败事件。
- `outputs/e1_v6/queue_state.json`：累计用时、活动预留、队列状态；必须保留，不能用删除它重置预算。
- `outputs/e1_v6/preflight_verification.json`：启动前的独立数据重验报告，写在输出目录，不改冻结数据报告。
- `outputs/e1_v6/_provenance/`：发布 SHA、模型权重 SHA、环境、GPU、计划快照。
- 每个 run：日志、`provenance.json`、`token_coverage.json`、adapter、预测、metrics，全部校验通过才写 `completion.json`；未完成写 `incomplete.json`。

仅完整且指纹一致的 run 可被跳过。已有但未完成或不一致的输出会阻止自动继续；
不会覆盖它们。全部计划完成后执行 `analyze_v6_main.py`；若预算先结束，已完成的 run 保留，
可单独 CPU 汇总，确认性均值仍要求同模型完整三 seed。

```bash
/root/miniconda3/bin/python src/analyze_v6_main.py
```

## PE 对照

在同一发布目录运行 `bash scripts/run_pe_v6.sh`。新请求只读取当前环境的
`DASHSCOPE_API_KEY`，不要把 key 写进脚本或发布包。
三臂依次为 DeepSeek 十示例、qwen-max 零样本、qwen-max 十示例，最后 CPU 汇总。
有效完整缓存无需 key，且不会重新请求；缺请求又缺 key 会立即报错。
缓存绑定完整请求/源码/数据/示例哈希并校验响应与 completion，损坏或来源不符时停止，
不拿旧 v5 请求充作 v6 结果。API 不占本地训练 GPU，可独立运行。

本地 CPU 测试覆盖固定 SHA 防篡改、GPU 门槛解析、预算终止、NaN 停止、
失败停止后续任务、验证失败零启动、逐 run manifest、重启预算保留、
以及实际 provenance/artifacts 被分析器接受且篡改后拒绝。
Windows 本地没有验证目标服务器 Linux `flock`、GNU `timeout` 与 NVIDIA 驱动的真实联动；
交付时没有声称任何 v6 GPU 结果。
