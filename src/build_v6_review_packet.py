"""Export a deterministic, blinded human-review sample from frozen v6 data.

The exporter is intentionally separate from the training JSONL files. It only
copies the exact compiler-visible chat messages into reviewer packets; source
IDs, strata, labels, witnesses, and model predictions stay in the private
selection manifest or the original data directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from build_dataset_v6 import SUBSETS
from run_e1 import chat_messages_v4

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data" / "processed_v6"
DEFAULT_OUT_DIR = ROOT / "data" / "review_v6_seed20261125_n5"
DEFAULT_SEED = 20261125
DEFAULT_PER_STRATUM = 5
CONSTRAINT_TYPES = ("budget", "deadline", "order", "privacy", "tool_auth")
NEAR_MISS_SUBTYPES = ("waiver", "revoked", "other_party", "permission")
REVIEWER_VERSION = "v6-blind-review-v1"

ANNOTATION_INSTRUCTIONS = (
    "Read the model-visible messages below as the complete information available to the compiler. "
    "List every supported plan constraint and no unsupported constraint. Copy the full supporting "
    "query sentence or clause verbatim as its evidence span. Use the supplied policy and tool catalog to determine "
    "type, state, severity, scope, and parameters. Mark uncertainty rather than guessing. Also decide "
    "whether the query supports an empty constraint set and an unchanged default plan. Do not seek "
    "hidden task information or discuss this item with the other reviewer before submitting."
)


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stratum(kind: str, subset: str, label: str) -> str:
    return f"{kind}|{subset}|{label}"


def _rank(seed: int, stratum: str, sample_id: str) -> str:
    material = f"{seed}\0{stratum}\0{sample_id}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _packet_id(seed: int, sample_id: str) -> str:
    material = f"review-v6\0{seed}\0{sample_id}".encode("utf-8")
    return "rvw_" + hashlib.sha256(material).hexdigest()[:20]


def select_items(
    rows: list[dict[str, Any]],
    *,
    splits: tuple[str, ...] = SUBSETS,
    per_stratum: int = DEFAULT_PER_STRATUM,
    seed: int = DEFAULT_SEED,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Select I constraint records and N records, tracking overlapping strata.

    Each record is included once in the blind packets even when selected by
    multiple type/subtype strata. Its full stratum membership is retained in
    the researcher-only manifest.
    """
    if per_stratum < 1:
        raise ValueError("per_stratum must be positive")

    rows_by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen_ids: set[str] = set()
    for row in rows:
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError("every source row needs a non-empty sample_id")
        if sample_id in seen_ids:
            raise ValueError(f"duplicate source sample_id: {sample_id}")
        seen_ids.add(sample_id)
        subset = row.get("subset")
        if subset not in splits:
            raise ValueError(f"unexpected subset {subset!r} for sample {sample_id}")
        rows_by_split[subset].append(row)

    selected: dict[str, dict[str, Any]] = {}
    cell_report: dict[str, dict[str, Any]] = {}

    def add_cell(kind: str, subset: str, label: str, candidates: list[dict[str, Any]]) -> None:
        cell = _stratum(kind, subset, label)
        candidates = sorted(candidates, key=lambda row: _rank(seed, cell, row["sample_id"]))
        if len(candidates) < per_stratum:
            raise ValueError(f"stratum {cell} has {len(candidates)} candidates; needs {per_stratum}")
        chosen = candidates[:per_stratum]
        cell_report[cell] = {
            "candidate_records": len(candidates),
            "selected_records": len(chosen),
            "selected_sample_ids": [row["sample_id"] for row in chosen],
        }
        for row in chosen:
            entry = selected.setdefault(row["sample_id"], {"row": row, "strata": []})
            entry["strata"].append(cell)

    for subset in splits:
        split_rows = rows_by_split.get(subset, [])
        implicit_rows = [row for row in split_rows if row.get("variant") == "implicit"]
        for ctype in CONSTRAINT_TYPES:
            candidates = [
                row for row in implicit_rows
                if any(c.get("type") == ctype for c in row.get("gold", {}).get("constraints", []))
            ]
            if candidates:
                add_cell("I", subset, ctype, candidates)
            else:
                cell_report[_stratum("I", subset, ctype)] = {
                    "candidate_records": 0,
                    "selected_records": 0,
                    "selected_sample_ids": [],
                    "status": "no_candidates",
                }

        none_rows = [row for row in split_rows if row.get("variant") == "none"]
        for subtype in NEAR_MISS_SUBTYPES:
            candidates = [
                row for row in none_rows
                if subtype in (row.get("near_miss_subtypes") or [])
            ]
            add_cell("N", subset, subtype, candidates)

    for entry in selected.values():
        entry["strata"] = sorted(set(entry["strata"]))

    by_stratum = {
        cell: set(info["selected_sample_ids"])
        for cell, info in cell_report.items()
    }
    overlaps = []
    for left, right in combinations(sorted(by_stratum), 2):
        shared = sorted(by_stratum[left] & by_stratum[right])
        if shared:
            overlaps.append({"left": left, "right": right, "shared_unique_records": len(shared)})

    multiplicity = Counter(len(entry["strata"]) for entry in selected.values())
    selection_payload = [
        {"sample_id": sid, "strata": selected[sid]["strata"]}
        for sid in sorted(selected)
    ]
    report = {
        "seed": seed,
        "per_stratum": per_stratum,
        "splits": list(splits),
        "cells": cell_report,
        "unique_selected_records": len(selected),
        "selected_record_stratum_multiplicity": dict(sorted(multiplicity.items())),
        "overlapping_strata": overlaps,
        "selection_sha256": _sha256_bytes(_json_bytes(selection_payload)),
    }
    return selected, report


