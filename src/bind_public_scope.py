"""Post-hoc, all-arm comparison of emitted vs. publicly specified catalog scope."""
from collections import Counter
from pathlib import Path
import json

from rescore_v4_side import ROOT, SUBSETS, aligned, digest, load_jsonl, outcome
from run_e1 import score, strict_parse


def bind(raw, catalog):
    obj = strict_parse(raw)
    if obj is None:
        return raw
    allowed = {x['role'] for x in catalog}
    for c in obj['constraints']:
        kind = c.get('type')
        p = c.get('params')
        if kind == 'budget':
            roles = [x['role'] for x in catalog if x['paid']]
        elif kind == 'privacy':
            roles = [x['role'] for x in catalog if x['recipient'] == 'external']
        elif kind == 'deadline':
            roles = ['*']
        elif kind in ('tool_auth','order') and isinstance(p,dict):
            keys = ('required_role',) if kind=='tool_auth' else ('before_role','after_role')
            roles = [p.get(k) for k in keys]
            if not all(isinstance(r,str) and r in allowed for r in roles):
                continue
        else:
            continue
        c['scope'] = sorted('role:'+r for r in roles)
    return json.dumps(obj,ensure_ascii=False)


def main():
    out = ROOT/'outputs/e1_v4_side/public-scope-v1'
    out.mkdir(exist_ok=False)
    paths = {k: ROOT/'outputs/e1'/('Qwen3-'+k+'-v4')/'trained_predictions' for k in ['0.6B','1.7B','4B']}
    paths.update({k:out.parent/k for k in ['qwen-max-zero','qwen-max-few','deepseek-v4-pro-0813-few']})
    report = {'source': digest(Path(__file__)), 'subsets':{}}
    for subset in SUBSETS:
        src = ROOT/'data/processed_v4'/(subset+'.jsonl')
        rows = load_jsonl(src)
        subset_report = report['subsets'][subset] = {'data_sha256':digest(src),'arms':{}}
        for arm,folder in paths.items():
            source = folder/src.name
            raw = aligned(rows,load_jsonl(source))
            after = [bind(t,r['catalog']) for r,t in zip(rows,raw,strict=True)]
            counts = Counter(n=0,before=0,after=0,improved=0,regressed=0,execution_flips=0)
            for r,o,n in zip(rows,raw,after,strict=True):
                a,b = outcome(r,o),outcome(r,n)
                counts['execution_flips'] += a['faithful_success'] != b['faithful_success']
                if r['gold']['constraints']:
                    x,y = a['exact_with_evidence'],b['exact_with_evidence']
                    counts.update(n=1,before=int(x),after=int(y),improved=int(y and not x),regressed=int(x and not y))
            if counts['execution_flips']:
                raise ValueError('Scope-only intervention changed execution')
            scores = [score(rows,[None]*len(rows),v)['constraint_micro']['f1'] for v in (raw,after)]
            subset_report['arms'][arm] = dict(record_counts=counts,strict_f1_before=scores[0],
                                               strict_f1_after=scores[1],prediction_sha256=digest(source))
            print(subset,arm,counts['before'],counts['after'],flush=True)
    (out/'scores.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
