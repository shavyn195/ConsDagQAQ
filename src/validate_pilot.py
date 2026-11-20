"""Validate frozen pilot JSONL files and emit a machine-readable report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from pilot_schema import validate_rows  # noqa: E402


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = args.paths or [HERE.parent / "data" / "processed" / "train.jsonl", HERE.parent / "data" / "processed" / "test.jsonl"]
    rows = []
    for path in paths:
        rows.extend(load_rows(path))
    errors = validate_rows(rows)
    result = {
        "files": [str(path) for path in paths],
        "records": len(rows),
        "groups": len({row.get("group_id") for row in rows}),
        "valid": not errors,
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
