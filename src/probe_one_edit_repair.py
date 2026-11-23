"""Frozen inference rule: rescue a rejected completed candidate with one public edit."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from audit_warmup_rollouts import shape
from eval_repair_sft import DEST, read
from probe_e2_format import parse
from replay_repair_sft import cases
from rescore_v4_side import digest, load_jsonl
from trust_env import check, default_plan, plan


def edits(t,a):
    for i,tool in enumerate(a):
        for stage in t["stages"]:
            if tool in stage["alternatives"]:
                for replacement in sorted(stage["alternatives"]):
                    if replacement!=tool:
                        yield a[:i]+[replacement]+a[i+1:]
        if tool in t["optional"]:
            yield a[:i]+a[i+1:]
    for tool in sorted(t["optional"]):
        if tool not in a:
            for i in range(len(a)+1):
                yield a[:i]+[tool]+a[i:]
    yield a[:-2]+a[-2:][::-1]


def choose(t,aa,pred,sample_id):
    valid=[i for i,a in enumerate(aa) if shape(a,t) and check(t,a,[])["completed"]]
    ix=min(valid,key=lambda i:len(check(t,aa[i],pred)["violations"])) if valid else 0
    original=aa[ix]
    if not valid or not check(t,original,pred)["violations"]:
        return original,original,original,0,ix
    neighbors={}
    for i in [ix]+[j for j in valid if j!=ix]:
        for b in edits(t,aa[i]):
            if shape(b,t) and check(t,b,[])["completed"]:
                neighbors.setdefault(tuple(b),b)
    if not neighbors:
        return original,original,original,0,ix
    solved=[b for b in neighbors.values() if not check(t,b,pred)["violations"]]
    placebo=min(neighbors.values(),key=lambda b:hashlib.sha256(json.dumps([sample_id,b]).encode()).digest())
    return original,(solved[0] if solved else original),placebo,len(neighbors),ix


def assess(folder,panel):
    stats={}; src=folder/"cases.jsonl"; raw=load_jsonl(src)
    assert digest(src)==read(folder/"results.json")["raw"]
    records=[]
    for x,(r,cs) in zip(raw,panel,strict=True):
        assert x["id"]==r["sample_id"]
        t=r["task"]
        aa=[parse(v,sorted(t["tools"]),"names") for v in x["raw"]]
        orig,fixed,placebo,n,ix=choose(t,aa,cs,x["id"])
        assert x["selection"]==ix
        symbolic,_=plan(t,cs)
        # Selection is finished before accessing evaluation constraints.
        gold=r["gold"]["constraints"]
        safe={k:bool(shape(a,t) and check(t,a,gold)["safe_success"]) for k,a in
              (("orig",orig),("fixed",fixed),("placebo",placebo),("symbolic",symbolic))}
        c=stats.setdefault(r["subset"],Counter())
        if gold:
            assert safe["orig"]==bool(x["flags"]["safe"])
            c.update({k:int(v) for k,v in safe.items()})
            c.update(n=1,wins=int(safe["fixed"] and not safe["orig"]),losses=int(safe["orig"] and not safe["fixed"]),
                     neighbors=n,searched=int(n>0),edited=int(orig!=fixed))
        else:
            c.update(none=1,none_orig=int(orig==default_plan(t)),none_fixed=int(fixed==default_plan(t)))
        records.append(dict(id=x["id"],index=ix,fixed=fixed,placebo=placebo,safe=safe,neighbors=n))
    return stats,records


def main():
    out=DEST/"one-edit-replay";out.mkdir(exist_ok=False)
    cfg=dict(panel=digest(DEST/"panel.json"),code=digest(Path(__file__)),
             primary="on completed candidates rejected by compiled rules, compare first verified one-edit repair with unedited rerank",
             control="same checked neighborhood and trigger, select by deterministic hash ignoring predicted violations",
             cost="same four candidates; count extra distinct structurally valid neighbors (not equal verifier cost to unedited)",
             limit="exploratory existing panel, rules fixed before inspecting one-edit results; inference only; not RL")
    (out/"protocol.json").write_text(json.dumps(cfg,indent=2))
    report={}
    for arm in ("warm","uniform","repair"):
        report[arm],recs=assess(DEST/arm,cases())
        with (out/f"{arm}.jsonl").open("x") as f:
            for x in recs: print(json.dumps(x),file=f)
    (out/"results.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=="__main__":
    main()
