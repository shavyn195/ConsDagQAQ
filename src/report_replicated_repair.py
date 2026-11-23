"""Check frozen inputs and estimate paired improvement across both evaluated weights."""
from collections import Counter
import json
from pathlib import Path

import numpy as np
from eval_repair_sft import read, SPLITS
from full_one_edit import OUT
from prepare_e2_credit_panel import PARENT
from rescore_v4_side import digest, load_jsonl


def main():
    folders = (OUT, PARENT / "verified-one-edit-full-order44-v1")
    first, second = (read(folder / "protocol.json") for folder in folders)
    assert first["adapter"] != second["adapter"]
    assert all(first[k] == second[k] for k in first if k != "adapter")
    scores = {}
    gains = {}
    for folder in folders:
        result = read(folder / "results.json")
        assert digest(folder / "cases.jsonl") == result["cases"]
        assert digest(folder / "raw.jsonl") == result["raw"]
        rows = load_jsonl(folder / "cases.jsonl")
        assert [r["id"] for r in rows] == first["ids"]
        groups = {}
        values = Counter()
        for row in rows:
            if row["variant"] == "none":
                continue
            flags = row["flags"]
            values.update(groups_scored=1, rerank=flags["rerank"], repair=flags["repair"])
            groups.setdefault((row["split"], row["group"]), {})[row["variant"]] = flags["repair"] - flags["rerank"]
        assert len(groups) == 700 and all(set(g) == {"explicit","implicit"} for g in groups.values())
        values["normalized_symbolic"] = sum(s["normalized"] for s in read(folder / "normalized-symbolic.json")["by_split"].values())
        routed = read(folder / "empty-route.json")["by_split"]
        values["routed_safe"] = sum(s["routed_safe"] for s in routed.values())
        values["none_default"] = sum(s["new_default"] for s in routed.values())
        scores[folder.name] = values
        gains[folder.name] = groups
    g1,g2 = gains.values()
    assert g1.keys() == g2.keys()
    rng = np.random.default_rng(8201)
    means, boot = [], []
    for split in SPLITS:
        a = np.array([np.mean([g[k][v] for g in (g1,g2) for v in ("explicit","implicit")])
                      for k in sorted(g1) if k[0] == split])
        assert len(a) == 350
        means.append(a.mean())
        boot.append(a[rng.integers(0,len(a),(10000,len(a)))].mean(axis=1))
    ci = np.quantile(np.mean(boot,axis=0)*100,[.025,.975])
    report = dict(counts=scores, pooled_paired_gain_pp=float(np.mean(means)*100),
                  interval95=ci.tolist(), condition="two fixed training orders, shared generation seed; resampling DAG groups jointly",
                  code=digest(Path(__file__)))
    (folders[1]/"replicated-summary.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    main()
