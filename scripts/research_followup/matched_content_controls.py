"""Matched generic/PE task-SFT controls for the learned constraint interface."""
import argparse
import gc
import json
from pathlib import Path
import sys
import time
from common import evaluate_plan,paired,public_row,read_rows,sha,summarize
from fixed_planner import summary_messages
from format_recovery import explicit_messages,string_array
from shared_planner_sft import train,training_target,write_json
from planner_learning_probe import verify_training

RECIPE_KEYS=('model','seed','epochs','learning_rate','lora_rank','lora_alpha','lora_dropout',
    'target_modules','gradient_accumulation_steps','max_seq_len','weight_decay','gradient_checkpointing',
    'initial_planner_adapter','max_new_tokens')


def require_same_recipe(control,matched):
    differences=[k for k in RECIPE_KEYS if control.get(k)!=matched.get(k)]
    if differences:raise ValueError('Unmatched SFT recipe fields: '+', '.join(differences))


def first_messages(row,mode,compiler_messages=None):
    public=public_row(row)
    if mode=='generic':return summary_messages(public)
    if mode!='pe':raise ValueError('Unknown content control')
    if compiler_messages is None:
        from run_e1 import chat_messages
        compiler_messages=chat_messages
    return compiler_messages(public)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--config',type=Path,required=True)
    a=p.parse_args();sys.path.insert(0,str(a.root/'src'));sys.path.insert(1,'/root/ConsDagSubmissionReview/src')
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer
    from run_e1 import load_model,render_chat
    from run_e1_v6 import validate_v6_freeze
    from sub_e2_monolithic import parse_plan
    cfg=json.loads(a.config.read_text());parent=Path(cfg['parent']);matched=Path(cfg['matched'])
    done,prior_training=verify_training(parent);previous=json.loads((parent/'protocol.json').read_text())
    assert previous['config_sha256']==cfg['expected_parent_config_sha256']
    matched_done=json.loads((matched/'completion.json').read_text())
    assert matched_done['status']=='complete' and matched_done['results_sha256']==sha(matched/'results.json')
    baseline=json.loads((matched/'protocol.json').read_text())
    assert baseline['config_sha256']==cfg['expected_matched_config_sha256']
    require_same_recipe(cfg,baseline['config'])
    assert baseline['initial_adapter_sha256']==prior_training['adapter_sha256']
    dependency=Path(cfg['dependency']);relay_done=json.loads((dependency/'completion.json').read_text())
    assert relay_done['status']=='complete' and relay_done['results_sha256']==sha(dependency/'results.json')
    data=a.root/'data/processed_v6';validate_v6_freeze(data)
    train_all={r['sample_id']:r for r in read_rows(data/'train.jsonl')}
    dev_all={r['sample_id']:r for r in read_rows(data/'dev.jsonl')}
    training=[train_all[s] for s in baseline['train_sample_ids']];evaluation=[dev_all[s] for s in baseline['eval_sample_ids']]
    assert len(training)==96 and len(evaluation)==144 and all(r['subset']=='train' for r in training)
    assert not {r['group_id'] for r in training}&{r['group_id'] for r in evaluation}
    for split in ('train','dev'):assert sha(data/(split+'.jsonl'))==baseline['data_sha256'][split]
    model_path=a.root/'models'/cfg['model'];compiler=a.root/'outputs/e1_v6/Qwen3-4B-v6-seed42/adapter'
    hashes={str(f.relative_to(model_path)):sha(f) for f in model_path.rglob('*') if f.is_file()}
    assert hashes==previous['model_sha256']
    fixed=Path(cfg['fixed']);assert sha(fixed/'calls.jsonl')==previous['fixed_inputs']['calls.jsonl']
    fixed_protocol=json.loads((fixed/'protocol.json').read_text())
    compiler_hash={f.name:sha(f) for f in compiler.iterdir() if f.is_file()}
    assert compiler_hash==fixed_protocol['adapter_sha256']
    cached={(r['sample_id'],r['call']):r for r in read_rows(fixed/'calls.jsonl') if r['call'].endswith('_first')}
    assert set(cached)=={(r['sample_id'],m+'_first') for r in evaluation for m in ('generic','pe','sft')}
    tok=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    targets={r['sample_id']:training_target(r) for r in training}
    # Public-only first stage and all cached dev prompt lengths checked before GPU load.
    for row in training:
        for mode in cfg['training_inputs']:
            n=render_chat(tok,first_messages(row,mode),add_generation_prompt=True)['input_ids'].numel()
            assert n+cfg['max_new_tokens']<=tok.model_max_length
    for row in evaluation:
        for condition in ('raw','generic','pe','contract'):
            auxiliary=None if condition=='raw' else cached[(row['sample_id'],('sft' if condition=='contract' else condition)+'_first')]['raw']
            n=render_chat(tok,explicit_messages(row,auxiliary),add_generation_prompt=True)['input_ids'].numel()
            assert n+cfg['max_new_tokens']<=tok.model_max_length
    a.out.mkdir(parents=True,exist_ok=True)
    protocol=dict(config=cfg,config_sha256=sha(a.config),parent_results_sha256=done['results_sha256'],
        matched_results_sha256=matched_done['results_sha256'],dependency_results_sha256=relay_done['results_sha256'],
        initial_adapter_sha256=prior_training['adapter_sha256'],model_sha256=hashes,compiler_sha256=compiler_hash,
        train_sample_ids=baseline['train_sample_ids'],eval_sample_ids=baseline['eval_sample_ids'],
        data_sha256=baseline['data_sha256'],fixed_cache_sha256=sha(fixed/'calls.jsonl'),
        source_sha256={str(f):sha(f) for f in Path(__file__).parent.glob('*.py')},
        stage_one='Exact original fixed_planner summary_messages / run_e1.chat_messages; original compiler wrapper with adapter disabled for BOTH generic and PE.',
        evaluation='Each new model receives raw, its own auxiliary form, and the SAME cached SFT contract; 2x3x144 real calls.',
        selection='Same prior 96 train rows, no new sample or checkpoint selection.')
    with (a.out/'protocol.json').open('x') as f:json.dump(protocol,f,indent=2)
    torch.set_num_threads(1);assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    started=time.monotonic();base,tok=load_model(str(model_path),'bf16')
    model=PeftModel.from_pretrained(base,str(compiler),is_trainable=False);model.eval();model.config.use_cache=True
    cache={};costs=[]
    with (a.out/'first_stage_calls.jsonl').open('x') as stream:
        for index,row in enumerate(training):
            modes=cfg['training_inputs'];shift=index%len(modes)
            for mode in modes[shift:]+modes[:shift]:
                if time.monotonic()-started>=cfg['compile_seconds_cap']-90:raise TimeoutError('Content-control first-stage budget; retain partial output')
                messages=first_messages(row,mode)
                inp={k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
                torch.cuda.synchronize();tick=time.monotonic()
                with model.disable_adapter(),torch.inference_mode():
                    generated=model.generate(**inp,do_sample=False,max_new_tokens=cfg['max_new_tokens'],pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                torch.cuda.synchronize();new=generated[0,inp['input_ids'].shape[1]:];raw=tok.decode(new,skip_special_tokens=True)
                cost=dict(calls=1,seconds=time.monotonic()-tick,prompt_tokens=inp['input_ids'].numel(),output_tokens=new.numel())
                record=dict(sample_id=row['sample_id'],mode=mode,messages=messages,raw=raw,cost=cost,cap_hit=new.numel()==cfg['max_new_tokens'])
                cache[(row['sample_id'],mode)]=record;costs.append(cost)
                print(json.dumps(record),file=stream,flush=True)
                print(json.dumps(dict(first_stage_calls=len(cache),total=192)),flush=True)
    write_json(a.out/'first_stage_complete.json',dict(calls=len(cache),sha256=sha(a.out/'first_stage_calls.jsonl'),
        elapsed_seconds=time.monotonic()-started,cost={k:sum(c[k] for c in costs) for k in costs[0]}))
    del model,base;gc.collect();torch.cuda.empty_cache()
    examples={}
    for mode in cfg['training_inputs']:
        examples[mode]=[]
        for row in training:
            prefix=render_chat(tok,explicit_messages(row,cache[(row['sample_id'],mode)]['raw']),add_generation_prompt=True)['input_ids'][0].tolist()
            answer=tok(targets[row['sample_id']]+tok.eos_token,add_special_tokens=False)['input_ids']
            if len(prefix)+len(answer)>cfg['max_seq_len']:raise ValueError('Training length exceeded; no truncation or sample dropping')
            examples[mode].append(dict(sample_id=row['sample_id'],ids=prefix+answer,labels=[-100]*len(prefix)+answer,prompt_tokens=len(prefix)))
    write_json(a.out/'training_input_preflight.json',dict(rows=len(training),
        max_tokens={m:max(len(e['ids']) for e in es) for m,es in examples.items()},
        target_tokens={m:sum(len(e['ids'])-e['prompt_tokens'] for e in es) for m,es in examples.items()},
        shared_order=[r['sample_id'] for r in training],no_generated_content_repair=True))
    results={};records=[]
    with (a.out/'calls.jsonl').open('x') as calls,(a.out/'decisions.jsonl').open('x') as decisions:
        for mode in cfg['training_inputs']:
            dest=a.out/(mode+'_sft');dest.mkdir(exist_ok=False)
            torch.manual_seed(cfg['seed']);torch.cuda.manual_seed_all(cfg['seed']);torch.cuda.reset_peak_memory_stats()
            tick=time.monotonic();base,tok=load_model(str(model_path),'bf16')
            model,trained=train(base,tok,examples[mode],cfg,dest,tick);results[mode]=dict(training=trained)
            if trained['status']!='complete':raise RuntimeError('Incomplete control training retained')
            tick=time.monotonic()
            for index,row in enumerate(evaluation):
                conditions=['raw',mode,'contract'];shift=index%len(conditions)
                for condition in conditions[shift:]+conditions[:shift]:
                    if time.monotonic()-tick>=cfg['eval_seconds_cap']-60:raise TimeoutError('Evaluation budget; retain incomplete panel')
                    first=None if condition=='raw' else cached[(row['sample_id'],('sft' if condition=='contract' else condition)+'_first')]
                    messages=explicit_messages(row,None if first is None else first['raw'])
                    inp={k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
                    torch.cuda.synchronize();t=time.monotonic()
                    with torch.inference_mode():generated=model.generate(**inp,do_sample=False,max_new_tokens=cfg['max_new_tokens'],pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                    torch.cuda.synchronize();new=generated[0,inp['input_ids'].shape[1]:];raw=tok.decode(new,skip_special_tokens=True)
                    cost=dict(calls=1,seconds=time.monotonic()-t,prompt_tokens=inp['input_ids'].numel(),output_tokens=new.numel())
                    arm=mode+'_sft/'+condition;candidate=parse_plan(raw,public_row(row))
                    print(json.dumps(dict(sample_id=row['sample_id'],arm=arm,messages=messages,raw=raw,cost=cost,cap_hit=new.numel()==cfg['max_new_tokens'])),file=calls,flush=True)
                    record=dict(sample_id=row['sample_id'],arm=arm,plan=candidate,outcome=evaluate_plan(row,candidate),string_array=string_array(raw),new_cost=cost,reused_cost=first['cost'] if first else {k:0 for k in cost})
                    records.append(record);print(json.dumps(record),file=decisions,flush=True)
                print(json.dumps(dict(input=mode,eval_rows=index+1,total_calls=len(records))),flush=True)
            results[mode]['eval_seconds']=time.monotonic()-tick
            del model,base;gc.collect();torch.cuda.empty_cache()
    by_arm={arm:[r['outcome'] for r in records if r['arm']==arm] for arm in sorted({r['arm'] for r in records})}
    baseline_decisions=read_rows(matched/'decisions.jsonl')
    reference={arm:[r['outcome'] for r in baseline_decisions if r['arm']==arm] for arm in ('raw_sft/raw','contract_sft/contract')}
    result=dict(status='complete',runs=results,calls=len(records),elapsed_seconds=time.monotonic()-started,
        arms={a:summarize(rs) for a,rs in by_arm.items()},
        matched_controls_vs_raw={m:paired(by_arm[m+'_sft/'+m],reference['raw_sft/raw']) for m in cfg['training_inputs']},
        contract_vs_matched_controls={m:paired(reference['contract_sft/contract'],by_arm[m+'_sft/'+m]) for m in cfg['training_inputs']},
        same_contract_input_comparison={m:paired(reference['contract_sft/contract'],by_arm[m+'_sft/contract']) for m in cfg['training_inputs']},
        costs={kind:{k:sum(r[kind][k] for r in records) for k in ('calls','seconds','prompt_tokens','output_tokens')} for kind in ('new_cost','reused_cost')},
        caveat='Exploratory seed42 content controls; same supervised task/target/update count, unequal prompt tokens and first-stage costs. Original capped first-stage outputs retained.')
    write_json(a.out/'results.json',result);write_json(a.out/'completion.json',dict(status='complete',results_sha256=sha(a.out/'results.json')))


if __name__=='__main__':main()
