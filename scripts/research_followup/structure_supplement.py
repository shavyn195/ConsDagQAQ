"""Fixed-planner interface ablations; oracle is an explicitly privileged diagnostic."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
import time

from common import evaluate_plan, paired, public_row, read_rows, sha, summarize
from fixed_planner import planner_messages, select_groups


def core_payload(parsed, task):
    """Project a whole well-formed contract; never silently delete a bad constraint."""
    from trust_env import normalize_constraint
    if parsed is None or any(normalize_constraint(c, task) is None for c in parsed['constraints']):
        return {'interface_status':'invalid', 'constraints':None}
    return {'interface_status':'valid', 'constraints':[
        {'type':c['type'], 'params':c['params']} for c in parsed['constraints']]}


def core_text(parsed, task):
    return json.dumps(core_payload(parsed,task),ensure_ascii=False,sort_keys=True)


def compiler_index(records, sample_ids):
    indexed = {}
    for record in records:
        if record['sample_id'] not in sample_ids or record['call'] not in ('pe_first','sft_first'):
            continue
        key = (record['sample_id'],record['call'])
        if key in indexed:
            raise ValueError('Duplicate frozen compiler call')
        indexed[key] = record
    if set(indexed) != {(sid,kind) for sid in sample_ids for kind in ('pe_first','sft_first')}:
        raise ValueError('Missing frozen compiler call; do not substitute a different cache')
    return indexed


def complete_group_ids(records, rows, arms):
    """One E/I/N trio, every arm, or no paired inference for that group."""
    seen = set()
    for record in records:
        key = (record['sample_id'],record['arm'])
        if key in seen:
            raise ValueError('Duplicate decision')
        seen.add(key)
    groups = defaultdict(list)
    for row in rows:
        groups[row['group_id']].append(row)
    return {g for g,rs in groups.items()
            if sorted(r['variant'] for r in rs)==['explicit','implicit','none']
            and all((r['sample_id'],arm) in seen for r in rs for arm in arms)}


def report(records, previous, rows, arms):
    complete = complete_group_ids(records,rows,arms)
    subset = [r for r in records if r['outcome']['group_id'] in complete]
    by_arm = {arm:[r['outcome'] for r in subset if r['arm']==arm] for arm in arms}
    old = {arm:[r['outcome'] for r in previous if r['arm']==arm and r['outcome']['group_id'] in complete]
           for arm in ('direct','generic','pe','sft')}
    comparisons = {'discarded_pe_minus_direct':paired(by_arm['discarded_pe'],old['direct']),
                   'predicted_core_minus_full_sft':paired(by_arm['predicted_core'],old['sft']),
                   'predicted_core_minus_generic':paired(by_arm['predicted_core'],old['generic']),
                   'oracle_core_minus_predicted_core':paired(by_arm['oracle_core'],by_arm['predicted_core'])}
    old_plans = {r['sample_id']:r['plan'] for r in previous if r['arm']=='direct'}
    repeats = [r for r in records if r['arm']=='discarded_pe']
    return dict(complete_ein_groups=len(complete), decisions_not_in_complete_groups=len(records)-len(subset),
                arms={arm:summarize(outcomes) for arm,outcomes in by_arm.items()},
                previous_same_panel={arm:summarize(outcomes) for arm,outcomes in old.items()},
                paired=comparisons, direct_repeat=dict(n=len(repeats),identical_plans=sum(
                    r['plan']==old_plans[r['sample_id']] for r in repeats)),
                warning='Exploratory dev; oracle is privileged, not a deployable competitor. No multiple-comparison correction.')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--prepare-only',action='store_true')
    a=p.parse_args()
    sys.path.insert(0,str(a.root/'src'))
    sys.path.insert(1,'/root/ConsDagSubmissionReview/src')
    from run_e1 import load_model, render_chat, strict_parse
    from run_e1_v6 import validate_v6_freeze
    from sub_e2_monolithic import parse_plan
    from transformers import AutoTokenizer
    cfg=json.loads(a.config.read_text())
    previous=Path(cfg['previous'])
    data=a.root/'data/processed_v6'
    validate_v6_freeze(data)
    rows=select_groups(read_rows(data/'dev.jsonl'),cfg['groups'])
    sample_ids=[r['sample_id'] for r in rows]
    model_path=a.root/'models'/cfg['model']
    adapter=a.root/'outputs/e1_v6/Qwen3-4B-v6-seed42/adapter'
    if not (adapter/'adapter_model.safetensors').exists():
        raise ValueError('Reference adapter missing')
    previous_protocol=json.loads((previous/'protocol.json').read_text())
    if previous_protocol['panel']!=sample_ids:
        raise ValueError('Reference panel mismatch')
    tok=AutoTokenizer.from_pretrained(str(model_path),local_files_only=True)
    # Preflight only: use the sealed compiler cache to check representative lengths.
    cache=a.root/'outputs/e1_v6/Qwen3-4B-v6-seed42/trained_predictions/dev.jsonl'
    predicted={r['sample_id']:r['raw'] for r in read_rows(cache)}
    lengths=[]
    for row in rows:
        for aux in (None,core_text(strict_parse(predicted[row['sample_id']]),row['task']),
                    core_text(row['gold'],row['task'])):
            n=render_chat(tok,planner_messages(public_row(row),aux),add_generation_prompt=True)['input_ids'].numel()
            if n+cfg['max_new_tokens']>tok.model_max_length:
                raise ValueError('Context overflow')
            lengths.append(n)
    import run_e1, trust_env, sub_e2_public_contract, sub_e2_monolithic
    manifest=dict(config=cfg,config_sha256=sha(a.config),data_sha256=sha(data/'dev.jsonl'),
        previous_protocol_sha256=sha(previous/'protocol.json'),preflight_compiler_cache_sha256=sha(cache),
        sample_ids=sample_ids,max_prompt_tokens=max(lengths),
        source_sha256={**{str(f):sha(f) for f in Path(__file__).parent.glob('*.py')},
                       **{str(Path(m.__file__)):sha(Path(m.__file__)) for m in
                          (run_e1,trust_env,sub_e2_public_contract,sub_e2_monolithic)}},
        model_sha256={str(f.relative_to(model_path)):sha(f) for f in model_path.rglob('*') if f.is_file()},
        adapter_sha256={f.name:sha(f) for f in adapter.iterdir() if f.is_file()},
        planner='Identical base 4B through the same disabled PEFT wrapper; greedy bf16 batch1',
        oracle='Only oracle_core may read gold into its input; all real arms use public input and frozen first calls.')
    a.out.mkdir(parents=True,exist_ok=True)
    path=a.out/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=manifest:
        raise ValueError('Preflight inputs changed')
    if not path.exists(): path.write_text(json.dumps(manifest,indent=2))
    if a.prepare_only:
        print(json.dumps(dict(preflight='PASS',rows=len(rows),max_calls=len(rows)*len(cfg['arms']),
                              max_prompt_tokens=max(lengths),protocol_sha256=sha(path))),flush=True)
        return
    done=json.loads((previous/'completion.json').read_text())
    if done.get('status')!='complete' or done['results_sha256']!=sha(previous/'results.json'):
        raise ValueError('Fixed planner completion not verified')
    indexed=compiler_index(read_rows(previous/'calls.jsonl'),set(sample_ids))
    old=read_rows(previous/'decisions.jsonl')
    input_files={n:sha(previous/n) for n in ('calls.jsonl','decisions.jsonl','results.json','completion.json')}
    (a.out/'reference_receipt.json').write_text(json.dumps(input_files,indent=2))
    if (a.out/'calls.jsonl').exists():
        raise ValueError('Prior output preserved; no implicit restart')
    import torch
    from peft import PeftModel
    torch.set_num_threads(1)
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise ValueError('Native bf16 GPU required')
    started=time.monotonic()
    base,tok=load_model(str(model_path),'bf16')
    model=PeftModel.from_pretrained(base,str(adapter),is_trainable=False)
    model.eval()
    model.config.use_cache=True
    load_seconds=time.monotonic()-started
    torch.cuda.reset_peak_memory_stats()
    records=[]
    status='complete'
    with (a.out/'calls.jsonl').open('x') as calls,(a.out/'decisions.jsonl').open('x') as decisions:
        for index,row in enumerate(rows):
            if status!='complete': break
            shift=index%len(cfg['arms'])
            for arm in cfg['arms'][shift:]+cfg['arms'][:shift]:
                if time.monotonic()-started>=cfg['active_seconds_cap']-90:
                    status='budget_exhausted'
                    break
                sid=row['sample_id']
                first=None
                if arm=='discarded_pe':
                    first=indexed[(sid,'pe_first')]
                    aux=None
                elif arm=='predicted_core':
                    first=indexed[(sid,'sft_first')]
                    aux=core_text(strict_parse(first['raw']),row['task'])
                else:
                    # Privileged diagnostic only, never copied to another arm.
                    aux=core_text(row['gold'],row['task'])
                messages=planner_messages(public_row(row),aux)
                inputs={k:v.to(model.device) for k,v in render_chat(tok,messages,add_generation_prompt=True).items()}
                if inputs['input_ids'].numel()+cfg['max_new_tokens']>tok.model_max_length:
                    raise ValueError('Actual prompt exceeds context')
                torch.cuda.synchronize()
                t=time.monotonic()
                with model.disable_adapter(),torch.inference_mode():
                    output=model.generate(**inputs,do_sample=False,max_new_tokens=cfg['max_new_tokens'],
                        pad_token_id=tok.pad_token_id,eos_token_id=tok.eos_token_id)
                torch.cuda.synchronize()
                new=output[0,inputs['input_ids'].shape[1]:]
                cost=dict(calls=1,prompt_tokens=inputs['input_ids'].numel(),output_tokens=new.numel(),seconds=time.monotonic()-t)
                raw=tok.decode(new,skip_special_tokens=True)
                print(json.dumps(dict(sample_id=sid,arm=arm,messages=messages,raw=raw,cost=cost,
                    cap_hit=new.numel()==cfg['max_new_tokens'])),file=calls,flush=True)
                candidate=parse_plan(raw,{'task':row['task']})
                # Real-arm scoring uses gold only after its plan is frozen.
                outcome=evaluate_plan(row,candidate)
                reused=first['cost'] if first else {k:0 for k in cost}
                record=dict(sample_id=sid,arm=arm,plan=candidate,outcome=outcome,new_cost=cost,
                    reused_first_cost=reused,pipeline_cost={k:cost[k]+reused[k] for k in cost},
                    oracle_privileged=arm=='oracle_core')
                records.append(record)
                print(json.dumps(record),file=decisions,flush=True)
            print(json.dumps(dict(rows_reached=index+1,total=len(rows),calls=len(records),elapsed_s=time.monotonic()-started)),flush=True)
    result=report(records,old,rows,cfg['arms'])
    result.update(status=status,elapsed_s=time.monotonic()-started,load_seconds=load_seconds,
                  peak_memory_allocated_bytes=torch.cuda.max_memory_allocated(),protocol_sha256=sha(path))
    result['cost']={arm:{kind:{k:sum(r[kind][k] for r in records if r['arm']==arm)
                       for k in ('calls','prompt_tokens','output_tokens','seconds')}
                       for kind in ('new_cost','reused_first_cost','pipeline_cost')} for arm in cfg['arms']}
    (a.out/'results.json').write_text(json.dumps(result,indent=2))
    (a.out/'completion.json').write_text(json.dumps(dict(status=status,results_sha256=sha(a.out/'results.json'),calls=len(records))))


if __name__=='__main__':
    main()
