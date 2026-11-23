"""Single frozen E2 transfer assessment: E1-used holdouts; never select checkpoints by score."""
import fcntl
import hashlib
import json
from collections import Counter
from pathlib import Path
import torch
from audit_warmup_rollouts import shape
from eval_e2_credit import decode_config, inputs, load
from prepare_e2_credit_panel import OUT, PARENT
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import digest, load_jsonl
from trust_env import check, default_plan

DEST=PARENT/"frozen-planner-transfer-v1"
ARMS=("function","trace","protect")
SEEDS=(42,43,44)
SPLITS=("test_tpl_ho","test_tool_ho")


def main():
    lock=(PARENT/"planner-probe.lock").open("a")
    fcntl.flock(lock,fcntl.LOCK_EX)
    DEST.mkdir(exist_ok=False)
    previous=json.loads((PARENT/"frozen-planner-swap-panel-v1/config.json").read_text())
    rows=[]
    inputs_sha={}
    for split in SPLITS:
        path=ROOT/f"data/processed_v4/{split}.jsonl"
        inputs_sha[split]=digest(path)
        data=load_jsonl(path)
        used_ids=set(previous["sources"][split]["ids"])
        exclude={r["group_id"] for r in data if r["sample_id"] in used_ids}
        assert len(exclude)==15
        for variant in ("explicit","implicit","none"):
            eligible=[r for r in data if r["variant"]==variant and r["group_id"] not in exclude]
            eligible.sort(key=lambda r:hashlib.sha256(("e2-transfer-1122|"+r["group_id"]).encode()).digest())
            selected=eligible[:40]
            assert len(set(r["group_id"] for r in selected))==40
            exclude.update(r["group_id"] for r in selected)
            rows.extend(selected)
    assert len(rows)==len({r["group_id"] for r in rows})==240
    paths={(arm,seed): (OUT/"preventive-comparison-v1" if arm=="protect" else OUT)/f"{arm}-s{seed}" for arm in ARMS for seed in SEEDS}
    assert all((p/"done.json").is_file() for p in paths.values())
    cfg=dict(ids=[r["sample_id"] for r in rows],data=inputs_sha,seeds=SEEDS,arms=ARMS,
             adapters={f"{a}-{s}":digest(p/"adapter/adapter_model.safetensors") for (a,s),p in paths.items()},
             code=digest(Path(__file__)),batch=8,greedy=True,
             primary="trace minus function, strict safe success on constrained queries within each split",
             secondary="protect minus trace; strict completion; N default preservation. E1-used splits; exploratory transfer. No tuning.")
    (DEST/"protocol.json").write_text(json.dumps(cfg,indent=2))
    all_out={}
    for key,path in paths.items():
        arm,seed=key
        tok,model=load(path/"adapter")
        stats={sp:Counter() for sp in SPLITS}
        values={}
        with (DEST/f"{arm}-{seed}.jsonl").open("x") as f,torch.inference_mode():
            for i in range(0,len(rows),8):
                batch=rows[i:i+8]
                inp=inputs(tok,batch)
                seq=model.generate(**inp,generation_config=decode_config(tok,False))
                for r,gen in zip(batch,seq[:,inp.input_ids.shape[1]:],strict=True):
                    raw=tok.decode(gen,skip_special_tokens=True)
                    acts=parse(raw,sorted(r["task"]["tools"]),"names")
                    res=check(r["task"],acts,r["gold"]["constraints"])
                    done=bool(res["completed"] and shape(acts,r["task"]))
                    safe=bool(done and res["safe_success"])
                    n=r["variant"]=="none"
                    stats[r["subset"]].update(n=1,done=done,constrained=not n,safe_constrained=safe and not n,
                                             none=n,none_faithful=n and safe and acts==default_plan(r["task"]))
                    values[r["sample_id"]]=safe
                    print(json.dumps(dict(id=r["sample_id"],variant=r["variant"],raw=raw,done=done,safe=safe)),file=f)
                f.flush()
        assert len(values)==240
        all_out[key]=values
        (DEST/f"{arm}-{seed}.json").write_text(json.dumps(stats))
        print(arm,seed,dict(stats),flush=True)
        del model,tok
        torch.cuda.empty_cache()
    paired={}
    for seed in SEEDS:
        for a,b in (("trace","function"),("protect","trace")):
            for sp in SPLITS:
                ix=[r["sample_id"] for r in rows if r["subset"]==sp and r["variant"]!="none"]
                assert len(ix)==80
                diffs=[int(all_out[a,seed][k])-int(all_out[b,seed][k]) for k in ix]
                paired[f"{a}-{b}-{sp}-{seed}"]=dict(wins=diffs.count(1),losses=diffs.count(-1),net=sum(diffs))
    (DEST/"paired.json").write_text(json.dumps(paired,indent=2))


if __name__=="__main__":
    main()
