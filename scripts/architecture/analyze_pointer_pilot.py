"""Paired, group-bootstrap development comparisons; one training seed only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def compare(left: list[dict], right: list[dict], *, resamples: int = 4000) -> dict:
    a = {(r["group_id"], r["subset"]): r for r in left}
    b = {(r["group_id"], r["subset"]): r for r in right}
    if a.keys() != b.keys():
        raise ValueError("Unpaired evaluation inputs")
    groups = sorted({g for g, _ in a})
    gi = {g: i for i, g in enumerate(groups)}
    sums = np.zeros(len(groups))
    counts = np.zeros(len(groups))
    wins = losses = 0
    for key in a:
        if a[key]["n"] != b[key]["n"]:
            raise ValueError("Constraint-presence labels disagree")
        if a[key]["n"]:
            continue
        delta = int(a[key]["faithful"]) - int(b[key]["faithful"])
        sums[gi[key[0]]] += delta
        counts[gi[key[0]]] += 1
        wins += delta > 0
        losses += delta < 0
    if not counts.sum():
        raise ValueError("No constrained development rows")
    rng = np.random.default_rng(42)
    sample = rng.integers(len(groups), size=(resamples, len(groups)))
    denom = counts[sample].sum(1)
    differences = sums[sample].sum(1)[denom > 0] / denom[denom > 0]
    return {"constrained_rows": int(counts.sum()), "groups": len(groups),
            "difference_pp": float(100 * sums.sum() / counts.sum()),
            "wins": int(wins), "losses": int(losses),
            "descriptive_group_bootstrap_95ci_pp": (100 * np.quantile(differences, [0.025, 0.975])).tolist(),
            "limitation": "Exploratory development comparison, one training seed; not a seed-population CI or multiplicity-adjusted claim."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    completion = json.loads((args.run / "completion.json").read_text())
    if completion["status"] != "complete" or completion["engineering_smoke"]:
        raise ValueError("Need a completed development run, not smoke")
    result = {"scope": "oracle-record train/dev pilot, one seed; numerical/combination challenges still pending",
              "analysis_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "elapsed_seconds": completion["elapsed_seconds"], "summary": completion["results"],
              "comparisons": {}, "artifact_sha256": {}}
    for probe in ("original", "rename_reorder", "duplicate"):
        outcomes = {}
        for arm in completion["results"]:
            path = args.run / arm / f"{probe}.json"
            result["artifact_sha256"][f"{arm}/{probe}.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
            outcomes[arm] = json.loads(path.read_text())["outcomes"]
        result["comparisons"][probe] = {}
        for left, right in (("dense_set", "dense_single"), ("graph_single", "dense_single"),
                            ("graph_set", "dense_set"), ("graph_set", "dense_single")):
            if left not in outcomes or right not in outcomes:
                continue
            result["comparisons"][probe][f"{left}_minus_{right}"] = compare(outcomes[left], outcomes[right])
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result["comparisons"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
