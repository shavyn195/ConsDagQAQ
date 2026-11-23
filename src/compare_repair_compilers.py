"""Swap only the compiler cache on the same saved candidates, rule and environment."""
import argparse
from collections import Counter
import json
from pathlib import Path

from confirm_one_edit import OUT as SMALL,score
from eval_empty_route import route
from eval_repair_sft import SPLITS,read
from full_one_edit import OUT as LARGE
from prepare_e2_credit_panel import COMP
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import aligned,digest,load_jsonl
from trust_env import check,default_plan
from audit_warmup_rollouts import shape


def main(folder):
    xs=load_jsonl(folder/"raw.jsonl"); old=load_jsonl(folder/"cases.jsonl")
    pr=read(folder/"protocol.json"); ref=read(folder/"results.json")
    assert digest(folder/"raw.jsonl")==ref["raw"] and digest(folder/"cases.jsonl")==ref["cases"]
    assert pr["ids"]==[x["id"] for x in xs]==[y["id"] for y in old]
    data={}; cache={};sha={}
    arms=("0.6B","qwen-max-zero","qwen-max-few","deepseek-v4-pro-0813-few")
    for sp in SPLITS:
        dd=ROOT/f"data/processed_v4/{sp}.jsonl";rows=load_jsonl(dd)
        assert digest(dd)==pr["sources"][sp][0]
        allids={r["sample_id"] for r in rows}
        data.update({r["sample_id"]:r for r in rows})
        for a in arms:
            target=(COMP/"trained_predictions" if a=="0.6B" else ROOT/"outputs/e1_v4_side"/a)/dd.name
            rec=load_jsonl(target);sha[a+"-"+sp]=digest(target)
            if a=="0.6B": pp=aligned(rows,rec)
            else:
                assert len(rec)==len(rows) and {p["sample_id"] for p in rec}==allids
                assert all(isinstance(p.get("raw"),str) for p in rec)
                by={p["sample_id"]:p["raw"] for p in rec};pp=[by[r["sample_id"]] for r in rows]
            cache.setdefault(a,{}).update(zip([r["sample_id"] for r in rows],pp,strict=True))
    dest=folder/"compiler-swap";dest.mkdir(exist_ok=False)
    protocol=dict(raw=ref["raw"],hashes=sha,arms=arms,code=digest(Path(__file__)),
                  note="fixed trained 1.7B generator, same four plans; replace only predicted rule source. Cached PE, no new API use.")
    (dest/"protocol.json").write_text(json.dumps(protocol,indent=2))
    sums={a:{s:Counter() for s in SPLITS} for a in arms}
    with (dest/"rows.jsonl").open("x") as f:
        for i,(x,y) in enumerate(zip(xs,old,strict=True)):
            r=data[x["id"]];t=r["task"];gold=r["gold"]["constraints"]
            checks={}
            for a in arms:
                p=cache[a][x["id"]]
                res=y if a=="0.6B" else score(r,p,x["raw"])
                selected,empty=route(p,t,res["actions"]["repair"])
                safe=bool(shape(selected,t) and check(t,selected,gold)["safe_success"])
                checks[a]=dict(safe=safe,default=selected==default_plan(t),empty=empty)
                c=sums[a][r["subset"]]
                if gold:
                    c.update(n=1,rerank=res["safe"]["rerank"],repair=res["safe"]["repair"],routed=safe,
                             symbolic=res["safe"]["symbolic"],false_empty=int(empty),
                             wins=int(safe and not checks["0.6B"]["safe"]),losses=int(checks["0.6B"]["safe"] and not safe))
                else: c.update(none=1,none_default=checks[a]["default"],true_empty=int(empty))
            print(json.dumps(dict(id=x["id"],checks=checks)),file=f)
            if (i+1)%200==0:print("compared",i+1,"/",len(xs),flush=True)
    out=dict(by_arm=sums,source=ref["raw"],scored=digest(dest/"rows.jsonl"))
    (dest/"results.json").write_text(json.dumps(out,indent=2));print(json.dumps(out))


if __name__=="__main__":
    pp=argparse.ArgumentParser();pp.add_argument("--full",action="store_true")
    main(LARGE if pp.parse_args().full else SMALL)
