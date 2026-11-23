"""Check whether completion gating can change group-relative rewards on fresh multi-constraint train groups."""
from collections import Counter
from pathlib import Path
import json
import random
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from probe_e2_format import parse, choose
from probe_e2_planner_v1 import select
from warmup_planner_v4 import DATA, MODEL, ROOT, OUT as WARM, prefix
from rescore_v4_side import digest, load_jsonl
from trust_env import check
from audit_warmup_rollouts import shape

OUT=ROOT/'outputs/e2_v4/multiconstraint-gate-opportunity-v1'


def main():
    import fcntl
    lock=(OUT.parent/'planner-probe.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    data=load_jsonl(DATA)
    ids={r['sample_id']:r for r in data}
    cfg=json.loads((WARM/'config.json').read_text())
    used={ids[k]['group_id'] for k in cfg['probes']+cfg['demos']} | {r['group_id'] for r in select(data)+choose(data)}
    rng=random.Random(99411)
    rows=[]
    for n in [2,3]:
        for v in ['explicit','implicit']:
            part=rng.sample([r for r in data if r['group_id'] not in used and r['variant']==v
                             and len(r['gold']['constraints'])==n],8)
            rows.extend(part)
            used.update(r['group_id'] for r in part)
    OUT.mkdir(exist_ok=False)
    meta=dict(groups=[r['sample_id'] for r in rows],adapter=digest(WARM/'adapter/adapter_model.safetensors'),
              data=digest(DATA),code=digest(Path(__file__)),n_per_group=4,seed=99411,
              definition='Exploratory oracle: C=fraction of gold constraints not violated on a valid action list; malformed C=0. Compare A+C with A+A*C; A=original completion. No compiler, no updates.')
    (OUT/'config.json').write_text(json.dumps(meta,indent=2))
    tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(MODEL,dtype=torch.bfloat16,device_map='cuda',local_files_only=True)
    model=PeftModel.from_pretrained(model,WARM/'adapter').eval()
    stats=Counter(n=0,valid=0,completed=0,safe=0,tight_completed=0,mixed_safe_among_completed=0,
                  gate_closed=0,raw_reward_different=0,groups_different_normalized_reward=0)
    def standardized(values):
        a=torch.tensor(values,dtype=torch.float64)
        return (a-a.mean())/(a.std(unbiased=False)+1e-8)
    with (OUT/'samples.jsonl').open('x') as f, torch.inference_mode():
        for i,row in enumerate(rows):
            torch.manual_seed(99411+i)
            pre=prefix(tok,row)
            outs=model.generate(input_ids=pre,attention_mask=torch.ones_like(pre),do_sample=True,num_return_sequences=4,
                                temperature=.8,top_p=.95,top_k=0,max_new_tokens=160,pad_token_id=tok.eos_token_id)
            ads,gs,safes=[],[],set()
            for out in outs:
                raw=tok.decode(out[pre.shape[1]:],skip_special_tokens=True).strip()
                acts=parse(raw,sorted(row['task']['tools']),'names')
                gold=row['gold']['constraints']
                res=check(row['task'],acts,gold)
                A=int(res['completed'])
                if A: safes.add(res['safe_success'])
                C=1-len(res['violations'])/len(gold) if acts is not None else 0.
                ads.append(A+C); gs.append(A+A*C)
                stats.update(n=1,valid=int(acts is not None),completed=A,safe=int(res['safe_success']),
                             tight_completed=int(bool(A and shape(acts,row['task']))),gate_closed=1-A,
                             raw_reward_different=int(ads[-1]!=gs[-1]))
                print(json.dumps(dict(id=row['sample_id'],raw=raw,plan=acts,result=res,add=ads[-1],gate=gs[-1])),file=f,flush=True)
            stats['mixed_safe_among_completed']+=int(len(safes)==2)
            stats['groups_different_normalized_reward']+=int(not torch.allclose(standardized(ads),standardized(gs),atol=1e-6,rtol=0))
    (OUT/'scores.json').write_text(json.dumps(dict(groups=len(rows),counts=stats),indent=2))


if __name__=='__main__':
    main()
