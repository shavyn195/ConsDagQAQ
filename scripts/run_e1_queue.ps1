# E1 实验队列：等待 0.6B 完成后自动接力 1.7B（4060 串行，避免显存争抢）
$ErrorActionPreference = "Stop"
$root = "d:\Proj\AAAKXSJKJ\all\consdag_constraint_compiler_exp"

# 1) 等 0.6B 的 metrics.json 出现（0.6B 流程完整结束的标志）
Write-Output "等待 Qwen3-0.6B E1 完成..."
while (-not (Test-Path "$root\outputs\e1\Qwen3-0.6B\metrics.json")) { Start-Sleep -Seconds 300 }

# 2) 等 1.7B 模型下载完整（主权重两个分片齐）
Write-Output "等待 Qwen3-1.7B 权重完整..."
$probe = @("model-00001-of-00002.safetensors", "model-00002-of-00002.safetensors", "model.safetensors.index.json")
while ($true) {
    $ok = $true
    foreach ($f in $probe) { if (-not (Test-Path "$root\models\Qwen3-1.7B\$f")) { $ok = $false } }
    if ($ok) { break }
    Start-Sleep -Seconds 60
}

# 3) 接力跑 1.7B（eval batch 调小以适配 8GB 显存）
Write-Output "启动 Qwen3-1.7B E1..."
Set-Location $root
python src/run_e1.py --model models/Qwen3-1.7B --eval-batch-size 8 2>&1 | Tee-Object -FilePath "outputs\e1_1.7b_run.log"
Write-Output "QUEUE DONE"
