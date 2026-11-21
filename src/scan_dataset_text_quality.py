"""Scan frozen v2 queries for mechanically suspicious rendering artifacts.

This is a diagnostic gate, not a semantic oracle. It records exact sample IDs
and the matched fragments so a later regenerated dataset can be compared
without silently changing the evaluation corpus.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SUBSETS = ("train", "dev", "test_tpl_ho", "test_tool_ho")
PATTERNS = {
    "repeated_article": re.compile(r"\b(the|a|an)\s+\1\b", re.IGNORECASE),
    "article_after_connector": re.compile(
        r"\b(no|before|after|within)\s+the\s+(the|a|an)\b", re.IGNORECASE
    ),
    "repeated_noun": re.compile(
        r"\b(entry|workflow|validation|approval)\s+\1\b", re.IGNORECASE
    ),
}


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "processed_v2")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = args.output or args.data_dir.parent.parent / "outputs" / "dataset_text_quality_20261120.json"

    report: dict[str, Any] = {"tool": "scan_dataset_text_quality", "patterns": list(PATTERNS), "subsets": {}}
    for subset in SUBSETS:
        path = args.data_dir / f"{subset}.jsonl"
        rows = load_rows(path)
        matches: list[dict[str, Any]] = []
        for row in rows:
            query = str(row.get("query", ""))
            found = {name: pattern.findall(query) for name, pattern in PATTERNS.items()}
            found = {name: values for name, values in found.items() if values}
            if found:
                matches.append({"sample_id": row.get("sample_id"), "matches": found, "query": query})
        report["subsets"][subset] = {
            "records": len(rows),
            "suspect_records": len(matches),
            "suspect_rate": len(matches) / max(len(rows), 1),
            "examples": matches[:20],
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["suspect_records"] for k, v in report["subsets"].items()}, ensure_ascii=False))
    print(output)


if __name__ == "__main__":
    main()
