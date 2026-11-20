from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from generate_pilot import render_rows  # noqa: E402
from pilot_schema import validate_rows  # noqa: E402


def test_default_pilot_is_150_plus_51_and_valid():
    rows = render_rows()
    assert len(rows) == 201
    assert sum(row["split"] == "train" for row in rows) == 150
    assert sum(row["split"] == "test" for row in rows) == 51
    assert not validate_rows(rows)


def test_groups_are_exactly_explicit_implicit_none():
    rows = render_rows(5, 2)
    grouped = {}
    for row in rows:
        grouped.setdefault(row["group_id"], []).append(row)
    assert all({row["variant"] for row in group} == {"explicit", "implicit", "none"} for group in grouped.values())
    for group in grouped.values():
        assert group[0]["graph"] == group[1]["graph"] == group[2]["graph"]
        assert group[0]["witness"] == group[1]["witness"] == group[2]["witness"]


def test_constrained_templates_are_disjoint_between_splits():
    rows = render_rows()
    train_templates = {
        row["gold"]["constraints"][0]["evidence_span"]
        for row in rows if row["split"] == "train" and row["gold"]["constraints"]
    }
    test_templates = {
        row["gold"]["constraints"][0]["evidence_span"]
        for row in rows if row["split"] == "test" and row["gold"]["constraints"]
    }
    assert train_templates.isdisjoint(test_templates)


def test_validator_catches_evidence_and_witness_tampering():
    rows = render_rows(1, 0)
    tampered = copy.deepcopy(rows)
    explicit = next(row for row in tampered if row["variant"] == "explicit")
    explicit["gold"]["constraints"][0]["evidence_span"] = "not in query"
    assert any("evidence_span" in error for error in validate_rows(tampered))

    tampered = render_rows(1, 0)
    constrained = next(row for row in tampered if row["variant"] == "explicit" and row["gold"]["constraints"])
    constrained["witness"] = list(reversed(constrained["witness"]))
    assert any("witness" in error or "dependency" in error or "budget" in error for error in validate_rows(tampered))
