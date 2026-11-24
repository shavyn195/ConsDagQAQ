from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from build_dataset_v5 import gen_group  # noqa: E402
from build_dataset_v6 import SUBSETS, add_witnesses, combo_of  # noqa: E402
from dataset_v6_spec import HELDOUT_CONSTRAINT_COMBINATION, contains_heldout_pair  # noqa: E402
from verify_dataset_v6 import independent_replay, independently_violates, load, verify  # noqa: E402


def test_v6_adds_counterfactual_and_noop_witnesses():
    # The v5 generator's witness contract defines the expected paired constraint semantics.
    group = gen_group(random.Random(11), "toy-00000", "train", set())
    assert group is not None
    for row in group["records"]:
        row["spec_version"] = "v6"
        add_witnesses(row)
    explicit, implicit, none = group["records"]
    assert len(explicit["generation_witness"]["constraints"]) == len(explicit["gold"]["constraints"])
    assert [c["type"] for c in explicit["gold"]["constraints"]] == [
        c["type"] for c in implicit["gold"]["constraints"]
    ]
    for row in (explicit, implicit):
        assert independent_replay(row["task"], row["witness_plan"])["completed"]
        for constraint, witness in zip(row["gold"]["constraints"], row["generation_witness"]["constraints"]):
            assert row["query"].count(witness["evidence_span"]) == 1
            assert independently_violates(row["task"], witness["counterfactual_plan"], constraint)
    assert none["gold"]["constraints"] == []
    assert none["generation_witness"]["none_noop_plan"] == none["default_plan"]


def test_v6_composition_holdout_is_explicit_and_singleton():
    # This type set is absent from train/dev/other tests by build_dataset_v6's accept filter.
    assert HELDOUT_CONSTRAINT_COMBINATION == ("privacy", "tool_auth")
    assert contains_heldout_pair(["tool_auth", "privacy"])
    assert contains_heldout_pair(["privacy", "tool_auth", "order"])
    assert not contains_heldout_pair(["tool_auth", "order"])


@pytest.fixture(scope="module")
def small_v6_corpus(tmp_path_factory):
    """Real generator triplets, with one accepted group in each of the six splits."""
    data_dir = tmp_path_factory.mktemp("v6-corpus")
    rng, used_goals, rows, hashes = random.Random(20261124), set(), [], {}
    for subset in SUBSETS:
        for attempt in range(1000):
            group = gen_group(rng, f"{subset}-{attempt:05d}", subset, used_goals)
            if group is None:
                continue
            types = combo_of(group)
            if (subset == "test_composition_ho" and types != tuple(sorted(HELDOUT_CONSTRAINT_COMBINATION))) or (
                subset != "test_composition_ho" and contains_heldout_pair(types)
            ):
                continue
            break
        else:
            pytest.fail(f"Could not generate a valid {subset} group")
        for row in group["records"]:
            row["spec_version"] = "v6"
            add_witnesses(row)
        used_goals.add(group["records"][0]["task_goal"])
        rows.extend(group["records"])
        path = data_dir / f"{subset}.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in group["records"]), encoding="utf-8")
        hashes[subset] = hashlib.sha256(path.read_bytes()).hexdigest()
    (data_dir / "generation_report.json").write_text(json.dumps({"sha256": hashes}), encoding="utf-8")
    return rows, data_dir


def test_v6_verifier_records_all_split_pair_overlaps_and_allows_triplets(small_v6_corpus, monkeypatch):
    rows, data_dir = small_v6_corpus
    monkeypatch.setattr("verify_dataset_v6.EXPECTED_GROUPS", dict.fromkeys(SUBSETS, 1))
    report = verify(load(data_dir), data_dir)
    assert report["verdict"] == "PASS", report["sample_errors"]
    # Design v6 requires all six split pairs for query/goal/group: C(6, 2) * 3.
    assert len(report["leakage"]) == 45
    assert not any(report["leakage"].values())
    # Generator contract shares each goal and group across E/I/N inside its split.
    assert len({row["task_goal"] for row in rows}) == len(SUBSETS)


