"""Recompute strict selection and a relaxed-structure sensitivity from saved responses."""
import argparse
from collections import Counter
import json
from pathlib import Path
import random

from audit_warmup_rollouts import shape
from eval_repair_sft import DEST, SPLITS, read
from prepare_e2_credit_panel import COMP, PARENT
from probe_e2_format import parse
from probe_e2_planner_v1 import DATA, ROOT
from rescore_v4_side import aligned, digest, load_jsonl
from run_e1 import strict_parse
from trust_env import check, default_plan, normalize_constraint


def audit_train():
    data={r["sample_id"]:r for r in load_jsonl(DATA)}
    rows=load_jsonl(DEST/"train-pairs.jsonl")
    assert len(rows)==len({data[p["id"]]["group_id"] for p in rows})==256
    stat=Counter()
    for p in rows:
        r=data[p["id"]]
        t=r["task"];cs=r["gold"]["constraints"]
        assert shape(p["target"],t) and check(t,p["target"],cs)["safe_success"]
        pos=set();stat.update(groups=1,normalized=int(p["reordered"]),marked=int(bool(p["marked"])))
        for e in p["examples"]:
            out=check(t,e["draft"],cs)
            assert shape(e["draft"],t) and out["completed"] and not out["safe_success"]
            assert out["violations"]==e["violations"] and out["violations"]
            pos.update(e["positions"]);stat.update(edits=1)
        assert pos==set(p["marked"])
    return stat


def cases():
    prot=read(DEST/"panel.json"); by={}
    for sp in SPLITS:
        path=ROOT/f"data/processed_v4/{sp}.jsonl"
        cache=COMP/f"trained_predictions/{sp}.jsonl"
        assert [digest(path),digest(cache)]==prot["hashes"][sp]
        rows=load_jsonl(path)
        for r,p in zip(rows,aligned(rows,load_jsonl(cache)),strict=True):
            cs=(strict_parse(p) or {}).get("constraints",[])
            by[r["sample_id"]]=(r,[c for c in cs if normalize_constraint(c,r["task"]) is not None])
    return [by[k] for k in prot["ids"]]


def audit_arm(fold,arm,panel):
    sub=fold/arm
    meta=read(sub/"results.json"); raw=load_jsonl(sub/"cases.jsonl")
    assert digest(sub/"cases.jsonl")==meta["raw"]
    sums={s:Counter() for s in SPLITS}; scores=[]
    for x,(r,cs) in zip(raw,panel,strict=True):
        assert x["id"]==r["sample_id"]
        t=r["task"];gold=r["gold"]["constraints"]
        aa=[parse(s,sorted(t["tools"]),"names") for s in x["raw"]]
        assert len(aa)==4
        env=[check(t,a,gold) for a in aa]
        is_done=[bool(o["completed"] and shape(a,t)) for a,o in zip(aa,env)]
        is_safe=[bool(d and o["safe_success"]) for d,o in zip(is_done,env)]
        valid=[i for i,v in enumerate(is_done) if v]
        ix=min(valid,key=lambda i:len(check(t,aa[i],cs)["violations"])) if valid else 0
        assert x["selection"]==ix
        stats=dict(covered=int(bool(gold) and any(is_safe)),safe=int(bool(gold) and is_safe[ix]),
                   functional_safe=int(bool(gold) and is_safe[valid[0] if valid else 0]),
                   completed=int(bool(gold) and is_done[ix]),none_default=int(not gold and is_safe[ix] and aa[ix]==default_plan(t)))
        assert all(x["flags"][k]==v for k,v in stats.items())
        stats["env_covered"]=int(bool(gold) and any(o["safe_success"] for o in env))
        stats["env_selected"]=int(bool(gold) and env[ix]["safe_success"])
        scores.append(stats);sums[r["subset"]].update(stats)
    for s in SPLITS:
        assert all(meta["by_split"][s][k]==sums[s][k] for k in ("safe","covered","none_default","completed","functional_safe"))
    return scores,sums


def run(all_orders):
    rep=PARENT/"verified-repair-sft-1.7B-orders-v1"
    folds=[DEST]+([rep/"order-43",rep/"order-44"] if all_orders else [])
    panel=cases(); summary=dict(training=audit_train(),orders={},replay_script=digest(Path(__file__)))
    deltas=[]
    for fold in folds:
        assert read(fold/"repair/budget.json")==read(fold/"uniform/budget.json")
        per={};totals={}
        for arm in ("uniform","repair","warm"):
            per[arm],totals[arm]=audit_arm(fold,arm,panel)
        summary["orders"][fold.name]=totals
        deltas.append([a["covered"]-b["covered"] for a,b in zip(per["repair"],per["uniform"],strict=True)])
    # Resample distinct task groups, stratified by split and expression, retaining all matched orders.
    strata=[[i for i,(r,_) in enumerate(panel) if r["subset"]==s and r["variant"]==v]
            for s in SPLITS for v in ("explicit","implicit")]
    assert list(map(len,strata))==[20]*4
    means=[sum(x)/len(x) for x in zip(*deltas)]
    rng=random.Random(73596)
    boot=sorted(sum(means[i] for g in strata for i in rng.choices(g,k=len(g)))/80*100 for _ in range(10000))
    summary["coverage_delta_pp"]=dict(point=sum(means)/80*100,percentile95=[boot[249],boot[9749]],
                                      interpretation="paired by task group, conditional on the fixed training orders and generation seed")
    fn=(rep if all_orders else DEST)/"independent-replay.json"
    fn.write_text(json.dumps(summary,indent=2))
    print(json.dumps(dict(training=summary["training"],coverage=summary["coverage_delta_pp"])))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--all-orders",action="store_true")
    run(p.parse_args().all_orders)