def _response_template() -> dict[str, Any]:
    return {
        "query_state": "explicit|implicit|none|unsure",
        "constraints": [],
        "constraint_item_schema": {
            "type": "budget|deadline|privacy|tool_auth|order|other",
            "state": "explicit|implicit|unsure",
            "severity": "high|medium|low|unsure",
            "scope": ["role:..."],
            "params": {},
            "evidence_span": "exact substring from the query",
            "uncertain": False,
            "uncertainty_note": "",
        },
        "overall_uncertain": False,
        "overall_uncertainty_note": "",
        "should_be_empty_and_leave_default_unchanged": "yes|no|unsure",
        "reviewer_notes": "",
    }


def make_blind_item(row: dict[str, Any], seed: int) -> dict[str, Any]:
    messages = chat_messages_v4(row)
    if not messages or any(not isinstance(m.get("content"), str) for m in messages):
        raise ValueError(f"invalid compiler-visible prompt for {row.get('sample_id')}")
    return {
        "packet_item_id": _packet_id(seed, row["sample_id"]),
        "annotation_instructions": ANNOTATION_INSTRUCTIONS,
        "model_visible_messages": messages,
        "response_template": _response_template(),
    }


def _reviewer_order(items: list[dict[str, Any]], seed: int, reviewer: str) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: hashlib.sha256(
            f"{seed}\0{reviewer}\0{item['packet_item_id']}".encode("utf-8")
        ).hexdigest(),
    )


def _read_and_check_inputs(data_dir: Path) -> tuple[list[dict[str, Any]], dict[str, str], str, str]:
    generation_path = data_dir / "generation_report.json"
    verification_path = data_dir / "verification_report.json"
    if not generation_path.is_file() or not verification_path.is_file():
        raise FileNotFoundError("v6 generation_report.json and verification_report.json are required")
    generation = json.loads(generation_path.read_text(encoding="utf-8"))
    verification = json.loads(verification_path.read_text(encoding="utf-8"))
    if generation.get("spec_version") != "v6" or generation.get("synthetic_only") is not True:
        raise ValueError("input generation report is not a synthetic v6 freeze")
    if verification.get("verdict") != "PASS":
        raise ValueError("v6 verification report must have verdict PASS")

    rows: list[dict[str, Any]] = []
    actual_hashes: dict[str, str] = {}
    for subset in SUBSETS:
        path = data_dir / f"{subset}.jsonl"
        if not path.is_file():
            raise FileNotFoundError(f"missing v6 split: {path}")
        raw = path.read_bytes()
        actual_hashes[subset] = _sha256_bytes(raw)
        if actual_hashes[subset] != generation.get("sha256", {}).get(subset):
            raise ValueError(f"split hash disagrees with generation report: {subset}")
        if actual_hashes[subset] != verification.get("sha256", {}).get(subset):
            raise ValueError(f"split hash disagrees with verification report: {subset}")
        for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("subset") != subset or row.get("spec_version") != "v6":
                raise ValueError(f"wrong subset/spec at {path}:{line_number}")
            rows.append(row)
    return (
        rows,
        actual_hashes,
        _sha256_bytes(generation_path.read_bytes()),
        _sha256_bytes(verification_path.read_bytes()),
    )


