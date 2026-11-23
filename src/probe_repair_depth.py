"""Paired depth perturbation: same catalog and frozen request, optional vs mandatory review."""
from collections import Counter
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import torch
from audit_warmup_rollouts import shape
from confirm_one_edit import make_panel,score
from eval_e2_credit import load,inputs,decode_config
from eval_empty_route import route
from eval_repair_sft import DEST,SPLITS
from prepare_e2_credit_panel import PARENT
from rescore_v4_side import digest
from trust_env import check,default_plan


OUT=PARENT/"verified-one-edit-depth-pair-v1"
ROLE="review_delivery_manifest"


def world(r,mandatory):
    new=deepcopy(r); t=new["task"]
    assert ROLE not in t["tools"]
    t["tools"][ROLE]=dict(cost_cny=0,duration_min=0,recipient="local",clears_pii=False)
    if mandatory:
        t["stages"].append(dict(stage="review",alternatives=[ROLE],default=ROLE))
    else:
        t["optional"][ROLE]=list(t["finish"])
    gold=r["gold"]["constraints"]
    initial=r["witness_plan"] if gold else default_plan(r["task"])
    clean=[a for a in initial if a not in t["finish"]]+[a for a in initial if a in t["finish"]]
    witness=clean[:-2]+([ROLE] if mandatory else [])+clean[-2:]
    assert shape(witness,t) and check(t,witness,gold)["safe_success"]
    if mandatory: assert not check(t,clean,[])["completed"]
    return new


def main():
    pack,hs=make_panel()
    changed={arm:[(world(r,arm=="mandatory"),p) for r,p in pack] for arm in ("optional","mandatory")}
    for (a,_),(b,_) in zip(*changed.values(),strict=True):
        assert a["task"]["tools"]==b["task"]["tools"] and a["query"]==b["query"] and a["gold"]==b["gold"]
    OUT.mkdir(exist_ok=False)
    adapter=DEST/"uniform/adapter"
    conf=dict(ids=[r["sample_id"] for r,_ in pack],sources=hs,code=digest(Path(__file__)),
              adapter=digest(adapter/"adapter_model.safetensors"),seed=96544,G=4,max_new_tokens=160,
              primary="pair by ID: mandatory vs optional additional review, safe-completed after one-edit repair",
              secondary="original rerank, symbolically constructed plan, N default with empty gate, strict task completion",
              limits="single synthetic depth perturbation. Same input tools, changed public stage declaration; compiler cache frozen for original user request.")
    (OUT/"protocol.json").write_text(json.dumps(conf,indent=2))
    all_scores={}; totals={}
    with (PARENT/"planner-probe.lock").open("a") as lk:
        fcntl.flock(lk,fcntl.LOCK_EX)
        tok,model=load(adapter)
        for arm,rows in changed.items():
            counts={sp:Counter() for sp in SPLITS}; vals={}
            with (OUT/f"{arm}.jsonl").open("x") as f,torch.inference_mode():
                for i in range(0,len(rows),4):
                    part=rows[i:i+4];inp=inputs(tok,[r for r,_ in part]);torch.manual_seed(conf["seed"]+i)
                    gen=model.generate(**inp,generation_config=decode_config(tok,True))[:,inp.input_ids.shape[1]:]
                    assert gen.shape[0]==4*len(part)
                    raw=tok.batch_decode(gen,skip_special_tokens=True)
                    for j,(r,p) in enumerate(part):
                        out=score(r,p,raw[4*j:4*j+4]);t=r["task"];gold=r["gold"]["constraints"]
                        a,_=route(p,t,out["actions"]["repair"]); old=out["actions"]["repair"]
                        done=bool(shape(old,t) and check(t,old,[])["completed"])
                        c=counts[r["subset"]];c.update(out["flags"])
                        if gold:
                            c.update(strict_completed=done,routed_safe=bool(shape(a,t) and check(t,a,gold)["safe_success"]))
                            vals[r["sample_id"]]=out["safe"]["repair"]
                        else:c.update(routed_default=a==default_plan(t))
                        print(json.dumps(dict(id=r["sample_id"],raw=raw[4*j:4*j+4],scored=out)),file=f)
                    f.flush()
                    if (i+4)%16==0:print(arm,i+4,"/120",flush=True)
            all_scores[arm]=vals;totals[arm]=counts
    pair=Counter()
    for k,a in all_scores["mandatory"].items():
        b=all_scores["optional"][k]
        pair.update(n=1,wins=int(a and not b),losses=int(b and not a))
    result=dict(by_arm=totals,mandatory_minus_optional=pair,
                hashes={a:digest(OUT/f"{a}.jsonl") for a in changed})
    (OUT/"results.json").write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)


if __name__=="__main__":
    main()
