"""Development diagnostic: select from identical frozen samples with public, predicted rules."""
from collections import Counter
import argparse
import fcntl
import hashlib
import json
from pathlib import Path

import torch
from audit_warmup_rollouts import shape
from eval_e2_credit import decode_config, inputs, load
from prepare_e2_credit_panel import COMP, OUT, PARENT, WARM
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import aligned, digest, load_jsonl
from run_e1 import strict_parse
from trust_env import check, default_plan, normalize_constraint, plan

DEST=PARENT/"shared-candidate-selection-dev-v1"


def rate(task,acts,cs):
    result=check(task,acts,cs)
    done=bool(result["completed"] and shape(acts,task))
    return done,done and result["safe_success"],len(result["violations"])


def select(task,acts,cs):
    # Incomplete plans are tied at fallback priority; earlier index breaks ties.
    scores=[rate(task,a,cs) for a in acts]
    return min(range(len(acts)),key=lambda j:(not scores[j][0],scores[j][2] if scores[j][0] else 0,j))


def main(transfer=False):
    lock=(PARENT/"planner-probe.lock").open("a")
    fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
    splits=("test_tpl_ho","test_tool_ho") if transfer else ("dev",)
    folder=PARENT/"shared-candidate-selection-transfer-v1" if transfer else DEST
    panel=(PARENT/"frozen-planner-transfer-v1" if transfer else OUT/"preventive-comparison-v1")/"protocol.json"
    prot=json.loads(panel.read_text())
    cases=[]; datahash={}; predhash={}
    for sp in splits:
        dev=ROOT/f"data/processed_v4/{sp}.jsonl"
        rows=load_jsonl(dev)
        src=COMP/f"trained_predictions/{sp}.jsonl"
        datahash[sp]=digest(dev); predhash[sp]=digest(src)
        assert datahash[sp]==(prot["data"][sp] if transfer else prot["dev"])
        by={r["sample_id"]:(r,p) for r,p in zip(rows,aligned(rows,load_jsonl(src)),strict=True)}
        if not transfer:
            cases.extend(by[k] for k in prot["ids"])
            continue
        prev=json.loads((PARENT/"frozen-planner-swap-panel-v1/config.json").read_text())
        old=set(prot["ids"])|set(prev["sources"][sp]["ids"])
        used={r["group_id"] for r in rows if r["sample_id"] in old}
        for variant in ("explicit","implicit","none"):
            pool=[r for r in rows if r["variant"]==variant and r["group_id"] not in used]
            pool.sort(key=lambda r:hashlib.sha256(("selection-transfer-v1|"+r["group_id"]).encode()).digest())
            for r in pool[:20]:
                cases.append(by[r["sample_id"]]);used.add(r["group_id"])
    assert len(cases)==len({r["group_id"] for r,_ in cases})==120
    folder.mkdir(exist_ok=False)
    cfg=dict(source=datahash,panel=digest(panel),ids=[r["sample_id"] for r,_ in cases],cache=predhash,warm=digest(WARM/"adapter/adapter_model.safetensors"),
             code=digest(Path(__file__)),T=.8,G=4,seed=82601,max_new_tokens=160,mode="E1-used splits, disjoint prior E2 groups" if transfer else "exploratory reused dev",
             primary="gold strict safe success: predicted selector minus first strictly complete (same candidates)",
             comparator="symbolic planner with same cached predicted rules: no neural planner forwards",
             diagnostic="gold selector is nondeployable candidate coverage; N separately audited for default matches")
    (folder/"protocol.json").write_text(json.dumps(cfg,indent=2))
    tok,model=load(WARM/"adapter")
    counts={}; pairs={k:Counter() for k in ("pred-minus-functional","oracle-minus-pred")}
    cost=0; bysplit={}
    with torch.inference_mode(), (folder/"cases.jsonl").open("x") as f:
        for i in range(0,len(cases),4):
            batch=cases[i:i+4]
            inp=inputs(tok,[r for r,_ in batch])
            torch.manual_seed(cfg["seed"]+i)
            outs=model.generate(**inp,generation_config=decode_config(tok,True))[:,inp.input_ids.shape[1]:].cpu().tolist()
            assert len(outs)==4*len(batch)
            for j,(r,raw_pred) in enumerate(batch):
                task=r["task"]
                pred=strict_parse(raw_pred)
                cs=[c for c in (pred or {}).get("constraints",[]) if normalize_constraint(c,task) is not None]
                texts=[]; lens=[]
                for ids in outs[4*j:4*j+4]:
                    if tok.eos_token_id in ids: ids=ids[:ids.index(tok.eos_token_id)+1]
                    lens.append(len(ids));texts.append(tok.decode(ids,skip_special_tokens=True))
                acts=[parse(t,sorted(task["tools"]),"names") for t in texts]
                ix={"first":0,"functional":select(task,acts,[]),"pred":select(task,acts,cs)}
                sym,_=plan(task,cs)
                gold=r["gold"]["constraints"]
                ix["oracle"]=select(task,acts,gold)
                choices={k:acts[v] for k,v in ix.items()}
                choices["symbolic"]=sym
                safe={}
                for k,a in choices.items():
                    done,safe[k],_=rate(task,a,gold)
                    bucket=counts.setdefault(k,Counter())
                    n=r["variant"]=="none"
                    bucket.update(n=1,done=done,constrained=int(not n),constrained_done=int(done and not n),
                                  safe_constrained=int(safe[k] and not n),none=int(n),
                                  none_default=int(n and safe[k] and a==default_plan(task)))
                    bysplit.setdefault(r["subset"],{}).setdefault(k,Counter()).update(
                        constrained=int(not n),safe=int(safe[k] and not n),none=int(n),default=int(n and safe[k] and a==default_plan(task)))
                if gold:
                    assert safe["oracle"]>=safe["pred"]
                    for a,b,key in [("pred","functional","pred-minus-functional"),("oracle","pred","oracle-minus-pred")]:
                        pairs[key].update(n=1,wins=int(safe[a] and not safe[b]),losses=int(safe[b] and not safe[a]))
                cost+=sum(lens)
                print(json.dumps(dict(id=r["sample_id"],variant=r["variant"],raw=texts,tokens=lens,
                                      selected=ix,symbolic=sym,safe=safe)),file=f)
            f.flush()
            print(f"groups {i+len(batch)}/{len(cases)}",flush=True)
    assert all((v["constrained"],v["none"])==((80,40) if transfer else (90,30)) for v in counts.values())
    report=dict(counts=counts,by_split=bysplit,paired=pairs,tokens=cost,raw_sha256=digest(folder/"cases.jsonl"))
    (folder/"results.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--transfer",action="store_true")
    main(p.parse_args().transfer)
