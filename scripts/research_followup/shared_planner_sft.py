"""A train-only shared planner initialization, followed by frozen-input comparisons."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import sys
import time

from common import evaluate_plan, paired, read_rows, sha, summarize
from fixed_planner import select_groups
from format_recovery import explicit_messages, smoke_gate, string_array
from structure_supplement import complete_group_ids, core_text


def select_training(rows, count, salt, evaluation_rows):
    """Hash only group identity; neither target difficulty nor dev performance selects training."""
    if any(r.get('subset') != 'train' for r in rows):
        raise ValueError('Only the frozen train split can initialize the planner')
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate training sample')
    if {r['group_id'] for r in rows} & {r['group_id'] for r in evaluation_rows}:
        raise ValueError('Training/evaluation group leakage')
    if {r['sample_id'] for r in rows} & {r['sample_id'] for r in evaluation_rows}:
        raise ValueError('Training/evaluation sample leakage')
    groups = defaultdict(list)
    for row in rows:
        groups[row['group_id']].append(row)
    chosen = sorted(groups, key=lambda g: hashlib.sha256((salt+g).encode()).digest())[:count]
    if len(chosen) != count or any(sorted(r['variant'] for r in groups[g]) !=
                                   ['explicit', 'implicit', 'none'] for g in chosen):
        raise ValueError('Training selection must contain complete E/I/N groups')
    return [r for g in chosen for r in groups[g]]


def training_target(row):
    from trust_env import default_plan
    candidate = row['witness_plan'] if row['gold']['constraints'] else default_plan(row['task'])
    if not evaluate_plan(row, candidate)['faithful_success']:
        raise ValueError('Training witness failed independent task checks: '+row['sample_id'])
    return json.dumps(candidate, separators=(',', ':'))


def accumulation_batches(examples, accumulation):
    if not examples or accumulation <= 0 or len(examples) % accumulation:
        raise ValueError('No dropped or underweighted accumulation tail is permitted')
    return [examples[i:i+accumulation] for i in range(0, len(examples), accumulation)]


def write_json(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    temp.replace(path)


def train(model, tokenizer, examples, cfg, out, started):
    import torch
    from peft import LoraConfig, get_peft_model, PeftModel
    from peft.tuners.lora import model as peft_lora_model
    from run_e1 import require_finite_loss
    if hasattr(peft_lora_model, 'dispatch_torchao'):
        peft_lora_model.dispatch_torchao = lambda *_a, **_k: None
    if cfg.get('initial_planner_adapter'):
        model = PeftModel.from_pretrained(model,cfg['initial_planner_adapter'],is_trainable=True)
    else:
        model = get_peft_model(model, LoraConfig(r=cfg['lora_rank'], lora_alpha=cfg['lora_alpha'],
            lora_dropout=cfg['lora_dropout'], target_modules=cfg['target_modules'], task_type='CAUSAL_LM'))
    model.config.use_cache = False
    if cfg['gradient_checkpointing']:
        model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    model.train()
    parameters = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(parameters, lr=cfg['learning_rate'], weight_decay=cfg['weight_decay'])
    ordered = list(examples)
    random.Random(cfg['seed']).shuffle(ordered)
    batches = accumulation_batches(ordered, cfg['gradient_accumulation_steps'])
    assert cfg['epochs'] == 1, 'This bounded initialization is exactly one epoch'
    steps = 0
    tokens = dict(prompt=0, completion=0)
    status = 'complete'
    with (out/'train_steps.jsonl').open('x', encoding='utf-8') as log:
        for batch in batches:
            # Budget is checked only at whole optimizer-step boundaries.
            if time.monotonic()-started >= cfg['train_seconds_cap']-90:
                status = 'train_budget_exhausted'
                break
            tick = time.monotonic()
            losses = []
            optimizer.zero_grad(set_to_none=True)
            for example in batch:
                ids = torch.tensor([example['ids']], dtype=torch.long, device=model.device)
                labels = torch.tensor([example['labels']], dtype=torch.long, device=model.device)
                result = model(input_ids=ids, attention_mask=torch.ones_like(ids), labels=labels)
                require_finite_loss(result.loss, torch=torch, epoch=1,
                                    example_index=steps*len(batch)+len(losses), optimizer_step=steps+1)
                (result.loss/len(batch)).backward()
                losses.append(float(result.loss.detach().cpu()))
                tokens['prompt'] += example['prompt_tokens']
                tokens['completion'] += len(example['ids'])-example['prompt_tokens']
                del result
            norm = torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(p.detach()).all() for p in parameters):
                raise FloatingPointError('Nonfinite parameter after optimizer step')
            steps += 1
            record = dict(step=steps, loss=sum(losses)/len(losses), grad_norm=float(norm),
                          seconds=time.monotonic()-tick, elapsed_seconds=time.monotonic()-started,
                          sample_ids=[e['sample_id'] for e in batch], tokens=dict(tokens))
            print(json.dumps(record), file=log, flush=True)
            print(json.dumps(dict(train_step=steps, loss=record['loss'], seconds=record['seconds'])), flush=True)
    optimizer.zero_grad(set_to_none=True)
    del optimizer
    destination = out/('adapter' if status == 'complete' else 'partial_adapter')
    model.save_pretrained(destination)
    tokenizer.save_pretrained(destination)
    model.gradient_checkpointing_disable()
    model.config.use_cache = True
    model.eval()
    torch.cuda.empty_cache()
    result = dict(status=status, steps=steps, planned_steps=len(batches), examples_seen=steps*len(batches[0]),
                  trainable_parameters=sum(p.numel() for p in parameters), tokens=tokens,
                  elapsed_seconds=time.monotonic()-started,
                  peak_memory_bytes=torch.cuda.max_memory_allocated(),
                  adapter_sha256={f.name:sha(f) for f in destination.iterdir() if f.is_file()})
    write_json(out/'training.json', result)
    return model, result


def evaluate(model, tok, rows, first, cfg, out):
    import torch
    from run_e1 import render_chat
    from sub_e2_monolithic import parse_plan
    started = time.monotonic()
    records = []
    status = 'complete'
    gate = None
    with (out/'calls.jsonl').open('x') as calls, (out/'decisions.jsonl').open('x') as decisions:
        for index, row in enumerate(rows):
            if index == cfg['smoke_groups']*3:
                gate = smoke_gate(records, cfg)
                write_json(out/'smoke_gate.json', gate)
                if not gate['passed']:
                    status = 'smoke_gate_failed'
                    break
            if status != 'complete':
                break
            shift = index % len(cfg['arms'])
            for arm in cfg['arms'][shift:]+cfg['arms'][:shift]:
                if time.monotonic()-started >= cfg['eval_seconds_cap']-90:
                    status = 'eval_budget_exhausted'
                    break
                if arm == 'direct':
                    auxiliary, prior = None, None
                elif arm == 'oracle_core':
                    auxiliary, prior = core_text(row['gold'], row['task']), None
                else:
                    cached = first[(row['sample_id'], arm+'_first')]
                    auxiliary, prior = cached['raw'], cached['cost']
                messages = explicit_messages(row, auxiliary)
                inputs = {k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
                torch.cuda.synchronize()
                tick = time.monotonic()
                # The SAME newly trained planner adapter is active in every arm.
                with torch.inference_mode():
                    output = model.generate(**inputs, do_sample=False, max_new_tokens=cfg['max_new_tokens'],
                        pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id)
                torch.cuda.synchronize()
                new = output[0,inputs['input_ids'].shape[1]:]
                raw = tok.decode(new, skip_special_tokens=True)
                cost = dict(calls=1, prompt_tokens=inputs['input_ids'].numel(), output_tokens=new.numel(),
                            seconds=time.monotonic()-tick)
                print(json.dumps(dict(sample_id=row['sample_id'],arm=arm,messages=messages,raw=raw,cost=cost,
                                      cap_hit=new.numel()==cfg['max_new_tokens'])),file=calls,flush=True)
                candidate = parse_plan(raw, row)
                prior = prior or {k:0 for k in cost}
                record = dict(sample_id=row['sample_id'],arm=arm,plan=candidate,outcome=evaluate_plan(row,candidate),
                              string_array=string_array(raw),new_cost=cost,reused_cost=prior,
                              pipeline_cost={k:cost[k]+prior[k] for k in cost})
                records.append(record)
                print(json.dumps(record),file=decisions,flush=True)
            print(json.dumps(dict(eval_rows_reached=index+1,calls=len(records))),flush=True)
    complete = complete_group_ids(records, rows, cfg['arms'])
    by_arm = {a:[r['outcome'] for r in records if r['arm']==a and r['outcome']['group_id'] in complete]
              for a in cfg['arms']}
    return dict(status=status,smoke_gate=gate,complete_ein_groups=len(complete),calls=len(records),
        elapsed_seconds=time.monotonic()-started,arms={a:summarize(rs) for a,rs in by_arm.items()},
        paired={a:paired(by_arm[a],by_arm['direct']) for a in cfg['arms'] if a!='direct'},
        sft_minus_generic=paired(by_arm['sft'],by_arm['generic']),
        cost={a:{kind:{k:sum(r[kind][k] for r in records if r['arm']==a)
                            for k in ('calls','prompt_tokens','output_tokens','seconds')}
                 for kind in ('new_cost','reused_cost','pipeline_cost')} for a in cfg['arms']})


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--prepare-only',action='store_true')
    args = p.parse_args()
    sys.path.insert(0,str(args.root/'src'))
    sys.path.insert(1,'/root/ConsDagSubmissionReview/src')
    from run_e1 import load_model, render_chat
    from run_e1_v6 import validate_v6_freeze
    from transformers import AutoTokenizer
    import sub_e2_monolithic,sub_e2_public_contract,trust_env,run_e1
    cfg = json.loads(args.config.read_text())
    data = args.root/'data/processed_v6'
    validate_v6_freeze(data)
    all_dev = read_rows(data/'dev.jsonl')
    rows = select_groups(all_dev,cfg['groups'])
    training = select_training(read_rows(data/'train.jsonl'),cfg['train_groups'],cfg['train_selection_salt'],all_dev)
    model_path = args.root/'models'/cfg['model']
    fixed = Path(cfg['fixed'])
    completed = json.loads((fixed/'completion.json').read_text())
    assert completed['status']=='complete' and completed['results_sha256']==sha(fixed/'results.json')
    previous = json.loads((fixed/'protocol.json').read_text())
    assert previous['panel']==[r['sample_id'] for r in rows]
    first = {}
    for r in read_rows(fixed/'calls.jsonl'):
        if r['call'].endswith('_first'):
            key = (r['sample_id'],r['call'])
            if key in first: raise ValueError('Duplicate cached first-stage output')
            first[key]=r
    assert set(first)=={(r['sample_id'],a+'_first') for r in rows for a in ('generic','pe','sft')}
    tok = AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    examples = []
    for row in training:
        prefix = render_chat(tok,explicit_messages(row),add_generation_prompt=True)['input_ids'][0].tolist()
        answer = tok(training_target(row)+tok.eos_token,add_special_tokens=False)['input_ids']
        if len(prefix)+len(answer)>cfg['max_seq_len']:
            raise ValueError('Training sequence too long; no silent truncation')
        examples.append(dict(sample_id=row['sample_id'],ids=prefix+answer,labels=[-100]*len(prefix)+answer,
                             prompt_tokens=len(prefix)))
    accumulation_batches(examples,cfg['gradient_accumulation_steps'])
    max_eval = 0
    for row in rows:
        for a in cfg['arms']:
            auxiliary = None if a=='direct' else core_text(row['gold'],row['task']) if a=='oracle_core' else first[(row['sample_id'],a+'_first')]['raw']
            n = render_chat(tok,explicit_messages(row,auxiliary),add_generation_prompt=True)['input_ids'].numel()
            assert n+cfg['max_new_tokens']<=tok.model_max_length
            max_eval = max(max_eval,n)
    hashes = {str(f.relative_to(model_path)):sha(f) for f in model_path.rglob('*') if f.is_file()}
    assert hashes==previous['model_sha256']
    protocol = dict(config=cfg,config_sha256=sha(args.config),
        data_sha256={s:sha(data/(s+'.jsonl')) for s in ('train','dev')},
        train_sample_ids=[r['sample_id'] for r in training],eval_sample_ids=[r['sample_id'] for r in rows],
        model_sha256=hashes,fixed_inputs={n:sha(fixed/n) for n in ('calls.jsonl','protocol.json','completion.json','results.json')},
        source_sha256={str(f):sha(f) for f in Path(__file__).parent.glob('*.py')},
        dependency_source_sha256={str(Path(m.__file__)):sha(m.__file__) for m in
            (sub_e2_monolithic,sub_e2_public_contract,trust_env,run_e1)},
        max_train_tokens=max(len(e['ids']) for e in examples),max_eval_prompt_tokens=max_eval,
        train_examples=len(examples),optimizer_steps=len(examples)//cfg['gradient_accumulation_steps'],
        training_prompt='Only original request + public task; no compiled/gold auxiliary input',
        checkpoint_selection='Final fixed one-epoch model only; no dev-based selection')
    args.out.mkdir(parents=True,exist_ok=True)
    path = args.out/'protocol.json'
    if path.exists():
        if json.loads(path.read_text())!=protocol: raise ValueError('Prepared protocol changed')
    else: write_json(path,protocol)
    if args.prepare_only:
        print(json.dumps(dict(preflight='PASS',train_rows=len(training),steps=protocol['optimizer_steps'],
                              max_train_tokens=protocol['max_train_tokens'],max_eval_prompt_tokens=max_eval)),flush=True)
        return
    dependency = Path(cfg['dependency'])
    done = json.loads((dependency/'completion.json').read_text())
    assert done['status'] in cfg.get('accepted_dependency_statuses',['smoke_gate_failed'])
    assert done['results_sha256']==sha(dependency/'results.json')
    if cfg.get('dependency_results_sha256'):
        assert done['results_sha256']==cfg['dependency_results_sha256']
    assert not (args.out/'train_steps.jsonl').exists(), 'Existing run must be preserved'
    import torch
    torch.set_num_threads(1)
    assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    torch.manual_seed(cfg['seed']); torch.cuda.manual_seed_all(cfg['seed'])
    torch.cuda.reset_peak_memory_stats()
    started = time.monotonic()
    model,tok = load_model(str(model_path),'bf16')
    load_seconds = time.monotonic()-started
    model,trained = train(model,tok,examples,cfg,args.out,started)
    result = dict(status=trained['status'],training=trained,load_seconds=load_seconds)
    if trained['status']=='complete':
        result.update(evaluate(model,tok,rows,first,cfg,args.out))
    result['total_elapsed_seconds']=time.monotonic()-started
    write_json(args.out/'results.json',result)
    write_json(args.out/'completion.json',dict(status=result['status'],results_sha256=sha(args.out/'results.json')))


if __name__=='__main__': main()