@pytest.mark.parametrize("field", ["query", "task_goal", "group_id"])
def test_v6_verifier_rejects_composition_overlap(small_v6_corpus, monkeypatch, field):
    original, data_dir = small_v6_corpus
    rows = copy.deepcopy(original)
    monkeypatch.setattr("verify_dataset_v6.EXPECTED_GROUPS", dict.fromkeys(SUBSETS, 1))
    train = next(row for row in rows if row["subset"] == "train")
    target = next(row for row in rows if row["subset"] == "test_composition_ho")
    target[field] = train[field]
    report = verify(rows, data_dir)
    # The intentionally copied value is one exact cross-split collision, including
    # composition records excluded from the inherited v5 verifier.
    assert report["leakage"][f"test_composition_ho_{field}_overlap_with_train"] == 1
    assert report["failures"]["cross_split_overlap"] >= 1
    assert report["verdict"] == "FAIL"


def test_v6_loader_rejects_mislabeled_source_file(tmp_path):
    # Do not allow records physically in train.jsonl to claim a different split.
    (tmp_path / "train.jsonl").write_text('{"subset":"dev"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="mislabeled v6 split file"):
        load(tmp_path)


@pytest.mark.parametrize("counterfactual", [["INVALID_ROLE"], [], "not-a-plan"])
def test_v6_verifier_rejects_invalid_or_incomplete_counterfactual(small_v6_corpus, monkeypatch, counterfactual):
    original, data_dir = small_v6_corpus
    rows = copy.deepcopy(original)
    monkeypatch.setattr("verify_dataset_v6.EXPECTED_GROUPS", dict.fromkeys(SUBSETS, 1))
    target = next(row for row in rows if row["subset"] == "test_composition_ho" and row["variant"] == "explicit")
    target["generation_witness"]["constraints"][0]["counterfactual_plan"] = counterfactual
    report = verify(rows, data_dir)
    assert report["failures"]["counterfactual_necessity"] == 1
    assert report["verdict"] == "FAIL"


def test_v6_counterfactual_must_preserve_other_constraints(small_v6_corpus, monkeypatch):
    original, data_dir = small_v6_corpus
    rows = copy.deepcopy(original)
    monkeypatch.setattr("verify_dataset_v6.EXPECTED_GROUPS", dict.fromkeys(SUBSETS, 1))
    target = next(row for row in rows if row["subset"] == "test_composition_ho" and row["variant"] == "explicit")
    # The real generator makes every positive constraint bind on the default
    # plan. It completes, but violates both members of this privacy/auth pair.
    assert independent_replay(target["task"], target["default_plan"])["completed"]
    assert all(independently_violates(target["task"], target["default_plan"], c)
               for c in target["gold"]["constraints"])
    target["generation_witness"]["constraints"][0]["counterfactual_plan"] = target["default_plan"]
    report = verify(rows, data_dir)
    assert report["failures"]["counterfactual_necessity"] == 1
    assert report["verdict"] == "FAIL"


def test_v6_composition_records_receive_inherited_alias_checks(small_v6_corpus, monkeypatch):
    from dataset_v5_spec import PII_CLASSES

    original, data_dir = small_v6_corpus
    rows = copy.deepcopy(original)
    monkeypatch.setattr("verify_dataset_v6.EXPECTED_GROUPS", dict.fromkeys(SUBSETS, 1))
    target = next(row for row in rows if row["subset"] == "test_composition_ho")
    # This reserved test-pool alias is forbidden in train-world inputs by V11.
    target["query"] += " " + next(iter(PII_CLASSES.values()))["fields"]["test"][0]
    report = verify(rows, data_dir)
    assert report["failures"]["v5_V11_alias_leak"] == 1
    assert report["verdict"] == "FAIL"
