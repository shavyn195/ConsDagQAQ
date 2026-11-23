"""Train-only paired reachability check; both prompts expose the same codebook and world."""
from collections import Counter
import hashlib
import json
import random
import torch

from probe_e2_planner_v1 import ROOT, DATA, MODEL, prompt, select
from rescore_v4_side import digest, load_jsonl
from trust_env import check
from transformers import AutoModelForCausalLM, AutoTokenizer

OUT=ROOT/'outputs/e2_v4/reachability-format-v2'


def choose(rows):
    used={r['group_id'] for r in select(rows)}
    rng=random.Random(20261122)
    result=[]
    for variant in ['explicit','implicit']:
        for typ in ['budget','deadline','order','privacy','tool_auth']:
            r=rng.choice([r for r in rows if r['group_id'] not in used and r['variant']==variant
                          and [c['type'] for c in r['gold']['constraints']]==[typ]])
            used.add(r['group_id'])
            result.append(r)
    return result


def parse(raw,roles,arm):
    try:
        plan=json.loads(raw)
    except ValueError:
        return None
    if not isinstance(plan,list) or not plan:
        return None
    if arm=='numbers':
        if all(type(x) is int and 1<=x<=len(roles) for x in plan):
            return [roles[x-1] for x in plan]
    elif arm=='names' and all(isinstance(x,str) and x in roles for x in plan):
        return plan
    return None


def main():
    rows=choose(load_jsonl(DATA))
    cfg=dict(groups=[r['sample_id'] for r in rows],train_hash=digest(DATA),code=digest(ROOT/'src/probe_e2_format.py'),
             v1_code=digest(ROOT/'src/probe_e2_planner_v1.py'),model=str(MODEL),seed=42,
             group_size=4,max_new_tokens=160,temperature=0.8,top_p=0.95,top_k=0,
             hypothesis='Numbered actions may improve syntactic validity; mixed safety among completed plans is separately measured.',
             decoding='strict nonempty JSON list, no repair; common 1-based codebook, no gold/witness in prompt')
    OUT.mkdir(exist_ok=False,parents=True)
    (OUT/'config.json').write_text(json.dumps(cfg,indent=2))
    tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(MODEL,dtype=torch.bfloat16,device_map='cuda',local_files_only=True).eval()
    counts={k:Counter(samples=0,valid=0,completed=0,safe=0,mixed_groups=0) for k in ['names','numbers']}
    with (OUT/'samples.jsonl').open('x') as f, torch.inference_mode():
        for i,row in enumerate(rows):
            roles=sorted(row['task']['tools'])
            codebook=json.dumps(dict(enumerate(roles,1)),separators=(',',':'))
            for arm in counts:
                torch.manual_seed(42+i)
                instruction=('Return only a JSON array of '+('integer codes' if arm=='numbers' else 'tool ID strings')
                             +' in execution order. Codebook: '+codebook)
                p=prompt(row).replace('Return only a JSON array of tool IDs in execution order.',instruction)
                assert instruction in p
                text=tok.apply_chat_template([dict(role='user',content=p)],tokenize=False,add_generation_prompt=True,enable_thinking=False)
                batch=tok(text,add_special_tokens=False,return_tensors='pt').to(model.device)
                outputs=model.generate(**batch,do_sample=True,num_return_sequences=4,temperature=0.8,top_p=0.95,top_k=0,
                                       max_new_tokens=160,pad_token_id=tok.eos_token_id)
                signals=set()
                for out in outputs:
                    raw=tok.decode(out[batch.input_ids.shape[1]:],skip_special_tokens=True).strip()
                    actions=parse(raw,roles,arm)
                    res=check(row['task'],actions,row['gold']['constraints'])
                    counts[arm].update(samples=1,valid=int(actions is not None),completed=int(res['completed']),safe=int(res['safe_success']))
                    signals.add((res['completed'],res['safe_success']))
                    print(json.dumps(dict(arm=arm,sample_id=row['sample_id'],prompt_hash=hashlib.sha256(p.encode()).hexdigest(),
                                          raw=raw,actions=actions,result=res)),file=f,flush=True)
                counts[arm]['mixed_groups']+=int((True,False) in signals and (True,True) in signals)
    (OUT/'summary.json').write_text(json.dumps(counts,indent=2))
    print(json.dumps(counts),flush=True)


if __name__=='__main__':
    main()
