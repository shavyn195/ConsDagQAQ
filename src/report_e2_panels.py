"""Cross-seed descriptive report. Resample tasks, keeping paired arms and seeds together."""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from audit_warmup_rollouts import shape
from prepare_e2_credit_panel import OUT
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import digest, load_jsonl
from trust_env import check, default_plan


def summarize(panel, seeds):
    original = panel == "original"
    dest = OUT if original else OUT/"preventive-comparison-v1"
    proto = json.loads((dest/("panel.json" if original else "protocol.json")).read_text())
    ids = proto["dev" if original else "ids"]
    path = ROOT/"data/processed_v4/dev.jsonl"
    assert digest(path) == (proto["data"]["dev"] if original else proto["dev"])
    data = {r["sample_id"]:r for r in load_jsonl(path)}
    rows = [data[i] for i in ids]
    assert len({r["group_id"] for r in rows}) == len(ids)
    mask = np.array([r["variant"] for r in rows])
    arms = ("action","trace","shifted","function") if original else ("protect","protect_shifted","action","trace")
    contrasts = (("action","trace"),("action","shifted"),("trace","function")) if original else (
        ("protect","action"),("protect","protect_shifted"),("protect","trace"))
    vals, counts, hashes = {}, {}, {}
    for arm in arms:
        vals[arm] = []
        counts[arm] = {}
        for seed in seeds:
            if original:
                source=dest/f"{arm}-s{seed}"/"dev.jsonl"
                assert json.loads((source.parent/"done.json").read_text())["dev_sha256"]==digest(source)
            else:
                source=dest/f"assessment-{arm}-{seed}.jsonl"
            records=load_jsonl(source)
            assert [x["id"] for x in records]==ids
            col=[]
            c=Counter()
            for r,x in zip(rows,records,strict=True):
                a=parse(x["raw"],sorted(r["task"]["tools"]),"names")
                checked=check(r["task"],a,r["gold"]["constraints"])
                done=bool(checked["completed"] and shape(a,r["task"]))
                safe=done and checked["safe_success"]
                n=r["variant"]=="none"
                assert (done,safe)==((x["flags"]["completed"],x["flags"]["safe"]) if original else (x["done"],x["safe"]))
                c.update(n=1,completed=done,constrained=not n,constrained_safe=not n and safe,none=n,
                         none_faithful=n and safe and a==default_plan(r["task"]),calls=len(a or []))
                col.append(int(safe))
            if not original:
                assert all(c[k]==v for k,v in json.loads(source.with_suffix(".json").read_text()).items())
            vals[arm].append(col)
            counts[arm][seed]=c
            hashes[f"{arm}-{seed}"]=digest(source)
    rng=np.random.default_rng(76307)
    strata=[np.flatnonzero(mask==v) for v in ("explicit","implicit")]
    indices=np.concatenate([rng.choice(s,(10000,len(s)),replace=True) for s in strata],axis=1)
    out={}
    for a,b in contrasts:
        d=np.array(vals[a])-np.array(vals[b])
        task=d.mean(axis=0)
        sampled=task[indices].mean(axis=1)*100
        out[f"{a}-minus-{b}"]=dict(net_by_seed=d[:,mask!="none"].sum(axis=1).tolist(),
            mean_pp=float(task[mask!="none"].mean()*100),
            conditional_task_interval_pp=np.quantile(sampled,[.025,.975]).tolist())
    report=dict(panel=panel,seeds=seeds,counts=counts,contrasts=out,raw_sha256=hashes,
                note="Paired query-group bootstrap within E/I, conditional on these training seeds; not a training-seed confidence interval.")
    target=dest/("rechecked-"+panel+"-"+"-".join(map(str,seeds))+".json")
    target.write_text(json.dumps(report,indent=2))
    print(json.dumps(out))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("panel",choices=("original","prevention"))
    p.add_argument("seeds",nargs="+",type=int,choices=(42,43,44))
    args=p.parse_args()
    assert len(set(args.seeds))==len(args.seeds)
    summarize(args.panel,args.seeds)
