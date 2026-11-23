"""Independently verify actions, locality and costs, then report K=1/2/4 sensitivity."""
from collections import Counter
import json
from pathlib import Path
from audit_warmup_rollouts import shape
from confirm_one_edit import OUT, make_panel
from eval_repair_sft import read
from probe_e2_format import parse
from probe_one_edit_repair import choose
from rescore_v4_side import digest,load_jsonl
from run_e1 import strict_parse
from trust_env import check,default_plan,normalize_constraint


def one_edit(a,b,t):
    if not a or not b or not shape(a,t) or not shape(b,t): return False
    if len(a)==len(b):
        d=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
        if d==[len(a)-2,len(a)-1] and a[-2:]==b[-2:][::-1]: return True
        return len(d)==1 and any({a[d[0]],b[d[0]]}<=set(s["alternatives"]) for s in t["stages"])
    longer,shorter=(a,b) if len(a)>len(b) else (b,a)
    return len(longer)-len(shorter)==1 and any(v in t["optional"] and longer[:i]+longer[i+1:]==shorter for i,v in enumerate(longer))


def main():
    pack,hs=make_panel();prot=read(OUT/"protocol.json");agg=read(OUT/"results.json")
    saved=load_jsonl(OUT/"cases.jsonl");raw=load_jsonl(OUT/"raw.jsonl")
    assert hs==prot["sources"] and prot["ids"]==[r["sample_id"] for r,_ in pack]
    assert digest(OUT/"cases.jsonl")==agg["cases"] and digest(OUT/"raw.jsonl")==agg["raw"]
    totals={sp:Counter() for sp in agg["by_split"]};costs=Counter()
    for (r,p),x,y in zip(pack,raw,saved,strict=True):
        t=r["task"];g=r["gold"]["constraints"]
        assert x["id"]==y["id"]==r["sample_id"]
        aa=[parse(v,sorted(t["tools"]),"names") for v in x["raw"]]
        pred=[c for c in (strict_parse(p) or {}).get("constraints",[]) if normalize_constraint(c,t) is not None]
        candidates=[i for i,a in enumerate(aa) if shape(a,t) and check(t,a,[])["completed"]]
        ref=min(candidates,key=lambda i:len(check(t,aa[i],pred)["violations"])) if candidates else 0
        assert y["source_index"]==ref and aa[ref]==y["actions"]["rerank"]
        for method,a in y["actions"].items():
            safe=bool(shape(a,t) and check(t,a,g)["safe_success"])
            assert safe==y["safe"][method]
            if g: totals[r["subset"]][method]+=int(safe)
            else: totals[r["subset"]]["keep_"+method]+=int(a==default_plan(t))
        b=y["actions"]["repair"]
        if b!=aa[ref]:
            assert any(one_edit(aa[i],b,t) for i in candidates)
            assert not check(t,b,pred)["violations"] and check(t,b,[])["completed"]
        costs.update(generated_tokens=x["tokens"],groups=1)
        if g:
            for k in (1,2,4):
                _,b,_,nn,_=choose(t,aa[:k],pred,x["id"])
                if k==4: assert b==y["actions"]["repair"]
                costs.update({f"safe_with_{k}":int(bool(shape(b,t) and check(t,b,g)["safe_success"])),
                              f"neighbors_with_{k}":nn})
    for sp,c in totals.items():
        assert all(agg["by_split"][sp][k]==v for k,v in c.items())
    report=dict(verified=totals,cost_sensitivity=costs,code=digest(Path(__file__)))
    (OUT/"independent-replay.json").write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=="__main__":
    main()
