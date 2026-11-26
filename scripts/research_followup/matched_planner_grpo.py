"""Raw/contract planner GRPO from the SAME shared SFT checkpoint and train panel.

Gold is consulted only by the training verifier; predicted contracts are inputs.
Both trained models are evaluated with both input forms, without scoring repair.
"""
import argparse
import gc
import json
from pathlib import Path
import random
import sys
import time
from common import evaluate_plan,paired,public_row,read_rows,sha,summarize
from format_recovery import explicit_messages,string_array
from planner_learning_probe import verify_training
from planner_reward_probe import outcome_vector
from shared_planner_sft import write_json
from planner_grpo_core import group_advantages,completion_ids,load_policy_reference,set_policy,token_logps,clipped_loss


def train_arm(model,tok,rows,compiled,mode,cfg,out):
    import torch
    from transformers import GenerationConfig
    from run_e1 import render_chat
    from sub_e2_monolithic import parse_plan
    started=time.monotonic();ordered=list(rows);random.Random(cfg['seed']).shuffle(ordered)
    size=cfg['prompts_per_batch'];group_size=cfg['samples_per_prompt']
    if len(ordered)%size:raise ValueError('No dropped prompt batch')
    params=[p for p in model.parameters() if p.requires_grad]
    reference_before={n:p.detach().cpu().clone() for n,p in model.named_parameters() if '.reference.' in n}
    assert reference_before and params
    optimizer=torch.optim.AdamW(params,lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
    generation=GenerationConfig(do_sample=True,temperature=1.,top_p=1.,top_k=0,
        max_new_tokens=cfg['max_new_tokens'],num_return_sequences=group_size,
        pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id,repetition_penalty=1.)
    stats=dict(steps=0,rollouts=0,variable_reward_groups=0,zero_reward_groups=0,
        reward_sum=0.,sample_prompt_tokens=0,sample_completion_tokens=0,
        backward_completion_tokens=0,sampling_seconds=0.,old_reference_seconds=0.,update_seconds=0.)
    status='complete'
    with (out/'rollouts.jsonl').open('x') as rollout_log,(out/'train_steps.jsonl').open('x') as step_log:
        for batch_index,start in enumerate(range(0,len(ordered),size)):
            if time.monotonic()-started>=cfg['train_seconds_cap']-120:
                status='train_budget_exhausted';break
            batch=ordered[start:start+size];cached=[]
            model.gradient_checkpointing_disable();model.eval();model.config.use_cache=True
            set_policy(model,'policy')
            for offset,row in enumerate(batch):
                auxiliary=compiled[row['sample_id']]['raw'] if mode=='contract' else None
                messages=explicit_messages(row,auxiliary)
                inp={k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
                prefix=inp['input_ids'][0].tolist()
                torch.manual_seed(cfg['seed']+start+offset);torch.cuda.manual_seed_all(cfg['seed']+start+offset)
                torch.cuda.synchronize();tick=time.monotonic()
                with torch.inference_mode():output=model.generate(**inp,generation_config=generation)
                torch.cuda.synchronize();elapsed=time.monotonic()-tick
                stats['sampling_seconds']+=elapsed;items=[]
                for draw,sequence in enumerate(output.tolist()):
                    completion=completion_ids(sequence,len(prefix),tok.eos_token_id)
                    raw=tok.decode(completion,skip_special_tokens=True)
                    plan=parse_plan(raw,public_row(row));outcome=evaluate_plan(row,plan)
                    reward=float(outcome['faithful_success'])
                    items.append(dict(sample_id=row['sample_id'],group_id=row['group_id'],variant=row['variant'],
                        draw=draw,seed=cfg['seed']+start+offset,raw=raw,plan=plan,outcome=outcome,
                        signal=outcome_vector(row,plan),reward=reward,prefix=prefix,completion=completion,
                        cap_hit=len(completion)==cfg['max_new_tokens'],messages=messages))
                advantages=group_advantages([r['reward'] for r in items],cfg['advantage_epsilon'])
                stats['variable_reward_groups']+=len(set(r['reward'] for r in items))>1
                stats['zero_reward_groups']+=all(r['reward']==0 for r in items)
                for item,advantage in zip(items,advantages):
                    item['advantage']=advantage
                    stats['rollouts']+=1;stats['reward_sum']+=item['reward']
                    stats['sample_prompt_tokens']+=len(prefix);stats['sample_completion_tokens']+=len(item['completion'])
                    print(json.dumps(dict(item,batch=batch_index,input=mode)),file=rollout_log,flush=True)
                    cached.append(item)
                del output,inp
            # Neither old nor reference changes while sampling/caching this complete batch.
            tick=time.monotonic()
            with torch.no_grad():
                for item in cached:
                    item['old']=token_logps(model,item['prefix'],item['completion']).detach().cpu()
                set_policy(model,'reference')
                for item in cached:
                    item['reference']=token_logps(model,item['prefix'],item['completion']).detach().cpu()
            set_policy(model,'policy');torch.cuda.synchronize()
            stats['old_reference_seconds']+=time.monotonic()-tick
            model.train();model.config.use_cache=False
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
            for iteration in range(cfg['num_iterations']):
                tick=time.monotonic();optimizer.zero_grad(set_to_none=True);metrics=[];losses=[]
                for item in cached:
                    current=token_logps(model,item['prefix'],item['completion'])
                    loss,m=clipped_loss(current,item['old'].to(model.device),item['reference'].to(model.device),
                        item['advantage'],beta=cfg['beta'],clip_epsilon=cfg['clip_epsilon'])
                    # First forward of each freshly collected batch must reproduce its old policy.
                    if iteration==0 and m['ratio_max_abs_delta']>cfg['initial_ratio_tolerance']:
                        raise ValueError('Old-policy mismatch before update; dropout/sampling/precision audit required')
                    (loss/len(cached)).backward();losses.append(float(loss.detach()));metrics.append(m)
                    stats['backward_completion_tokens']+=len(item['completion'])
                    del current,loss
                norm=torch.nn.utils.clip_grad_norm_(params,1.,error_if_nonfinite=True);optimizer.step()
                if any(not torch.isfinite(p).all() for p in params):raise FloatingPointError('Nonfinite policy parameter')
                torch.cuda.synchronize();elapsed=time.monotonic()-tick
                stats['steps']+=1;stats['update_seconds']+=elapsed
                record=dict(step=stats['steps'],batch=batch_index,iteration=iteration,loss=sum(losses)/len(losses),
                    grad_norm=float(norm),seconds=elapsed,elapsed_seconds=time.monotonic()-started,
                    sample_ids=[r['sample_id'] for r in batch],rollouts=len(cached),
                    reward_mean=sum(r['reward'] for r in cached)/len(cached),
                    metrics={k:sum(m[k] for m in metrics)/len(metrics) for k in metrics[0]},
                    max_ratio_delta=max(m['ratio_max_abs_delta'] for m in metrics),totals=dict(stats))
                print(json.dumps(record),file=step_log,flush=True)
                print(json.dumps(dict(input=mode,grpo_step=stats['steps'],reward=record['reward_mean'],
                    kl=record['metrics']['kl'],ratio_delta=record['max_ratio_delta'])),flush=True)
    optimizer.zero_grad(set_to_none=True);del optimizer
    for n,p in model.named_parameters():
        if '.reference.' in n:
            assert not p.requires_grad and p.grad is None
            assert torch.equal(p.detach().cpu(),reference_before[n]),'Reference changed: '+n
    destination=out/('adapter' if status=='complete' else 'partial_adapter')
    model.save_pretrained(destination,selected_adapters=['policy']);tok.save_pretrained(destination)
    model.gradient_checkpointing_disable();model.eval();model.config.use_cache=True
    result=dict(status=status,**stats,planned_steps=len(ordered)//size*cfg['num_iterations'],
        trainable_parameters=sum(p.numel() for p in params),elapsed_seconds=time.monotonic()-started,
        peak_memory_bytes=torch.cuda.max_memory_allocated(),reference_unchanged=True,
        adapter_sha256={str(f.relative_to(destination)):sha(f) for f in destination.rglob('*') if f.is_file()})
    write_json(out/'training.json',result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args();sys.path.insert(0,str(args.root/'src'));sys.path.insert(1,'/root/ConsDagSubmissionReview/src')
    from run_e1 import load_model,render_chat
    from run_e1_v6 import validate_v6_freeze
    from sub_e2_monolithic import parse_plan
    from transformers import AutoTokenizer
    cfg=json.loads(args.config.read_text());parent=Path(cfg['parent']);dependency=Path(cfg['dependency'])
    done,trained=verify_training(parent)
    previous=json.loads((parent/'protocol.json').read_text());assert previous['config_sha256']==cfg['expected_parent_config_sha256']
    completed=json.loads((dependency/'completion.json').read_text())
    assert completed['status']=='complete' and completed['results_sha256']==sha(dependency/'results.json')
    matched=json.loads((dependency/'protocol.json').read_text())
    assert matched['config_sha256']==cfg['expected_matched_config_sha256']
    cache_complete=json.loads((dependency/'compiler_complete.json').read_text())
    assert cache_complete['rows']==96 and cache_complete['sha256']==sha(dependency/'compiler_calls.jsonl')
    data=args.root/'data/processed_v6';validate_v6_freeze(data)
    train_all={r['sample_id']:r for r in read_rows(data/'train.jsonl')}
    dev_all={r['sample_id']:r for r in read_rows(data/'dev.jsonl')}
    training=[train_all[s] for s in matched['train_sample_ids']]
    evaluation=[dev_all[s] for s in matched['eval_sample_ids']]
    assert len(training)==96 and len(evaluation)==144
    assert not {r['group_id'] for r in training}&{r['group_id'] for r in evaluation}
    assert all(r['subset']=='train' for r in training)
    assert matched['initial_adapter_sha256']==trained['adapter_sha256']
    compiled={r['sample_id']:r for r in read_rows(dependency/'compiler_calls.jsonl')}
    assert len(compiled)==96 and set(compiled)==set(matched['train_sample_ids'])
    fixed=Path(cfg['fixed']);assert sha(fixed/'calls.jsonl')==previous['fixed_inputs']['calls.jsonl']
    cached={r['sample_id']:r for r in read_rows(fixed/'calls.jsonl') if r['call']=='sft_first'}
    assert set(cached)==set(matched['eval_sample_ids'])
    model_path=args.root/'models'/cfg['model']
    hashes={str(f.relative_to(model_path)):sha(f) for f in model_path.rglob('*') if f.is_file()}
    assert hashes==previous['model_sha256']
    tok=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    lengths=[]
    for rows,cache in ((training,compiled),(evaluation,cached)):
        for row in rows:
            for mode in cfg['training_inputs']:
                auxiliary=cache[row['sample_id']]['raw'] if mode=='contract' else None
                n=render_chat(tok,explicit_messages(row,auxiliary),add_generation_prompt=True)['input_ids'].numel()
                assert n+cfg['max_new_tokens']<=min(cfg['max_seq_len'],tok.model_max_length)
                lengths.append(n)
    import importlib.metadata as metadata
    protocol=dict(config=cfg,config_sha256=sha(args.config),parent_results_sha256=done['results_sha256'],
        matched_results_sha256=completed['results_sha256'],initial_adapter_sha256=trained['adapter_sha256'],
        compiler_cache_sha256=sha(dependency/'compiler_calls.jsonl'),model_sha256=hashes,
        train_sample_ids=matched['train_sample_ids'],eval_sample_ids=matched['eval_sample_ids'],
        data_sha256={s:sha(data/(s+'.jsonl')) for s in ('train','dev')},max_prompt_tokens=max(lengths),
        source_sha256={str(f):sha(f) for f in Path(__file__).parent.glob('*.py')},
        dependencies={n:metadata.version(n) for n in ('torch','transformers','peft','accelerate')},
        reward='Gold-verifier faithful_success: all constraints and minimal changes; N preserves default.',
        reference='Frozen same shared SFT parent adapter, NOT adapter-disabled pretrained base.',
        sampling='Temperature1/top_p1/top_k0; log probabilities describe the actual untruncated policy.',
        comparison='Same 96 tasks, common start and 24 steps; SFT vs GRPO is not equal compute or equal token exposure.')
    args.out.mkdir(parents=True,exist_ok=True);path=args.out/'protocol.json'
    if path.exists():assert json.loads(path.read_text())==protocol
    else:write_json(path,protocol)
    if args.prepare_only:
        print(json.dumps(dict(preflight='PASS',train_rows=len(training),eval_rows=len(evaluation),max_prompt=max(lengths))));return
    import torch
    torch.set_num_threads(1);assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    started=time.monotonic();results={};records=[]
    with (args.out/'calls.jsonl').open('x') as calls,(args.out/'decisions.jsonl').open('x') as decisions:
        for mode in cfg['training_inputs']:
            out=args.out/(mode+'_grpo');out.mkdir(exist_ok=False)
            torch.manual_seed(cfg['seed']);torch.cuda.manual_seed_all(cfg['seed']);torch.cuda.reset_peak_memory_stats()
            tick=time.monotonic();base,tok=load_model(str(model_path),'bf16')
            model=load_policy_reference(base,parent/'adapter');load_seconds=time.monotonic()-tick
            trained_arm=train_arm(model,tok,training,compiled,mode,cfg,out)
            results[mode]=dict(training=trained_arm,load_seconds=load_seconds)
            if trained_arm['status']!='complete':raise RuntimeError('Incomplete training retained; no incomplete-arm comparison')
            eval_start=time.monotonic()
            for index,row in enumerate(evaluation):
                for condition in (['raw','contract'] if index%2==0 else ['contract','raw']):
                    if time.monotonic()-eval_start>=cfg['eval_seconds_cap']-60:raise TimeoutError('Eval budget; partial outputs retained')
                    auxiliary=cached[row['sample_id']]['raw'] if condition=='contract' else None
                    messages=explicit_messages(row,auxiliary)
                    inp={k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
                    torch.cuda.synchronize();tick=time.monotonic()
                    with torch.inference_mode():output=model.generate(**inp,do_sample=False,max_new_tokens=cfg['max_new_tokens'],pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                    torch.cuda.synchronize();new=output[0,inp['input_ids'].shape[1]:];raw=tok.decode(new,skip_special_tokens=True)
                    cost=dict(calls=1,seconds=time.monotonic()-tick,prompt_tokens=inp['input_ids'].numel(),output_tokens=new.numel())
                    arm=mode+'_grpo/'+condition;candidate=parse_plan(raw,public_row(row))
                    print(json.dumps(dict(sample_id=row['sample_id'],arm=arm,messages=messages,raw=raw,cost=cost,cap_hit=new.numel()==cfg['max_new_tokens'])),file=calls,flush=True)
                    record=dict(sample_id=row['sample_id'],arm=arm,plan=candidate,outcome=evaluate_plan(row,candidate),
                        string_array=string_array(raw),new_cost=cost,
                        reused_cost=cached[row['sample_id']]['cost'] if condition=='contract' else {k:0 for k in cost})
                    records.append(record);print(json.dumps(record),file=decisions,flush=True)
                print(json.dumps(dict(input=mode,eval_rows=index+1,total_calls=len(records))),flush=True)
            results[mode]['eval_seconds']=time.monotonic()-eval_start
            del model,base;gc.collect();torch.cuda.empty_cache()
    by_arm={arm:[r['outcome'] for r in records if r['arm']==arm] for arm in sorted({r['arm'] for r in records})}
    sft=read_rows(dependency/'decisions.jsonl')
    result=dict(status='complete',runs=results,calls=len(records),elapsed_seconds=time.monotonic()-started,
        arms={k:summarize(v) for k,v in by_arm.items()},
        matched_input_comparison=paired(by_arm['contract_grpo/contract'],by_arm['raw_grpo/raw']),
        grpo_minus_matched_sft={mode:paired(by_arm[mode+'_grpo/'+mode],
            [r['outcome'] for r in sft if r['arm']==mode+'_sft/'+mode]) for mode in cfg['training_inputs']},
        same_raw_input=paired(by_arm['contract_grpo/raw'],by_arm['raw_grpo/raw']),
        same_contract_input=paired(by_arm['contract_grpo/contract'],by_arm['raw_grpo/contract']),
        costs={kind:{k:sum(r[kind][k] for r in records) for k in ('calls','seconds','prompt_tokens','output_tokens')}
            for kind in ('new_cost','reused_cost')},
        caveat='Exploratory fixed dev, seed42, bounded 24-update baseline; not a new GRPO method or convergence claim.')
    write_json(args.out/'results.json',result);write_json(args.out/'completion.json',dict(status='complete',results_sha256=sha(args.out/'results.json')))


if __name__=='__main__':main()
