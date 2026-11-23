"""Paired train-only coverage experiment; no model updates or dev selection."""
from collections import Counter
import fcntl
import json
from pathlib import Path
import random

import torch
from audit_warmup_rollouts import shape
from eval_e2_credit import decode_config, inputs, load
from prepare_e2_credit_panel import OUT, PARENT, WARM
from probe_e2_format import choose, parse
from probe_e2_planner_v1 import DATA, select
from rescore_v4_side import digest, load_jsonl
from trust_env import check

DEST=PARENT/"temperature-coverage-1.7B-train-v1"


def main():
    guard=(PARENT/"planner-probe.lock").open("a")
    fcntl.flock(guard,fcntl.LOCK_EX | fcntl.LOCK_NB)
    rows=load_jsonl(DATA)
    by={r["sample_id"]:r for r in rows}
    used={r["group_id"] for r in select(rows)+choose(rows)}
    for file,keys in [(OUT/"panel.json",["train"]),(WARM/"config.json",["demos","probes"]),
                      (PARENT/"multiconstraint-gate-opportunity-v1/config.json",["groups"]),
                      (PARENT/"frozen-record-choice-v1/config.json",["ids"])]:
        source=json.loads(file.read_text())
        used.update(by[k]["group_id"] for key in keys for k in source[key])
    order=rows.copy()
    rng=random.Random(917251)
    rng.shuffle(order)
    panel=[]
    for variant in ("explicit","implicit"):
        for count in (1,2,3):
            part=[r for r in order if r["group_id"] not in used and r["variant"]==variant
                  and len(r["gold"]["constraints"])==count][:8]
            assert len(part)==8 and len({r["group_id"] for r in part})==8
            used.update(r["group_id"] for r in part)
            panel.extend(part)
    rng.shuffle(panel)
    DEST.mkdir(exist_ok=False)
    cfg=dict(ids=[r["sample_id"] for r in panel],train=digest(DATA),adapter=digest(WARM/"adapter/adapter_model.safetensors"),
             code=digest(Path(__file__)),seed=917251,n_per_arm=192,T=[.8,1.1],max_new_tokens=160,
             primary="groups with >=1 strict safe and >=1 strictly completed unsafe plan",
             secondary="any strict safe; strict completion; actual generated tokens through EOS; any parse failure",
             note="One shared warm planner. Equal rollout count and maximum tokens; actual costs reported. No oracle used to choose actions.")
    (DEST/"protocol.json").write_text(json.dumps(cfg,indent=2))
    tok,model=load(WARM/"adapter")
    data={t:{} for t in cfg["T"]}
    with torch.inference_mode(), (DEST/"raw.jsonl").open("x") as f:
        for i in range(0,len(panel),4):
            batch=panel[i:i+4]
            inp=inputs(tok,batch)
            for temp in cfg["T"][::1 if i%8==0 else -1]:
                torch.manual_seed(cfg["seed"]+i)
                gen=decode_config(tok,True)
                gen.temperature=temp
                seq=model.generate(**inp,generation_config=gen)[:,inp.input_ids.shape[1]:].cpu().tolist()
                assert len(seq)==len(batch)*4
                for j,r in enumerate(batch):
                    c=Counter(n=4)
                    for ids in seq[j*4:j*4+4]:
                        if tok.eos_token_id in ids:
                            ids=ids[:ids.index(tok.eos_token_id)+1]
                        raw=tok.decode(ids,skip_special_tokens=True)
                        a=parse(raw,sorted(r["task"]["tools"]),"names")
                        res=check(r["task"],a,r["gold"]["constraints"])
                        done=bool(res["completed"] and shape(a,r["task"]))
                        safe=bool(done and res["safe_success"])
                        c.update(done=done,safe=safe,tokens=len(ids),malformed=a is None)
                        print(json.dumps(dict(id=r["sample_id"],T=temp,raw=raw,done=done,safe=safe,tokens=len(ids))),file=f)
                    c.update(mixed=0<c["safe"]<c["done"],anysafe=c["safe"]>0,groups=1)
                    data[temp][r["sample_id"]]=c
            f.flush()
            print(f"paired groups {i+len(batch)}/{len(panel)}",flush=True)
    lo,hi=(data[t] for t in cfg["T"])
    assert list(lo)==list(hi)==cfg["ids"]
    summary={str(t):dict(sum(rs.values(),Counter())) for t,rs in data.items()}
    pairs={k:dict(wins=sum(hi[x][k]>lo[x][k] for x in lo),losses=sum(hi[x][k]<lo[x][k] for x in lo))
           for k in ("mixed","anysafe")}
    report=dict(counts=summary,paired=pairs,raw_sha256=digest(DEST/"raw.jsonl"))
    (DEST/"results.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=="__main__":
    main()
