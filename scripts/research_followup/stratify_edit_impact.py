"""Describe frozen replay by active constraint family; never fit a new policy."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path

from common import align, read_rows, sha, summarize

SPLITS = ('dev', 'test_tpl_ho', 'test_tool_ho', 'test_struct_ho')
ARMS = ('unedited', 'repaired', 'predicate_all', 'impact_with_cost_valid2', 'symbolic')


def selected(row, arm):
    if arm == 'symbolic':
        return row['scores']['symbolic']
    return row['scores']['repaired' if row['accept'][arm] else 'original']


def describe(pairs):
    result = {'n': len(pairs), 'arms': {}}
    for arm in ARMS:
        values = [selected(p, arm) for _, p in pairs]
        original = [p['scores']['original'] for _, p in pairs]
        repaired = [p['scores']['repaired'] for _, p in pairs]
        def success(score):
            return bool(score['faithful_success'])
        result['arms'][arm] = dict(
            faithful=sum(map(success, values)),
            safe=sum(bool(v['safe_success']) for v in values),
            legal=sum(bool(v['planned']) for v in values),
            wins_vs_original=sum(not success(o) and success(v) for o, v in zip(original, values)),
            losses_vs_original=sum(success(o) and not success(v) for o, v in zip(original, values)),
            wins_vs_repaired=sum(not success(r) and success(v) for r, v in zip(repaired, values)),
            losses_vs_repaired=sum(success(r) and not success(v) for r, v in zip(repaired, values)),
            lost_beneficial_repairs=sum(not success(o) and success(r) and not success(v)
                                        for o, r, v in zip(original, repaired, values)))
    return result


def main(args):
    args.out.mkdir(parents=True, exist_ok=False)
    probe = read_rows(args.probe / 'per_sample.jsonl')
    summary = json.loads((args.probe / 'summary.json').read_text(encoding='utf-8'))
    history = read_rows(args.history / 'per_sample.jsonl')
    hashes = {str(p): sha(p) for p in (args.probe / 'per_sample.jsonl', args.probe / 'summary.json',
                                       args.history / 'per_sample.jsonl', Path(__file__))}
    results, cases = {}, []
    for split in SPLITS:
        path = args.data / (split + '.jsonl')
        hashes[str(path)] = sha(path)
        # The server manifest can contain absolute POSIX paths. Match one unique suffix.
        source_hashes = [v for k, v in summary['input_sha256'].items()
                         if k.replace('\\', '/').endswith('/processed_v5/' + split + '.jsonl')]
        if source_hashes != [hashes[str(path)]]:
            raise ValueError('Data differs from the frozen replay: ' + split)
        data = read_rows(path)
        rows = align(data, [p for p in probe if p['split'] == split])
        hist = align(data, [p for p in history if p['split'] == split])
        families = {}
        grouped = defaultdict(list)
        for d in data:
            grouped[d['group_id']].append(d)
        for group, members in grouped.items():
            if sorted(d['variant'] for d in members) != ['explicit', 'implicit', 'none']:
                raise ValueError('Incomplete E/I/N group: ' + group)
            active = [tuple(sorted({c['type'] for c in d['gold']['constraints']}))
                      for d in members if d['variant'] != 'none']
            if not active[0] or active[0] != active[1]:
                raise ValueError('Different active families within E/I group: ' + group)
            families[group] = '+'.join(active[0])
        buckets = defaultdict(list)
        for d, p, h in zip(data, rows, hist):
            # N inherits a paired label for descriptive grouping only; it has no active constraint.
            if d['variant'] == 'none' and d['gold']['constraints']:
                raise ValueError('N has active gold constraints')
            family = families[d['group_id']]
            cohort = 'N_paired_family' if d['variant'] == 'none' else 'EI_active_family'
            buckets[(cohort, family)].append((d, p))
            if cohort == 'EI_active_family':
                buckets[(d['variant'], family)].append((d, p))
                for core in ('privacy', 'tool_auth'):
                    if core in family.split('+'):
                        buckets[('EI_contains_family_nonadditive', core)].append((d, p))
                current = selected(p, 'impact_with_cost_valid2')
                if {'privacy', 'tool_auth'}.intersection(family.split('+')) and current['faithful_success'] != p['scores']['repaired']['faithful_success']:
                    cases.append(dict(sample_id=d['sample_id'], split=split, family=family,
                                      query=d['query'], gold=d['gold'], history=h, replay=p))
        reports = {cohort: {} for cohort in ('EI_active_family', 'N_paired_family', 'explicit', 'implicit',
                                           'EI_contains_family_nonadditive')}
        for (cohort, family), pairs in sorted(buckets.items()):
            reports[cohort][family] = describe(pairs)
        # Reconcile all disjoint family counts against the previously frozen full aggregates.
        for arm in ARMS[:-1]:
            aggregate = summarize([selected(p, arm) for p in rows])
            if aggregate != summary['splits'][split][arm]['aggregate']:
                raise ValueError('Prior aggregate mismatch: ' + split + '/' + arm)
            for cohort, n_key, rate_key in [('EI_active_family', 'constrained_n', 'faithful'),
                                           ('N_paired_family', 'none_n', 'none_faithful')]:
                n = sum(v['n'] for v in reports[cohort].values())
                count = sum(v['arms'][arm]['faithful'] for v in reports[cohort].values())
                if n != aggregate[n_key] or count != round(aggregate[rate_key] * n):
                    raise ValueError('Family reconciliation failed')
        results[split] = reports
    (args.out / 'summary.json').write_text(json.dumps(dict(
        scope='Descriptive stratification of exposed historical data; no policy changes, new inference, or causal claim.',
        note='N paired family is the E sibling label, not an active N constraint. All families retained.',
        input_sha256=hashes, splits=results), ensure_ascii=False, indent=2), encoding='utf-8')
    (args.out / 'privacy_authorization_changed_cases.jsonl').write_text(
        ''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in cases), encoding='utf-8')
    for split, reports in results.items():
        print(split, json.dumps({k: dict(n=v['n'], faithful={a:s['faithful'] for a,s in v['arms'].items()},
                                        gate_wins=v['arms']['impact_with_cost_valid2']['wins_vs_repaired'],
                                        gate_losses=v['arms']['impact_with_cost_valid2']['losses_vs_repaired'])
                                for k,v in reports['EI_contains_family_nonadditive'].items()}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('data', 'probe', 'history', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    main(parser.parse_args())
