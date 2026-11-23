"""Recover one missing mandatory stage from the public plan schema; score against gold afterwards."""
import fcntl
import hashlib
import json
from collections import Counter
from pathlib import Path
import torch
from audit_warmup_rollouts import shape
from confirm_one_edit import make_panel
from eval_e2_credit import decode_config,inputs,load
from eval_repair_sft import DEST,read
from prepare_e2_credit_panel import COMP,PARENT
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from probe_one_edit_repair import choose
from probe_repair_depth import OUT as DEPTH,world
from rescore_v4_side import aligned,digest,load_jsonl
from run_e1 import strict_parse
from trust_env import check,default_plan,normalize_constraint,plan


OUT=PARENT/"verified-missing-stage-v1"


def insert_one(task,candidates):
    if any(shape(a,task) and check(task,a,[])["completed"] for a in candidates):
        return candidates,0
    augmented=[]
    for a in candidates:
        if not a: continue
        missing=[st for st in task["stages"] if not set(st["alternatives"]).intersection(a)]
        if len(missing)!=1: continue
        for tool in sorted(missing[0]["alternatives"]):
            for i in range(len(a)+1):
                b=a[:i]+[tool]+a[i:]
                if b not in augmented and shape(b,task) and check(task,b,[])["completed"]:
                    augmented.append(b)
    return augmented or candidates,len(augmented)


def measure(row,prediction,raw):
    task=row["task"]
    aa=[parse(s,sorted(task["tools"]),"names") for s in raw]
    pred=[c for c in (strict_parse(prediction) or {}).get("constraints",[]) if normalize_constraint(c,task) is not None]
    _,base,_,_,_=choose(task,aa,pred,row["sample_id"])
    candidates,n=insert_one(task,aa)
    _,fixed,_,_,_=choose(task,candidates,pred,row["sample_id"])
    sy,_=plan(task,pred)
    if sy and not shape(sy,task):
        normalized=[v for v in sy if v not in task["finish"]]+[v for v in sy if v in task["finish"]]
        if shape(normalized,task) and check(task,normalized,pred)["safe_success"]:sy=normalized
    gold=row["gold"]["constraints"]
    def safe(a):
        return bool(shape(a,task) and check(task,a,gold)["safe_success"])
    return dict(id=row["sample_id"],before=base,after=fixed,admitted=n,
                flags=dict(constrained=int(bool(gold)),orig=int(bool(gold) and safe(base)),
                 fixed=int(bool(gold) and safe(fixed)),symbolic=int(bool(gold) and safe(sy)),
                 wins=int(bool(gold) and safe(fixed) and not safe(base)),losses=int(bool(gold) and safe(base) and not safe(fixed)),
                 generated_repairs=n,none=int(not gold),none_default=int(not gold and fixed==default_plan(task))))


def fresh_panel():
    data=ROOT/"data/processed_v4/dev.jsonl";pred=COMP/"trained_predictions/dev.jsonl"
    rows=load_jsonl(data);pp=aligned(rows,load_jsonl(pred));by={r["sample_id"]:v for r,v in zip(rows,pp,strict=True)}
    selected=[]; used=set()
    for variant in ("explicit","implicit","none"):
        options=[r for r in rows if r["variant"]==variant and r["group_id"] not in used]
        options.sort(key=lambda r: hashlib.sha256(("missing-midstage-v1"+r["group_id"]).encode()).digest())
        for r in options[:32]:
            used.add(r["group_id"]);selected.append((r,by[r["sample_id"]]))
    assert len(used)==96
    return selected, [digest(data),digest(pred)]


def middle(row):
    r=world(row,False);t=r["task"]
    from probe_repair_depth import ROLE
    del t["tools"][ROLE]; del t["optional"][ROLE]
    roles=["confirm_dataset_manifest","review_dataset_manifest"]
    for role in roles:
        assert role not in t["tools"]
        t["tools"][role]=dict(cost_cny=0,duration_min=0,recipient="local",clears_pii=False)
    t["stages"].insert(1,dict(stage="review",alternatives=roles,default=roles[0]))
    orig=row["witness_plan"] if row["gold"]["constraints"] else default_plan(row["task"])
    a=[v for v in orig if v not in t["finish"]]+[v for v in orig if v in t["finish"]]
    i=next(i for i,v in enumerate(a) if v in t["stages"][0]["alternatives"])+1
    witness=a[:i]+roles[:1]+a[i:]
    assert shape(witness,t) and check(t,witness,row["gold"]["constraints"])["safe_success"]
    return r


def main():
    source,_=make_panel(); fresh,hs=fresh_panel(); fresh=[(middle(r),p) for r,p in fresh]
    OUT.mkdir(exist_ok=False)
    cfg=dict(ids=[r["sample_id"] for r,_ in fresh],source=hs,code=digest(Path(__file__)),
             adapter=digest(DEST/"uniform/adapter/adapter_model.safetensors"),
             seed=96812,draws=4,max_new_tokens=160,
             methods="before/after inserting one absent public stage if all neural candidates are structurally incomplete; reference normalized symbolic planner",
             panels="exploratory replay of mandatory last-stage probe, prospective two-alternative intermediate-stage dev perturbation, not external data")
    (OUT/"protocol.json").write_text(json.dumps(cfg,indent=2))
    counts={k:Counter() for k in ("replay","prospective")}
    old=read(DEPTH/"results.json"); src=DEPTH/"mandatory.jsonl"
    assert digest(src)==old["hashes"]["mandatory"]
    with (OUT/"replay.jsonl").open("x") as f:
        for (r,p),x in zip(source,load_jsonl(src),strict=True):
            result=measure(world(r,True),p,x["raw"])
            assert result["id"]==x["id"] and result["flags"]["orig"]==x["scored"]["flags"].get("repair",0)
            counts["replay"].update(result["flags"]);print(json.dumps(result),file=f)
    print("replay",dict(counts["replay"]),flush=True)
    with (PARENT/"planner-probe.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        tok,model=load(DEST/"uniform/adapter")
        with (OUT/"raw.jsonl").open("x") as f,torch.inference_mode():
            for i in range(0,len(fresh),4):
                batch=fresh[i:i+4];inp=inputs(tok,[r for r,_ in batch]);torch.manual_seed(96812+i)
                gen=model.generate(**inp,generation_config=decode_config(tok,True))[:,inp.input_ids.shape[1]:]
                assert len(gen)==4*len(batch)
                raw=tok.batch_decode(gen,skip_special_tokens=True)
                for j,(r,p) in enumerate(batch):
                    out=measure(r,p,raw[j*4:j*4+4]);counts["prospective"].update(out["flags"])
                    print(json.dumps(dict(id=r["sample_id"],raw=raw[j*4:j*4+4],result=out)),file=f)
                f.flush();print("prospective",i+4,"/96",flush=True)
    report=dict(counts=counts,raw=digest(OUT/"raw.jsonl"),replay=digest(OUT/"replay.jsonl"))
    (OUT/"results.json").write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=="__main__":
    main()
