"""Paired exploratory transfer of frozen compiler outputs to a learned planner."""
import fcntl
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from audit_warmup_rollouts import shape
from bind_public_scope import bind
from probe_e2_planner_v1 import ROOT, MODEL, prompt
from probe_e2_format import parse
from rescore_v4_side import load_jsonl, aligned, digest
from run_e1 import strict_parse
from trust_env import check, plan, default_plan

OUT=ROOT/'outputs/e2_v4/frozen-planner-swap-panel-v1'
ADAPTER=ROOT/'outputs/e2_v4/planner-warmup-1.7B-v1/adapter'
ARMS=('raw','pred','gold')


def canon(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def select(rows):
    picked=set()
    for count in (1,2,3):
        eligible=[r['group_id'] for r in rows if r['variant']=='explicit' and len(r['gold']['constraints'])==count]
        key=lambda gid: hashlib.sha256(('consdag-swap-v1|'+gid).encode()).hexdigest()
        picked.update(sorted(eligible,key=key)[:5])
    panel=[r for r in rows if r['group_id'] in picked]
    assert len(picked)==15 and len(panel)==45
    return panel


def main():
    lock=(OUT.parent/'planner-probe.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    frozen=ROOT/'outputs/e1/Qwen3-4B-v4'
    config=dict(seed=42,batch=8,max_new_tokens=160,decode='greedy',arms=ARMS,
                adapter=digest(ADAPTER/'adapter_model.safetensors'),
                compiler=digest(frozen/'adapter/adapter_model.safetensors'),script=digest(Path(__file__)),sources={})
    cases=[]
    for split in ('test_tpl_ho','test_tool_ho'):
        data=ROOT/'data/processed_v4'/(split+'.jsonl')
        pred=frozen/'trained_predictions'/data.name
        rows=load_jsonl(data)
        panel=select(rows)
        by={r['sample_id']:t for r,t in zip(rows,aligned(rows,load_jsonl(pred)),strict=True)}
        config['sources'][split]=dict(data=digest(data),pred=digest(pred),ids=[r['sample_id'] for r in panel])
        for r in panel:
            obj=strict_parse(bind(by[r['sample_id']],r['catalog']))
            for arm in ARMS:
                extra=None if arm=='raw' else obj if arm=='pred' else r['gold']
                msg=prompt(r)
                if arm!='raw':
                    msg+='\nConstraint record for this request: '+(canon(extra) if extra is not None else 'unavailable')
                cs=extra['constraints'] if extra else []
                sym,_=plan(r['task'],cs)
                ref=check(r['task'],sym,r['gold']['constraints'])
                cases.append((split,r,arm,msg,ref['safe_success']))
    OUT.mkdir(exist_ok=False)
    (OUT/'config.json').write_text(json.dumps(config,indent=2))
    torch.manual_seed(42)
    tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    tok.padding_side='left'
    if tok.pad_token_id is None: tok.pad_token=tok.eos_token
    model=AutoModelForCausalLM.from_pretrained(MODEL,dtype=torch.bfloat16,device_map='cuda',local_files_only=True)
    model=PeftModel.from_pretrained(model,ADAPTER).eval()
    stats=defaultdict(lambda:defaultdict(lambda:defaultdict(Counter)))
    with (OUT/'samples.jsonl').open('x') as f,torch.inference_mode():
        for i in range(0,len(cases),8):
            batch=cases[i:i+8]
            texts=[tok.apply_chat_template([dict(role='user',content=x[3])],tokenize=False,
                    add_generation_prompt=True,enable_thinking=False) for x in batch]
            inp=tok(texts,return_tensors='pt',padding=True,add_special_tokens=False).to('cuda')
            generated=model.generate(**inp,do_sample=False,max_new_tokens=160,pad_token_id=tok.pad_token_id)
            for (split,r,arm,msg,sy),out in zip(batch,generated,strict=True):
                raw=tok.decode(out[inp.input_ids.shape[1]:],skip_special_tokens=True).strip()
                acts=parse(raw,sorted(r['task']['tools']),'names')
                result=check(r['task'],acts,r['gold']['constraints'])
                strict_ok=bool(result['completed'] and shape(acts,r['task']))
                flags=dict(n=1,completed=int(result['completed']),safe=int(result['safe_success']),
                           strict_safe=int(strict_ok and result['safe_success']),symbolic_safe=int(sy),
                           matches_default=int(acts==default_plan(r['task'])))
                stats[split][arm][r['variant']].update(flags)
                print(canon(dict(split=split,id=r['sample_id'],group=r['group_id'],variant=r['variant'],arm=arm,
                    prompt_hash=hashlib.sha256(msg.encode()).hexdigest(),raw=raw,actions=acts,result=result,flags=flags)),file=f,flush=True)
    (OUT/'scores.json').write_text(json.dumps(stats,indent=2))


if __name__=='__main__':
    main()
