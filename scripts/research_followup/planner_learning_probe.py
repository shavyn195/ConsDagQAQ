"""Matched sampled policies before/after shared SFT; diagnostic only, no updates."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import time

from common import evaluate_plan, public_row, read_rows, sha
from format_recovery import explicit_messages
from planner_reward_probe import outcome_vector, select_panel, summarize_groups
from audit_comparison_signal import summarize as comparison_summary


def policy_input(arm):
    if arm not in ('base_raw','base_contract','sft_raw','sft_contract'):
        raise ValueError('Unregistered policy/input arm')
    return arm.startswith('sft_'),arm.endswith('_contract')


def verify_training(dependency):
    done=json.loads((dependency/'completion.json').read_text())
    assert done['status']=='complete' and done['results_sha256']==sha(dependency/'results.json')
    trained=json.loads((dependency/'training.json').read_text())
    assert trained['status']=='complete' and trained['steps']==trained['planned_steps']==96
    actual={f.name:sha(f) for f in (dependency/'adapter').iterdir() if f.is_file()}
    assert actual==trained['adapter_sha256']
    return done,trained


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    args=p.parse_args()
    sys.path.insert(0,str(args.root/'src'))
    sys.path.insert(1,'/root/ConsDagSubmissionReview/src')
    from run_e1 import load_model,render_chat
    from run_e1_v6 import validate_v6_freeze
    from sub_e2_monolithic import parse_plan
    from transformers import AutoTokenizer
    cfg=json.loads(args.config.read_text())
    dependency=Path(cfg['dependency'])
    done,trained=verify_training(dependency)
    previous=json.loads((dependency/'protocol.json').read_text())
    assert previous['config_sha256']==cfg['expected_training_config_sha256']
    data=args.root/'data/processed_v6'
    validate_v6_freeze(data)
    rows=select_panel(read_rows(data/'dev.jsonl'),cfg)
    assert not {r['sample_id'] for r in rows}&set(previous['eval_sample_ids'])
    assert not {r['sample_id'] for r in rows}&set(previous['train_sample_ids'])
    cache=args.root/'outputs/e1_v6/Qwen3-4B-v6-seed42/trained_predictions/dev.jsonl'
    predictions=read_rows(cache)
    compiled={r['sample_id']:r['raw'] for r in predictions}
    assert len(compiled)==len(predictions) and all(r['sample_id'] in compiled for r in rows)
    model_path=args.root/'models'/cfg['model']
    hashes={str(f.relative_to(model_path)):sha(f) for f in model_path.rglob('*') if f.is_file()}
    assert hashes==previous['model_sha256']
    tok=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    max_prompt=0
    for row in rows:
        for arm in cfg['arms']:
            _,contract=policy_input(arm)
            messages=explicit_messages(row,compiled[row['sample_id']] if contract else None)
            n=render_chat(tok,messages,add_generation_prompt=True)['input_ids'].numel()
            assert n+cfg['max_new_tokens']<=tok.model_max_length
            max_prompt=max(max_prompt,n)
    args.out.mkdir(parents=True,exist_ok=True)
    manifest=dict(config=cfg,config_sha256=sha(args.config),data_sha256=sha(data/'dev.jsonl'),
        cache_sha256=sha(cache),sample_ids=[r['sample_id'] for r in rows],model_sha256=hashes,
        parent_results_sha256=done['results_sha256'],adapter_sha256=trained['adapter_sha256'],
        max_prompt_tokens=max_prompt,source_sha256={str(f):sha(f) for f in Path(__file__).parent.glob('*.py')})
    with (args.out/'protocol.json').open('x') as f: json.dump(manifest,f,indent=2)
    import torch
    from peft import PeftModel
    torch.set_num_threads(1)
    assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    started=time.monotonic()
    base,tok=load_model(str(model_path),'bf16')
    model=PeftModel.from_pretrained(base,str(dependency/'adapter'),is_trainable=False)
    model.eval(); model.config.use_cache=True
    load_seconds=time.monotonic()-started
    records=[]; status='complete'
    with (args.out/'calls.jsonl').open('x') as stream:
        for index,row in enumerate(rows):
            if status!='complete': break
            shift=index%len(cfg['arms'])
            for arm in cfg['arms'][shift:]+cfg['arms'][:shift]:
                if status!='complete': break
                active,contract=policy_input(arm)
                messages=explicit_messages(row,compiled[row['sample_id']] if contract else None)
                inputs={k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
                for draw in range(cfg['samples_per_prompt']):
                    if time.monotonic()-started>=cfg['active_seconds_cap']-90:
                        status='budget_exhausted'; break
                    seed=cfg['seed']+index*cfg['samples_per_prompt']+draw
                    torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
                    torch.cuda.synchronize(); tick=time.monotonic()
                    with (nullcontext() if active else model.disable_adapter()),torch.inference_mode():
                        output=model.generate(**inputs,do_sample=True,temperature=cfg['temperature'],top_p=cfg['top_p'],
                            max_new_tokens=cfg['max_new_tokens'],pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                    torch.cuda.synchronize()
                    elapsed=time.monotonic()-tick
                    new=output[0,inputs['input_ids'].shape[1]:]
                    raw=tok.decode(new,skip_special_tokens=True)
                    plan=parse_plan(raw,public_row(row))
                    signal=outcome_vector(row,plan)
                    outcome=evaluate_plan(row,plan)
                    assert signal['valid']==outcome['planned']
                    # Keep the old safe scalar for direct comparison; minimality is separately observed.
                    record=dict(sample_id=row['sample_id'],group_id=row['group_id'],variant=row['variant'],
                        arm=arm,draw=draw,seed=seed,messages=messages,raw=raw,plan=plan,signal=signal,outcome=outcome,
                        seconds=elapsed,prompt_tokens=inputs['input_ids'].numel(),output_tokens=new.numel(),
                        cap_hit=new.numel()==cfg['max_new_tokens'])
                    records.append(record)
                    print(json.dumps(record),file=stream,flush=True)
                    print(json.dumps(dict(calls=len(records),maximum_calls=cfg['maximum_model_calls'])),flush=True)
    result=dict(status=status,calls=len(records),groups=summarize_groups(records,cfg['samples_per_prompt'],cfg['arms']),
        comparison_signal=comparison_summary(records,cfg['samples_per_prompt']),
        load_seconds=load_seconds,elapsed_seconds=time.monotonic()-started,
        prompt_tokens=sum(r['prompt_tokens'] for r in records),output_tokens=sum(r['output_tokens'] for r in records),
        planner_seconds=sum(r['seconds'] for r in records),
        scope='Same prompt panel, output contract and draw seeds; different frozen policies. No optimizer update. Cached compiler cost excluded. Not a POLPO or GRPO reproduction.')
    (args.out/'results.json').write_text(json.dumps(result,indent=2))
    (args.out/'completion.json').write_text(json.dumps(dict(status=status,results_sha256=sha(args.out/'results.json'))))


if __name__=='__main__': main()
