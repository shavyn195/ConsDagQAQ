"""Reparse saved warm-up generations. Also apply a stricter structural diagnostic."""
import json
from collections import Counter, defaultdict
from pathlib import Path

from rescore_v4_side import ROOT, digest, load_jsonl
from trust_env import check


def shape(actions,task):
    if not actions or len(set(actions)) != len(actions):
        return False
    matches = [[i for i,a in enumerate(actions) if a in s['alternatives']] for s in task['stages']]
    if not all(len(m)==1 for m in matches):
        return False
    indices = [m[0] for m in matches]
    if indices != sorted(indices) or set(actions[-2:]) != set(task['finish']):
        return False
    used = {actions[i] for i in indices} | set(task['finish']) | set(task['optional'])
    return all(a in used for a in actions)


def main():
    d=ROOT/'outputs/e2_v4/planner-warmup-1.7B-v1'
    cfg=json.loads((d/'config.json').read_text())
    records={r['sample_id']:r for r in load_jsonl(ROOT/'data/processed_v4/train.jsonl')}
    assert {records[k]['group_id'] for k in cfg['probes']}.isdisjoint(records[k]['group_id'] for k in cfg['demos'])
    prev=json.loads((d/'scores.json').read_text())
    audit={}
    for arm in ['base','warm']:
        samples=load_jsonl(d/(arm+'.jsonl'))
        assert Counter(x['id'] for x in samples)==Counter({r:4 for r in cfg['probes']})
        co=Counter(n=0,valid=0,completed=0,safe=0,mixed=0)
        tight=Counter(completed=0,safe=0,mixed=0)
        by=defaultdict(Counter)
        mixed=defaultdict(set)
        strict=defaultdict(set)
        for x in samples:
            r=records[x['id']]
            try: acts=json.loads(x['raw'])
            except ValueError: acts=None
            if not isinstance(acts,list) or not acts or not all(isinstance(a,str) and a in r['task']['tools'] for a in acts):
                acts=None
            result=check(r['task'],acts,r['gold']['constraints'])
            assert result==x['result'] and acts==x['actions']
            done,safe=result['completed'],result['safe_success']
            co.update(n=1,valid=int(acts is not None),completed=int(done),safe=int(safe))
            if done: mixed[x['id']].add(safe)
            valid=done and shape(acts,r['task'])
            tight.update(completed=int(valid),safe=int(valid and safe))
            if valid: strict[x['id']].add(safe)
            by[r['gold']['constraints'][0]['type']].update(n=1,strict_completed=int(valid),strict_safe=int(valid and safe))
        co['mixed']=sum(len(s)==2 for s in mixed.values())
        tight['mixed']=sum(len(s)==2 for s in strict.values())
        assert co==prev[arm]
        audit[arm]=dict(original=co,strict=tight,by_type=by,raw_sha256=digest(d/(arm+'.jsonl')))
    (d/'audit.json').write_text(json.dumps(audit,indent=2))


if __name__=='__main__':
    main()
