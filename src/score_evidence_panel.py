"""Score complete paired raw outputs, and independently replay the stored certificates."""
import argparse
from collections import Counter, defaultdict
import json
import random

from audit_warmup_rollouts import shape
from build_evidence_panel import ARMS, MODELS, OUT, SEED, digest, write_json
from run_e1 import constraint_key, core_key, strict_parse
from trust_env import check, normalize_constraint


def exact_object(c):
    return constraint_key(c), c.get("evidence_span") if isinstance(c.get("evidence_span"), str) else None


def validate(rec):
    i, task = rec["idx"], rec["task"]
    old, new = (rec[k]["constraints"] for k in ("old", "new"))
    assert old[:i]+old[i+1:] == new[:i]+new[i+1:] and len(old) > 1
    assert old[i]["params"] != new[i]["params"]
    assert rec["queries"]["original"].replace(old[i]["evidence_span"], new[i]["evidence_span"]) == rec["queries"]["edited"]
    assert all(c["evidence_span"] in rec["queries"][arm] for arm in ARMS
               for c in (new if arm == "edited" else old))
    cert = rec["certificate"]
    for label, items in (("old", old), ("new", new)):
        witness = cert["witness"][label]
        assert shape(witness, task) and check(task, witness, items)["safe_success"]
        plan = cert["distinguish"]["plan"]
        assert shape(plan, task)
        assert check(task, plan, items)["safe_success"] == cert["distinguish"][label]
        assert check(task, plan, items[:i]+items[i+1:])["safe_success"]
    assert cert["distinguish"]["old"] != cert["distinguish"]["new"]


def measure(rec, arm, raw):
    ref = rec["new"] if arm == "edited" else rec["old"]
    gold = ref["constraints"]
    goal = gold[rec["idx"]]
    parsed = strict_parse(raw)
    ok = parsed is not None and not parsed.get("abstain", False)
    items = parsed["constraints"] if ok else []
    targets = [c for c in items if c["type"] == goal["type"]]
    target = targets[0] if len(targets) == 1 else None
    others = Counter(exact_object(c) for c in items if c["type"] != goal["type"])
    others_gold = Counter(exact_object(c) for c in gold if c["type"] != goal["type"])
    params = target is not None and core_key(target) == core_key(goal)
    scope = target is not None and constraint_key(target)[3] == constraint_key(goal)[3]
    span = target is not None and target.get("evidence_span") == goal["evidence_span"]
    full = ok and ref["query_state"] == parsed["query_state"] and Counter(map(exact_object, items)) == Counter(map(exact_object, gold))
    dec = None
    if ok and all(normalize_constraint(c, rec["task"]) is not None for c in items):
        dec = check(rec["task"], rec["certificate"]["distinguish"]["plan"], items)["safe_success"]
    label = rec["certificate"]["distinguish"]["new" if arm == "edited" else "old"]
    return dict(parse=parsed is not None, params=params, scope=scope, span=span,
                other=ok and others == others_gold, full=bool(full), plan_verdict=dec == label,
                annotated_other=sum(others_gold.values()), matched_other=sum((others & others_gold).values()))


def get_rates(r):
    return dict(n=len(r), **{k:sum(int(x[k]) for x in r) for k in r[0]
                             if k != "numeric" and isinstance(r[0][k], bool)})


def semantic_output(raw):
    parsed = strict_parse(raw)
    if parsed is None:
        return None
    return parsed["query_state"], parsed.get("abstain", False), Counter(map(exact_object, parsed["constraints"]))


def bootstrap(rows, field):
    strata = defaultdict(lambda: defaultdict(list))
    for r in rows:
        strata[(r["subset"], r["kind"])][r["group"]].append(r[field])
    rng = random.Random(SEED)
    clusters = [[sum(v)/len(v) for v in cell.values()] for cell in strata.values()]
    assert all(len(v) == 6 for v in clusters)
    means = sorted(sum(sum(rng.choices(v, k=len(v))) for v in clusters)/48 for _ in range(5000))
    return [means[124], means[4874]]


def score(size):
    proto = json.loads((OUT/"protocol.json").read_text())
    assert proto["panel_sha256"] == digest(OUT/"panel.jsonl")
    panel = [json.loads(s) for s in (OUT/"panel.jsonl").read_text().splitlines()]
    directory = OUT/size
    rawpath = directory/"raw.jsonl"
    raw = [json.loads(s) for s in rawpath.read_text().splitlines()]
    assert Counter((x["id"], x["arm"]) for x in raw) == Counter((r["id"], a) for r in panel for a in ARMS)
    by_id = {(x["id"], x["arm"]):x["raw"] for x in raw}
    rows = []
    arm_scores = defaultdict(list)
    for r in panel:
        validate(r)
        vals = {a:measure(r, a, by_id[r["id"], a]) for a in ARMS}
        for arm, v in vals.items():
            arm_scores[arm].append(v)
        old, edited, n0, n1 = (vals[a] for a in ARMS)
        neutral_a, neutral_b = (semantic_output(by_id[r["id"], a]) for a in ("neutral_old","neutral_new"))
        pair = {k:old[k] and edited[k] for k in ("params", "scope", "span", "full", "other", "plan_verdict")}
        rows.append({k:r[k] for k in ("id","group","subset","kind","variant","difficulty")} |
                    pair | dict(neutral_full=n0["full"] and n1["full"],
                                neutral_same=neutral_a is not None and neutral_a == neutral_b, old_other=old["other"],
                                regressed_other=old["other"] and not edited["other"],
                                neutral_correct_to_wrong=n0["full"] and not n1["full"],
                                neutral_wrong_to_correct=n1["full"] and not n0["full"],
                                arms=vals, numeric=r["kind"] in ("deadline","budget")))
    report = dict(raw_sha256=digest(rawpath), panel_sha256=proto["panel_sha256"], overall=get_rates(rows),
                  primary_95pct_stratified_group_bootstrap=bootstrap(rows,"full"),
                  arms={a:get_rates(v) for a,v in arm_scores.items()})
    for key in ("subset", "kind", "variant"):
        report[key] = {x:get_rates([r for r in rows if r[key]==x]) for x in sorted({r[key] for r in rows})}
    report["family_by_variant"] = {f"{typ}/{variant}":get_rates([r for r in rows if r["kind"]==typ and r["variant"]==variant])
                    for typ in sorted({r["kind"] for r in rows}) for variant in ("explicit", "implicit")}
    calc = [r for r in rows if r["numeric"] and r["variant"] == "implicit" and r["difficulty"]>=2]
    if calc:
        report["implicit_numeric_arithmetic"] = get_rates(calc)
    write_json(directory/"summary.json", report)
    write_json(directory/"paired_scores.json", rows)
    print(size, json.dumps(report["overall"]))


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("sizes", nargs="*", default=MODELS)
    for size in args.parse_args().sizes:
        score(size)
