"""Recheck paired transfer results from the unmodified saved model answers."""
from collections import Counter,defaultdict
import json
from audit_warmup_rollouts import shape
from probe_e2_format import parse
from rescore_v4_side import ROOT,digest,load_jsonl
from trust_env import check

def main():
    d=ROOT/'outputs/e2_v4/frozen-planner-swap-panel-v1'
    conf=json.loads((d/'config.json').read_text())
    samples=load_jsonl(d/'samples.jsonl')
    report={'samples_sha256':digest(d/'samples.jsonl'),'splits':{}}
    assert len(samples)==270
    for split,meta in conf['sources'].items():
        src=ROOT/'data/processed_v4'/(split+'.jsonl')
        assert digest(src)==meta['data']
        rows={r['sample_id']:r for r in load_jsonl(src)}
        by=defaultdict(dict)
        for case in samples:
            if case['split']!=split: continue
            k,arm=case['id'],case['arm']
            r=rows[k]
            assert r['variant']==case['variant'] and r['group_id']==case['group']
            acts=parse(case['raw'],sorted(r['task']['tools']),'names')
            obs=check(r['task'],acts,r['gold']['constraints'])
            assert obs==case['result'] and acts==case['actions']
            val=bool(obs['safe_success'] and shape(acts,r['task']))
            assert val==case['flags']['strict_safe'] and arm not in by[k]
            by[k][arm]=case
        assert set(by)==set(meta['ids']) and all(set(v)=={'raw','pred','gold'} for v in by.values())
        out=report['splits'][split]={}
        for name,ids in [('constrained',[k for k in by if rows[k]['gold']['constraints']]),
                         ('none',[k for k in by if not rows[k]['gold']['constraints']])]:
            totals={arm:dict(sum((Counter(by[k][arm]['flags']) for k in ids),Counter())) for arm in conf['arms']}
            changes={}
            for arm in ['pred','gold']:
                diff=[int(by[k][arm]['flags']['strict_safe'])-by[k]['raw']['flags']['strict_safe'] for k in ids]
                changes[arm]=dict(gained=diff.count(1),lost=diff.count(-1))
            same=[k for k in ids if by[k]['pred']['prompt_hash']==by[k]['gold']['prompt_hash']]
            out[name]=dict(n=len(ids),scores=totals,paired_against_raw=changes,
                           identical_pred_gold_prompts=len(same),identical_prompts_different_answers=sum(
                               by[k]['pred']['raw']!=by[k]['gold']['raw'] for k in same))
    (d/'paired-audit.json').write_text(json.dumps(report,indent=2))
    for split,data in report['splits'].items():
        print(split,json.dumps(data['constrained']),flush=True)

if __name__=='__main__':
    main()
