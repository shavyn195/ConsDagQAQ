"""Confirm the fixed single-edit rule on groups excluded from preceding E2 panels."""
import fcntl
import hashlib
import json
from collections import Counter
from pathlib import Path
import time

import torch
from audit_warmup_rollouts import shape
from eval_e2_credit import decode_config, inputs, load
from eval_repair_sft import DEST, SPLITS, read
from prepare_e2_credit_panel import COMP,PARENT
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from probe_one_edit_repair import choose
import probe_one_edit_repair as rule
from rescore_v4_side import aligned,digest,load_jsonl
from run_e1 import strict_parse
from trust_env import check,default_plan,normalize_constraint,plan


OUT=PARENT/"verified-one-edit-confirmation-v1"


def make_panel():
    used=set(read(DEST/"panel.json")["ids"])
    for name in ("frozen-planner-transfer-v1","shared-candidate-selection-transfer-v1"):
        used.update(read(PARENT/name/"protocol.json")["ids"])
    swap=read(PARENT/"frozen-planner-swap-panel-v1/config.json")
    pack=[]; hashes={}
    for sp in SPLITS:
        seen=used|set(swap["sources"][sp]["ids"])
        d=ROOT/f"data/processed_v4/{sp}.jsonl"; p=COMP/f"trained_predictions/{sp}.jsonl"
        rows=load_jsonl(d); hashes[sp]=[digest(d),digest(p)]
        cache={r["sample_id"]:v for r,v in zip(rows,aligned(rows,load_jsonl(p)),strict=True)}
        exclude={r["group_id"] for r in rows if r["sample_id"] in seen}
        for v in ("explicit","implicit","none"):
            pool=[r for r in rows if r["variant"]==v and r["group_id"] not in exclude]
            pool.sort(key=lambda r:hashlib.sha256(("one-edit-fixed-20261122|"+r["group_id"]).encode()).digest())
            assert len(pool)>=20
            for row in pool[:20]:
                exclude.add(row["group_id"]);pack.append((row,cache[row["sample_id"]]))
    assert len(pack)==len({r["group_id"] for r,_ in pack})==120
    return pack,hashes


def score(r,p,raw):
    t=r["task"]
    cs=[c for c in (strict_parse(p) or {}).get("constraints",[]) if normalize_constraint(c,t) is not None]
    aa=[parse(v,sorted(t["tools"]),"names") for v in raw]
    start=time.perf_counter()
    orig,fixed,placebo,n,ix=choose(t,aa,cs,r["sample_id"])
    elapsed=time.perf_counter()-start
    default=default_plan(t)
    _,df,_,nd,_=choose(t,[default],cs,r["sample_id"])
    sy,_=plan(t,cs)
    methods=dict(rerank=orig,repair=fixed,placebo=placebo,default_only=default,default_edit=df,symbolic=sy)
    gold=r["gold"]["constraints"]
    safe={k:bool(shape(a,t) and check(t,a,gold)["safe_success"]) for k,a in methods.items()}
    flags=Counter(n=1)
    if gold:
        flags.update(constrained=1,**{k:int(v) for k,v in safe.items()},
                     wins=int(safe["repair"] and not safe["rerank"]),losses=int(safe["rerank"] and not safe["repair"]),
                     vs_default_wins=int(safe["repair"] and not safe["default_edit"]),
                     vs_default_losses=int(safe["default_edit"] and not safe["repair"]),
                     edited=int(fixed!=orig),neighbors=n,default_neighbors=nd)
        for k,a in methods.items(): flags[k+"_env"]=int(bool(check(t,a,gold)["safe_success"]))
    else:
        flags.update(none=1,**{"keep_"+k:int(a==default) for k,a in methods.items()})
    return dict(id=r["sample_id"],actions=methods,source_index=ix,safe=safe,flags=flags,selection_seconds=elapsed)


def main():
    folder=DEST/"uniform/adapter"; out=OUT
    pack,hashes=make_panel()
    out.mkdir(exist_ok=False)
    config=dict(ids=[r["sample_id"] for r,_ in pack],sources=hashes,code=digest(Path(__file__)),
                rule=digest(Path(rule.__file__)),uniform_adapter=digest(folder/"adapter_model.safetensors"),
                sampling_seed=93800,draws=4,temperature=.8,max_tokens=160,
                primary="repair minus rerank on constrained strict success",
                secondary="default-only one edit (no neural generation), hash placebo, full symbolic, N default; count verifier work",
                scope="new E2 task groups, not external data or a novel topology; originally finite synthetic benchmark")
    (out/"protocol.json").write_text(json.dumps(config,indent=2))
    with (PARENT/"planner-probe.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        tok,model=load(folder)
        with torch.inference_mode(), (out/"raw.jsonl").open("x") as f:
            for i in range(0,len(pack),4):
                part=pack[i:i+4];inp=inputs(tok,[r for r,_ in part]);torch.manual_seed(93800+i)
                all_ids=model.generate(**inp,generation_config=decode_config(tok,True))[:,inp.input_ids.shape[1]:].cpu().tolist()
                assert len(all_ids)==4*len(part)
                for j,(r,_) in enumerate(part):
                    ids=all_ids[4*j:4*j+4]
                    ids=[a[:a.index(tok.eos_token_id)+1] if tok.eos_token_id in a else a for a in ids]
                    print(json.dumps(dict(id=r["sample_id"],raw=tok.batch_decode(ids,skip_special_tokens=True),tokens=sum(map(len,ids)))),file=f)
                f.flush();print("groups",i+len(part),"/120",flush=True)
    totals={s:Counter() for s in SPLITS}
    with (out/"cases.jsonl").open("x") as f:
        for (r,p),x in zip(pack,load_jsonl(out/"raw.jsonl"),strict=True):
            assert r["sample_id"]==x["id"] and len(x["raw"])==4
            result=score(r,p,x["raw"]);totals[r["subset"]].update(result["flags"])
            print(json.dumps(result),file=f)
    report=dict(by_split=totals,raw=digest(out/"raw.jsonl"),cases=digest(out/"cases.jsonl"))
    (out/"results.json").write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=="__main__":
    main()
