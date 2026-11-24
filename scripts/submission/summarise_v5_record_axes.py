"""Frozen v5 three-seed N alarms and evidence-inclusive record accuracy.

Uses exactly the record definition in rescore_v4_side.outcome, without planning.
Compares that shortcut against the full scorer on 12 rows per run and split.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from analyze_v5_main import alarm
from rescore_v4_side import aligned, load_jsonl, outcome
from run_e1 import constraint_key, strict_parse


def exact(row, raw):
    parsed = strict_parse(raw)
    if parsed is None or parsed["query_state"] != row["variant"]:
        return False
    got, gold = parsed["constraints"], row["gold"]["constraints"]
    def spans(items):
        return Counter((constraint_key(c), c["evidence_span"]) for c in items
                       if isinstance(c.get("evidence_span"), str) and c["evidence_span"].strip()
                       and c["evidence_span"] in row["query"])
    return (spans(got) & spans(gold)).total() == len(got) == len(gold)


def main():
    dest = ROOT / "outputs/submission/audit_20261125/v5_record_axes_three_seed.json"
    if dest.exists():
        raise ValueError("Existing aggregate preserved")
    result = {"data_version": "v5", "seeds": [42, 43, 44], "table": {}, "input_sha256": {},
              "note": "Exact-with-evidence denominators are constrained E/I rows. N alarm includes malformed output, nonempty constraints or non-none query_state. SD is sample SD across three fixed seeds, not a confidence interval."}
    def tracked(path):
        result["input_sha256"][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        return load_jsonl(path)
    checks = 0
    for size in ("1.7B", "4B"):
        table = result["table"][size] = {}
        for split in ("dev", "test_tpl_ho", "test_tool_ho", "test_struct_ho"):
            rows = tracked(ROOT / "data/processed_v5" / f"{split}.jsonl")
            per_seed = {}
            for seed in result["seeds"]:
                pred = ROOT / f"outputs/e1/Qwen3-{size}-v5-seed{seed}/trained_predictions/{split}.jsonl"
                raw = aligned(rows, tracked(pred))
                constrained = [(r, t) for r, t in zip(rows, raw) if r["variant"] != "none"]
                none = [(r, t) for r, t in zip(rows, raw) if r["variant"] == "none"]
                hits = sum(exact(r, t) for r, t in constrained)
                alarms = sum(alarm(t) for _, t in none)
                for r, t in list(zip(rows, raw))[::max(1, len(rows) // 12)][:12]:
                    assert exact(r, t) == outcome(r, t)["exact_with_evidence"]
                    checks += 1
                per_seed[str(seed)] = {"exact_hits": hits, "n_constrained": len(constrained),
                                       "exact_with_evidence": hits / len(constrained),
                                       "none_alarm_count": alarms, "n_none": len(none),
                                       "none_false_alarm": alarms / len(none)}
            table[split] = {"per_seed": per_seed}
            for metric in ("exact_with_evidence", "none_false_alarm"):
                values = [v[metric] for v in per_seed.values()]
                table[split][metric] = {"mean": statistics.mean(values), "sd": statistics.stdev(values)}
    result["shortcut_vs_full_scorer_checks"] = checks
    result["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__), ROOT / "src/run_e1.py", ROOT / "src/rescore_v4_side.py", ROOT / "src/analyze_v5_main.py")}
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({"saved": str(dest), "checks": checks}), flush=True)


if __name__ == "__main__":
    main()
