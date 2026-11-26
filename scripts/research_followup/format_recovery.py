"""Explicit output-contract recovery, with a capability gate before full expansion."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
import time
from common import evaluate_plan, paired, public_row, read_rows, sha, summarize
from fixed_planner import planner_messages, select_groups
from structure_supplement import core_text


def explicit_messages(row,aux=None):
    messages=planner_messages(public_row(row),aux)
    messages[0]['content']='Output only a JSON array of strings, each string an exact tool role key from Public task.tools. Never output objects or tool metadata.'
    messages[-1]['content']+='\nRequired output type: array<string>. Shape example only: ["role_a","role_b"]. Replace these placeholders with real tool role keys from Public task.tools; copy each key exactly, without adding a "role:" prefix. Do not output objects, display names, constraints, explanations, or metadata. Include exactly one alternative from every stage in stage order and ALL finish roles. Optional roles are inserted only if needed. Output the COMPLETE plan, not merely the constrained subgraph.\nPlan JSON (strings only):'
    return messages


def string_array(raw):
    match=re.search(r'\[.*\]',raw,flags=re.DOTALL)
    for text in ([match.group()] if match else [])+[raw.strip()]:
        try: value=json.loads(text)
        except json.JSONDecodeError: continue
        if isinstance(value,list) and value and all(isinstance(x,str) for x in value): return True
    return False


def smoke_gate(records,cfg):
    expected=cfg['smoke_groups']*3
    counts={arm:dict(n=sum(r['arm']==arm for r in records),
                     strings=sum(r['arm']==arm and r['string_array'] for r in records),
                     valid=sum(r['arm']==arm and r['outcome']['planned'] for r in records)) for arm in cfg['arms']}
    passed=(all(c['n']==expected and c['strings']>=cfg['smoke_min_string_arrays_per_arm'] for c in counts.values())
            and all(counts[a]['valid']>=cfg['smoke_min_valid_direct_and_oracle'] for a in ('direct','oracle_core')))
    return dict(passed=passed,counts=counts,criterion='Format and structural validity only; never parser superiority')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--prepare-only',action='store_true')
    a=p.parse_args()
    sys.path.insert(0,str(a.root/'src'))
    sys.path.insert(1,'/root/ConsDagSubmissionReview/src')
    from run_e1 import load_model,render_chat
    from run_e1_v6 import validate_v6_freeze
    from sub_e2_monolithic import parse_plan
    from transformers import AutoTokenizer
    cfg=json.loads(a.config.read_text())
    fixed=Path(cfg['fixed'])
    done=json.loads((fixed/'completion.json').read_text())
    assert done['status']=='complete' and done['results_sha256']==sha(fixed/'results.json')
    data=a.root/'data/processed_v6'
    validate_v6_freeze(data)
    rows=select_groups(read_rows(data/'dev.jsonl'),cfg['groups'])
    old_protocol=json.loads((fixed/'protocol.json').read_text())
    assert old_protocol['panel']==[r['sample_id'] for r in rows]
    first={(r['sample_id'],r['call']):r for r in read_rows(fixed/'calls.jsonl') if r['call'].endswith('_first')}
    assert len(first)==len(rows)*3
    model_path=a.root/'models'/cfg['model']
    adapter=a.root/'outputs/e1_v6/Qwen3-4B-v6-seed42/adapter'
    tok=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    def auxiliary(row,arm):
        if arm=='direct': return None,None
        if arm=='oracle_core': return core_text(row['gold'],row['task']),None
        prior=first[(row['sample_id'],arm+'_first')]
        return prior['raw'],prior['cost']
    max_length=0
    for row in rows:
        for arm in cfg['arms']:
            aux,_=auxiliary(row,arm)
            n=render_chat(tok,explicit_messages(row,aux),add_generation_prompt=True)['input_ids'].numel()
            assert n+cfg['max_new_tokens']<=tok.model_max_length
            max_length=max(max_length,n)
    model_hash={str(f.relative_to(model_path)):sha(f) for f in model_path.rglob('*') if f.is_file()}
    adapter_hash={f.name:sha(f) for f in adapter.iterdir() if f.is_file()}
    assert model_hash==old_protocol['model_sha256'] and adapter_hash==old_protocol['adapter_sha256']
    manifest=dict(config=cfg,config_sha256=sha(a.config),data_sha256=sha(data/'dev.jsonl'),
        fixed_inputs={n:sha(fixed/n) for n in ('calls.jsonl','protocol.json','results.json','completion.json')},
        source_sha256={str(f):sha(f) for f in Path(__file__).parent.glob('*.py')},
        model_sha256=model_hash,adapter_sha256=adapter_hash,sample_ids=[r['sample_id'] for r in rows],
        max_prompt_tokens=max_length)
    a.out.mkdir(parents=True,exist_ok=True)
    path=a.out/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=manifest: raise ValueError('Prepared inputs changed')
    if not path.exists(): path.write_text(json.dumps(manifest,indent=2))
    if a.prepare_only:
        print(json.dumps(dict(preflight='PASS',rows=len(rows),smoke_calls=cfg['smoke_groups']*3*len(cfg['arms']),
                              max_calls=len(rows)*len(cfg['arms']),max_prompt_tokens=max_length)),flush=True)
        return
    if (a.out/'calls.jsonl').exists(): raise ValueError('Prior output preserved')
    import torch
    from peft import PeftModel
    torch.set_num_threads(1)
    assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    started=time.monotonic()
    base,tok=load_model(str(model_path),'bf16')
    model=PeftModel.from_pretrained(base,str(adapter),is_trainable=False)
    model.eval(); model.config.use_cache=True
    load_seconds=time.monotonic()-started
    records=[]; status='complete'; gate=None
    with (a.out/'calls.jsonl').open('x') as calls,(a.out/'decisions.jsonl').open('x') as decisions:
        for index,row in enumerate(rows):
            if index==cfg['smoke_groups']*3:
                gate=smoke_gate(records,cfg)
                (a.out/'smoke_gate.json').write_text(json.dumps(gate,indent=2))
                print(json.dumps(dict(smoke_gate=gate)),flush=True)
                if not gate['passed']:
                    status='smoke_gate_failed'
                    break
            if status!='complete': break
            shift=index%len(cfg['arms'])
            for arm in cfg['arms'][shift:]+cfg['arms'][:shift]:
                if time.monotonic()-started>=cfg['active_seconds_cap']-90:
                    status='budget_exhausted'; break
                aux,reused=auxiliary(row,arm)
                messages=explicit_messages(row,aux)
                inp={k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
                torch.cuda.synchronize(); t=time.monotonic()
                with model.disable_adapter(),torch.inference_mode():
                    output=model.generate(**inp,do_sample=False,max_new_tokens=cfg['max_new_tokens'],
                        pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                torch.cuda.synchronize()
                new=output[0,inp['input_ids'].shape[1]:]
                cost=dict(calls=1,prompt_tokens=inp['input_ids'].numel(),output_tokens=new.numel(),seconds=time.monotonic()-t)
                raw=tok.decode(new,skip_special_tokens=True)
                print(json.dumps(dict(sample_id=row['sample_id'],arm=arm,messages=messages,raw=raw,cost=cost,
                    cap_hit=new.numel()==cfg['max_new_tokens'])),file=calls,flush=True)
                candidate=parse_plan(raw,{'task':row['task']})
                outcome=evaluate_plan(row,candidate)
                reused=reused or {k:0 for k in cost}
                record=dict(sample_id=row['sample_id'],arm=arm,plan=candidate,outcome=outcome,
                    string_array=string_array(raw),new_cost=cost,reused_cost=reused,
                    pipeline_cost={k:cost[k]+reused[k] for k in cost})
                records.append(record)
                print(json.dumps(record),file=decisions,flush=True)
            print(json.dumps(dict(rows_reached=index+1,calls=len(records),elapsed_s=time.monotonic()-started)),flush=True)
    from structure_supplement import complete_group_ids
    complete=complete_group_ids(records,rows,cfg['arms'])
    by_arm={arm:[r['outcome'] for r in records if r['arm']==arm and r['outcome']['group_id'] in complete] for arm in cfg['arms']}
    result=dict(status=status,smoke_gate=gate,complete_ein_groups=len(complete),
        arms={k:summarize(v) for k,v in by_arm.items()},
        paired={k:paired(by_arm[k],by_arm['direct']) for k in cfg['arms'] if k!='direct'},
        sft_minus_generic=paired(by_arm['sft'],by_arm['generic']),
        load_seconds=load_seconds,elapsed_seconds=time.monotonic()-started,calls=len(records),
        cost={arm:{kind:{k:sum(r[kind][k] for r in records if r['arm']==arm) for k in ('calls','prompt_tokens','output_tokens','seconds')}
                   for kind in ('new_cost','reused_cost','pipeline_cost')} for arm in cfg['arms']})
    (a.out/'results.json').write_text(json.dumps(result,indent=2))
    (a.out/'completion.json').write_text(json.dumps(dict(status=status,results_sha256=sha(a.out/'results.json'))))


if __name__=='__main__': main()
