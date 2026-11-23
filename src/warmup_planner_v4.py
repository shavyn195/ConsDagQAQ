"""Small paired SFT reachability experiment; uses only the frozen v4 train split."""
import fcntl
import json
import random
from collections import Counter
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

from probe_e2_format import choose, parse
from probe_e2_planner_v1 import DATA, MODEL, ROOT, prompt, select
from rescore_v4_side import digest, load_jsonl
from trust_env import check

OUT = ROOT / 'outputs/e2_v4/planner-warmup-1.7B-v1'


def partition(rows):
    prior = {r['group_id'] for r in select(rows) + choose(rows)}
    rng = random.Random(723)
    probes = []
    used = set(prior)
    for v in ('explicit', 'implicit'):
        for kind in ('budget', 'deadline', 'privacy', 'order', 'tool_auth'):
            part = rng.sample([r for r in rows if r['variant'] == v and r['group_id'] not in used
                               and [c['type'] for c in r['gold']['constraints']] == [kind]], 2)
            probes.extend(part)
            used.update(r['group_id'] for r in part)
    pool = list(rows)
    rng.shuffle(pool)
    demos = []
    for row in pool:
        if row['group_id'] not in used:
            demos.append(row)
            used.add(row['group_id'])
            if len(demos) == 128:
                break
    assert len({r['group_id'] for r in probes+demos} - prior) == 148
    return probes, demos


def prefix(tok, row):
    text = tok.apply_chat_template([dict(role='user', content=prompt(row))],
                    tokenize=False, add_generation_prompt=True, enable_thinking=False)
    return tok(text, add_special_tokens=False, return_tensors='pt').input_ids.to('cuda')


def probe(model, tok, rows, arm):
    model.eval()
    stats = Counter(n=0, valid=0, completed=0, safe=0, mixed=0)
    with (OUT/(arm+'.jsonl')).open('x') as f, torch.inference_mode():
        for i, row in enumerate(rows):
            torch.manual_seed(1000+i)
            ids = prefix(tok,row)
            outs = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
                    do_sample=True, num_return_sequences=4, temperature=0.8, top_k=0, top_p=0.95,
                    max_new_tokens=160, pad_token_id=tok.eos_token_id)
            flags = set()
            for out in outs:
                raw = tok.decode(out[ids.shape[1]:],skip_special_tokens=True).strip()
                actions = parse(raw, sorted(row['task']['tools']), 'names')
                result = check(row['task'], actions, row['gold']['constraints'])
                done,safe = result['completed'],result['safe_success']
                stats.update(n=1,valid=int(actions is not None),completed=int(done),safe=int(safe))
                flags.add((done,safe))
                print(json.dumps(dict(id=row['sample_id'],raw=raw,actions=actions,result=result)),file=f,flush=True)
            stats['mixed'] += int((True, True) in flags and (True, False) in flags)
    print(arm,dict(stats),flush=True)
    return dict(stats)


def main():
    lock = (OUT.parent/'planner-probe.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    probes,demos = partition(load_jsonl(DATA))
    OUT.mkdir(exist_ok=False)
    meta = dict(data=digest(DATA), code=digest(Path(__file__)), model=str(MODEL),seed=42,
                probes=[r['sample_id'] for r in probes],demos=[r['sample_id'] for r in demos],
                rank=8,alpha=16,lr=2e-4,grad_accum=2,epochs=1,training='bf16, completion-only; gold train witness, N default',
                decoding=dict(temperature=.8,top_p=.95,top_k=0,group_size=4,max_new_tokens=160),
                criterion='diagnostic feasibility only: at least one group has both safe and unsafe completed trajectories')
    (OUT/'config.json').write_text(json.dumps(meta,indent=2))
    tok = AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(MODEL,dtype=torch.bfloat16,device_map='cuda',local_files_only=True)
    before = probe(base,tok,probes,'base')
    torch.manual_seed(42)
    model = get_peft_model(base,LoraConfig(r=8,lora_alpha=16,lora_dropout=0.0,
                target_modules=['q_proj','k_proj','v_proj','o_proj'],task_type='CAUSAL_LM'))
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params,lr=2e-4)
    with (OUT/'loss.jsonl').open('x') as f:
        for i,row in enumerate(demos):
            target = row['default_plan'] if row['variant']=='none' else row['witness_plan']
            assert check(row['task'],target,row['gold']['constraints'])['safe_success']
            pre = prefix(tok,row)
            end = tok(json.dumps(target,separators=(',',':'))+tok.eos_token,
                      add_special_tokens=False,return_tensors='pt').input_ids.to('cuda')
            seq = torch.cat([pre,end],dim=1)
            labels = torch.cat([torch.full_like(pre,-100),end],dim=1)
            loss = model(input_ids=seq,labels=labels,use_cache=False).loss
            if not torch.isfinite(loss):
                raise FloatingPointError(f'Nonfinite loss at {i}')
            (loss/2).backward()
            if i%2==1:
                norm = torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True)
                opt.step()
                if not all(torch.isfinite(p).all() for p in params):
                    raise FloatingPointError(f'Nonfinite parameter at {i}')
                opt.zero_grad(set_to_none=True)
                print(json.dumps(dict(step=(i+1)//2,last_micro_loss=loss.item(),grad_norm=norm.item())),file=f,flush=True)
    model.save_pretrained(OUT/'adapter')
    after = probe(model,tok,probes,'warm')
    (OUT/'scores.json').write_text(json.dumps(dict(groups=len(probes),base=before,warm=after),indent=2))


if __name__=='__main__':
    main()
