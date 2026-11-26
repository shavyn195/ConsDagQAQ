"""On-policy G=4 inference diagnostic; never updates weights or generates gold input."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time

from common import public_row, read_rows, sha
from fixed_planner import planner_messages, select_groups


def select_panel(rows, config):
    excluded = {r['group_id'] for r in select_groups(rows, config['exclude_fixed_planner_groups'])}
    grouped = defaultdict(list)
    for row in rows:
        if row['group_id'] not in excluded:
            grouped[row['group_id']].append(row)
    chosen = sorted(grouped, key=lambda g: hashlib.sha256(
        (config['selection_salt'] + g).encode()).digest())[:config['groups']]
    if len(chosen) != config['groups']:
        raise ValueError('Insufficient independent dev groups')
    if any(sorted(r['variant'] for r in grouped[g]) != ['explicit', 'implicit', 'none'] for g in chosen):
        raise ValueError('E/I/N siblings missing or duplicated')
    return [row for g in chosen for row in sorted(grouped[g], key=lambda r: r['sample_id'])]


def outcome_vector(row, candidate):
    """Post-generation diagnostic against labels; empty/invalid plans get no credit."""
    from trust_env import check
    cs = row['gold']['constraints']
    if candidate is None:
        return dict(scalar=0, components=[0, 0] + [0] * len(cs),
                    constraint_passes=[0] * len(cs), valid=False)
    result = check(row['task'], candidate, cs)
    passes = [int(i not in result['violations']) for i in range(len(cs))]
    return dict(scalar=int(result['safe_success']),
                components=[1, int(result['completed'])] + passes,
                constraint_passes=passes, valid=True)


def summarize_groups(records, size, arms=('raw_request', 'predicted_contract')):
    grouped = defaultdict(list)
    for record in records:
        grouped[(record['sample_id'], record['arm'])].append(record)
    output = {}
    for arm in arms:
        complete = [rs for (sid, a), rs in grouped.items() if a == arm and len(rs) == size]
        if any(len({r['draw'] for r in rs}) != size for rs in complete):
            raise ValueError('Duplicate draw in a rollout group')
        def constant(rs):
            return len({r['signal']['scalar'] for r in rs}) == 1
        output[arm] = dict(
            complete_prompt_groups=len(complete),
            partial_prompt_groups=sum(a == arm and len(rs) != size for (_, a), rs in grouped.items()),
            all_zero_groups=sum(all(r['signal']['scalar'] == 0 for r in rs) for rs in complete),
            constant_scalar_groups=sum(constant(rs) for rs in complete),
            constant_scalar_variable_components=sum(constant(rs) and len({tuple(r['signal']['components']) for r in rs}) > 1 for rs in complete),
            # Exclude invalid plans: format failures are not evidence of constraint-credit interference.
            constant_scalar_variable_constraints_all_valid=sum(
                constant(rs) and all(r['signal']['valid'] for r in rs)
                and len({tuple(r['signal']['constraint_passes']) for r in rs}) > 1 for rs in complete),
            invalid_calls=sum(not r['signal']['valid'] for rs in complete for r in rs),
            safe_calls=sum(r['signal']['scalar'] for rs in complete for r in rs))
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--prepare-only', action='store_true')
    a = p.parse_args()
    sys.path.insert(0, str(a.root/'src'))
    sys.path.insert(1, '/root/ConsDagSubmissionReview/src')
    from run_e1 import load_model, render_chat
    from run_e1_v6 import validate_v6_freeze
    from sub_e2_monolithic import parse_plan
    from transformers import AutoTokenizer
    cfg = json.loads(a.config.read_text())
    data = a.root/'data/processed_v6'
    validate_v6_freeze(data)
    rows = select_panel(read_rows(data/'dev.jsonl'), cfg)
    cache = a.root/'outputs/e1_v6/Qwen3-4B-v6-seed42/trained_predictions/dev.jsonl'
    predictions = read_rows(cache)
    compiled = {r['sample_id']: r['raw'] for r in predictions}
    if len(compiled) != len(predictions) or any(r['sample_id'] not in compiled for r in rows):
        raise ValueError('Compiler cache missing or duplicates')
    model_path = a.root/'models'/cfg['model']
    tok = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    prompt_lengths = []
    for row in rows:
        for arm in cfg['arms']:
            aux = compiled[row['sample_id']] if arm == 'predicted_contract' else None
            length = render_chat(tok, planner_messages(public_row(row), aux), add_generation_prompt=True)['input_ids'].numel()
            if length + cfg['max_new_tokens'] > tok.model_max_length:
                raise ValueError('Context overflow')
            prompt_lengths.append(length)
    import run_e1, trust_env, sub_e2_public_contract, sub_e2_monolithic
    sources = {str(Path(m.__file__)): sha(Path(m.__file__)) for m in
               (run_e1, trust_env, sub_e2_public_contract, sub_e2_monolithic)}
    sources.update({str(f): sha(f) for f in Path(__file__).parent.glob('*.py')})
    manifest = dict(config=cfg, config_sha256=sha(a.config), data_sha256=sha(data/'dev.jsonl'),
                    compiler_cache_sha256=sha(cache), source_sha256=sources,
                    model_sha256={str(f.relative_to(model_path)):sha(f) for f in model_path.rglob('*') if f.is_file()},
                    sample_ids=[r['sample_id'] for r in rows], max_prompt_tokens=max(prompt_lengths))
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out/'protocol.json'
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise ValueError('Prepared inputs changed')
    if not path.exists():
        path.write_text(json.dumps(manifest, indent=2))
    if a.prepare_only:
        print(json.dumps(dict(preflight='PASS', rows=len(rows), max_calls=len(rows)*2*cfg['samples_per_prompt'],
                              max_prompt_tokens=max(prompt_lengths), protocol_sha256=sha(path))), flush=True)
        return
    if (a.out/'calls.jsonl').exists():
        raise ValueError('Existing calls preserved; no implicit restart')
    import torch
    torch.set_num_threads(1)
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise ValueError('bf16 GPU required')
    started = time.monotonic()
    model, tok = load_model(str(model_path), cfg['precision'])
    model.config.use_cache = True
    load_seconds = time.monotonic() - started
    records = []
    status = 'complete'
    with (a.out/'calls.jsonl').open('x') as stream:
        for index, row in enumerate(rows):
            if status != 'complete':
                break
            arms = cfg['arms'][index % 2:] + cfg['arms'][:index % 2]
            for arm in arms:
                if status != 'complete':
                    break
                aux = compiled[row['sample_id']] if arm == 'predicted_contract' else None
                messages = planner_messages(public_row(row), aux)
                inputs = {k: v.to(model.device) for k, v in render_chat(tok, messages, add_generation_prompt=True).items()}
                for draw in range(cfg['samples_per_prompt']):
                    if time.monotonic() - started >= cfg['active_seconds_cap'] - 30:
                        status = 'budget_exhausted'
                        break
                    seed = cfg['seed'] + index * cfg['samples_per_prompt'] + draw
                    torch.manual_seed(seed)
                    torch.cuda.manual_seed_all(seed)
                    torch.cuda.synchronize()
                    t = time.monotonic()
                    with torch.inference_mode():
                        out = model.generate(**inputs, do_sample=True, temperature=cfg['temperature'],
                                             top_p=cfg['top_p'], max_new_tokens=cfg['max_new_tokens'],
                                             pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id)
                    torch.cuda.synchronize()
                    seconds = time.monotonic() - t
                    new = out[0, inputs['input_ids'].shape[1]:]
                    raw = tok.decode(new, skip_special_tokens=True)
                    candidate = parse_plan(raw, public_row(row))
                    # Labels are used only after the sampled decision is fixed.
                    signal = outcome_vector(row, candidate)
                    record = dict(sample_id=row['sample_id'], group_id=row['group_id'], variant=row['variant'],
                                  arm=arm, draw=draw, seed=seed, messages=messages, raw=raw, plan=candidate,
                                  signal=signal, seconds=seconds, prompt_tokens=inputs['input_ids'].numel(),
                                  output_tokens=new.numel(), cap_hit=new.numel()==cfg['max_new_tokens'])
                    records.append(record)
                    print(json.dumps(record, ensure_ascii=False), file=stream, flush=True)
                    print(json.dumps(dict(calls=len(records), maximum_calls=cfg['maximum_model_calls'],
                                          elapsed_seconds=time.monotonic()-started)), flush=True)
    report = dict(status=status, calls=len(records), groups=summarize_groups(records,cfg['samples_per_prompt']),
                  load_seconds=load_seconds, elapsed_seconds=time.monotonic()-started,
                  planner_seconds=sum(r['seconds'] for r in records),
                  prompt_tokens=sum(r['prompt_tokens'] for r in records),
                  output_tokens=sum(r['output_tokens'] for r in records),
                  token_cap_hits=sum(r['cap_hit'] for r in records),
                  scope='Frozen-policy sampled diagnostic. No weight update or GRPO effectiveness claim. Cached compiler cost excluded.')
    (a.out/'results.json').write_text(json.dumps(report, indent=2))
    (a.out/'completion.json').write_text(json.dumps(dict(status=status, results_sha256=sha(a.out/'results.json'))))


if __name__ == '__main__':
    main()
