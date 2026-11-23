"""Development diagnostic: select from identical frozen samples with public, predicted rules."""
from collections import Counter
import fcntl
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


def main():
    lock=(PARENT/"planner-probe.lock").open("a")
    fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
    dev=ROOT/"data/processed_v4/dev.jsonl"
    panel=OUT/"preventive-comparison-v1/protocol.json"
    prot=json.loads(panel.read_text())
    assert digest(dev)==prot["dev"]
    rows=load_jsonl(dev)
    src=COMP/"trained_predictions/dev.jsonl"
    by={r["sample_id"]:(r,p) for r,p in zip(rows,aligned(rows,load_jsonl(src)),strict=True)}
    cases=[by[k] for k in prot["ids"]]
    assert len(cases)==len({r["group_id"] for r,_ in cases})==120
    DEST.mkdir(exist_ok=False)
    cfg=dict(source=digest(dev),panel=digest(panel),cache=digest(src),warm=digest(WARM/"adapter/adapter_model.safetensors"),
             code=digest(Path(__file__)),T=.8,G=4,seed=82601,max_new_tokens=160,mode="exploratory reused dev",
             primary="gold strict safe success: predicted selector minus first strictly complete (same candidates)",
             comparator="symbolic planner with same cached predicted rules: no neural planner forwards",
             diagnostic="gold selector is nondeployable candidate coverage; N separately audited for default matches")
    (DEST/"protocol.json").write_text(json.dumps(cfg,indent=2))
    tok,model=load(WARM/"adapter")
    counts={}; pairs={k:Counter() for k in ("pred-minus-functional","oracle-minus-pred")}
    cost=0
    with torch.inference_mode(), (DEST/"cases.jsonl").open("x") as f:
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
                if gold:
                    assert safe["oracle"]>=safe["pred"]
                    for a,b,key in [("pred","functional","pred-minus-functional"),("oracle","pred","oracle-minus-pred")]:
                        pairs[key].update(n=1,wins=int(safe[a] and not safe[b]),losses=int(safe[b] and not safe[a]))
                cost+=sum(lens)
                print(json.dumps(dict(id=r["sample_id"],variant=r["variant"],raw=texts,tokens=lens,
                                      selected=ix,symbolic=sym,safe=safe)),file=f)
            f.flush()
            print(f"groups {i+len(batch)}/{len(cases)}",flush=True)
    assert all(v["constrained"]==90 and v["none"]==30 for v in counts.values())
    report=dict(counts=counts,paired=pairs,tokens=cost,raw_sha256=digest(DEST/"cases.jsonl"))
    (DEST/"results.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=="__main__":
    main()
