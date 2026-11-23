"""CPU-only companion metrics for frozen v4 runs. Never write to training outputs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from eval_exec import bootstrap_ci, record_outcome
from run_e1 import SUBSETS, constraint_key, load_jsonl, score, strict_parse

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def aligned(rows, predictions):
    ids = [r["sample_id"] for r in rows]
    by_id = {p["sample_id"]: p["raw"] for p in predictions}
    if len(set(ids)) != len(ids) or len(by_id) != len(predictions) or set(ids) != set(by_id):
        raise ValueError("Missing, duplicate or unexpected sample IDs")
    return [by_id[k] for k in ids]


def outcome(row, raw):
    parsed = strict_parse(raw)
    got = parsed["constraints"] if parsed else []
    gold = row["gold"]["constraints"]
    def spans(items):
        return Counter((constraint_key(c), c["evidence_span"]) for c in items
                       if isinstance(c.get("evidence_span"), str) and c["evidence_span"].strip()
                       and c["evidence_span"] in row["query"])
    correct = (spans(got) & spans(gold)).total()
    o = record_outcome(row, parsed)
    o.update({
        "faithful_success": bool(o["safe_success"] and
            (not o["deviates_from_default"] if not gold else o["extra_changes"] == 0)),
        "valid_safe": parsed is not None and o["safe_success"],
        "exact_with_evidence": bool(parsed and parsed["query_state"] == row["variant"]
                                    and correct == len(got) == len(gold)),
        "evidence_hits": correct, "gold_count": len(gold),
    })
    return o


def summarise(items):
    def mean(k):
        return sum(o[k] for o in items) / len(items)
    return {"n": len(items), **{k: mean(k) for k in ("safe_success", "faithful_success",
            "valid_safe", "exact_with_evidence", "malformed")},
            "faithful_ci95_group": bootstrap_ci(items, "faithful_success"),
            "unusable_record_rate": sum(o["unusable_constraints"] > 0 for o in items)/len(items),
            "no_plan_rate": 1 - mean("planned"),
            "bound_span_recall": (sum(o["evidence_hits"] for o in items)/sum(o["gold_count"] for o in items)
                                  if any(o["gold_count"] for o in items) else None)}


def rescore(data, pred):
    report = {}
    for subset in SUBSETS:
        source = data / (subset + ".jsonl")
        saved = pred / source.name
        rows = load_jsonl(source)
        raw = aligned(rows, load_jsonl(saved))
        outcomes = [outcome(r,t) for r,t in zip(rows,raw)]
        bins = {"all": outcomes, "constrained": [o for o in outcomes if o["gold_count"]]}
        bins.update({v: [o for o in outcomes if o["variant"] == v] for v in ("explicit","implicit","none")})
        report[subset] = {"data_sha256": digest(source), "pred_sha256": digest(saved),
                          "v5": score(rows, [None]*len(rows), raw),
                          "side_v1": {k:summarise(items) for k,items in bins.items()}}
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pred", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    report = rescore(ROOT/"data/processed_v4", a.pred)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
