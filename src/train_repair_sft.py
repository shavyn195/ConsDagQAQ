"""Paired SFT: identical verified plans, change only loss on necessary action tokens."""
from collections import Counter
import fcntl
import gc
import hashlib
import json
from pathlib import Path

import torch
import torch.nn.functional as F
from audit_warmup_rollouts import shape
from eval_e2_credit import load
from eval_repair_sft import DEST, evaluate, read
from prepare_e2_credit_panel import OUT, PARENT, WARM, panel
from probe_e2_planner_v1 import DATA, prompt
from rescore_v4_side import digest, load_jsonl
from trust_env import check, default_plan


def training_rows():
    rows=load_jsonl(DATA)
    old=read(WARM/"config.json")
    ids=set(old["demos"]+old["probes"]+read(OUT/"panel.json")["train"])
    exclude={r["group_id"] for r in rows if r["sample_id"] in ids}
    picked=panel(rows,exclude,256,51028)
    assert len(picked)==len({r["group_id"] for r in picked})==256
    return picked


def make_pair(row):
    t=row["task"]; cs=row["gold"]["constraints"]
    target=row["witness_plan"] if cs else default_plan(t)
    original=list(target)
    if not shape(target,t):
        target=[a for a in target if a not in t["finish"]]+[a for a in target if a in t["finish"]]
    assert shape(target,t) and check(t,target,cs)["safe_success"]
    examples=[]
    def try_edit(positions, draft):
        if not shape(draft,t): return
        res=check(t,draft,cs)
        if res["completed"] and res["violations"]:
            examples.append(dict(positions=positions,draft=draft,violations=res["violations"]))
    if cs:
        for i,a in enumerate(target):
            if a in t["optional"]: try_edit([i],target[:i]+target[i+1:])
            for stage in t["stages"]:
                if a in stage["alternatives"]:
                    for b in stage["alternatives"]:
                        if b!=a: try_edit([i],target[:i]+[b]+target[i+1:])
        try_edit([len(target)-2,len(target)-1],target[:-2]+target[-2:][::-1])
    return dict(id=row["sample_id"],target=target,reordered=original!=target,examples=examples,
                marked=sorted({i for e in examples for i in e["positions"]}))


def encode(tok,row,pair):
    context=tok.apply_chat_template([dict(role="user",content=prompt(row))],tokenize=False,
                                    add_generation_prompt=True,enable_thinking=False)
    pre=tok(context,add_special_tokens=False).input_ids
    rendered=json.dumps(pair["target"],separators=(",",":"))
    suffix=tok(rendered,add_special_tokens=False,return_offsets_mapping=True)
    ranges=[]; cur=1
    for i,act in enumerate(pair["target"]):
        literal=json.dumps(act)
        assert rendered[cur:cur+len(literal)]==literal
        if i in pair["marked"]: ranges.append((cur+1,cur+len(literal)-1))
        cur+=len(literal)+1
    assert cur==len(rendered)
    mask=[any(a<right and b>left for left,right in ranges) for a,b in suffix.offset_mapping]
    assert bool(any(mask))==bool(ranges)
    end=list(suffix.input_ids)+[tok.eos_token_id]
    return pre,end,mask+[False]


