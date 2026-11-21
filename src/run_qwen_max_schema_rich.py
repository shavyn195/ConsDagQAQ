"""Run the qwen-max E1 prompt with an explicit parameter schema.

This is a measurement-control arm for the original E1 prompt.  It keeps the
same rows, scorer, decoding settings, checkpointed JSONL files and request
handling as ``run_qwen_max_e1.py`` while making the parameter contract
observable to the API model.  It must be reported separately from the
original prompt arm.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_qwen_max_e1 as runner
from run_e1 import SUBSETS, load_jsonl


PARAMETER_SCHEMA = (
    "For each constraint, fill params using exactly these type-specific keys: "
    "budget={max_total_cost_cny:number}; "
    "deadline={max_duration_hours:number}; "
    "privacy={forbidden_recipients:string[],protected_data_classes:string[]}; "
    "tool_auth={approval_role:string,required_role:string}; "
    "order={before_role:string,after_role:string}, where before_role is the "
    "earlier role and after_role is the later role. "
    "Use values supported by the query, preserving numeric values and units. "
    "Use severity high for budget, deadline, and privacy; medium for tool_auth "
    "and order. scope must contain matching role:<name> values from Available "
    "role vocabulary: budget includes cost-incurring roles; deadline includes "
    "the terminal task role; privacy includes roles sending protected data to "
    "a forbidden recipient; tool_auth includes required_role; order includes "
    "both before_role and after_role. evidence_span must be a verbatim query "
    "span. state=explicit when directly stated, implicit when only conveyed by "
    "context, and none only when the query contains no constraint."
)


def schema_rich_messages(row: dict[str, object]) -> list[dict[str, str]]:
    prompt = (
        "You are a typed constraint compiler for tool-planning tasks in a trusted "
        "data space. Extract every explicit or clearly implied user constraint. "
        "For a query with no constraint, return query_state=none, abstain=false, "
        "and constraints=[]. Do not invent constraints unsupported by the query. "
        "Return exactly one compact JSON object and no explanation. Keep each "
        "description to at most 12 words so the complete object fits the output "
        "budget.\n"
        "Output schema:\n"
        "{\"query_state\":\"explicit|implicit|none\",\"abstain\":false,"
        "\"constraints\":[{\"type\":\"budget|deadline|privacy|tool_auth|order\","
        "\"description\":\"...\",\"evidence_span\":\"...\","
        "\"state\":\"explicit|implicit|none\",\"confidence\":0.0,"
        "\"severity\":\"high|medium|low\",\"scope\":[\"role:...\"],"
        "\"params\":{}}]}\n"
        + PARAMETER_SCHEMA
        + "\nAvailable role vocabulary: "
        + json.dumps(row["available_roles"], ensure_ascii=False)
        + "\nUser query: "
        + str(row["query"])
        + "\nJSON (compact, no markdown):"
    )
    return [
        {"role": "system", "content": "Output JSON only."},
        {"role": "user", "content": prompt},
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=runner.ROOT / "data" / "processed_v2")
    parser.add_argument("--out-dir", type=Path, default=runner.ROOT / "outputs" / "prompt_qwen_max_schema_rich")
    parser.add_argument("--api-key-env", default="DASHSCOPE_API_KEY")
    parser.add_argument("--model", default="qwen-max")
    parser.add_argument("--max-tokens", type=int, default=384)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"missing API key environment variable: {args.api_key_env}")

    data = runner.select_smoke_rows(args.data_dir) if args.smoke else {
        subset: load_jsonl(args.data_dir / f"{subset}.jsonl") for subset in SUBSETS
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "experiment": "E1_P_qwen_max_schema_rich",
        "model": args.model,
        "prompt_style": "schema_rich",
        "prompt_contract": PARAMETER_SCHEMA,
        "temperature": 0,
        "max_tokens": args.max_tokens,
        "smoke": args.smoke,
        "records": {subset: len(rows) for subset, rows in data.items()},
        "data_sha256": {
            subset: hashlib.sha256((args.data_dir / f"{subset}.jsonl").read_bytes()).hexdigest()
            for subset in data
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scorer": "run_e1.score / e1_score_v3",
        "credential_env": args.api_key_env,
    }
    (args.out_dir / ("metadata_smoke.json" if args.smoke else "metadata.json")).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    original_messages_for = runner.messages_for
    runner.messages_for = lambda row, style: schema_rich_messages(row) if style == "schema_rich" else original_messages_for(row, style)
    results: dict[str, object] = {"metadata": metadata, "scores": {}}
    try:
        for subset, rows in data.items():
            name = f"{subset}{'_smoke' if args.smoke else ''}.schema_rich.jsonl"
            result = runner.run_subset(
                rows, api_key=api_key, url=runner.DEFAULT_URL, model=args.model,
                max_tokens=args.max_tokens, timeout=args.timeout, retries=args.retries,
                prompt_style="schema_rich", workers=args.workers,
                output_path=args.out_dir / "predictions" / name,
            )
            results["scores"][subset] = result
            print(json.dumps({
                "subset": subset,
                "f1": result["constraint_micro"]["f1"],
                "state_accuracy": result["state_accuracy"],
                "parse_rate": result["json_parse_rate"],
                "request_errors": result["request_errors"],
            }, ensure_ascii=False), flush=True)
    finally:
        runner.messages_for = original_messages_for
    result_name = f"results{'_smoke' if args.smoke else ''}.schema_rich.json"
    (args.out_dir / result_name).write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
