"""Paired constrained execution and API audit for the completed cross-family PE arm."""
from collections import Counter
import json

from eval_exec import bootstrap_ci
from pe_v4_side import fingerprint, restore
from rescore_v4_side import ROOT, SUBSETS, aligned, digest, load_jsonl, outcome
from run_cross_family_pe import DATA, MODEL, OUT, PARAMS, chat_messages_v4, demonstrations, write_json


def main():
    config=json.loads((OUT/'config.json').read_text())
    scores=json.loads((OUT/'full-scores.json').read_text())
    train=DATA/'train.jsonl'
    assert config['data']['train']==digest(train)
    demo=demonstrations(load_jsonl(train))
    assert fingerprint(demo)==config['demo_hash'] and PARAMS==config['params']
    dirs={k+'-trained':ROOT/'outputs/e1'/('Qwen3-'+k+'-v4')/'trained_predictions'
          for k in ['0.6B','1.7B','4B']}
    dirs.update({k:ROOT/'outputs/e1_v4_side'/k for k in ['qwen-max-zero','qwen-max-few']})
    report={}
    for subset in SUBSETS:
        data=DATA/(subset+'.jsonl')
        rows=load_jsonl(data)
        ids={}
        for r in rows:
            system,user=chat_messages_v4(r)
            ids[r['sample_id']]=fingerprint([PARAMS,[system,*demo,user]])
        pred=OUT/data.name
        cached=restore(pred,ids)
        assert set(cached)==set(ids) and len(ids)==len(rows)
        assert digest(pred)==scores[subset]['pred_sha256'] and digest(data)==scores[subset]['data_sha256']==config['data'][subset]
        assert all(p['model']==MODEL for p in cached.values())
        def wins(raw):
            return [outcome(r,t)['faithful_success'] for r,t in zip(rows,raw,strict=True) if r['gold']['constraints']]
        primary=wins([cached[r['sample_id']]['raw'] for r in rows])
        groups=[r['group_id'] for r in rows if r['gold']['constraints']]
        assert abs(sum(primary)/len(primary)-scores[subset]['side_v1']['constrained']['faithful_success'])<1e-9
        comp={}
        for name,folder in dirs.items():
            otherfile=folder/data.name
            reference=wins(aligned(rows,load_jsonl(otherfile)))
            pairs=Counter((a,b) for a,b in zip(primary,reference,strict=True))
            diffs=[dict(group_id=g,difference=int(a)-int(b)) for g,a,b in zip(groups,primary,reference,strict=True)]
            comp[name]=dict(only_deepseek=pairs[True,False],only_other=pairs[False,True],
                            delta=(sum(primary)-sum(reference))/len(primary),ci95=bootstrap_ci(diffs,'difference'),
                            other_prediction_hash=digest(otherfile))
        totals=Counter()
        for p in cached.values():
            totals.update({k:v for k,v in (p['usage'] or {}).items() if type(v) is int})
        report[subset]=dict(n=len(cached),constrained_n=len(primary),primary_hits=sum(primary),
            finish=dict(Counter(p['finish'] for p in cached.values())),empty=sum(not p['raw'].strip() for p in cached.values()),
            with_usage=sum(bool(p['usage']) for p in cached.values()),usage=totals,paired=comp)
    write_json(OUT/'full-paired.json',report)


if __name__=='__main__':
    main()
