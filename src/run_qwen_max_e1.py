"""Run the v2 E1 prompt baseline against DashScope qwen-max.

The runner deliberately reuses the E1 prompt, parser, normalisation and scorer
so that the closed-model P arm is comparable with the local T/Z arms. API
credentials are read from an environment variable and are never written to
metadata or prediction files.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_e1 import SCHEMA_HINT, SUBSETS, chat_messages, extract_json, load_jsonl, normalise_prediction, score

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"


def select_smoke_rows(data_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Select one complete E/I/N group per subset without changing row order."""
    selected: dict[str, list[dict[str, Any]]] = {}
    for subset in SUBSETS:
        rows = load_jsonl(data_dir / f"{subset}.jsonl")
        by_group: dict[str, dict[str, dict[str, Any]]] = {}
        for row in rows:
            by_group.setdefault(row["group_id"], {})[row["variant"]] = row
        complete = [by_group[g] for g in sorted(by_group) if {"explicit", "implicit", "none"} <= set(by_group[g])]
        if not complete:
            raise ValueError(f"{subset}: no complete E/I/N group found")
        group = complete[0]
        selected[subset] = [group[v] for v in ("explicit", "implicit", "none")]
    return selected


def atlas_adapted_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    """Adapt the ATLAS Constraint Manager's enumerate-explicit-and-implied instruction.

    ATLAS's original prompt is travel-domain and returns a numbered list, so this
    translation preserves its enumeration policy while keeping the E1 output
    contract for a matched evaluation.
    """
    prompt = (
        "You are an expert constraint manager for tool-planning tasks in a trusted data space. "
        "List every constraint that the user explicitly states or that is clearly implied by "
        "the query context. Do not add constraints unsupported by the query or context, and do "
        "not judge whether the requested plan is feasible. Preserve entities and numeric values "
        "as stated. Return the constraints as JSON matching this schema:\n"
        + SCHEMA_HINT + "\n"
        "Available role vocabulary: " + json.dumps(row["available_roles"], ensure_ascii=False) + "\n"
        "User query: " + row["query"] + "\n"
        "JSON:"
    )
    return [
        {"role": "system", "content": "Output JSON only."},
        {"role": "user", "content": prompt},
    ]


def messages_for(row: dict[str, Any], prompt_style: str) -> list[dict[str, str]]:
    if prompt_style == "e1_original":
        return chat_messages(row)
    if prompt_style == "atlas_adapted":
        return atlas_adapted_messages(row)
    raise ValueError(f"unknown prompt style: {prompt_style}")


