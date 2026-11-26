"""Replay four crossed input/training cells from recovered, SHA-verified artifacts."""
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from common import read_rows,sha,evaluate_plan,summarize,paired
from audit_planner_learning_readout import original_parser
from trust_env import check,default_plan


def interaction_ci(by_arm,algorithm):
    keyed={a:{r['sample_id']:r for r in rows} for a,rows in by_arm.items()}
    groups=defaultdict(list)
    for sid,r in keyed['raw_'+algorithm+'/raw'].items():
        if r['variant']=='none':continue
        success=lambda a:int(keyed[a][sid]['faithful_success'])
        delta=(success('contract_'+algorithm+'/contract')-success('contract_'+algorithm+'/raw')
            -success('raw_'+algorithm+'/contract')+success('raw_'+algorithm+'/raw'))
        groups[r['group_id']].append(delta)
    values=np.array([sum(v)/len(v) for v in groups.values()]);rng=np.random.default_rng(20261126)
    boots=rng.choice(values,size=(10000,len(values)),replace=True).mean(1)
    return dict(delta=float(values.mean()),ci95=list(np.quantile(boots,[.025,.975])),groups=len(values),
        meaning='Change in the effect of contract input after contract training versus raw training; exposed dev, one seed, exploratory interval.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--algorithm',choices=['sft','grpo'],default='sft');args=p.parse_args();folder=args.folder
    receipt=json.loads((folder.parent/'receipt.json').read_text())
    for name,digest in receipt.items():assert sha(folder/name)==digest,name
    done=json.loads((folder/'completion.json').read_text());reported=json.loads((folder/'results.json').read_text())
    assert done['status']=='complete' and done['results_sha256']==sha(folder/'results.json')
    protocol=json.loads((folder/'protocol.json').read_text());data=ROOT/'data/processed_v6'
    for split in ('train','dev'):assert sha(data/(split+'.jsonl'))==protocol['data_sha256'][split]
    rows={r['sample_id']:r for r in read_rows(data/'dev.jsonl')}
    calls=read_rows(folder/'calls.jsonl');decisions=read_rows(folder/'decisions.jsonl')
    keyed={(r['sample_id'],r['arm']):r for r in decisions}
    assert len(calls)==len(decisions)==len(keyed)==576
    parser,parser_hash=original_parser();by_arm=defaultdict(list);details=defaultdict(lambda:defaultdict(Counter))
    for call in calls:
        sid,arm=call['sample_id'],call['arm'];row=rows[sid];saved=keyed[(sid,arm)]
        candidate=parser(call['raw'],row);outcome=evaluate_plan(row,candidate)
        assert candidate==saved['plan'] and outcome==saved['outcome']
        by_arm[arm].append(outcome)
        for label in [row['variant'],'constraints='+str(len(row['gold']['constraints']))]:
            d=details[arm][label];d['n']+=1
            for k in ('planned','safe_success','faithful_success'):d[k]+=int(outcome[k])
        details[arm]['all']['cap_hits']+=int(call['cap_hit'])
        if candidate is not None:
            checked=check(row['task'],candidate,row['gold']['constraints'])
            for i,c in enumerate(row['gold']['constraints']):
                d=details[arm]['type='+c['type']];d['valid_plan_instances']+=1;d['violated']+=int(i in checked['violations'])
    for arm,records in by_arm.items():
        assert len(records)==144 and {r['sample_id'] for r in records}==set(protocol['eval_sample_ids'])
        assert summarize(records)==reported['arms'][arm]
    train_orders={}
    for mode in ('raw','contract'):
        name=mode+'_'+args.algorithm;training=json.loads((folder/name/'training.json').read_text())
        assert training['steps']==training['planned_steps']==24
        steps=read_rows(folder/name/'train_steps.jsonl');assert len(steps)==24
        assert all(math.isfinite(r['loss']) and math.isfinite(r['grad_norm']) for r in steps)
        # GRPO uses each batch twice; its sequence of batch membership must still match across inputs.
        train_orders[mode]=[r['sample_ids'] for r in steps]
    assert train_orders['raw']==train_orders['contract']
    same_model_input_effect={m:paired(by_arm[m+'_'+args.algorithm+'/contract'],by_arm[m+'_'+args.algorithm+'/raw'])
        for m in ('raw','contract')}
    result=dict(records_replayed=len(calls),parser_sha256=parser_hash,source_receipt=receipt,
        arms={a:summarize(rs) for a,rs in by_arm.items()},breakdown=details,
        input_effect=same_model_input_effect,interaction=interaction_ci(by_arm,args.algorithm),
        same_training_order=True,scope='Recovered results only, no new inference; original parser and scoring unchanged.')
    (folder/'readout_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(dict(replayed=len(calls),input_effect=same_model_input_effect,interaction=result['interaction'],breakdown=details),indent=2))


if __name__=='__main__':main()
