"""Run the prevention extension with the unchanged v1 optimizer/sampler in a separate process."""
import argparse
from collections import Counter
import fcntl
import json
import math
from pathlib import Path
import statistics
import sys

import torch
import train_e2_credit as driver
from e2_preventive_credit import score_with_prevention, preventive_advantages
from eval_e2_credit import load, inputs, decode_config
from prepare_e2_credit_panel import OUT, PARENT, panel as select_panel
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import digest, load_jsonl
from trust_env import check, default_plan
from audit_warmup_rollouts import shape

DEST = OUT/"preventive-comparison-v1"
DEV = ROOT/"data/processed_v4/dev.jsonl"
ARMS = ("trace","action","protect","protect_shifted")
SEEDS = (42,43,44)


def freeze():
    DEST.mkdir(exist_ok=False)
    data = load_jsonl(DEV)
    base = json.loads((OUT/"panel.json").read_text())
    assert digest(DEV)==base["data"]["dev"]
    prior = {r["group_id"] for r in data if r["sample_id"] in set(base["dev"])}
    assert len(prior)==160
    cases=select_panel(data,prior.copy(),120,20261123)
    assert len({r["group_id"] for r in cases}-prior)==120
    conf=dict(ids=[r["sample_id"] for r in cases],dev=digest(DEV),panel=digest(OUT/"panel.json"),
              seeds=SEEDS,arms=ARMS,description="120 v4 dev groups unused by v1 E2 dev panel; not a blind external test.",
              primary="paired strict safe success on 90 constrained queries, by seed; report all results",
              secondary="strict completion and exact default preservation for 30 N samples",
              revision="after original s42 seen: run if any s42-44 nonpositive against trace or shifted, or median action-trace <=6/120",
              direct_comparison="protect minus action; protect minus protect_shifted isolates position of preventive credit",
              code={f:digest(ROOT/"src"/f) for f in ("train_e2_credit.py","run_e2_prevention.py","e2_preventive_credit.py","eval_e2_credit.py")})
    (DEST/"protocol.json").write_text(json.dumps(conf,indent=2))


def gate():
    replay=json.loads((OUT/"prevention-train-v1.json").read_text())
    assert replay["counts"]["changed_groups"]>=8
    res=[json.loads((OUT/f"paired-dev-s{s}.json").read_text())["paired"] for s in SEEDS]
    nets=[r["action-minus-trace"]["net"] for r in res]
    shifted=[r["action-minus-shifted"]["net"] for r in res]
    run=min(nets+shifted)<=0 or statistics.median(nets)<=6
    (DEST/"decision.json").write_text(json.dumps(dict(run=run,trace_nets=nets,shifted_nets=shifted)))
    return run


def where(arm,seed):
    return (DEST if arm.startswith("protect") else OUT)/f"{arm}-s{seed}"


def train(arm,seed):
    run=where(arm,seed)
    run.mkdir(exist_ok=False)
    protocol=json.loads((DEST/"protocol.json").read_text())
    for f,h in protocol["code"].items():
        assert digest(ROOT/"src"/f)==h
    # This entry point owns the process. Only the two reward functions differ from v1.
    driver.score_plan=score_with_prevention
    driver.advantages=preventive_advantages
    try:
        driver.run(arm,seed,run)
    except BaseException as exc:
        (run/"failure.json").write_text(json.dumps(dict(type=type(exc).__name__,reason=str(exc))))
        raise


def assess(arm,seed):
    prot=json.loads((DEST/"protocol.json").read_text())
    assert digest(DEV)==prot["dev"]
    rows={r["sample_id"]:r for r in load_jsonl(DEV)}
    rows=[rows[k] for k in prot["ids"]]
    d=where(arm,seed)
    assert (d/"done.json").is_file()
    tok,model=load(d/"adapter")
    stats=Counter()
    with (DEST/f"assessment-{arm}-{seed}.jsonl").open("x") as f,torch.inference_mode():
        for i in range(0,len(rows),8):
            batch=rows[i:i+8]
            inp=inputs(tok,batch)
            out=model.generate(**inp,generation_config=decode_config(tok,False))
            for r,tokens in zip(batch,out[:,inp.input_ids.shape[1]:],strict=True):
                raw=tok.decode(tokens,skip_special_tokens=True)
                acts=parse(raw,sorted(r["task"]["tools"]),"names")
                res=check(r["task"],acts,r["gold"]["constraints"])
                done=bool(res["completed"] and shape(acts,r["task"]))
                safe=bool(done and res["safe_success"])
                n=r["variant"]=="none"
                stats.update(n=1,completed=done,constrained=not n,constrained_safe=safe and not n,
                             none=n,none_faithful=n and safe and acts==default_plan(r["task"]))
                print(json.dumps(dict(id=r["sample_id"],variant=r["variant"],raw=raw,done=done,safe=safe)),file=f,flush=True)
    assert stats["constrained"]==90 and stats["none"]==30
    (DEST/f"assessment-{arm}-{seed}.json").write_text(json.dumps(stats))


def compare():
    prot=json.loads((DEST/"protocol.json").read_text())
    pairs={}
    for s in SEEDS:
        by={a:load_jsonl(DEST/f"assessment-{a}-{s}.jsonl") for a in ARMS}
        for a in ARMS:
            assert [r["id"] for r in by[a]]==prot["ids"]
        for control in ("action","protect_shifted","trace"):
            pairs[f"protect-minus-{control}-s{s}"]=dict(Counter(
                (("win" if x["safe"] else "loss") if x["safe"]!=y["safe"] else "tie")
                for x,y in zip(by["protect"],by[control],strict=True) if x["variant"]!="none"))
    (DEST/"comparison.json").write_text(json.dumps(pairs,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("op",choices=("freeze","gate","train","assess","compare"))
    p.add_argument("--arm",choices=ARMS)
    p.add_argument("--seed",type=int,choices=SEEDS)
    a=p.parse_args()
    if a.op=="freeze": freeze()
    elif a.op=="gate": sys.exit(0 if gate() else 3)
    elif a.op=="compare": compare()
    else:
        lock=(PARENT/"planner-probe.lock").open("a")
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        if a.op=="train":
            assert a.arm in ("protect","protect_shifted")
            train(a.arm,a.seed)
        else:
            assess(a.arm,a.seed)
