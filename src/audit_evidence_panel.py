"""Audit source alignment, split overlap, and the primary score without the E1 scoring key."""
import argparse
from collections import Counter
import json
import re
import statistics

from build_evidence_panel import ARMS, MODELS, OUT, ROOT, digest, write_json
from score_evidence_panel import validate


def load(path):
    with path.open(encoding="utf8") as stream:
        return [json.loads(s) for s in stream]


def panel_audit(panel):
    training = load(ROOT/"data/processed_v4/train.jsonl")
    train_queries = {r["query"] for r in training}
    train_groups = {r["group_id"] for r in training}
    audit = dict(train_query_overlap=sum(q in train_queries for r in panel for q in r["queries"].values()),
                 train_group_overlap=len(train_groups & {r["group"] for r in panel}), panel_rows=len(panel))
    assert audit["train_query_overlap"] == audit["train_group_overlap"] == 0
    directions, differences = Counter(), []
    for subset in {r["subset"] for r in panel}:
        source = {r["sample_id"]:r for r in load(ROOT/f"data/processed_v4/{subset}.jsonl")}
        for r in (r for r in panel if r["subset"] == subset):
            validate(r)
            orig = source[r["id"]]
            assert (r["task"], r["catalog"], r["old"], r["queries"]["original"]) == (
                    orig["task"], orig["catalog"], orig["gold"], orig["query"])
            old, new = [r[k]["constraints"][r["idx"]] for k in ("old","new")]
            if r["variant"] == "explicit" and r["kind"] in ("deadline","budget"):
                directions["tightened" if next(iter(old["params"].values())) >
                           next(iter(new["params"].values())) else "relaxed"] += 1
            differences.append((len(r["queries"]["edited"])-len(r["queries"]["original"]),
                                len(r["queries"]["neutral_new"])-len(r["queries"]["neutral_old"])))
            assert old["state"] == new["state"] == r["variant"]
    audit.update(numeric_groups_by_direction=directions,
                 character_length_changes_equal=sum(a==b for a,b in differences),
                 median_abs_active_length_delta=statistics.median(abs(a) for a,b in differences),
                 median_abs_neutral_length_delta=statistics.median(abs(b) for a,b in differences),
                 distinct_inputs=len({(r["id"],s) for r in panel for s in r["queries"].values()}))
    write_json(OUT/"panel_audit.json", audit)
    return audit


def read_object(text):
    try:
        return json.loads(text)
    except ValueError:
        match = re.search(r"\{.*\}", text, re.S)
        try:
            return json.loads(match[0]) if match else None
        except ValueError:
            return None


def equivalent(ref, pred):
    def key(c):
        scope = c["scope"]
        scope = [scope] if isinstance(scope, str) else scope
        return (c["type"], c["state"], c["severity"], tuple(sorted(scope)),
                repr(sorted(c["params"].items())), c["evidence_span"])
    # All gold and predicted numeric parameters on this panel are ordinary JSON integers.
    try:
        return (ref["query_state"] == pred["query_state"] and not pred.get("abstain", False)
                and Counter(map(key, ref["constraints"])) == Counter(map(key, pred["constraints"])))
    except (TypeError, AttributeError, KeyError):
        return False


def verify(size, panel):
    folder = OUT/size
    raw = {(r["id"],r["arm"]):r["raw"] for r in load(folder/"raw.jsonl")}
    primary = json.loads((folder/"paired_scores.json").read_text())
    assert len(raw)==len(panel)*len(ARMS) and len(primary)==len(panel)
    saved = {r["id"]:r for r in primary}
    for r in panel:
        for arm in ARMS:
            ok = equivalent(r["new"] if arm=="edited" else r["old"], read_object(raw[r["id"],arm]))
            assert ok == saved[r["id"]]["arms"][arm]["full"], (size,r["id"],arm)
        assert saved[r["id"]]["full"] == all(saved[r["id"]]["arms"][a]["full"] for a in ("original","edited"))
    result = dict(size=size, arm_level_primary_reproduced=len(raw),
                  paired_primary_reproduced=len(panel), raw_sha256=digest(folder/"raw.jsonl"))
    write_json(folder/"audit.json",result)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("sizes",nargs="*")
    args=parser.parse_args()
    panel=load(OUT/"panel.jsonl")
    if not args.sizes:
        print(panel_audit(panel))
    for size in args.sizes:
        print(verify(size,panel))
