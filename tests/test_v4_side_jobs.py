import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pe_v4_side import restore
from rescore_v4_side import ROOT, aligned, outcome


def test_omitting_evidence_keeps_execution_but_loses_evidence_credit():
    with (ROOT / "data/processed_v4/dev.jsonl").open(encoding="utf-8") as handle:
        row = next(r for r in map(json.loads, handle) if r["variant"] == "implicit")
    gold = row["gold"]
    assert outcome(row, json.dumps(gold))["exact_with_evidence"]
    for c in gold["constraints"]:
        del c["evidence_span"]
    actual = outcome(row, json.dumps(gold))
    assert actual["faithful_success"] and not actual["exact_with_evidence"]
    assert actual["evidence_hits"] == 0


def test_foreign_or_incomplete_predictions_fail_closed(tmp_path):
    row = {"sample_id":"x","raw":"{}"}
    for rows in [[], [row,row], [dict(row,sample_id="other")]]:
        with pytest.raises(ValueError):
            aligned([row], rows)
    path = tmp_path / "partial.jsonl"
    path.write_text(json.dumps(dict(row,request_hash="old")))
    with pytest.raises(ValueError):
        restore(path, {"x":"new"})
