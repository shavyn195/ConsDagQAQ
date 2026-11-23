"""Reparse outputs and report paired differences on the same dev IDs for each seed."""
import argparse
from collections import Counter
import json
from pathlib import Path
from audit_warmup_rollouts import shape
from prepare_e2_credit_panel import OUT
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import digest, load_jsonl
from trust_env import check, default_plan


def summarize(seed):
    panel = json.loads((OUT/"panel.json").read_text())
    data = ROOT/"data/processed_v4/dev.jsonl"
    assert digest(data) == panel["data"]["dev"]
    by = {r["sample_id"]:r for r in load_jsonl(data)}
    systems = {}
    for arm in ["warm","trace","action","shifted","function"]:
        d = OUT/(arm if arm=="warm" else f"{arm}-s{seed}")
        raw = load_jsonl(d/"dev.jsonl")
        assert [v["id"] for v in raw] == panel["dev"] and len(set(panel["dev"])) == 160
        values, counts = {}, Counter()
        for x in raw:
            r = by[x["id"]]
            acts = parse(x["raw"],sorted(r["task"]["tools"]),"names")
            result = check(r["task"],acts,r["gold"]["constraints"])
            done = bool(result["completed"] and shape(acts,r["task"]))
            safe = bool(done and result["safe_success"])
            faithful = bool(safe and (r["variant"]!="none" or acts==default_plan(r["task"])))
            assert (done,safe,faithful)==tuple(x["flags"][k] for k in ("completed","safe","faithful"))
            values[x["id"]]=safe
            counts.update(n=1,completed=done, constrained_safe=int(safe and r["variant"]!="none"),
                          constrained=int(r["variant"]!="none"),none_faithful=int(faithful and r["variant"]=="none"),
                          none=int(r["variant"]=="none"),calls=len(acts or []))
        training = {}
        if arm!="warm":
            assert json.loads((d/"done.json").read_text())["dev_sha256"] == digest(d/"dev.jsonl")
            steps = load_jsonl(d/"progress.jsonl")
            assert [v["id"] for v in steps] == panel["train"]
            training = dict(groups=len(steps),rollouts=len(steps)*4,updates=sum(v["updated"] for v in steps),
                            moved_groups=sum(v["relocated"]>0 for v in steps),tokens=sum(v["tokens"] for v in steps))
        systems[arm] = dict(values=values,counts=counts,training=training,hash=digest(d/"dev.jsonl"))
    paired = {}
    for a,b in [("action","trace"),("action","shifted"),("trace","function"),("action","warm")]:
        row = Counter(n=0,wins=0,losses=0)
        for k in panel["dev"]:
            if by[k]["variant"]=="none":
                continue
            u,v = systems[a]["values"][k],systems[b]["values"][k]
            row.update(n=1,wins=u and not v,losses=v and not u)
        paired[f"{a}-minus-{b}"]=dict(row,net=row["wins"]-row["losses"])
    report=dict(seed=seed,panel=digest(OUT/"panel.json"),paired=paired,
                systems={k:{f:v for f,v in x.items() if f!="values"} for k,x in systems.items()})
    (OUT/f"paired-dev-s{seed}.json").write_text(json.dumps(report,indent=2))
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--require-signal",action="store_true")
    a=p.parse_args()
    rep=summarize(a.seed)
    print(json.dumps(rep["paired"]))
    if a.require_signal and any(rep["systems"][k]["training"]["moved_groups"]<8 for k in ("action","shifted")):
        raise SystemExit("Hold expansion: fewer than eight groups actually received relocated credit.")
