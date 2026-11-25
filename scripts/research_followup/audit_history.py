"""Audit downloaded v5 records; no model calls, training, or new plan generation.

Agreement policies are retrospective probes on exposed data, not calibrated methods.
Gold is used only for analysis labels; gates receive predictions alone.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import align, paired, read_rows, sha, summarize
from run_e1 import constraint_key, strict_parse
from trust_env import normalize_constraint

SEEDS = (42, 43, 44)
SPLITS = ('dev', 'test_tpl_ho', 'test_tool_ho', 'test_struct_ho')


def predicate_signature(parsed, task):
    """Sufficient signature for the frozen consumer, NOT complete NL equivalence.

    None is unusable, () is a valid empty conjunction. Different thresholds can
    still behave identically on a finite world; signature mismatch is not proof
    of different feasible sets. Metadata unused by trust_env is excluded.
    """
    if parsed is None:
        return None
    predicates = set()
    for item in parsed['constraints']:
        norm = normalize_constraint(item, task)
        if norm is None:
            return None
        kind = norm['type']
        if kind == 'budget':
            value = (kind, norm['limit'])
        elif kind == 'deadline':
            value = (kind, norm['minutes'])
        elif kind == 'privacy':
            value = (kind, tuple(sorted(norm['classes'])))
        else:
            # Both branches call exactly the same precedence predicate.
            value = ('precedence', norm['first'], norm['second'])
        predicates.add(value)
    return tuple(sorted(predicates))


def strict_signature(parsed):
    if parsed is None:
        return None
    return (parsed['query_state'], tuple(sorted(constraint_key(c) for c in parsed['constraints'])))


def support_for_first(signatures):
    """Count valid signatures matching seed42; invalids never vote together."""
    if signatures[0] is None:
        return 0
    return sum(sig is not None and sig == signatures[0] for sig in signatures)


def changes(rows, before='original', after='repaired'):
    def count(key, arm):
        return sum(bool(r['scores'][arm][key]) for r in rows)
    n = len(rows)
    wins = sum(not r['scores'][before]['faithful_success'] and r['scores'][after]['faithful_success'] for r in rows)
    losses = sum(r['scores'][before]['faithful_success'] and not r['scores'][after]['faithful_success'] for r in rows)
    return dict(n=n, original_faithful=count('faithful_success', before),
                repaired_faithful=count('faithful_success', after), wins=wins, losses=losses,
                delta_pp=100*(wins-losses)/n if n else None,
                original_safe=count('safe_success', before), repaired_safe=count('safe_success', after),
                edited=sum(r['decision'][before] != r['decision'][after] for r in rows),
                illegal_to_legal=sum(not r['scores'][before]['planned'] and r['scores'][after]['planned'] for r in rows))


def require_hash(path, expected, provenance):
    actual = sha(path)
    if actual != expected:
        raise ValueError(f'Hash mismatch: {path}: {actual} != {expected}')
    provenance[str(path.relative_to(ROOT))] = actual


def run(out):
    out.mkdir(parents=True, exist_ok=False)
    provenance = {}
    summaries, cases = {}, []
    all_details = []
    for split in SPLITS:
        replay_dir = ROOT / 'outputs/local_planning_20261126' / ('cpu-dev-v2' if split == 'dev' else 'cpu-heldout')
        protocol_path = replay_dir / 'protocol.json'
        protocol = json.loads(protocol_path.read_text())
        hashes = protocol['hashes']
        provenance[str(protocol_path.relative_to(ROOT))] = sha(protocol_path)
        for name in ('run_e1.py', 'trust_env.py', 'dataset_v5_spec.py'):
            require_hash(ROOT / 'src' / name, hashes['source/'+name], provenance)
        require_hash(Path(__file__).with_name('common.py'), hashes['common.py'], provenance)
        data_path = ROOT / 'data/processed_v5' / f'{split}.jsonl'
        require_hash(data_path, hashes['data/'+split], provenance)
        data = read_rows(data_path)
        replay_path = replay_dir / f'{split}.jsonl'
        provenance[str(replay_path.relative_to(ROOT))] = sha(replay_path)
        replay = align(data, read_rows(replay_path))
        groups = defaultdict(list)
        for row in data:
            groups[row['group_id']].append(row['variant'])
        if any(sorted(v) != ['explicit', 'implicit', 'none'] for v in groups.values()):
            raise ValueError('Unbalanced E/I/N groups')
        preds = []
        metrics = []
        for seed in SEEDS:
            base = ROOT / f'outputs/e1/Qwen3-1.7B-v5-seed{seed}'
            metric = json.loads((base/'metrics.json').read_text())
            require_hash(data_path, metric['data_sha256'][split], provenance)
            provenance[str((base/'metrics.json').relative_to(ROOT))] = sha(base/'metrics.json')
            path = base / 'trained_predictions' / f'{split}.jsonl'
            if seed == 42:
                require_hash(path, hashes['compiler/'+split], provenance)
            else:
                provenance[str(path.relative_to(ROOT))] = sha(path)
            preds.append(align(data, read_rows(path)))
            metrics.append(metric)
        if len({m['code_sha256'] for m in metrics}) != 1:
            raise ValueError('Compiler seeds have different training code hashes')
        # Frozen scorer is independently hash-checked above; training code may differ.
        saved = json.loads((replay_dir/'results.json').read_text())['splits'][split]['arms']
        arms = {arm: summarize([r['scores'][arm] for r in replay]) for arm in saved}
        if arms != saved:
            raise ValueError(f'Existing replay aggregates not reproduced: {split}')

        strata = defaultdict(list)
        agreement = defaultdict(list)
        gates = {f'{kind}_{threshold}': [] for kind in ('predicate', 'strict') for threshold in (2, 3)}
        details = []
        for i, (row, rec) in enumerate(zip(data, replay)):
            parsed = [strict_parse(p[i]['raw']) for p in preds]
            sigs = [predicate_signature(p, row['task']) for p in parsed]
            stricts = [strict_signature(p) for p in parsed]
            psupport, ssupport = support_for_first(sigs), support_for_first(stricts)
            gold_sig = predicate_signature(row['gold'], row['task'])
            gold_strict = strict_signature(row['gold'])
            if gold_sig is None:
                raise ValueError('Unusable gold')
            match = sigs[0] is not None and sigs[0] == gold_sig
            strict_match = stricts[0] is not None and stricts[0] == gold_strict
            legal = rec['scores']['original']['planned']
            cohort = 'N' if row['variant'] == 'none' else 'EI'
            if rec['decision']['compile_valid'] != (parsed[0] is not None) or rec['decision']['usable'] != (sigs[0] is not None):
                raise ValueError('Raw parse/consumer mismatch with frozen replay')
            strata[f'{cohort}/legal={int(legal)}/predicate_match={int(match)}'].append(rec)
            detail = dict(sample_id=row['sample_id'], group_id=row['group_id'], split=split,
                          variant=row['variant'], original_legal=legal,
                          predicate_match=match, strict_match=strict_match,
                          predicate_support=psupport, strict_support=ssupport,
                          valid_by_seed=[p is not None for p in parsed],
                          usable_by_seed=[s is not None for s in sigs],
                          predicate_match_by_seed=[s is not None and s == gold_sig for s in sigs],
                          strict_match_by_seed=[s is not None and s == gold_strict for s in stricts],
                          edited=rec['decision']['original'] != rec['decision']['repaired'],
                          original_faithful=rec['scores']['original']['faithful_success'],
                          repaired_faithful=rec['scores']['repaired']['faithful_success'])
            details.append(detail)
            agreement[f'{cohort}/support={psupport}'].append(detail)
            for name, target in gates.items():
                kind, threshold = name.split('_')
                accept = (psupport if kind == 'predicate' else ssupport) >= int(threshold)
                target.append(rec['scores']['repaired' if accept else 'original'])
            if cohort == 'N' and detail['original_faithful'] and not detail['repaired_faithful']:
                cases.append(dict(**detail, query=row['query'],
                                  raw_by_seed={str(s): p[i]['raw'] for s,p in zip(SEEDS,preds)},
                                  signatures=sigs, gold=row['gold'], decision=rec['decision'], scores=rec['scores']))

        policy_results = {}
        original_scores = [r['scores']['original'] for r in replay]
        repair_scores = [r['scores']['repaired'] for r in replay]
        for name, scores in gates.items():
            def n_if(predicate):
                return sum(predicate(row, old, repair, gated) for row,old,repair,gated in zip(data,original_scores,repair_scores,scores))
            policy_results[name] = dict(
                aggregate=summarize(scores),
                edited_after_gate=sum(s is r['scores']['repaired'] and d['edited'] for s,r,d in zip(scores,replay,details)),
                retained_EI_wins=n_if(lambda row,o,r,g: row['variant']!='none' and not o['faithful_success'] and r['faithful_success'] and g['faithful_success']),
                lost_EI_wins=n_if(lambda row,o,r,g: row['variant']!='none' and not o['faithful_success'] and r['faithful_success'] and not g['faithful_success']),
                prevented_N_new_harms=n_if(lambda row,o,r,g: row['variant']=='none' and o['faithful_success'] and not r['faithful_success'] and g['faithful_success']),
                remaining_N_new_harms=n_if(lambda row,o,r,g: row['variant']=='none' and o['faithful_success'] and not r['faithful_success'] and not g['faithful_success']),
                vs_repair=paired(scores, repair_scores, repetitions=10000))
        nsets = {
            'old_valid_misedit': {r['sample_id'] for r in replay if r['scores']['original']['variant']=='none' and r['scores']['original']['planned'] and r['scores']['original']['deviates_from_default']},
            'new_harm': {r['sample_id'] for r in replay if r['scores']['original']['variant']=='none' and r['scores']['original']['faithful_success'] and not r['scores']['repaired']['faithful_success']},
            'symbolic_failure': {r['sample_id'] for r in replay if r['scores']['symbolic']['variant']=='none' and not r['scores']['symbolic']['faithful_success']}}
        agreements = {k: dict(n=len(v), predicate_matches=sum(d['predicate_match'] for d in v),
                              strict_matches=sum(d['strict_match'] for d in v),
                              edited=sum(d['edited'] for d in v),
                              new_harms=sum(d['original_faithful'] and not d['repaired_faithful'] for d in v))
                      for k,v in sorted(agreement.items())}
        summary = dict(n=len(data), groups=len(groups), arms=arms,
                       strata={k:changes(v) for k,v in sorted(strata.items())},
                       agreement=agreements, policies=policy_results,
                       none_sets={k: sorted(v) for k,v in nsets.items()},
                       none_intersections={f'{a}&{b}':len(nsets[a]&nsets[b]) for a in nsets for b in nsets if a<b},
                       none_union=len(set.union(*nsets.values())),
                       seed_diagnostics={str(seed):dict(
                           raw_invalid=sum(not d['valid_by_seed'][j] for d in details),
                           consumer_unusable=sum(not d['usable_by_seed'][j] for d in details),
                           predicate_matches=sum(d['predicate_match_by_seed'][j] for d in details),
                           strict_matches=sum(d['strict_match_by_seed'][j] for d in details)) for j,seed in enumerate(SEEDS)})
        if split == 'test_tpl_ho':
            # Independently reported in the frozen 2026-11-26 replay readout.
            if [len(nsets[k]) for k in ('old_valid_misedit','new_harm','symbolic_failure')] != [83,9,11]:
                raise ValueError('Historical tpl N counts do not reconcile')
        summaries[split] = summary
        all_details.extend(details)
        print(json.dumps(dict(split=split,n=len(data),agreement=agreements,
                              strata=summary['strata'],policies=policy_results), ensure_ascii=False),flush=True)
    result = dict(created_utc=datetime.now(timezone.utc).isoformat(), provenance=provenance,
                  analysis_sha256=sha(__file__), splits=summaries,
                  limitations=[
                      'Exposed v5 historical panel; exploratory, not confirmation or a new calibrated method.',
                      'Gate anchored to seed42; seeds43/44 provide support, not selected replacement predictions.',
                      'Three separately trained compilers imply three inference costs in deployment; saved replay cost excludes these.',
                      'Predicate signature equality is sufficient for this consumer, not NL truth or complete finite-world equivalence.',
                      'Invalid raw predictions preserved; invalids cannot vote as a valid empty constraint set.',
                      'Bootstrap intervals condition on fixed weights and are not seed-variance intervals.',
                      'Fallback retains original plan; retention is not a safety guarantee.'])
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'new_none_harm_cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'per_sample.jsonl').open('w',encoding='utf-8') as f:
        for row in all_details:
            print(json.dumps(row,ensure_ascii=False),file=f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    run(parser.parse_args().out)
