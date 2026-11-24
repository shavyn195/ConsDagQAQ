"""Replay frozen API responses with E2's existing public-task plan reader.

Retains strict JSON scores and a single-code-fence sensitivity check. Changes no
roles, tool order, requests, responses, or running training source. This disclosed
post-hoc parsing correction is not a new model run or a gold-guided repair.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
MODES = ("strict_json", "single_fence", "e2_shared")


def parse_actions(text, task, mode, e2_parser):
    if mode == "e2_shared":
        # This function deliberately receives no gold, witness, or query.
        return e2_parser(text, {"task": task})
    if mode not in MODES:
        raise ValueError(mode)
    raw = text.strip()
    if mode == "single_fence":
        match = re.fullmatch(r"```(?:json)?[ \t]*\r?\n(.*?)\r?\n```", raw,
                             flags=re.DOTALL | re.IGNORECASE)
        if match:
            raw = match.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def components(root):
    sys.path.insert(0, str(root / "src"))
    sys.path.insert(0, str(root / "scripts/submission"))
    import deepseek_planner as api
    import analyse_deepseek_planner as analysis
    from sub_e2_monolithic import parse_plan
    return api, analysis, parse_plan


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--cache", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["OMP_NUM_THREADS"] = "1"
    if a.out.exists():
        raise ValueError("Existing replay preserved; use a new directory")
    api, analysis, parse_plan = components(a.root)
    config = json.loads((a.cache / "config.json").read_text())
    responses = api.load(a.cache / "responses.jsonl")
    original = api.load(a.cache / "outcomes.jsonl")
    analysis.check_coverage(config, original, responses)
    if api.file_hash(Path(api.__file__)) != config["source_sha256"]:
        raise ValueError("Original API source has drifted")
    for name, expected in config["consumer_source_sha256"].items():
        if api.file_hash(a.root / "src" / name) != expected:
            raise ValueError(f"Consumer source has drifted: {name}")
    jobs, provenance = api.panel(a.root)
    if provenance != config["input_sha256"]:
        raise ValueError("Frozen data or compiler caches changed")
    if {j["id"]: j["request_hash"] for j in jobs} != config["requests"]:
        raise ValueError("Reconstructed requests differ")
    source_paths = {"original_worker": Path(api.__file__),
                    "analysis": Path(analysis.__file__), "replay": Path(__file__),
                    "shared_e2_parser": a.root / "src/sub_e2_monolithic.py"}
    old = {r["id"]: r for r in original}
    cache = {r["request_hash"]: r for r in responses}
    replay = []
    mismatches = Counter()
    formats = Counter()
    for response in responses:
        text = response["raw"]
        strict = parse_actions(text, {}, "strict_json", None)
        fence = parse_actions(text, {}, "single_fence", None)
        kind = "strict_json_array" if isinstance(strict, list) else (
            "single_fence_json_array" if isinstance(fence, list) else "other")
        formats[kind] += 1
    a.out.mkdir(parents=True)
    for i, j in enumerate(jobs):
        row, raw = j["row"], cache[j["request_hash"]]["raw"]
        memo, parsed, results = {}, {}, {}
        for mode in MODES:
            actions = parse_actions(raw, row["task"], mode, parse_plan)
            parsed[mode] = actions
            key = json.dumps(actions, sort_keys=True, ensure_ascii=False)
            if key not in memo:
                memo[key] = api.outcome(row, actions)
            results[mode] = memo[key]
        symbolic, _ = api.plan(row["task"], j["parsed"]["constraints"] if j["parsed"] else [])
        symbolic_result = api.outcome(row, symbolic)
        if results["strict_json"] != old[j["id"]]["api"]:
            raise ValueError(f"Original strict score does not reproduce: {j['id']}")
        if symbolic_result != old[j["id"]]["symbolic"]:
            raise ValueError(f"Original symbolic score does not reproduce: {j['id']}")
        for mode in ("strict_json", "single_fence"):
            if results[mode] != results["e2_shared"]:
                mismatches[mode + "_versus_shared_outcome"] += 1
        replay.append(dict(old[j["id"]], api=results["e2_shared"],
                           parsers=results, shared_actions=parsed["e2_shared"]))
        if (i + 1) % 1000 == 0:
            print(json.dumps({"replayed": i + 1, "total": len(jobs)}), flush=True)
    analysis.check_coverage(config, replay, responses)
    for mode in MODES:
        records = [dict(r, api=r["parsers"][mode]) for r in replay]
        result = analysis.summarise(records, responses)
        result["parse_mode"] = mode
        result["provenance"] = {"source_sha256": {k: api.file_hash(v) for k, v in source_paths.items()},
                                "original_inputs_sha256": {n: api.file_hash(a.cache / n) for n in
                                                            ("config.json", "responses.jsonl", "outcomes.jsonl", "paired_analysis.json")}}
        result["scoring_revision"] = "20261125-cache-only-parsing-parity-v1"
        with (a.out / f"{mode}_analysis.json").open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    with (a.out / "outcomes.jsonl").open("x", encoding="utf-8") as f:
        for r in replay:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    audit = {"rows": len(replay), "unique_responses": len(responses), "unique_response_formats": dict(formats),
             "finish_reason_counts": dict(Counter(r["finish_reason"] for r in responses)),
             "outcome_disagreements": dict(mismatches), "original_strict_outcomes_exactly_reproduced": True,
             "original_symbolic_outcomes_exactly_reproduced": True,
             "api_calls_made": 0, "requests_reconstructed_exactly": True,
             "interpretation": "Strict format compliance is retained. e2_shared uses the existing monolithic plan reader with public task only. No role/value/order repair or gold-guided parsing. This is a disclosed post-hoc parsing parity analysis, not a new inference result."}
    with (a.out / "audit.json").open("x", encoding="utf-8") as f:
        json.dump(audit, f, indent=2)
    print(json.dumps(audit), flush=True)


if __name__ == "__main__":
    main()
