from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from run_e1 import SUBSETS, load_jsonl, score


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def recompute(data_dir: Path, prediction_dir: Path, model: str, seed: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "metrics_version": "e1_score_v5",
        "model": model,
        "seed": seed,
        "source": "saved raw predictions scored by src/run_e1.py",
        "subsets": {},
    }
    for subset in SUBSETS:
        data_path = data_dir / f"{subset}.jsonl"
        prediction_path = prediction_dir / f"{subset}.jsonl"
        rows = load_jsonl(data_path)
        records = load_jsonl(prediction_path)
        by_id = {record["sample_id"]: record for record in records}
        if len(by_id) != len(records):
            raise ValueError(f"duplicate prediction sample_id in {prediction_path}")
        expected_ids = {row["sample_id"] for row in rows}
        if expected_ids != set(by_id):
            raise ValueError(
                f"sample_id mismatch for {subset}: missing={len(expected_ids - set(by_id))}, "
                f"extra={len(set(by_id) - expected_ids)}"
            )
        predictions = [by_id[row["sample_id"]]["prediction"] for row in rows]
        raw = [by_id[row["sample_id"]].get("raw", "") for row in rows]
        result["subsets"][subset] = score(rows, predictions, raw)
        if rows and "task" in rows[0]:
            from eval_exec import evaluate as evaluate_exec

            result["subsets"][subset]["exec"] = evaluate_exec(rows, raw)[0]
        result["subsets"][subset]["data_sha256"] = sha256(data_path)
        result["subsets"][subset]["prediction_sha256"] = sha256(prediction_path)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-score saved E1 predictions with e1_score_v5 (+ e1_exec_v1 on v4 data).")
    parser.add_argument("--data-dir", type=Path, default=Path("data/processed_v2"))
    parser.add_argument("--prediction-dir", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = recompute(args.data_dir, args.prediction_dir, args.model, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "saved": str(args.output),
        "subsets": {
            key: value["constraint_micro"]["f1"] for key, value in result["subsets"].items()
        },
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
