#!/usr/bin/env bash
# One pass over the frozen v4 queue. Does not start or stop any training.
set -eu
cd "$(dirname "$0")/.."
out=outputs/e1_v4_side
manifest=outputs/e1_v4_queue_manifest.jsonl
mkdir -p "$out"
exec 9>"$out/postscore.lock"
flock -n 9 || exit 0
for size in 0.6B 1.7B 4B; do
  model="Qwen3-$size"
  dir="outputs/e1/$model-v4"
  until test -s "$dir/metrics.json"; do
    if grep -Fq '"event":"queue_end"' "$manifest" ||
       grep -Eq "\"event\":\"(smoke_failed|failed)\",\"model\":\"Qwen3-${size/./\\.}\"" "$manifest"; then
      echo "No completed model: $model"; break
    fi
    sleep 60
  done
  test -s "$dir/metrics.json" || continue
  for pair in zero:zeroshot trained:trained; do
    result="$out/${pair%:*}-$size.json"
    test ! -e "$result" || continue
    temp=$(mktemp -d "$out/.score.XXXXXXXX")
    nice -n 10 /root/miniconda3/bin/python src/rescore_v4_side.py --pred "$dir/${pair#*:}_predictions" --out "$temp/result.json"
    mv "$temp/result.json" "$result"
    rmdir "$temp"
    echo "Scored $model ${pair%:*}"
  done
done
