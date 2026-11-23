"""Single-pass online group-relative policy gradients, fixed panel, matched arms.

One on-policy gradient at the sampling policy per prompt (GRPO at ratio 1,
KL coefficient 0; no replay or repeated PPO epochs). Not a TAG/RLVP reproduction.
"""
import argparse
import fcntl
import json
from pathlib import Path
import time

import torch
from bind_public_scope import bind
from e2_credit import score_plan, advantages, role_tokens
from eval_e2_credit import decode_config, inputs, load, evaluate
from prepare_e2_credit_panel import OUT, PARENT, WARM
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import digest, load_jsonl
from run_e1 import strict_parse
from trust_env import normalize_constraint


def run(arm, seed, dest):
    st = time.monotonic()
    panel = json.loads((OUT/"panel.json").read_text())
    cache = OUT/"compiler.jsonl"
    src = ROOT/"data/processed_v4/train.jsonl"
    assert digest(src) == panel["data"]["train"]
    assert digest(cache) == json.loads((OUT/"cache-ready.json").read_text())["sha256"]
    assert digest(WARM/"adapter/adapter_model.safetensors") == panel["warm"]
    predictions = load_jsonl(cache)
    assert [p["id"] for p in predictions] == panel["train"]
    rows = {r["sample_id"]:r for r in load_jsonl(src)}
    cfg = dict(arm=arm,seed=seed,groups=len(predictions),group_size=4,lr=1e-5,temperature=.8,
               max_new_tokens=160,top_k=0,top_p=1,beta=0,updates_per_group=1,std_floor=.25,clip_norm=1.,
               precision="bf16",optimizer="AdamW no decay; skip zero-credit groups",
               panel=digest(OUT/"panel.json"),compiler_cache=digest(cache),warm=panel["warm"],
               code={n:digest(ROOT/"src"/n) for n in ("train_e2_credit.py","e2_credit.py","eval_e2_credit.py",
                     "probe_e2_planner_v1.py","probe_e2_format.py","trust_env.py","audit_warmup_rollouts.py")},
               eval="dev greedy, strict completion + gold constraints; N also report default-plan match")
    (dest/"config.json").write_text(json.dumps(cfg,indent=2))
    torch.manual_seed(seed)
    tok, model = load(WARM/"adapter",trainable=True)
    params = [p for p in model.parameters() if p.requires_grad]
    assert params and all(p.dtype == torch.float32 for p in params)
    opt = torch.optim.AdamW(params, lr=cfg["lr"], weight_decay=0.)
    updates = 0
    with (dest/"rollouts.jsonl").open("x") as rawf, (dest/"progress.jsonl").open("x") as log:
        for j, pred in enumerate(predictions):
            row = rows[pred["id"]]
            obj = strict_parse(bind(pred["raw"],row["catalog"]))
            cs = [c for c in (obj or {}).get("constraints",[]) if normalize_constraint(c,row["task"]) is not None]
            inp = inputs(tok,[row])
            torch.manual_seed(seed*1000+j)
            with torch.no_grad():
                seq = model.generate(**inp,generation_config=decode_config(tok,True))
            pre = inp.input_ids.shape[1]
            ends, scores, maps, observations = [], [], [], []
            for gen in seq[:,pre:].tolist():
                if tok.eos_token_id in gen:
                    gen = gen[:gen.index(tok.eos_token_id)+1]
                raw = tok.decode(gen,skip_special_tokens=True,clean_up_tokenization_spaces=False)
                acts = parse(raw, sorted(row["task"]["tools"]), "names")
                scores.append(score_plan(row["task"], acts, cs))
                maps.append(role_tokens(tok,gen,acts))
                observations.append(dict(raw=raw,actions=acts,token_ids=gen,role_positions=maps[-1],**scores[-1]))
                ends.append(gen)
            rewards, av, moved = advantages(scores,list(map(len,ends)),maps,len(cs),arm)
            nz = any(any(abs(x)>1e-9 for x in vs) for vs in av)
            norm, pg = 0., 0.
            if nz:
                opt.zero_grad(set_to_none=True)
                for k,(end,weight) in enumerate(zip(ends,av,strict=True)):
                    if not any(weight):
                        continue
                    seq_k = seq[k:k+1,:pre+len(end)]
                    # Only materialize vocabulary logits for response positions.
                    logits = model(input_ids=seq_k, use_cache=False, logits_to_keep=len(end)+1).logits
                    logits = logits[:,:-1,:].float()/cfg["temperature"]
                    target = seq_k[:,pre:]
                    assert logits.shape[:2] == target.shape
                    logp = -torch.nn.functional.cross_entropy(logits.transpose(1,2),target,reduction="none")
                    advantage = torch.tensor(weight,device=logp.device)
                    loss = -(logp*advantage).mean()/len(ends)
                    if not torch.isfinite(loss):
                        raise FloatingPointError(f"nonfinite loss group {j}")
                    loss.backward()
                    pg += loss.detach().item()
                norm = torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True).item()
                opt.step()
                if not all(torch.isfinite(p).all().item() for p in params):
                    raise FloatingPointError(f"nonfinite parameter group {j}")
                updates += 1
            print(json.dumps(dict(id=pred["id"],cs=cs,rewards=rewards,rollouts=observations)),file=rawf,flush=True)
            step = dict(group=j+1,id=pred["id"],updated=nz,updates=updates,tokens=sum(map(len,ends)),
                        completed=sum(int(s["done"]) for s in scores),relocated=moved,
                        nonempty_source=bool(cs),loss=pg,grad_norm=norm,elapsed_s=round(time.monotonic()-st,2))
            print(json.dumps(step),file=log,flush=True)
            if j<2 or (j+1)%8==0:
                print(step,flush=True)
    model.save_pretrained(dest/"adapter")
    evaluate(tok,model,dest)
    (dest/"done.json").write_text(json.dumps(dict(groups=len(predictions),updates=updates,seed=seed,
                   seconds=time.monotonic()-st,dev_sha256=digest(dest/"dev.jsonl"))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm",required=True,choices=["function","trace","action","shifted"])
    parser.add_argument("--seed",type=int,default=42)
    args = parser.parse_args()
    guard = (PARENT/"planner-probe.lock").open("a")
    fcntl.flock(guard,fcntl.LOCK_EX | fcntl.LOCK_NB)
    out = OUT/f"{args.arm}-s{args.seed}"
    out.mkdir(exist_ok=False)
    try:
        run(args.arm,args.seed,out)
    except BaseException as exc:
        (out/"failure.json").write_text(json.dumps(dict(type=type(exc).__name__,reason=str(exc))))
        raise
