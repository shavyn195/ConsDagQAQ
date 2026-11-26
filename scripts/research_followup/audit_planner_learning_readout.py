"""Re-score only recovered outputs; retain the original parser and fixed metric."""
import argparse
import ast
from collections import Counter,defaultdict
import json
from pathlib import Path
import sys
from typing import Any
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from common import evaluate_plan,read_rows,sha,summarize,paired
from trust_env import check,plan_change_count,default_plan
from audit_fixed_interface import audit


def original_parser():
    source=ROOT/'src/sub_e2_monolithic.py'
    initial=json.loads((ROOT/'outputs/local_planning_20261126/gpu-fixed-planner/protocol.json').read_text())
    assert sha(source) in initial['source_sha256'].values()
    fn=next(n for n in ast.parse(source.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='parse_plan')
    namespace=dict(json=json,Any=Any,plan_change_count=plan_change_count)
    exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),namespace)
    return namespace['parse_plan'],sha(source)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--folder',type=Path,required=True)
    p.add_argument('--baseline',type=Path)
    args=p.parse_args(); folder=args.folder
    receipt=json.loads((folder.parent/'receipt.json').read_text())
    for n,digest in receipt.items(): assert sha(folder/n)==digest,n
    done=json.loads((folder/'completion.json').read_text())
    assert done['status']=='complete' and sha(folder/'results.json')==done['results_sha256']
    protocol=json.loads((folder/'protocol.json').read_text())
    data=ROOT/'data/processed_v6/dev.jsonl'
    expected=protocol['data_sha256']
    if isinstance(expected,dict): expected=expected['dev']
    assert sha(data)==expected
    rows={r['sample_id']:r for r in read_rows(data)}
    calls=read_rows(folder/'calls.jsonl'); records=read_rows(folder/'decisions.jsonl')
    keyed={(r['sample_id'],r['arm']):r for r in records}
    assert len(keyed)==len(records)==len(calls)==720
    parser,parser_sha=original_parser()
    by_arm=defaultdict(list); detail=defaultdict(lambda:defaultdict(Counter)); examples=[]
    for call in calls:
        sid,arm=call['sample_id'],call['arm']; row=rows[sid]; saved=keyed[(sid,arm)]
        plan=parser(call['raw'],row)
        assert plan==saved['plan'] and evaluate_plan(row,plan)==saved['outcome']
        by_arm[arm].append(saved['outcome'])
        d=detail[arm]
        d['all']['n']+=1
        d['all']['string_array']+=int(saved['string_array'])
        d['all']['cap_hits']+=int(call['cap_hit'])
        variant=row['variant']; result=saved['outcome']
        for key in [variant,'constraints='+str(len(row['gold']['constraints']))]:
            d[key]['n']+=1
            for field in ('planned','safe_success','faithful_success'):
                d[key][field]+=int(result[field])
            d[key]['default_unchanged']+=int(plan==default_plan(row['task']))
        if plan is None:
            d['structural_errors'][audit(call['raw'],row['task'])['structural']]+=1
        else:
            verified=check(row['task'],plan,row['gold']['constraints'])
            for i,c in enumerate(row['gold']['constraints']):
                d['type='+c['type']]['valid_plan_constraints']+=1
                d['type='+c['type']]['violated']+=int(i in verified['violations'])
        examples.append(dict(sample_id=sid,arm=arm,variant=variant,outcome=result))
    reported=json.loads((folder/'results.json').read_text())
    for arm,rs in by_arm.items(): assert summarize(rs)==reported['arms'][arm]
    extra={}
    if args.baseline:
        baseline=read_rows(args.baseline/'decisions.jsonl')
        extra['same_arm_after_minus_before']={a:paired(rs,[r['outcome'] for r in baseline if r['arm']==a]) for a,rs in by_arm.items()}
    supplement=ROOT/'outputs/planner_structure_controls_20261126/results/calls.jsonl'
    if supplement.exists():
        controls={(r['sample_id'],r['arm']):r['messages'] for r in read_rows(supplement)}
        sids={s for s,a in controls}
        extra['prior_core_interface_matches']=dict(n=len(sids),identical_predicted_oracle_prompts=sum(
            controls[(s,'predicted_core')]==controls[(s,'oracle_core')] for s in sids))
    output=dict(records_replayed=len(records),parser_sha256=parser_sha,source_receipt=receipt,
        arms={a:summarize(rs) for a,rs in by_arm.items()},breakdown=detail,**extra,
        note='Existing recovered decisions only; no new model inference or repaired scoring. Type denominators are constraints among structurally valid plans, not all tasks.')
    (folder/'readout_audit.json').write_text(json.dumps(output,indent=2))
    print(json.dumps(dict(replayed=len(records),arms=output['arms'],extra=extra,breakdown=detail),indent=2))


if __name__=='__main__': main()
