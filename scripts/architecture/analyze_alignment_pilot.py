"""Post-hoc artifact audit; does not fit models, tune a gate, or change scoring."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = args.input
    completion, metadata = load(root / "completion.json"), load(root / "metadata.json")
    assert completion["status"] == "completed" and not completion["smoke"]
    cfg = metadata["config"]
    data = load(root / "dataset.json")
    assert digest(root / "dataset.json") == load(root / "dataset_audit.json")["dataset_sha256"]
    assert digest(root / "embeddings.pt") == load(root / "encoder.json")["cache_sha256"]
    refs = {}
    for group in data["dev"]:
        for i, row in enumerate(group["rows"]):
            assert row["sample_id"] not in refs
            refs[row["sample_id"]] = (group, i, row)
    audit = {"scope": "Post-hoc diagnostic on the same development sample; no new validation set",
             "source_sha256": digest(Path(__file__)), "arms": {}, "matched_comparisons": {},
             "registered_gate_passed": completion["screening_gate_passed"],
             "decision": completion["decision"]}
    for seed in cfg["seeds"]:
        fitted = {}
        for arm in cfg["arms"]:
            name = f"{arm}_seed{seed}"
            result = load(root / name / "result.json")
            logs = [json.loads(s) for s in (root / name / "train.jsonl").read_text().splitlines()]
            assert [v["step"] for v in logs] == list(range(25, cfg["steps"] + 1, 25))
            assert all(math.isfinite(v[k]) for v in logs for k in ("loss", "grad_norm", "seconds"))
            assert result["initial_sha256"] == digest(root / f"initial_seed{seed}.pt")
            assert result["schedule_sha256"] == digest(root / f"schedule_seed{seed}.json")
            outcomes = {v["sample_id"]: v for v in result["outcomes"]}
            assert outcomes.keys() == refs.keys() and len(outcomes) == result["summary"]["n"]
            errors, errors_ei, counts = Counter(), Counter(), Counter()
            for sid, outcome in outcomes.items():
                group, i, row = refs[sid]
                selected = group["candidates"][outcome["choice"]]
                correct = group["positive"][i][outcome["choice"]]
                assert correct == outcome["predicate_correct"]
                alarm = row["variant"] == "none" and bool(selected["constraints"])
                assert alarm == outcome["none_false_alarm"]
                counts["correct"] += int(correct)
                counts["N_alarm"] += int(alarm)
                counts["faithful"] += int(outcome["gold_candidate_faithful"])
                counts["behavior_success_predicate_wrong"] += int(outcome["gold_candidate_faithful"] and not correct)
                if not correct:
                    # This is the chosen candidate's construction label, not a causal diagnosis.
                    errors[selected["kind"]] += 1
                    if row["variant"] != "none":
                        errors_ei[selected["kind"]] += 1
            assert math.isclose(counts["correct"] / len(refs), result["summary"]["all"]["predicate_correct"])
            audit["arms"][name] = {
                "n": len(refs), "counts": dict(counts), "summary": result["summary"],
                "selected_wrong_candidate_kind": dict(errors),
                "EI_selected_wrong_candidate_kind": dict(errors_ei),
                "saved_training_records": len(logs), "final_step": logs[-1]["step"],
                "logged_loss_and_grad_finite": True, "train_seconds": result["train_seconds"],
                "parameter_count": result["parameter_count"],
                "result_sha256": digest(root / name / "result.json")}
            fitted[arm] = outcomes
        comp = Counter()
        for sid in refs:
            a, b = fitted["contrastive"][sid], fitted["rank"][sid]
            ac, bc = a["predicate_correct"], b["predicate_correct"]
            comp["both_correct" if ac and bc else "contrastive_only_correct" if ac else "rank_only_correct" if bc else "both_wrong"] += 1
            comp["same_selected_candidate"] += int(a["choice"] == b["choice"])
        audit["matched_comparisons"][str(seed)] = dict(comp)
    audit["limits"] = [
        "64 development groups; oracle-derived candidates; not end-to-end generation or held-out tool evidence",
        "Candidate-kind counts describe selected wrong records; they do not identify a causal mechanism",
        "The training runner checked every step; this audit validates every saved 25-step record",
        "Same aggregate accuracy does not imply identical predictions or statistical equivalence",
        "No random-negative control: cannot attribute gains to hard-negative construction"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "verified", "gate": audit["registered_gate_passed"],
                      "arms": {k: v["counts"] for k, v in audit["arms"].items()},
                      "matched": audit["matched_comparisons"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
