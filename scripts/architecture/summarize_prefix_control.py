"""Read completed paired controls; do not select checkpoints or test rows."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from analyze_pointer_pilot import compare


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    result = {"scope": "two-seed development control, oracle records; not a novel-method result",
              "seeds": {}, "data_and_evaluator_unchanged": True,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    prefix_hash = None
    source_hash = None
    total_seconds = 0.0
    for seed, old_name in ((42, "pilot_dev_v1"), (43, "pilot_dense_seed43")):
        old, new = args.base / old_name, args.base / f"pilot_allprefix_seed{seed}"
        before, after = read(old / "metadata.json"), read(new / "metadata.json")
        for key in ("data_sha256", "evaluator_sha256", "supervision_audit_sha256"):
            if before[key] != after[key]:
                raise ValueError(f"Unintended change in {key}")
        if before["config"]["seed_pilot"] != after["config"]["seed_pilot"]:
            raise ValueError("Seed mismatch")
        for key, value in before["config"]["fixed"].items():
            if key != "prefix_sampling" and after["config"]["fixed"][key] != value:
                raise ValueError(f"Unintended hyperparameter change: {key}")
        inputs = read(new / "inputs.json")
        if prefix_hash is not None and prefix_hash != inputs["prefix_manifest_sha256"]:
            raise ValueError("Different prefix support across seeds")
        prefix_hash = inputs["prefix_manifest_sha256"]
        if source_hash is not None and source_hash != after["source_sha256"]:
            raise ValueError("Source changed between seeds")
        source_hash = after["source_sha256"]
        completed = read(new / "completion.json")
        if completed["status"] != "complete" or completed["engineering_smoke"]:
            raise ValueError("Incomplete control or smoke output")
        total_seconds += completed["elapsed_seconds"]
        paired = {}
        for arm in ("dense_single", "dense_set"):
            old_rows = read(old / arm / "original.json")["outcomes"]
            new_rows = read(new / arm / "original.json")["outcomes"]
            paired[f"{arm}_new_minus_old"] = compare(new_rows, old_rows)
        paired["set_minus_single"] = compare(read(new / "dense_set/original.json")["outcomes"],
                                              read(new / "dense_single/original.json")["outcomes"])
        result["seeds"][str(seed)] = {"results": completed["results"], "comparisons": paired,
                                     "elapsed_seconds": completed["elapsed_seconds"]}
    result.update(prefix_manifest_sha256=prefix_hash, source_sha256_runs=source_hash,
                  total_control_seconds=total_seconds)
    result["limitations"] = ("All-prefix sampling changes state coverage and task weighting. "
                              "Two seed results are descriptive; bootstrap conditions on each fitted model. "
                              "No external or untouched confirmation test and no graph control in this stage.")
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({s: r["comparisons"]["set_minus_single"] for s, r in result["seeds"].items()}))


if __name__ == "__main__":
    main()
