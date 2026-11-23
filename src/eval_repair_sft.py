"""Frozen four-candidate evaluation for the verifier-guided repair SFT pilot."""
import argparse
from collections import Counter
import fcntl
import hashlib
import json
from pathlib import Path

import torch
from eval_e2_credit import decode_config, inputs, load
from prepare_e2_credit_panel import COMP, PARENT, WARM
from probe_e2_candidate_selection import rate, select
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import aligned, digest, load_jsonl
from run_e1 import strict_parse
from trust_env import default_plan, normalize_constraint, plan


DEST = PARENT / "verified-repair-sft-1.7B-v1"
SPLITS = ("test_tpl_ho", "test_tool_ho")


def read(p):
    return json.loads(p.read_text())


def freeze():
    prior = read(PARENT/"frozen-planner-swap-panel-v1/config.json")
    used_ids = set(read(PARENT/"frozen-planner-transfer-v1/protocol.json")["ids"])
    used_ids.update(read(PARENT/"shared-candidate-selection-transfer-v1/protocol.json")["ids"])
    cases = []
    hashes = {}
    for sp in SPLITS:
        data = ROOT/f"data/processed_v4/{sp}.jsonl"
        predictions = COMP/f"trained_predictions/{sp}.jsonl"
        rows = load_jsonl(data)
        hashes[sp] = [digest(data), digest(predictions)]
        by = {r["sample_id"]: p for r,p in zip(rows,aligned(rows,load_jsonl(predictions)),strict=True)}
        old = used_ids | set(prior["sources"][sp]["ids"])
        excluded = {r["group_id"] for r in rows if r["sample_id"] in old}
        for variant in ("explicit","implicit","none"):
            pool = [r for r in rows if r["variant"]==variant and r["group_id"] not in excluded]
            pool.sort(key=lambda r: hashlib.sha256(("verified-repair-F1|"+r["group_id"]).encode()).digest())
            assert len(pool)>=20
            for r in pool[:20]:
                excluded.add(r["group_id"])
                cases.append((r, by[r["sample_id"]]))
    assert len(cases)==len({r["group_id"] for r,_ in cases})==120
    config = dict(ids=[r["sample_id"] for r,_ in cases], hashes=hashes,
                  warm=digest(WARM/"adapter/adapter_model.safetensors"),
                  code=digest(Path(__file__)), seed=91011, generation="4 samples, T=.8, top_p=1, limit 160",
                  primary="gold safe and strictly complete among four, on constrained tasks",
                  secondary="safe after compiler selection, functional completion, N default; compared by identical IDs",
                  comparator="uniform vs verified action-token weighted SFT; same train pairs, tokens, initialization, updates and inference",
                  limits="one training order and sampling seed; E1-used splits, groups excluded from three previous E2 panels")
    DEST.mkdir(exist_ok=True)
    protocol = DEST/"panel.json"
    if protocol.exists():
        assert read(protocol)==config
    else:
        with protocol.open("x") as f: json.dump(config,f,indent=2)
    return cases


def evaluate(arm):
    cases=freeze()
    dest=DEST/arm
    dest.mkdir(exist_ok=True)
    adapter=(WARM if arm=="warm" else dest)/"adapter"
    tok,model=load(adapter)
    counts={sp:Counter() for sp in SPLITS}
    with (dest/"cases.jsonl").open("x") as f, torch.inference_mode():
        for i in range(0,len(cases),4):
            batch=cases[i:i+4]
            inp=inputs(tok,[r for r,_ in batch])
            torch.manual_seed(91011+i)
            all_ids=model.generate(**inp,generation_config=decode_config(tok,True))[:,inp.input_ids.shape[1]:].cpu().tolist()
            assert len(all_ids)==4*len(batch)
            for j,(r,p) in enumerate(batch):
                t=r["task"]; gold=r["gold"]["constraints"]
                pred=[c for c in (strict_parse(p) or {}).get("constraints",[]) if normalize_constraint(c,t) is not None]
                part=all_ids[4*j:4*j+4]
                part=[a[:a.index(tok.eos_token_id)+1] if tok.eos_token_id in a else a for a in part]
                raw=tok.batch_decode(part,skip_special_tokens=True)
                acts=[parse(v,sorted(t["tools"]),"names") for v in raw]
                flags=[rate(t,a,gold) for a in acts]
                ix=select(t,acts,pred); fx=select(t,acts,[])
                sym,_=plan(t,pred)
                n=r["variant"]=="none"
                values=dict(n=1, constrained=int(not n), covered=int(not n and any(z[1] for z in flags)),
                     safe=int(not n and flags[ix][1]), functional_safe=int(not n and flags[fx][1]),
                     completed=int(not n and flags[ix][0]), symbolic=int(not n and rate(t,sym,gold)[1]),
                     none=int(n), none_default=int(n and flags[ix][1] and acts[ix]==default_plan(t)),
                     tokens=sum(map(len,part)))
                print(json.dumps(dict(id=r["sample_id"],variant=r["variant"],raw=raw,selection=ix,flags=values)),file=f)
                counts[r["subset"]].update(values)
            f.flush()
            print(arm,"groups",i+len(batch),"/120",flush=True)
    for c in counts.values(): assert c["constrained"]==40 and c["none"]==20
    report=dict(by_split=counts,raw=digest(dest/"cases.jsonl"),adapter=digest(adapter/"adapter_model.safetensors"))
    (dest/"results.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("arm",choices=("warm","uniform","repair"))
    arm=p.parse_args().arm
    with (PARENT/"planner-probe.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        evaluate(arm)
