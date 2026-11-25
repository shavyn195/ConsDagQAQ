"""Compare frozen edit consequences across three compiler views on the server."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time

from audit_history import SEEDS, SPLITS, predicate_signature, support_for_first
from common import align, paired, read_rows, sha, summarize
from run_e1 import strict_parse
from trust_env import check, plan_change_count


def rank_plan(task, candidate, constraints):
    if candidate is None:
        return (1, 1, 0, 0)
    try:
        edits = plan_change_count(task, candidate)
    except (ValueError, TypeError):
        return (1, 1, 0, 0)
    result = check(task, candidate, constraints)
    return (0, int(not result['completed']), len(result['violations']), edits)


def impact_accept(before, after, *, include_cost):
    if before is None or after is None:
        return False
    width = 4 if include_cost else 3
    old, new = [v[:width] for v in before], [v[:width] for v in after]
    return all(n <= o for n,o in zip(new,old)) and any(n < o for n,o in zip(new,old))


def available_view_decisions(signatures, before, after):
    """Invalid views abstain; at least two valid views must support a decision."""
    ids = [i for i,s in enumerate(signatures) if s is not None]
    if len(ids) < 2:
        return dict(predicate_valid2=False,candidate_safe_valid2=False,impact_with_cost_valid2=False)
    old,new = [before[i] for i in ids], [after[i] for i in ids]
    return dict(predicate_valid2=all(signatures[i]==signatures[ids[0]] for i in ids),
                candidate_safe_valid2=all(v[:3]==(0,0,0) for v in new),
                impact_with_cost_valid2=impact_accept(old,new,include_cost=True))


def main(a):
    start = time.monotonic()
    a.out.mkdir(parents=True,exist_ok=False)
    prior = json.loads(a.prior.read_text(encoding='utf-8'))
    prior['provenance'] = {k.replace('\\','/'):v for k,v in prior['provenance'].items()}
    provenance = {}
    def verify(path, key):
        actual = sha(path)
        if actual != prior['provenance'][key]:
            raise ValueError('Input changed: '+str(path))
        provenance[str(path)] = actual
    for name in ('run_e1.py','trust_env.py','dataset_v5_spec.py'):
        verify(Path(__file__).resolve().parents[2]/'src'/name,'src/'+name)
    summaries = {}
    with (a.out/'per_sample.jsonl').open('w',encoding='utf-8') as stream:
        for split in SPLITS:
            data_path = a.data / f'{split}.jsonl'
            verify(data_path,f'data/processed_v5/{split}.jsonl')
            data = read_rows(data_path)
            folder = 'cpu-dev-v2' if split=='dev' else 'cpu-heldout'
            replay_path = a.replay / folder / f'{split}.jsonl'
            verify(replay_path,f'outputs/local_planning_20261126/{folder}/{split}.jsonl')
            records = align(data,read_rows(replay_path))
            predictions = []
            for seed in SEEDS:
                name = f'Qwen3-1.7B-v5-seed{seed}/trained_predictions/{split}.jsonl'
                verify(a.compilers/name,'outputs/e1/'+name)
                predictions.append(align(data,read_rows(a.compilers/name)))
            names = ('unedited','repaired','predicate_all','candidate_safe_all','impact_no_cost','impact_with_cost',
                     'predicate_valid2','candidate_safe_valid2','impact_with_cost_valid2')
            scores = {name:[] for name in names}
            accepted_edits = {name:0 for name in names}
            for i,(row,rec) in enumerate(zip(data,records)):
                parsed = [strict_parse(p[i]['raw']) for p in predictions]
                sigs = [predicate_signature(p,row['task']) for p in parsed]
                usable = all(s is not None for s in sigs)
                available_before = [rank_plan(row['task'],rec['decision']['original'],p['constraints']) if sig is not None else None for p,sig in zip(parsed,sigs)]
                available_after = [rank_plan(row['task'],rec['decision']['repaired'],p['constraints']) if sig is not None else None for p,sig in zip(parsed,sigs)]
                before = available_before if usable else None
                after = available_after if usable else None
                decisions = dict(unedited=False,repaired=True,predicate_all=support_for_first(sigs)==3,
                                 candidate_safe_all=usable and all(v[:3]==(0,0,0) for v in after),
                                 impact_no_cost=impact_accept(before,after,include_cost=False),
                                 impact_with_cost=impact_accept(before,after,include_cost=True))
                decisions.update(available_view_decisions(sigs,available_before,available_after))
                edited = rec['decision']['original'] != rec['decision']['repaired']
                for name,accept in decisions.items():
                    scores[name].append(rec['scores']['repaired' if accept else 'original'])
                    accepted_edits[name] += accept and edited
                print(json.dumps(dict(sample_id=row['sample_id'],split=split,group_id=row['group_id'],
                                      usable=usable,before=before,after=after,accept=decisions,
                                      available_before=available_before,available_after=available_after,
                                      edited=edited,scores=rec['scores'])),file=stream)
            results = {}
            for name,values in scores.items():
                def count(fn):
                    return sum(fn(r,o,u,g) for r,o,u,g in zip(data,scores['unedited'],scores['repaired'],values))
                results[name] = dict(aggregate=summarize(values),edited=accepted_edits[name],
                    retained_EI_wins=count(lambda r,o,u,g:r['variant']!='none' and not o['faithful_success'] and u['faithful_success'] and g['faithful_success']),
                    lost_EI_wins=count(lambda r,o,u,g:r['variant']!='none' and not o['faithful_success'] and u['faithful_success'] and not g['faithful_success']),
                    new_N_harms=count(lambda r,o,u,g:r['variant']=='none' and o['faithful_success'] and not g['faithful_success']),
                    vs_repaired=paired(values,scores['repaired']),vs_predicate_all=paired(values,scores['predicate_all']))
            # Reconcile independent prior analysis before reporting any new arm.
            if results['predicate_all']['aggregate'] != prior['splits'][split]['policies']['predicate_3']['aggregate']:
                raise ValueError('Prior agreement gate did not reproduce')
            summaries[split]=results
            print(json.dumps(dict(split=split,arms={k:dict(faithful=v['aggregate']['faithful'],lost=v['lost_EI_wins'],new_N_harms=v['new_N_harms']) for k,v in results.items()})),flush=True)
    (a.out/'summary.json').write_text(json.dumps(dict(splits=summaries,elapsed_s=time.monotonic()-start,
        input_sha256=provenance,analysis_sha256=sha(__file__),prior_sha256=sha(a.prior),
        scope='Exploratory historical replay; no calibration, novelty claim, or new inference; triple compiler cost excluded.'),indent=2),encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('data','compilers','replay','prior','out'):
        p.add_argument('--'+name,type=Path,required=True)
    main(p.parse_args())