def _content_from_response(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError(f"response has no choices: {payload}")
    message = choices[0].get("message", {})
    content = message.get("content", "") if isinstance(message, dict) else ""
    if isinstance(content, list):
        # Some compatible endpoints return typed content blocks.
        content = "".join(str(block.get("text", "")) for block in content if isinstance(block, dict))
    if not isinstance(content, str):
        content = str(content)
    return content


def request_completion(
    *,
    api_key: str,
    url: str,
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: float,
    retries: int,
) -> tuple[str, dict[str, Any]]:
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return _content_from_response(payload), {"status": "ok", "http_status": 200}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if (exc.code < 500 and exc.code != 429) or attempt >= retries:
                raise RuntimeError(f"HTTP {exc.code}: {detail[:500]}") from exc
            last_error = exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            if attempt >= retries:
                raise RuntimeError(str(exc)) from exc
        time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(str(last_error) if last_error else "request failed")


def run_subset(
    rows: list[dict[str, Any]],
    *,
    api_key: str,
    url: str,
    model: str,
    max_tokens: int,
    timeout: float,
    retries: int,
    prompt_style: str,
    workers: int,
    output_path: Path,
) -> dict[str, Any]:
    started = time.time()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    expected = {row["sample_id"]: i for i, row in enumerate(rows)}
    records_by_index: dict[int, dict[str, Any]] = {}
    if output_path.exists():
        for line in output_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            old = json.loads(line)
            index = expected.get(old.get("sample_id"))
            if index is not None and old.get("status", {}).get("status") == "ok":
                records_by_index[index] = old
        output_path.write_text(
            "".join(json.dumps(records_by_index[i], ensure_ascii=False) + "\n" for i in sorted(records_by_index)),
            encoding="utf-8",
        )
    missing = [(i, row) for i, row in enumerate(rows) if i not in records_by_index]
    errors: list[dict[str, Any]] = []
    completed = len(records_by_index)

    def request_row(index: int, row: dict[str, Any]) -> dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            raw, status = request_completion(
                api_key=api_key, url=url, model=model, messages=messages_for(row, prompt_style),
                max_tokens=max_tokens, timeout=timeout, retries=retries,
            )
        except Exception as exc:
            raw = ""
            status = {"status": "error", "error": str(exc)}
        prediction = normalise_prediction(extract_json(raw))
        return {
            "_index": index,
            "sample_id": row["sample_id"],
            "prediction": prediction,
            "raw": raw,
            "model": model,
            "base_url": url,
            "prompt_style": prompt_style,
            "timestamp_utc": timestamp,
            "status": status,
        }

    # Results are appended as they finish, so a restart can skip successful rows.
    with output_path.open("a", encoding="utf-8") as output_file, concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(request_row, index, row): (index, row) for index, row in missing}
        for future in concurrent.futures.as_completed(futures):
            index, row = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                record = {
                    "_index": index,
                    "sample_id": row["sample_id"],
                    "prediction": normalise_prediction(None),
                    "raw": "",
                    "model": model,
                    "base_url": url,
                    "prompt_style": prompt_style,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "status": {"status": "error", "error": str(exc)},
                }
            record_index = record.pop("_index")
            records_by_index[record_index] = record
            output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            output_file.flush()
            completed += 1
            if record["status"].get("status") != "ok":
                errors.append(record)
            if completed == len(rows) or completed % 25 == 0:
                print(json.dumps({"prompt_style": prompt_style, "completed": completed, "total": len(rows), "elapsed_s": round(time.time() - started, 1), "status": record["status"].get("status")}, ensure_ascii=False), flush=True)

    if errors:
        (output_path.parent / f"{output_path.stem}.errors.jsonl").write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in errors), encoding="utf-8"
        )
        raise RuntimeError(f"{prompt_style}: {len(errors)} request(s) failed; rerun to resume successful rows")
    ordered_records = [records_by_index[i] for i in range(len(rows))]
    predictions = [record["prediction"] for record in ordered_records]
    raw_outputs = [record["raw"] for record in ordered_records]
    result = score(rows, predictions, raw_outputs)
    result["elapsed_seconds"] = round(time.time() - started, 1)
    result["request_errors"] = 0
    result["resumed_records"] = len(rows) - len(missing)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data" / "processed_v2")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "prompt_qwen_max_e1")
    parser.add_argument("--api-key-env", default="DASHSCOPE_API_KEY")
    parser.add_argument("--base-url", default=DEFAULT_URL)
    parser.add_argument("--model", default="qwen-max")
    parser.add_argument("--prompt-style", choices=("e1_original", "atlas_adapted"), default="e1_original")
    parser.add_argument("--max-tokens", type=int, default=384)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--smoke", action="store_true", help="one complete E/I/N group per subset")
    args = parser.parse_args()

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"missing API key environment variable: {args.api_key_env}")
    data = select_smoke_rows(args.data_dir) if args.smoke else {
        subset: load_jsonl(args.data_dir / f"{subset}.jsonl") for subset in SUBSETS
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "experiment": f"E1_P_qwen_max_{args.prompt_style}",
        "model": args.model,
        "prompt_style": args.prompt_style,
        "base_url": args.base_url,
        "prompt": (
            "run_e1.chat_messages / original E1 schema prompt"
            if args.prompt_style == "e1_original"
            else "ATLAS Constraint Manager enumeration policy adapted to the E1 JSON schema; not a verbatim prompt reproduction"
        ),
        "temperature": 0,
        "max_tokens": args.max_tokens,
        "smoke": args.smoke,
        "records": {subset: len(rows) for subset, rows in data.items()},
        "data_sha256": {
            subset: hashlib.sha256((args.data_dir / f"{subset}.jsonl").read_bytes()).hexdigest()
            for subset in data
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "scorer": "run_e1.score / e1_score_v3",
        "credential_env": args.api_key_env,
    }
    (args.out_dir / ("metadata_smoke.json" if args.smoke else "metadata.json")).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    results: dict[str, Any] = {"metadata": metadata, "scores": {}}
    for subset, rows in data.items():
        output_name = f"{subset}.{args.prompt_style}.jsonl"
        if args.smoke:
            output_name = f"{subset}_smoke.{args.prompt_style}.jsonl"
        result = run_subset(
            rows, api_key=api_key, url=args.base_url, model=args.model,
            max_tokens=args.max_tokens, timeout=args.timeout, retries=args.retries,
            prompt_style=args.prompt_style, workers=args.workers,
            output_path=args.out_dir / "predictions" / output_name,
        )
        results["scores"][subset] = result
        print(json.dumps({"subset": subset, "f1": result["constraint_micro"]["f1"], "state_accuracy": result["state_accuracy"], "parse_rate": result["json_parse_rate"], "request_errors": result["request_errors"]}, ensure_ascii=False), flush=True)
    result_name = f"results_smoke.{args.prompt_style}.json" if args.smoke else f"results.{args.prompt_style}.json"
    (args.out_dir / result_name).write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"saved": str(args.out_dir / result_name)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
