"""Dev-only fixed 4B planner; direct, generic decomposition, PE and SFT compiler."""
import argparse
from collections import defaultdict
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from common import evaluate_plan, paired, public_row, read_rows, sha, summarize


def select_groups(rows, count):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['group_id']].append(row)
    chosen = sorted(grouped, key=lambda g: hashlib.sha256(('fixed-planner-20261126:'+g).encode()).digest())[:count]
    if len(chosen) != count or any(sorted(r['variant'] for r in grouped[g]) != ['explicit','implicit','none'] for g in chosen):
        raise ValueError('Panel requires complete E/I/N groups')
    return [row for g in chosen for row in grouped[g]]


def planner_messages(row, auxiliary=None):
    from sub_e2_public_contract import public_messages
    messages = public_messages(public_row(row))
    if auxiliary is not None:
        messages[-1]['content'] += '\nPreliminary analysis (may contain mistakes; use the original request and public task):\n'+auxiliary+'\nPlan JSON:'
    return messages


def summary_messages(row):
    messages = planner_messages(row)
    messages[0]['content'] = 'Analyze the task briefly before a separate planning step.'
    messages[-1]['content'] += '\nFor this call only, give a concise task decomposition and relevant requirements, not the final plan.'
    return messages


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--groups', type=int, default=48)
    p.add_argument('--prepare-only', action='store_true')
    a = p.parse_args()
    sys.path.insert(0, str(a.root/'src'))
    # The frozen v6 release predates the public monolithic prompt; use its audited copy.
    sys.path.insert(1, '/root/ConsDagSubmissionReview/src')
    import torch
    torch.set_num_threads(1)
    from run_e1 import chat_messages, load_model, render_chat, strict_parse, score
    from run_e1_v6 import validate_v6_freeze
    from sub_e2_monolithic import parse_plan
    from trust_env import normalize_constraint, plan
    from transformers import AutoTokenizer
    from eval_exec_v6 import evaluate_v6

    data = a.root/'data/processed_v6'
    model_path = a.root/'models/Qwen3-4B'
    adapter = a.root/'outputs/e1_v6/Qwen3-4B-v6-seed42/adapter'
    validate_v6_freeze(data)
    if not (adapter/'adapter_model.safetensors').exists() and not (adapter/'adapter_model.bin').exists():
        raise ValueError('Completed 4B seed42 adapter missing')
    rows = select_groups(read_rows(data/'dev.jsonl'), a.groups)
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    prompts = {}
    for row in rows:
        for label, messages in [('planner', planner_messages(row)), ('summary', summary_messages(row)),
                                 ('compiler', chat_messages(public_row(row)))]:
            encoded = render_chat(tokenizer, messages, add_generation_prompt=True)
            n = encoded['input_ids'].numel()
            if n+384*2 > tokenizer.model_max_length:
                raise ValueError('Context too long')
            prompts[row['sample_id']+'/'+label] = dict(tokens=n, sha256=hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest())
    import sub_e2_public_contract, sub_e2_monolithic, run_e1, trust_env
    sources = {str(Path(m.__file__)):sha(Path(m.__file__)) for m in
               (sub_e2_public_contract, sub_e2_monolithic, run_e1, trust_env)}
    sources.update({str(f):sha(f) for f in Path(__file__).parent.glob('*.py') if f.name != 'remote_ops.py'})
    manifest = dict(revision='dev-fixed-planner-v1', panel=[r['sample_id'] for r in rows],
        data_sha256=sha(data/'dev.jsonl'), source_sha256=sources, prompt_contract=prompts,
        model_sha256={str(f.relative_to(model_path)):sha(f) for f in model_path.rglob('*') if f.is_file()},
        adapter_sha256={f.name:sha(f) for f in adapter.iterdir() if f.is_file()},
        planner='Qwen3-4B base, no adapter; identical public prompt in every arm',
        compiler='Qwen3-4B base PE or v6 SFT seed42; same compiler prompt',
        decoding=dict(do_sample=False, max_new_tokens=384, precision='bf16', thinking=False, batch_size=1),
        calls=dict(direct=1, generic=2, pe=2, sft=2), active_seconds_cap=7200,
        interpretation='Exploratory dev pilot only. No novel mechanism or superiority inferred before results. All costs include failed outputs; loading reported separately.')
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out/'protocol.json'
    if path.exists():
        if json.loads(path.read_text()) != manifest:
            raise ValueError('Prepared manifest changed; preserve old run')
    else:
        path.write_text(json.dumps(manifest,indent=2))
    if a.prepare_only:
        print(json.dumps(dict(preflight='PASS', rows=len(rows), groups=a.groups, protocol_sha256=sha(path))), flush=True)
        return
    if (a.out/'calls.jsonl').exists():
        raise ValueError('Existing partial/completed pilot preserved; no silent resume')
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise ValueError('Native bf16 GPU required')
    from peft import PeftModel
    started = time.monotonic()
    base, tokenizer = load_model(str(model_path),'bf16')
    model = PeftModel.from_pretrained(base, str(adapter), is_trainable=False)
    model.eval()
    model.config.use_cache = True
    load_seconds = time.monotonic()-started
    torch.cuda.reset_peak_memory_stats()
    outcomes = {arm:[] for arm in ('direct','generic','pe','sft','sft_symbolic')}
    costs = {arm:dict(calls=0,prompt_tokens=0,output_tokens=0,seconds=0.) for arm in outcomes}
    compile_raw = {'pe':[], 'sft':[]}
    with (a.out/'calls.jsonl').open('x') as calls, (a.out/'decisions.jsonl').open('x') as decisions:
        def generate(sid, label, messages, trained=False):
            if time.monotonic()-started > 7000:
                raise TimeoutError('Pilot active-time limit; partial output retained')
            inputs = {k:v.to(model.device) for k,v in render_chat(tokenizer,messages,add_generation_prompt=True).items()}
            if inputs['input_ids'].numel()+384 > tokenizer.model_max_length:
                raise ValueError('Augmented prompt exceeds context')
            torch.cuda.synchronize()
            t = time.monotonic()
            with (nullcontext() if trained else model.disable_adapter()), torch.inference_mode():
                generated = model.generate(**inputs, do_sample=False, max_new_tokens=384,
                                           pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
            torch.cuda.synchronize()
            elapsed = time.monotonic()-t
            new = generated[0, inputs['input_ids'].shape[1]:]
            raw = tokenizer.decode(new, skip_special_tokens=True)
            cost = dict(calls=1,prompt_tokens=inputs['input_ids'].numel(), output_tokens=new.numel(),seconds=elapsed)
            print(json.dumps(dict(sample_id=sid, call=label, trained=trained, raw=raw, cost=cost,
                messages=messages, cap_hit=new.numel()==384)), file=calls, flush=True)
            return raw,cost

        for index,row in enumerate(rows):
            sid = row['sample_id']
            compiled = {}
            arms = ('direct','generic','pe','sft')
            shift = index % len(arms)
            for arm in arms[shift:] + arms[:shift]:
                aux = None
                spent = dict(calls=0,prompt_tokens=0,output_tokens=0,seconds=0.)
                if arm != 'direct':
                    messages = summary_messages(row) if arm=='generic' else chat_messages(public_row(row))
                    aux, cost = generate(sid,arm+'_first',messages, trained=arm=='sft')
                    for k in spent:
                        spent[k] += cost[k]
                    if arm in compile_raw:
                        compile_raw[arm].append(aux)
                        compiled[arm] = strict_parse(aux)
                raw, cost = generate(sid,arm+'_plan',planner_messages(row,aux))
                for k in spent:
                    spent[k] += cost[k]
                    costs[arm][k] += spent[k]
                candidate = parse_plan(raw, {'task':row['task']})
                # Gold is first accessed after this arm's decision is fixed.
                outcome = evaluate_plan(row,candidate)
                outcomes[arm].append(outcome)
                print(json.dumps(dict(sample_id=sid,arm=arm,plan=candidate,outcome=outcome,cost=spent)),file=decisions,flush=True)
            parsed = compiled['sft']
            t = time.monotonic()
            candidate = None
            if parsed is not None and all(normalize_constraint(c,row['task']) is not None for c in parsed['constraints']):
                candidate,_ = plan(row['task'],parsed['constraints'])
            symbolic_seconds = time.monotonic()-t
            outcome = evaluate_plan(row,candidate)
            outcomes['sft_symbolic'].append(outcome)
            # Reused first-stage cost is accounted from the logged SFT compiler call below.
            print(json.dumps(dict(sample_id=sid,arm='sft_symbolic',plan=candidate,outcome=outcome,
                                  symbolic_seconds=symbolic_seconds)),file=decisions,flush=True)
            costs['sft_symbolic']['seconds'] += symbolic_seconds
            print(json.dumps(dict(progress=index+1,total=len(rows),elapsed_s=time.monotonic()-started)),flush=True)
    for record in read_rows(a.out/'calls.jsonl'):
        if record['call']=='sft_first':
            for k in costs['sft_symbolic']:
                costs['sft_symbolic'][k] += record['cost'][k]
    report = dict(arms={k:summarize(v) for k,v in outcomes.items()}, cost=costs,
        paired={k:paired(outcomes[k],outcomes['direct']) for k in ('generic','pe','sft')},
        sft_minus_generic=paired(outcomes['sft'],outcomes['generic']),
        compiler={k:dict(fields=score(rows,[strict_parse(r) for r in raws],raws),
                        symbolic_fail_closed=evaluate_v6(rows,raws)[0]) for k,raws in compile_raw.items()},
        load_seconds=load_seconds,elapsed_s=time.monotonic()-started,
        peak_memory_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_memory_reserved_bytes=torch.cuda.max_memory_reserved(), protocol_sha256=sha(path))
    (a.out/'results.json').write_text(json.dumps(report,indent=2))
    (a.out/'completion.json').write_text(json.dumps(dict(status='complete', results_sha256=sha(a.out/'results.json'))))


if __name__=='__main__':
    main()
