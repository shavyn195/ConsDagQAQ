"""Pair by DAG, jointly resampling E/I for safe completion and measuring N behavior."""
from collections import Counter
from pathlib import Path
import json
import numpy as np
from eval_repair_sft import SPLITS,read
from full_one_edit import OUT
from rescore_v4_side import digest,load_jsonl


def main():
    results=read(OUT/"results.json")
    assert digest(OUT/"cases.jsonl")==results["cases"]
    raw=load_jsonl(OUT/"cases.jsonl")
    assert len(raw)==2100
    groups={}
    for r in raw:
        group=groups.setdefault((r["split"],r["group"]),{})
        assert r["variant"] not in group
        group[r["variant"]]=r
    assert all(set(g)=={"explicit","implicit","none"} for g in groups.values())
    comparisons={}
    for alt in ("rerank","placebo","default_edit","symbolic"):
        rng=np.random.default_rng(61773)
        boots=[];count=Counter()
        for sp in SPLITS:
            pairs=[]
            for (s,_),g in groups.items():
                if s!=sp:continue
                deltas=[]
                for v in ("explicit","implicit"):
                    r=g[v]; safe=r["safe"]
                    d=int(safe["repair"])-int(safe[alt])
                    deltas.append(d);count.update(wins=d==1,losses=d==-1,n=1)
                pairs.append(np.mean(deltas))
            assert len(pairs)==350
            arr=np.array(pairs)
            boots.append(np.mean(arr[rng.integers(0,350,(10000,350))],axis=1))
        distribution=(boots[0]+boots[1])*50
        comparisons[alt]=dict(**count,pp=100*(count["wins"]-count["losses"])/count["n"],
                               interval95=np.quantile(distribution,[.025,.975]).tolist())
    fields={"neighbors":0,"safe_env":0,"safe_strict":0,"symbolic_env":0,"symbolic_strict":0}
    for g in groups.values():
        for v in ("explicit","implicit"):
            f=g[v]["flags"];fields["neighbors"]+=f["neighbors"]
            fields["safe_strict"]+=f["repair"];fields["safe_env"]+=f["repair_env"]
            fields["symbolic_env"]+=f["symbolic_env"];fields["symbolic_strict"]+=f["symbolic"]
    report=dict(comparisons=comparisons,counts=fields,groups=len(groups),cases=digest(OUT/"cases.jsonl"),
                bootstrap="10k stratified by split, pair E/I in each task; fixed compiler, planner and draw seed",
                code=digest(Path(__file__)))
    (OUT/"paired-summary.json").write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=="__main__":
    main()
