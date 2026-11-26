"""Matched raw/contract continued SFT, same checkpoint, tasks and targets."""
import argparse
import gc
import json
from pathlib import Path
import sys
import time
from common import evaluate_plan,paired,public_row,read_rows,sha,summarize
from fixed_planner import select_groups
from format_recovery import explicit_messages,string_array
from shared_planner_sft import select_training,training_target,train,write_json
from planner_learning_probe import verify_training


def select_additional(rows,parent_ids,count,salt,dev):
    forbidden={r['group_id'] for r in rows if r['sample_id'] in set(parent_ids)}
    pool=[r for r in rows if r['group_id'] not in forbidden]
    selected=select_training(pool,count,salt,dev)
    assert not set(parent_ids)&{r['sample_id'] for r in selected}
    return selected


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True);a=p.parse_args()
    sys.path.insert(0,str(a.root/'src'));sys.path.insert(1,'/root/ConsDagSubmissionReview/src')
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer
    from run_e1 import load_model,render_chat,chat_messages
    from run_e1_v6 import validate_v6_freeze
    from sub_e2_monolithic import parse_plan
    cfg=json.loads(a.config.read_text());parent=Path(cfg['parent'])
    done,previous_training=verify_training(parent)
    previous=json.loads((parent/'protocol.json').read_text())
    assert previous['config_sha256']==cfg['expected_parent_config_sha256']
    dependency=Path(cfg['dependency']);probe_done=json.loads((dependency/'completion.json').read_text())
    assert probe_done['status']=='complete' and probe_done['results_sha256']==sha(dependency/'results.json')
    data=a.root/'data/processed_v6';validate_v6_freeze(data)
    all_dev=read_rows(data/'dev.jsonl');evaluation=select_groups(all_dev,cfg['groups'])
    training=select_additional(read_rows(data/'train.jsonl'),previous['train_sample_ids'],
        cfg['train_groups'],cfg['train_selection_salt'],all_dev)
    assert [r['sample_id'] for r in evaluation]==previous['eval_sample_ids']
    model_path=a.root/'models'/cfg['model'];compiler=a.root/'outputs/e1_v6/Qwen3-4B-v6-seed42/adapter'
    fixed=Path(cfg['fixed']);fixed_protocol=json.loads((fixed/'protocol.json').read_text())
    hashes={str(f.relative_to(model_path)):sha(f) for f in model_path.rglob('*') if f.is_file()}
    assert hashes==previous['model_sha256']
    compiler_hash={f.name:sha(f) for f in compiler.iterdir() if f.is_file()}
    assert compiler_hash==fixed_protocol['adapter_sha256']
    assert sha(fixed/'calls.jsonl')==previous['fixed_inputs']['calls.jsonl']
    cached={r['sample_id']:r for r in read_rows(fixed/'calls.jsonl') if r['call']=='sft_first'}
    assert set(cached)=={r['sample_id'] for r in evaluation}
    tok=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    # Validate all targets and raw/compiler lengths before allocating a GPU model.
    targets={r['sample_id']:training_target(r) for r in training}
    for row in training:
        for messages in (chat_messages(public_row(row)),explicit_messages(row)):
            assert render_chat(tok,messages,add_generation_prompt=True)['input_ids'].numel()+384<=tok.model_max_length
    a.out.mkdir(parents=True,exist_ok=True)
    manifest=dict(config=cfg,config_sha256=sha(a.config),parent_results_sha256=done['results_sha256'],
        dependency_results_sha256=probe_done['results_sha256'],initial_adapter_sha256=previous_training['adapter_sha256'],
        model_sha256=hashes,compiler_sha256=compiler_hash,
        train_sample_ids=[r['sample_id'] for r in training],eval_sample_ids=[r['sample_id'] for r in evaluation],
        data_sha256={s:sha(data/(s+'.jsonl')) for s in ('train','dev')},
        source_sha256={str(f):sha(f) for f in Path(__file__).parent.glob('*.py')})
    with (a.out/'protocol.json').open('x') as f:json.dump(manifest,f,indent=2)
    torch.set_num_threads(1);assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    started=time.monotonic();base,tok=load_model(str(model_path),'bf16')
    model=PeftModel.from_pretrained(base,str(compiler),is_trainable=False);model.eval();model.config.use_cache=True
    compiled={};compile_cost=[]
    with (a.out/'compiler_calls.jsonl').open('x') as f:
        for row in training:
            if time.monotonic()-started>cfg['compile_seconds_cap']-60:
                raise TimeoutError('Compiler budget; partial cache retained, no partial-panel training')
            messages=chat_messages(public_row(row))
            inp={k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
            torch.cuda.synchronize();tick=time.monotonic()
            with torch.inference_mode():
                output=model.generate(**inp,do_sample=False,max_new_tokens=384,pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
            torch.cuda.synchronize();elapsed=time.monotonic()-tick
            generated=output[0,inp['input_ids'].shape[1]:];raw=tok.decode(generated,skip_special_tokens=True)
            record=dict(sample_id=row['sample_id'],raw=raw,messages=messages,
                cost=dict(seconds=elapsed,prompt_tokens=inp['input_ids'].numel(),output_tokens=generated.numel(),calls=1),
                cap_hit=generated.numel()==384)
            print(json.dumps(record),file=f,flush=True);compiled[row['sample_id']]=raw;compile_cost.append(record['cost'])
            print(json.dumps(dict(compiler_calls=len(compiled),total=len(training))),flush=True)
    write_json(a.out/'compiler_complete.json',dict(rows=len(compiled),sha256=sha(a.out/'compiler_calls.jsonl'),
        elapsed_seconds=time.monotonic()-started,cost={k:sum(c[k] for c in compile_cost) for k in compile_cost[0]}))
    del model,base;gc.collect();torch.cuda.empty_cache()
    examples={}
    for mode in cfg['training_inputs']:
        examples[mode]=[]
        for row in training:
            aux=compiled[row['sample_id']] if mode=='contract' else None
            prefix=render_chat(tok,explicit_messages(row,aux),add_generation_prompt=True)['input_ids'][0].tolist()
            answer=tok(targets[row['sample_id']]+tok.eos_token,add_special_tokens=False)['input_ids']
            if len(prefix)+len(answer)>cfg['max_seq_len']:raise ValueError('No truncation or dropping allowed')
            examples[mode].append(dict(sample_id=row['sample_id'],ids=prefix+answer,
                labels=[-100]*len(prefix)+answer,prompt_tokens=len(prefix)))
    # Check both input distributions before either model is updated.
    write_json(a.out/'training_input_preflight.json',dict(rows=len(training),
        max_tokens={m:max(len(e['ids']) for e in es) for m,es in examples.items()},
        shared_order=[r['sample_id'] for r in training],target_source='Identical verified witness/default; never predicted-contract self-labeling'))
    results={};all_records=[]
    with (a.out/'calls.jsonl').open('x') as calls,(a.out/'decisions.jsonl').open('x') as decisions:
        for mode in cfg['training_inputs']:
            dest=a.out/(mode+'_sft');dest.mkdir(exist_ok=False)
            torch.manual_seed(cfg['seed']);torch.cuda.manual_seed_all(cfg['seed']);torch.cuda.reset_peak_memory_stats()
            tick=time.monotonic();base,tok=load_model(str(model_path),'bf16')
            model,trained=train(base,tok,examples[mode],cfg,dest,tick)
            results[mode]=dict(training=trained)
            if trained['status']!='complete':raise RuntimeError('Incomplete arm retained; do not compare with full counterpart')
            eval_started=time.monotonic();records=[]
            for index,row in enumerate(evaluation):
                for condition in (['raw','contract'] if index%2==0 else ['contract','raw']):
                    if time.monotonic()-eval_started>cfg['eval_seconds_cap']-60:
                        raise TimeoutError('Evaluation budget; no incomplete-panel winner')
                    aux=cached[row['sample_id']]['raw'] if condition=='contract' else None
                    messages=explicit_messages(row,aux)
                    inp={k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
                    assert inp['input_ids'].numel()+cfg['max_new_tokens']<=tok.model_max_length
                    torch.cuda.synchronize();t=time.monotonic()
                    with torch.inference_mode():
                        output=model.generate(**inp,do_sample=False,max_new_tokens=cfg['max_new_tokens'],
                            pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                    torch.cuda.synchronize();elapsed=time.monotonic()-t
                    new=output[0,inp['input_ids'].shape[1]:];raw=tok.decode(new,skip_special_tokens=True)
                    arm=mode+'_sft/'+condition
                    cost=dict(calls=1,seconds=elapsed,prompt_tokens=inp['input_ids'].numel(),output_tokens=new.numel())
                    print(json.dumps(dict(sample_id=row['sample_id'],arm=arm,messages=messages,raw=raw,cost=cost,
                        cap_hit=new.numel()==cfg['max_new_tokens'])),file=calls,flush=True)
                    candidate=parse_plan(raw,public_row(row));outcome=evaluate_plan(row,candidate)
                    record=dict(sample_id=row['sample_id'],arm=arm,plan=candidate,outcome=outcome,
                        string_array=string_array(raw),new_cost=cost,
                        reused_cost=cached[row['sample_id']]['cost'] if condition=='contract' else {k:0 for k in cost})
                    records.append(record);all_records.append(record)
                    print(json.dumps(record),file=decisions,flush=True)
                print(json.dumps(dict(arm=mode,eval_rows=index+1,total_calls=len(all_records))),flush=True)
            results[mode]['evaluation']={c:summarize([r['outcome'] for r in records if r['arm'].endswith('/'+c)]) for c in ('raw','contract')}
            results[mode]['eval_seconds']=time.monotonic()-eval_started
            del model,base;gc.collect();torch.cuda.empty_cache()
    by_arm={a:[r['outcome'] for r in all_records if r['arm']==a] for a in sorted({r['arm'] for r in all_records})}
    result=dict(status='complete',runs=results,calls=len(all_records),elapsed_seconds=time.monotonic()-started,
        arms={k:summarize(v) for k,v in by_arm.items()},
        matched_input_comparison=paired(by_arm['contract_sft/contract'],by_arm['raw_sft/raw']),
        same_raw_input=paired(by_arm['contract_sft/raw'],by_arm['raw_sft/raw']),
        same_contract_input=paired(by_arm['contract_sft/contract'],by_arm['raw_sft/contract']),
        costs=dict(new_planning={k:sum(r['new_cost'][k] for r in all_records) for k in ('calls','seconds','prompt_tokens','output_tokens')},
            reused_compile={k:sum(r['reused_cost'][k] for r in all_records) for k in ('calls','seconds','prompt_tokens','output_tokens')}),
        warning='Exploratory fixed-seed 32-group continuation; same updates/tasks are not equal token or total-cost budgets. No GRPO updates yet.')
    write_json(a.out/'results.json',result);write_json(a.out/'completion.json',dict(status='complete',results_sha256=sha(a.out/'results.json')))


if __name__=='__main__':main()
