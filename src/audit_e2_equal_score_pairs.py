import json
from pathlib import Path
from collections import Counter,defaultdict
from itertools import combinations
from rescore_v4_side import load_jsonl, digest
from trust_env import check
root=Path.cwd()
src=Path('outputs/e2_v4/multiconstraint-gate-opportunity-v1')
samples=load_jsonl(src/'samples.jsonl')
train={r['sample_id']:r for r in load_jsonl(Path('data/processed_v4/train.jsonl'))}
groups=defaultdict(list)
for s in samples:
 r=train[s['id']];gold=r['gold']['constraints']
 v=check(r['task'],s['plan'],gold);assert v==s['result']
 groups[s['id']].append((v['completed'],tuple(v['violations'])))
stats=Counter(); eg=None
for k,group in groups.items():
 assert len(group)==4
 collision=False
 for (ca,a),(cb,b) in combinations(group,2):
  if ca and cb:
   stats['completed_pairs']+=1
   if len(a)==len(b):
    stats['equal_count_pairs']+=1
    if a!=b:
     stats['different_identity_pairs']+=1
     collision=True
     if eg is None:
      kinds=[c['type'] for c in train[k]['gold']['constraints']]
      eg=[k,[kinds[i] for i in a],[kinds[i] for i in b]]
 stats['groups_with_collision']+=int(collision)
assert len(groups)==32 and all(len(g)==4 for g in groups.values())
report=dict(groups=len(groups),samples=len(samples),counts=stats,example=eg,raw_sha256=digest(src/'samples.jsonl'),data_sha256=digest(Path('data/processed_v4/train.jsonl')))
with (src/'equal-score-different-constraints.json').open('x') as f:
 json.dump(report,f,indent=2)
print(json.dumps(report))
