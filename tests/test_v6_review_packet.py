from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_v6_review_packet import make_blind_item, select_items  # noqa: E402


def review_rows() -> list[dict]:
    rows = []
    for subset in ("dev",):
        for index in range(5):
            constraints = [
                {"type": ctype, "state": "implicit", "severity": "high", "scope": [],
                 "params": {}, "evidence_span": f"Evidence {ctype}."}
                for ctype in ("budget", "deadline", "order", "privacy", "tool_auth")
            ]
            rows.append({
                "sample_id": f"i-{index}", "group_id": f"ig-{index}", "subset": subset,
                "variant": "implicit", "spec_version": "v6",
                "query": "Complete the task. Evidence budget. Evidence deadline. Evidence order. "
                         "Evidence privacy. Evidence tool_auth.",
                "catalog": [{"role": "r1", "name": "run", "paid": False, "recipient": "local"}],
                "gold": {"query_state": "implicit", "constraints": constraints},
            })
        for index in range(5):
            rows.append({
                "sample_id": f"n-{index}", "group_id": f"ng-{index}", "subset": subset,
                "variant": "none", "spec_version": "v6",
                "query": "Complete the task. No rule applies here.",
                "catalog": [{"role": "r1", "name": "run", "paid": False, "recipient": "local"}],
                "near_miss_subtypes": ["waiver", "revoked", "other_party", "permission"],
                "gold": {"query_state": "none", "constraints": []},
            })
    return rows


def test_selection_is_deterministic_balanced_and_tracks_overlap():
    rows = review_rows()
    first, first_report = select_items(rows, splits=("dev",), per_stratum=3, seed=17)
    second, second_report = select_items(rows, splits=("dev",), per_stratum=3, seed=17)

    assert sorted(first) == sorted(second)
    assert first_report["selection_sha256"] == second_report["selection_sha256"]
    assert all(cell["selected_records"] == 3 for cell in first_report["cells"].values())
    assert 6 <= first_report["unique_selected_records"] <= 10
    assert first_report["unique_selected_records"] == len(first)
    assert first_report["overlapping_strata"]
    assert any(len(entry["strata"]) > 1 for entry in first.values())


def test_blind_item_contains_compiler_input_but_no_hidden_labels_or_ids():
    row = review_rows()[0]
    packet = make_blind_item(row, seed=17)
    serialized = str(packet)

    assert "User query: " + row["query"] in serialized
    assert "Constraint types and params:" in serialized
    assert "Tool catalog (role: name; paid|free; local|external):" in serialized
    assert "sample_id" not in packet
    assert "group_id" not in packet
    assert "subset" not in packet
    assert "gold" not in packet
    assert "witness" not in packet
    assert "near_miss_subtypes" not in packet