def export_packet(
    data_dir: Path,
    out_dir: Path,
    *,
    seed: int = DEFAULT_SEED,
    per_stratum: int = DEFAULT_PER_STRATUM,
) -> dict[str, Any]:
    """Write two blinded packets and a researcher-only linkage manifest."""
    data_dir = data_dir.resolve()
    out_dir = out_dir.resolve()
    if data_dir == out_dir or data_dir in out_dir.parents:
        raise ValueError("review artifacts must be outside the frozen processed_v6 directory")
    if out_dir.exists():
        raise FileExistsError(f"refusing to overwrite review packet directory: {out_dir}")

    rows, input_hashes, generation_hash, verification_hash = _read_and_check_inputs(data_dir)
    selected, selection = select_items(rows, per_stratum=per_stratum, seed=seed)
    items = [make_blind_item(entry["row"], seed) for _, entry in sorted(selected.items())]
    if len({item["packet_item_id"] for item in items}) != len(items):
        raise ValueError("packet item ID collision")

    private_items = []
    for sample_id, entry in sorted(selected.items()):
        row = entry["row"]
        private_items.append({
            "packet_item_id": _packet_id(seed, sample_id),
            "source_sample_id": sample_id,
            "source_group_id": row["group_id"],
            "source_subset": row["subset"],
            "source_variant": row["variant"],
            "selection_strata": entry["strata"],
        })

    out_dir.mkdir(parents=True)
    packet_files = {
        "reviewer_a.jsonl": _reviewer_order(items, seed, "reviewer_a"),
        "reviewer_b.jsonl": _reviewer_order(items, seed, "reviewer_b"),
    }
    packet_hashes = {}
    for name, packet in packet_files.items():
        payload = b"".join(_json_bytes(item) for item in packet)
        path = out_dir / name
        path.write_bytes(payload)
        packet_hashes[name] = _sha256_bytes(payload)

    selection_with_sources = {
        **selection,
        "items": private_items,
    }
    selection_hash = _sha256_bytes(_json_bytes(selection_with_sources))
    manifest = {
        "packet_version": REVIEWER_VERSION,
        "status": "exported_not_reviewed",
        "seed": seed,
        "per_stratum": per_stratum,
        "source_data_dir": str(data_dir),
        "source_split_sha256": input_hashes,
        "source_generation_report_sha256": generation_hash,
        "source_verification_report_sha256": verification_hash,
        "selection": selection_with_sources,
        "selection_manifest_sha256": selection_hash,
        "reviewer_packet_sha256": packet_hashes,
        "blinding": {
            "reviewer_files_include_source_ids": False,
            "reviewer_files_include_split_or_stratum": False,
            "reviewer_files_include_gold_or_witnesses": False,
            "reviewer_files_include_model_predictions": False,
            "visible_context_source": "run_e1.chat_messages_v4(row)",
        },
    }
    (out_dir / "selection_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--per-stratum", type=int, default=DEFAULT_PER_STRATUM)
    parser.add_argument(
        "--confirm-ready", action="store_true",
        help="explicitly confirm that v6 regeneration is complete and frozen before exporting",
    )
    args = parser.parse_args()
    if not args.confirm_ready:
        parser.error("refusing to export before regeneration is declared ready; pass --confirm-ready")
    result = export_packet(args.data_dir, args.out_dir, seed=args.seed, per_stratum=args.per_stratum)
    print(json.dumps({
        "status": result["status"],
        "out_dir": str(args.out_dir.resolve()),
        "unique_selected_records": result["selection"]["unique_selected_records"],
        "selection_manifest_sha256": result["selection_manifest_sha256"],
        "reviewer_packet_sha256": result["reviewer_packet_sha256"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
