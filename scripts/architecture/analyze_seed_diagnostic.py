"""Check seed comparability and whether failures follow optimal alternative prefixes.

An association with alternative prefixes is not a causal exposure-bias test.
The teacher covers the documented canonical candidate domain only.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import torch


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base", type=Path, required=True)
    args = p.parse_args()
    base = args.base
    paths = [base / "pilot_dev_v1", base / "pilot_dense_seed43"]
    embeddings = [torch.load(path / "object_embeddings.pt", weights_only=True) for path in paths]
    assert embeddings[0].keys() == embeddings[1].keys()
    assert all(torch.equal(embeddings[0][k], embeddings[1][k]) for k in embeddings[0])
    meta = [json.loads((path / "metadata.json").read_text()) for path in paths]
    for key in ("source_sha256", "data_sha256", "evaluator_sha256"):
        assert meta[0][key] == meta[1][key], key
    assert meta[0]["config"]["fixed"] == meta[1]["config"]["fixed"]
    labels = {}
    for line in (base / "s0/dev_lattice.jsonl").read_text().splitlines():
        row = json.loads(line)
        for mask, label in row["lattice"].items():
            labels[(row["group_id"], mask)] = label
    report = {"encoder_tensors_identical": True, "source_data_evaluator_hashes_identical": True,
              "fixed_hyperparameters_identical": True, "source_sha256": sha(Path(__file__)),
              "by_type": {}, "alternative_prefix_association": {}, "artifact_sha256": {}}
    for path in paths:
        for arm in ("dense_single", "dense_set"):
            key = path.name + "/" + arm
            source = path / arm / "original.json"
            report["artifact_sha256"][key] = sha(source)
            rows = json.loads(source.read_text())["outcomes"]
            grouped = defaultdict(list)
            counters = dict(rows=0, failed=0, visited_alternative_optimal_prefix=0,
                            failed_after_alternative_optimal_prefix=0)
            for row in rows:
                label = labels[(row["group_id"], row["subset"])]
                for ctype in {c["type"] for c in label["constraints"]}:
                    grouped[ctype].append(row)
                if row["n"]:
                    continue
                counters["rows"] += 1
                counters["failed"] += not row["faithful"]
                alternative = False
                for k in range(1, len(row["plan"]) + 1):
                    prefix = row["plan"][:k]
                    supported = any(plan[:k] == prefix for plan in label["optimal_plans"] if len(plan) >= k)
                    if not supported:
                        break
                    alternative |= prefix != label["plan"][:k]
                counters["visited_alternative_optimal_prefix"] += alternative
                counters["failed_after_alternative_optimal_prefix"] += alternative and not row["faithful"]
            report["by_type"][key] = {t: {"rows": len(rs), "faithful": sum(r["faithful"] for r in rs) / len(rs)}
                                           for t, rs in sorted(grouped.items())}
            report["alternative_prefix_association"][key] = counters
    report["limitation"] = "Descriptive association, not causal attribution; overlapping constraint types; canonical teacher candidate domain only."
    (base / "pointer_seed_diagnostic.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["alternative_prefix_association"], indent=2))


if __name__ == "__main__":
    main()
