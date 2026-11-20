"""S6 oracle 可恢复性准入检查（I 版恢复 + N 版空恢复；强模型 API）。

规格（手册 2.5）：
- I 版抽样：oracle 只读 query 恢复约束集；恢复集须覆盖金标（容忍措辞差异）且不含金标外新约束。
- N 版抽样：oracle 恢复必须为空集。
- 匹配判定：同 type + 关键参数一致（数字限额/角色绑定/数据类），语义匹配交给 LLM 判官（同 API）。
用法（key 到位后）：
  python src/oracle_check.py --base-url https://dashscope.aliyuncs.com/compatible-mode/v1 \
      --model qwen-max --api-key $KEY [--n-implicit 120 --n-none 60 --subset dev]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_e1 import load_jsonl  # noqa: E402

RECOVER_PROMPT = (
    "Read the following tool-planning task query. List every constraint the user is imposing "
    "on the task (spending caps, time limits, data-privacy restrictions, approval prerequisites, "
    "ordering requirements). If the query imposes no constraint, output an empty list.\n"
    'Output JSON only: {"constraints":[{"type":"budget|deadline|privacy|tool_auth|order",'
    '"description":"..."}],"reasoning":"one sentence"}\n\nQuery:\n{query}'
)

JUDGE_PROMPT = (
    "You are a strict judge. Given a recovered constraint and the gold constraints, decide "
    "whether the recovered constraint corresponds to one specific gold constraint (same type, "
    "same parameters up to wording) or is a new constraint not present in gold.\n"
    'Output JSON only: {"match_gold_index": <0-based index in gold list or -1>, "is_new": true|false}\n\n'
    "Recovered: {recovered}\n\nGold list: {gold}"
)


def call_api(client: Any, model: str, prompt: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=600,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            if attempt == max_retries - 1:
                raise
            wait = 2 ** (attempt + 1)
            print(json.dumps({"retry": attempt + 1, "error": str(exc)[:200], "wait_s": wait}))
            time.sleep(wait)
    return ""


def parse_json_block(text: str) -> Any:
    text = text.strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        text = match.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://dashscope.aliyuncs.com/compatible-mode/v1")
    parser.add_argument("--model", default="qwen-max")
    parser.add_argument("--api-key", default=os.environ.get("ORACLE_API_KEY", ""))
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "processed_v2")
    parser.add_argument("--subsets", nargs="+", default=["dev"])
    parser.add_argument("--n-implicit", type=int, default=120)
    parser.add_argument("--n-none", type=int, default=60)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=ROOT / "outputs" / "oracle_check.json")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("缺 API key：用 --api-key 或环境变量 ORACLE_API_KEY")

    from openai import OpenAI

    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    rng = random.Random(args.seed)

    implicit_rows, none_rows = [], []
    for subset in args.subsets:
        rows = load_jsonl(args.data_dir / f"{subset}.jsonl")
        implicit_rows += [r for r in rows if r["variant"] == "implicit"]
        none_rows += [r for r in rows if r["variant"] == "none"]
    implicit_sample = rng.sample(implicit_rows, min(args.n_implicit, len(implicit_rows)))
    none_sample = rng.sample(none_rows, min(args.n_none, len(none_rows)))

    stats = {"implicit": {"n": 0, "gold_recovered": 0, "gold_total": 0, "new_constraints": 0},
             "none": {"n": 0, "nonempty_recovery": 0}}
    details: list[dict[str, Any]] = []

    # I 版：oracle 恢复 -> 判官匹配
    for row in implicit_sample:
        raw = call_api(client, args.model, RECOVER_PROMPT.format(query=row["query"]))
        parsed = parse_json_block(raw)
        recovered = (parsed or {}).get("constraints", [])
        gold = row["gold"]["constraints"]
        matched_flags = [False] * len(gold)
        new_count = 0
        for rec in recovered:
            judge_raw = call_api(client, args.model, JUDGE_PROMPT.format(
                recovered=json.dumps(rec, ensure_ascii=False),
                gold=json.dumps(gold, ensure_ascii=False, default=str),
            ))
            verdict = parse_json_block(judge_raw) or {}
            idx = verdict.get("match_gold_index", -1)
            if isinstance(idx, int) and 0 <= idx < len(gold):
                matched_flags[idx] = True
            else:
                new_count += 1
        stats["implicit"]["n"] += 1
        stats["implicit"]["gold_recovered"] += sum(matched_flags)
        stats["implicit"]["gold_total"] += len(gold)
        stats["implicit"]["new_constraints"] += new_count
        details.append({"sample_id": row["sample_id"], "recovered": recovered,
                        "gold_count": len(gold), "matched": sum(matched_flags), "new": new_count})
        print(json.dumps({"sample_id": row["sample_id"], "matched": sum(matched_flags),
                          "gold": len(gold), "new": new_count}))

    # N 版：恢复须为空
    for row in none_sample:
        raw = call_api(client, args.model, RECOVER_PROMPT.format(query=row["query"]))
        parsed = parse_json_block(raw)
        recovered = (parsed or {}).get("constraints", [])
        stats["none"]["n"] += 1
        stats["none"]["nonempty_recovery"] += int(bool(recovered))
        details.append({"sample_id": row["sample_id"], "recovered": recovered})

    recover_rate = stats["implicit"]["gold_recovered"] / max(stats["implicit"]["gold_total"], 1)
    new_rate = stats["implicit"]["new_constraints"] / max(stats["implicit"]["gold_total"], 1)
    none_nonempty_rate = stats["none"]["nonempty_recovery"] / max(stats["none"]["n"], 1)
    report = {
        "oracle_model": args.model, "base_url": args.base_url, "seed": args.seed,
        "subsets": args.subsets, "stats": stats,
        "implicit_gold_recovery_rate": round(recover_rate, 4),
        "implicit_new_constraint_rate": round(new_rate, 4),
        "none_nonempty_recovery_rate": round(none_nonempty_rate, 4),
        # 准入判据（手册）：恢复率高、新增率低、N 版空恢复率高 -> 全量发布
        "verdict": "PASS" if (recover_rate >= 0.9 and new_rate <= 0.05 and none_nonempty_rate <= 0.1) else "FAIL",
        "details": details,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "details"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