def train_arm(arm,rows,pairs):
    dest=DEST/arm;dest.mkdir(exist_ok=False)
    torch.manual_seed(42)
    tok,model=load(WARM/"adapter",trainable=True)
    model.train()
    params=[p for p in model.parameters() if p.requires_grad]
    opt=torch.optim.AdamW(params,lr=2e-4)
    opt.zero_grad(set_to_none=True)
    budget=Counter()
    token_hash=hashlib.sha256()
    with (dest/"steps.jsonl").open("x") as f:
        for i,(r,p) in enumerate(zip(rows,pairs,strict=True)):
            pre,end,mask=encode(tok,r,p)
            token_hash.update(json.dumps([r["sample_id"],pre,end,mask],separators=(",",":")).encode())
            ids=torch.tensor([pre+end],device="cuda")
            logits=model(input_ids=ids,use_cache=False).logits[0,len(pre)-1:-1].float()
            losses=F.cross_entropy(logits,ids[0,len(pre):],reduction="none")
            weights=torch.ones_like(losses)
            if arm=="repair":
                weights[torch.tensor(mask,device="cuda")]=3.
            loss=(losses*weights).sum()/weights.sum()
            if not torch.isfinite(loss): raise FloatingPointError(f"{arm}: loss at {i}")
            (loss/2).backward()
            budget.update(prompt=len(pre),target=len(end),marked=sum(mask))
            if (i+1)%2==0:
                norm=torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True)
                opt.step()
                if not all(torch.isfinite(p).all() for p in params): raise FloatingPointError(f"{arm}: weights at {i}")
                opt.zero_grad(set_to_none=True)
                print(json.dumps(dict(step=(i+1)//2,loss=loss.item(),grad=norm.item())),file=f,flush=True)
                if (i+1)%32==0: print(arm,"training",(i+1)//2,"/128",flush=True)
    model.save_pretrained(dest/"adapter")
    signature=dict(tokens=budget,hash=token_hash.hexdigest(),steps=len(rows)//2)
    (dest/"budget.json").write_text(json.dumps(signature,indent=2))
    del model,opt,params
    return signature


def finish():
    stats={}
    refs={arm:load_jsonl(DEST/arm/"cases.jsonl") for arm in ("uniform","repair","warm")}
    ids=read(DEST/"panel.json")["ids"]
    assert all([r["id"] for r in rec]==ids for rec in refs.values())
    for k in ("covered","safe","functional_safe","completed","none_default"):
        group={}
        for i in (0,60):
            compare=[int(a["flags"][k])-int(b["flags"][k]) for a,b in
                     zip(refs["repair"][i:i+60],refs["uniform"][i:i+60],strict=True)
                     if (a["variant"]=="none")== (k=="none_default")]
            group[("test_tpl_ho","test_tool_ho")[i//60]]=dict(n=len(compare),wins=compare.count(1),losses=compare.count(-1),net=sum(compare))
        stats[k]=group
    (DEST/"paired.json").write_text(json.dumps(stats,indent=2))
    print("finished",json.dumps(stats),flush=True)


def main():
    with (PARENT/"planner-probe.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        assert (DEST/"warm/results.json").exists()
        rows=training_rows(); pairs=[make_pair(r) for r in rows]
        test_groups=set()
        from eval_repair_sft import freeze
        test_groups.update(r["group_id"] for r,_ in freeze())
        assert not test_groups.intersection(r["group_id"] for r in rows)
        with (DEST/"train-pairs.jsonl").open("x") as f:
            for p in pairs: print(json.dumps(p),file=f)
        n=sum(bool(p["marked"]) for p in pairs); assert n>=64
        conf=dict(source=digest(DATA),code=digest(Path(__file__)),warm=digest(WARM/"adapter/adapter_model.safetensors"),
                  train_pairs=digest(DEST/"train-pairs.jsonl"),verified_examples=sum(len(p["examples"]) for p in pairs),
                  marked_groups=n, rows=len(rows),optimizer="AdamW lr=2e-4, grad accumulation=2, norm=1",
                  precision="bf16",seed=42,epochs=1,weight=3,
                  interpretation="train-only verifier supervision; inputs exclude counterfactuals and gold; not GRPO")
        (DEST/"training.json").write_text(json.dumps(conf,indent=2))
        print("protocol",json.dumps(conf),flush=True)
        budgets=[]
        for arm in ("uniform","repair"):
            budgets.append(train_arm(arm,rows,pairs))
            gc.collect();torch.cuda.empty_cache()
        assert budgets[0]==budgets[1]
        for arm in ("uniform","repair"):
            evaluate(arm)
            gc.collect();torch.cuda.empty_cache()
        finish()


if __name__=="__main__":
    main()
