"""CPU-only exploratory intervention on preserved v5 public-input predictions."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

from common import align, evaluate_plan, intervene, paired, read_rows, sha, summarize


def main():
    p = argparse.ArgumentParser()
    for key in ('source', 'data', 'monolithic', 'compiler', 'out'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--splits', nargs='+', default=['dev'])
    a = p.parse_args()
    os.environ.update(CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    sys.path.insert(0, str(a.source))
    import torch
    torch.set_num_threads(1)
    from run_e1 import strict_parse
    from sub_e2_monolithic import parse_plan
    a.out.mkdir(parents=True, exist_ok=False)
    protocol = json.loads((a.monolithic/'public_protocol.json').read_text())
    compiler_metrics = json.loads((a.compiler/'metrics.json').read_text())
    hashes = {}
    for name, value in protocol['source_sha256'].items():
        if sha(a.source/name) != value:
            raise ValueError('Frozen E2 source mismatch: '+name)
        hashes['source/'+name] = value
    for split in a.splits:
        hashes['data/'+split] = sha(a.data/(split+'.jsonl'))
        if hashes['data/'+split] != protocol['data_sha256'][split] or hashes['data/'+split] != compiler_metrics['data_sha256'][split]:
            raise ValueError('Data versions differ')
        for label, path in [('mono', a.monolithic/'raw_predictions'), ('compiler', a.compiler/'trained_predictions')]:
            hashes[label+'/'+split] = sha(path/(split+'.jsonl'))
    hashes.update({p.name: sha(p) for p in Path(__file__).parent.glob('*.py')})
    (a.out/'protocol.json').write_text(json.dumps(dict(hashes=hashes, args={k:str(v) for k,v in vars(a).items()},
        selection='One edit, first predicted-feasible neighbor; no gold/witness in selection. Invalid compiler: no intervention.',
        controls='Unedited, hash-selected same-trigger placebo, full symbolic diagnostic.',
        limitations='Historical exploratory panel; placebo is a negative control, not a competitive planner; no novel repair claim.'), indent=2))
    summary = {}
    start = time.monotonic()
    for split in a.splits:
        rows = read_rows(a.data/(split+'.jsonl'))
        monos = align(rows, read_rows(a.monolithic/'raw_predictions'/(split+'.jsonl')))
        compilers = align(rows, read_rows(a.compiler/'trained_predictions'/(split+'.jsonl')))
        saved = align(rows, read_rows(a.monolithic/'predictions'/(split+'.jsonl')))
        outcomes = {arm: [] for arm in ('original', 'repaired', 'placebo', 'symbolic')}
        counts = dict(triggered=0, compile_invalid=0, compile_unusable=0, candidates=0, semantic_checks=0, edited=0)
        with (a.out/(split+'.jsonl')).open('x') as f:
            for row, mono, comp, old in zip(rows, monos, compilers, saved):
                original = parse_plan(mono['raw'], {'task': row['task']})
                t = time.monotonic()
                decision = intervene(row['task'], original, strict_parse(comp['raw']), row['sample_id'])
                decision['decision_seconds_including_symbolic'] = time.monotonic()-t
                scores = {arm: evaluate_plan(row, decision[arm]) for arm in outcomes}
                for key in ('planned', 'completed', 'safe_success', 'faithful_success', 'extra_changes'):
                    if scores['original'][key] != old[key]:
                        raise ValueError('Frozen original scoring mismatch: '+row['sample_id'])
                for arm in outcomes:
                    outcomes[arm].append(scores[arm])
                counts['triggered'] += decision['triggered']
                counts['compile_invalid'] += not decision['compile_valid']
                counts['compile_unusable'] += decision['compile_valid'] and not decision['usable']
                counts['candidates'] += decision['candidate_count']
                counts['semantic_checks'] += decision['semantic_checks']
                counts['edited'] += decision['repaired'] != original
                print(json.dumps(dict(sample_id=row['sample_id'], decision=decision, scores=scores)), file=f)
        summary[split] = dict(arms={arm:summarize(v) for arm,v in outcomes.items()}, counts=counts,
            repaired_minus_original=paired(outcomes['repaired'], outcomes['original']),
            repaired_minus_placebo=paired(outcomes['repaired'], outcomes['placebo']))
        print(json.dumps({split:summary[split]}), flush=True)
    (a.out/'results.json').write_text(json.dumps(dict(splits=summary, elapsed_s=time.monotonic()-start), indent=2))


if __name__ == '__main__':
    main()
