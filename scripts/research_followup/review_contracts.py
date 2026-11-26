"""Bounded CPU model experiment on saved natural errors; no new training."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from common import align, evaluate_plan, public_row, read_rows, sha, summarize
from run_e1 import chat_messages, render_chat, strict_parse
from trust_env import normalize_constraint, plan, PRECEDENCE_KEYS

ARMS = ('invalid_fields', 'full_binding', 'fresh_compile')


def repair_slots(parsed: dict | None, task: dict) -> dict[int, list[str] | None]:
    """None permits replacement of an untyped clause; valid fields stay frozen."""
    if parsed is None:
        return {}
    slots = {}
    for i, clause in enumerate(parsed['constraints']):
        if normalize_constraint(clause, task) is not None:
            continue
        keys = PRECEDENCE_KEYS.get(clause['type'])
        if keys:
            bad = []
            for key in keys:
                value = clause['params'].get(key)
                role = value.removeprefix('role:').strip() if isinstance(value, str) else None
                if role not in task['tools']:
                    bad.append(key)
            slots[i] = bad if bad else None
        else:
            slots[i] = None
    return slots


def project_fields(before: dict | None, reviewed: dict | None, task: dict) -> dict | None:
    if before is None or reviewed is None or len(before['constraints']) != len(reviewed['constraints']):
        return None
    result = deepcopy(before)
    for i, keys in repair_slots(before, task).items():
        if keys is None:
            result['constraints'][i] = deepcopy(reviewed['constraints'][i])
        else:
            for key in keys:
                if key not in reviewed['constraints'][i]['params']:
                    return None
                result['constraints'][i]['params'][key] = reviewed['constraints'][i]['params'][key]
    return result


def messages(row: dict, raw: str, original: list | None, arm: str) -> list[dict]:
    result = chat_messages(public_row(row))
    instruction = {
        'invalid_fields': 'Repair only fields that fail the supplied catalogue/type checks. Preserve clause order, all valid fields, and all other clauses. A malformed clause may be rewritten if no individual invalid role field is identified. Return the COMPLETE contract JSON, not a patch.',
        'full_binding': 'Review every clause against the original request. A valid catalogue role may still be the wrong target. Verify applicability, constraint type, both roles, direction, thresholds and source evidence; correct or remove unsupported clauses and add omitted ones. Return the COMPLETE corrected contract JSON.',
        'fresh_compile': 'Compile the complete contract afresh from the original request and public policy. Treat the draft solely as an untrusted previous attempt, not evidence. Derive all applicable constraints independently and return the COMPLETE contract JSON.',
    }[arm]
    extra = dict(public_task=row['task'], original_plan=original, untrusted_compiler_output=raw,
                 invalid_field_locations=repair_slots(strict_parse(raw), row['task']))
    result[-1]['content'] += '\nReview context (draft can contain mistakes):\n' + json.dumps(extra, ensure_ascii=False)
    result[-1]['content'] += '\n' + instruction + '\nOutput JSON only; do not explain.\nJSON:'
    return result


def select_panel(source: Path, history: Path, cases_path: Path) -> list[dict]:
    """Freeze six previously identified task groups; retain all E/I/N siblings."""
    cases = read_rows(cases_path)
    wanted = {(r['split'], r['group_id']) for r in cases}
    panel = []
    for split in sorted({s for s, _ in wanted}):
        rows = read_rows(source / 'data/processed_v5' / (split + '.jsonl'))
        preds = align(rows, read_rows(source / 'outputs/e1/Qwen3-1.7B-v5-seed44/trained_predictions' / (split + '.jsonl')))
        plans = align(rows, read_rows(history / (split + '.jsonl')))
        for row, pred, record in zip(rows, preds, plans):
            if (split, row['group_id']) in wanted:
                panel.append(dict(row=row, compiler_raw=pred['raw'], original=record['decision']['original'], split=split))
    grouped = Counter((p['split'], p['row']['group_id']) for p in panel)
    if set(grouped) != wanted or any(n != 3 for n in grouped.values()):
        raise ValueError('Missing complete E/I/N siblings')
    for key in wanted:
        if sorted(p['row']['variant'] for p in panel if (p['split'], p['row']['group_id']) == key) != ['explicit', 'implicit', 'none']:
            raise ValueError('Invalid variant membership')
    # Only group ID and fixed salt choose order, never scores or review outputs.
    return sorted(panel, key=lambda p: (hashlib.sha256(('review-bindings-20261126:' + p['row']['group_id']).encode()).hexdigest(), p['row']['sample_id']))


def consume(row: dict, parsed: dict | None) -> tuple[list | None, dict]:
    candidate = None
    if parsed is not None and all(normalize_constraint(c, row['task']) is not None for c in parsed['constraints']):
        candidate, _ = plan(row['task'], parsed['constraints'])
    return candidate, evaluate_plan(row, candidate)


def main(a: argparse.Namespace) -> None:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, StoppingCriteria, StoppingCriteriaList
    torch.set_num_threads(a.threads)
    torch.set_num_interop_threads(1)
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('This probe must have CUDA hidden')
    a.out.mkdir(parents=True, exist_ok=False)
    panel = select_panel(a.source, a.history, a.cases)
    protocol = json.loads(a.protocol.read_text(encoding='utf-8'))
    if protocol['max_new_tokens'] != a.max_tokens or protocol['active_seconds_cap'] != a.seconds or protocol['threads'] != a.threads:
        raise ValueError('CLI differs from preregistered protocol')
    source_files = [Path(__file__), Path(__file__).with_name('common.py')]
    source_files += [Path(__file__).resolve().parents[2] / 'src' / n for n in ('run_e1.py', 'trust_env.py', 'dataset_v5_spec.py')]
    inputs = {str(a.cases): sha(a.cases)}
    for split in sorted({p['split'] for p in panel}):
        for path in (a.source / 'data/processed_v5' / (split+'.jsonl'),
                     a.source / 'outputs/e1/Qwen3-1.7B-v5-seed44/trained_predictions' / (split+'.jsonl'),
                     a.history / (split+'.jsonl')):
            inputs[str(path)] = sha(path)
    model_hashes = {str(p.relative_to(a.model)): sha(p) for p in a.model.rglob('*') if p.is_file()}
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), pid=os.getpid(), protocol=protocol,
                    protocol_sha256=sha(a.protocol), source_sha256={str(p):sha(p) for p in source_files},
                    input_sha256=inputs, model_sha256=model_hashes,
                    panel=[p['row']['sample_id'] for p in panel],
                    scope='Exposed historical-error diagnostic. Not independent confirmation or a natural error-rate estimate.')
    (a.out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (a.out/'panel.jsonl').write_text(''.join(json.dumps(p, ensure_ascii=False)+'\n' for p in panel), encoding='utf-8')
    started = time.monotonic()
    deadline = started + a.seconds
    tokenizer = AutoTokenizer.from_pretrained(str(a.model), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(str(a.model), torch_dtype=torch.float32,
               local_files_only=True, device_map='cpu', attn_implementation='sdpa').eval()
    if any(p.device.type != 'cpu' for p in model.parameters()):
        raise ValueError('Model is not entirely on CPU')
    model.config.use_cache = True
    loaded = time.monotonic() - started
    class WallLimit(StoppingCriteria):
        def __call__(self, input_ids, scores, **kwargs):
            return time.monotonic() >= deadline
    (a.out/'state.json').write_text(json.dumps(dict(status='running',pid=os.getpid(),loaded_seconds=loaded)),encoding='utf-8')
    print(json.dumps(dict(status='loaded',seconds=loaded,rows=len(panel),calls=len(panel)*len(ARMS))),flush=True)
    outcomes = {arm: [] for arm in (*ARMS, 'unreviewed')}
    completed_rows = []
    with (a.out/'calls.jsonl').open('x',encoding='utf-8') as log, (a.out/'decisions.jsonl').open('x',encoding='utf-8') as decisions:
        for index, item in enumerate(panel):
            row = item['row']; sid = row['sample_id']
            if time.monotonic() >= deadline:
                break
            pending = {}
            base_plan, base_score = consume(row, strict_parse(item['compiler_raw']))
            print(json.dumps(dict(sample_id=sid,arm='unreviewed',plan=base_plan,outcome=base_score)),file=decisions,flush=True)
            shift = index % len(ARMS)
            for arm in ARMS[shift:] + ARMS[:shift]:
                if time.monotonic() >= deadline:
                    break
                prompt = messages(row,item['compiler_raw'],item['original'],arm)
                encoded = render_chat(tokenizer,prompt,add_generation_prompt=True)
                if encoded['input_ids'].numel()+a.max_tokens > tokenizer.model_max_length:
                    raise ValueError('Prompt exceeds model context')
                t = time.monotonic()
                with torch.inference_mode():
                    generated = model.generate(**encoded,do_sample=False,max_new_tokens=a.max_tokens,
                        pad_token_id=tokenizer.eos_token_id,eos_token_id=tokenizer.eos_token_id,
                        stopping_criteria=StoppingCriteriaList([WallLimit()]))
                new = generated[0,encoded['input_ids'].shape[1]:]
                raw = tokenizer.decode(new,skip_special_tokens=True)
                reviewed = strict_parse(raw)
                applied = project_fields(strict_parse(item['compiler_raw']),reviewed,row['task']) if arm=='invalid_fields' else reviewed
                candidate, scored = consume(row,applied)
                record = dict(sample_id=sid,arm=arm,raw=raw,messages=prompt,
                    prompt_tokens=encoded['input_ids'].numel(),output_tokens=new.numel(),seconds=time.monotonic()-t,
                    cap_hit=new.numel()==a.max_tokens,deadline_hit=time.monotonic()>=deadline,
                    applied_contract=applied,plan=candidate,outcome=scored)
                print(json.dumps(record,ensure_ascii=False),file=log,flush=True)
                print(json.dumps(dict(sample_id=sid,arm=arm,plan=candidate,outcome=scored)),file=decisions,flush=True)
                pending[arm] = scored
                print(json.dumps({k:record[k] for k in ('sample_id','arm','output_tokens','seconds','cap_hit','deadline_hit')}),flush=True)
            if set(pending)==set(ARMS):
                for arm in ARMS:
                    outcomes[arm].append(pending[arm])
                outcomes['unreviewed'].append(base_score)
                completed_rows.append(sid)
    elapsed = time.monotonic()-started
    calls = read_rows(a.out/'calls.jsonl')
    report = dict(status='complete' if len(completed_rows)==len(panel) else 'budget_exhausted',
                  planned_rows=len(panel),completed_paired_rows=completed_rows,
                  completed_paired_row_count=len(completed_rows),calls=len(calls),
                  arms_on_same_completed_rows={k:summarize(v) for k,v in outcomes.items()},
                  all_call_cost={arm:dict(calls=sum(r['arm']==arm for r in calls),
                      prompt_tokens=sum(r['prompt_tokens'] for r in calls if r['arm']==arm),
                      output_tokens=sum(r['output_tokens'] for r in calls if r['arm']==arm),
                      seconds=sum(r['seconds'] for r in calls if r['arm']==arm)) for arm in ARMS},
                  load_seconds=loaded,elapsed_seconds=elapsed,protocol_sha256=sha(a.protocol),
                  note='Report partial/unpaired calls separately; no significance or superiority claim. Cached compiler costs excluded from reviewer-only totals.')
    (a.out/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (a.out/'completion.json').write_text(json.dumps(dict(status=report['status'],results_sha256=sha(a.out/'results.json'))),encoding='utf-8')
    (a.out/'state.json').write_text(json.dumps(dict(status=report['status'],pid=os.getpid(),calls=len(calls))),encoding='utf-8')
    print(json.dumps(dict(status=report['status'],paired_rows=len(completed_rows),calls=len(calls),elapsed_seconds=elapsed)),flush=True)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','history','cases','model','protocol','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--max-tokens',type=int,default=512)
    p.add_argument('--seconds',type=int,default=1800)
    p.add_argument('--threads',type=int,default=8)
    main(p.parse_args())
