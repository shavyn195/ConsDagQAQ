"""Cached v6 frontier API baselines; credentials are read only from the environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pe_v4_side import DEFAULT_URL, demonstrations, fingerprint
from rescore_v4_side import digest
from run_e1 import ROOT, chat_messages_v4, eval_subsets, load_jsonl
from run_pe_v5 import request
from run_e1_v6 import validate_v6_freeze

SOURCE_NAMES = (
    "run_e1", "run_e1_v6", "run_pe_v6", "run_pe_v5", "pe_v4_side", "rescore_v4_side",
    "eval_exec_v6", "eval_exec", "trust_env", "dataset_v6_spec", "dataset_v5_spec",
    "build_dataset_v6", "verify_dataset_v6",
)


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prediction_hash(prediction: dict) -> str:
    payload = {key: prediction.get(key) for key in
               ("sample_id", "request_hash", "raw", "model", "finish", "usage")}
    return canonical_hash(payload)


def request_fingerprint(config: dict, params: dict, messages: list[dict[str, str]]) -> str:
    # Include all source/data/config identity, even when a particular prompt is unchanged.
    return fingerprint([config, params, messages])


def restore_verified(path: Path, requests: dict[str, str], model: str) -> dict[str, dict]:
    cached = {}
    if not path.exists():
        return cached
    for pred in load_jsonl(path):
        sample_id = pred.get("sample_id")
        if (not isinstance(sample_id, str) or sample_id in cached or sample_id not in requests
                or requests[sample_id] != pred.get("request_hash")
                or pred.get("model") != model or not isinstance(pred.get("raw"), str)
                or pred.get("prediction_sha256") != prediction_hash(pred)):
            raise ValueError(f"Duplicate, stale, corrupt or foreign cached prediction: {sample_id}")
        cached[sample_id] = pred
    return cached


def write_json_atomic(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def verify_completion(out: Path, config: dict, subsets: list[str], model: str, style: str) -> None:
    marker = out / "completion.json"
    if not marker.exists():
        return
    saved = json.loads(marker.read_text(encoding="utf-8"))
    if (saved.get("schema_version") != 1 or saved.get("status") != "complete"
            or saved.get("model") != model or saved.get("style") != style
            or saved.get("config_sha256") != canonical_hash(config)):
        raise ValueError("Completed PE cache has a different config; use a new output directory")
    expected = {"config.json": out / "config.json", **{f"{s}.jsonl": out / f"{s}.jsonl" for s in subsets}}
    if (any(not path.is_file() for path in expected.values())
            or saved.get("artifacts") != {name: file_hash(path) for name, path in expected.items()}):
        raise ValueError("Completed PE cache artifact hashes differ; preserve and inspect the cache")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=("deepseek-v4-pro-0813", "qwen-max"))
    parser.add_argument("--style", required=True, choices=("zero", "few"))
    parser.add_argument("--data", type=Path, default=ROOT / "data/processed_v6")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    validate_v6_freeze(args.data)

    params = {"model": args.model, "temperature": 0, "max_tokens": 384}
    if args.model.startswith("deepseek"):
        params["enable_thinking"] = False
    out = ROOT / "outputs/e1_v6_side" / f"{args.model}-{args.style}"
    out.mkdir(parents=True, exist_ok=True)
    import fcntl  # deployment host is Linux
    lock_stream = (out / ".lock").open("a", encoding="utf-8")
    try:
        fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise RuntimeError(f"Another PE process owns the cache: {out}") from exc
    subsets = eval_subsets(args.data)
    rows_by_subset = {s: load_jsonl(args.data / f"{s}.jsonl") for s in subsets}
    demo = demonstrations(load_jsonl(args.data / "train.jsonl")) if args.style == "few" else []
    config = {
        "params": params,
        "url": DEFAULT_URL,
        "style": args.style,
        "demo_hash": fingerprint(demo),
        "data": {s: digest(args.data / f"{s}.jsonl") for s in ["train", *subsets]},
        "source_hashes": {
            name: digest(Path(__file__).with_name(name + ".py"))
            for name in SOURCE_NAMES
        },
    }
    manifest = out / "config.json"
    if manifest.exists() and json.loads(manifest.read_text(encoding="utf-8")) != config:
        raise ValueError("Run fingerprint changed; use a new output directory")
    if not manifest.exists():
        write_json_atomic(manifest, config)
    verify_completion(out, config, subsets, args.model, args.style)

    for subset, rows in rows_by_subset.items():
        path = out / f"{subset}.jsonl"

        def messages(row: dict) -> list[dict[str, str]]:
            base = chat_messages_v4(row)
            return [base[0], *demo, base[1]]

        keys = {row["sample_id"]: request_fingerprint(config, params, messages(row)) for row in rows}
        cached = restore_verified(path, keys, args.model)
        missing = [row for row in rows if row["sample_id"] not in cached]
        if missing and not os.environ.get("DASHSCOPE_API_KEY"):
            raise SystemExit("DASHSCOPE_API_KEY is required because this PE cache has missing requests")
        with path.open("a", encoding="utf-8") as stream, ThreadPoolExecutor(max_workers=args.workers) as pool:
            for start in range(0, len(missing), args.workers):
                batch = missing[start : start + args.workers]
                jobs = {pool.submit(request, params, messages(row)): row["sample_id"] for row in batch}
                errors = []
                for job in as_completed(jobs):
                    try:
                        prediction = job.result()
                    except Exception as exc:  # Keep successful cache rows; the next launch resumes missing IDs.
                        errors.append(exc)
                        continue
                    sid = jobs[job]
                    saved = {"sample_id": sid, "request_hash": keys[sid], **prediction}
                    saved["prediction_sha256"] = prediction_hash(saved)
                    stream.write(json.dumps(saved, ensure_ascii=False, allow_nan=False) + "\n")
                    stream.flush()
                if errors:
                    raise errors[0]
        if set(restore_verified(path, keys, args.model)) != set(keys):
            raise ValueError(f"Incomplete cohort: {path}")
        print(json.dumps({"subset": subset, "records": len(rows), "status": "complete"}))

    artifacts = {"config.json": file_hash(manifest)}
    artifacts.update({f"{subset}.jsonl": file_hash(out / f"{subset}.jsonl") for subset in subsets})
    write_json_atomic(out / "completion.json", {
        "schema_version": 1, "status": "complete", "model": args.model,
        "style": args.style, "config_sha256": canonical_hash(config), "artifacts": artifacts,
    })


if __name__ == "__main__":
    main()
