from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from generate_pilot import render_rows  # noqa: E402
from run_pilot import extract_json, score  # noqa: E402


def test_json_extractor_accepts_clean_and_wrapped_json():
    assert extract_json('{"query_state":"none","abstain":false,"constraints":[]}') is not None
    assert extract_json('result: {"query_state":"none","constraints":[]} done') is not None
    assert extract_json("not json") is None


def test_score_counts_constraint_and_state_errors():
    rows = render_rows(1, 0)
    explicit = next(row for row in rows if row["variant"] == "explicit")
    gold = explicit["gold"]
    pred = {
        "query_state": "none",
        "abstain": False,
        "constraints": [],
    }
    metrics = score([explicit], [pred], ['{"query_state":"none","constraints":[]}'])
    assert metrics["state_accuracy"] == 0.0
    assert metrics["abstain_accuracy"] == 1.0
    assert metrics["constraint_micro_precision"] == 0.0
    assert metrics["constraint_micro_recall"] == 0.0
    assert metrics["constraint_exact_accuracy"] == 0.0
    assert metrics["json_parse_rate"] == 1.0

    correct = {"query_state": gold["query_state"], "abstain": gold["abstain"], "constraints": gold["constraints"]}
    perfect = score([explicit], [correct], [__import__("json").dumps(correct)])
    assert perfect["constraint_micro_f1"] == 1.0
    assert perfect["evidence_exact_rate_constrained"] == 1.0
    assert perfect["constraint_metrics_by_variant"]["explicit"]["evidence_records"] == 1


def test_score_reports_constraint_metrics_by_variant_without_crediting_empty_evidence():
    rows = render_rows(1, 0)
    explicit = next(row for row in rows if row["variant"] == "explicit")
    none = next(row for row in rows if row["variant"] == "none")
    predictions = [explicit["gold"], none["gold"]]
    metrics = score(
        [explicit, none], predictions,
        [__import__("json").dumps(prediction) for prediction in predictions],
    )
    assert metrics["constraint_metrics_by_variant"]["explicit"]["f1"] == 1.0
    assert metrics["constraint_metrics_by_variant"]["none"]["f1"] is None
    assert metrics["constraint_metrics_by_variant"]["none"]["evidence_exact_rate"] is None
