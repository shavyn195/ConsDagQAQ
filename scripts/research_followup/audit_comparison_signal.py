"""Describe verifier information available to scalar and Pareto baselines; no training."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from common import read_rows, sha


def vector_signal(vectors):
    if not vectors or not vectors[0] or any(len(v)!=len(vectors[0]) for v in vectors):
        raise ValueError('Require a nonempty common verifier dimension')
    if any(x not in (0,1) for v in vectors for x in v):
        raise ValueError('This diagnostic assumes binary verifiers')
    edges=[(i,j) for i,a in enumerate(vectors) for j,b in enumerate(vectors)
           if i!=j and all(x>=y for x,y in zip(a,b)) and any(x>y for x,y in zip(a,b))]
    return dict(distinct_vectors=len({tuple(v) for v in vectors}),
                all_pass_varies=len({all(v) for v in vectors})>1,
                pass_rate_varies=len({sum(v) for v in vectors})>1,
                dominance_edges=len(edges),
                variable_but_no_dominance=len({tuple(v) for v in vectors})>1 and not edges,
                all_zero_vectors=all(not any(v) for v in vectors))


def summarize(records,size):
    grouped=defaultdict(list)
    for r in records:
        grouped[(r['sample_id'],r['arm'])].append(r)
    cases=[]
    for (sid,arm),rs in grouped.items():
        if len(rs)!=size: continue
        if len({r['draw'] for r in rs})!=size: raise ValueError('Repeated sampling draw')
        cs=[r['signal']['constraint_passes'] for r in rs]
        record=dict(sample_id=sid,arm=arm,all_valid=all(r['signal']['valid'] for r in rs),
                    constrained=bool(cs[0]),
                    full_components=vector_signal([r['signal']['components'] for r in rs]))
        # Empty N vectors would make all(v) vacuously true; do not invent an N constraint reward.
        record['constraints_only']=vector_signal(cs) if cs[0] else None
        cases.append(record)
    report={}
    for arm in sorted({r['arm'] for r in cases}):
        arm_cases=[r for r in cases if r['arm']==arm]
        valid=[r['constraints_only'] for r in arm_cases if r['all_valid'] and r['constrained']]
        report[arm]=dict(complete_prompt_groups=len(arm_cases),
            all_valid_constrained_groups=len(valid),
            available_groups={key:sum(bool(v[key]) for v in valid) for key in
                              ('all_pass_varies','pass_rate_varies','dominance_edges','variable_but_no_dominance')},
            interpretation='Counts describe information, not training improvement. Zero eligible groups is an interface floor, not evidence against a learning objective.')
    return dict(arms=report,cases=cases)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--calls',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--size',type=int,default=4)
    args=p.parse_args()
    result=summarize(read_rows(args.calls),args.size)
    result['source']=dict(path=str(args.calls),sha256=sha(args.calls),group_size=args.size)
    result['limitations']='Only existing recorded verifier vectors; N minimal-edit faithfulness is not encoded by these old vectors. No POLPO/GRPO reproduction or optimizer update.'
    args.out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result['arms'],indent=2))


if __name__=='__main__': main()
