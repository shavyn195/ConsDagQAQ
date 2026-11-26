"""Decompose cached record disagreement without generating plans or predictions."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from run_e1 import constraint_key, core_key, score, strict_parse
from common import align, read_rows, sha


def describe(gold, raw):
    parsed=strict_parse(raw)
    if parsed is None:
        return dict(category='invalid_output',differences=[])
    got=parsed['constraints']; want=gold['constraints']
    if Counter(map(core_key,got))!=Counter(map(core_key,want)):
        return dict(category='core_mismatch',differences=[])
    if parsed['query_state']!=gold['query_state']:
        return dict(category='query_state_mismatch',differences=[])
    if Counter(map(constraint_key,got))==Counter(map(constraint_key,want)):
        return dict(category='record_exact',differences=[])
    # Remove exact matches first. Do not invent alignment for duplicate core keys.
    remaining=list(got)
    unmatched=[]
    for g in want:
        indices=[i for i,p in enumerate(remaining) if constraint_key(p)==constraint_key(g)]
        if indices:
            remaining.pop(indices[0])
        else:
            unmatched.append(g)
    gp=defaultdict(list); pp=defaultdict(list)
    for g in unmatched: gp[core_key(g)].append(g)
    for p in remaining: pp[core_key(p)].append(p)
    differences=[]
    ambiguous=0
    for key, gs in gp.items():
        ps=pp[key]
        if len(gs)!=1 or len(ps)!=1:
            ambiguous+=len(gs)
            continue
        g,p=gs[0],ps[0]
        gk,pk=constraint_key(g),constraint_key(p)
        fields=[field for i,field in ((1,'state'),(2,'severity'),(3,'scope')) if gk[i]!=pk[i]]
        differences.append(dict(type=g['type'],fields=fields,
                                gold={f:g[f] for f in fields},predicted={f:p[f] for f in fields}))
    return dict(category='metadata_only',differences=differences,ambiguous_clauses=ambiguous)


def main():
    recovered=ROOT/'outputs/v6_4b_recovery_20261126'
    out=ROOT/'outputs/v6_4b_record_gap_20261126'
    out.mkdir(exist_ok=True)
    receipts=json.loads((recovered/'receipt.json').read_text())['sha256']
    summary=dict(scope='Descriptive audit of recovered predictions, no model or planner calls; field scorer recomputed, execution scorer not rerun.',
                 source_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'src/run_e1.py')},panels={})
    details=[]
    for seed in (42,43,44):
        run=recovered/f'seed{seed}'
        metrics=json.loads((run/'metrics.json').read_text())
        provenance=json.loads((run/'provenance.json').read_text())
        for split in ('dev','test_tpl_ho','test_tool_ho','test_struct_ho','test_composition_ho'):
            data=ROOT/'data/processed_v6'/f'{split}.jsonl'
            pred=run/'trained_predictions'/f'{split}.jsonl'
            assert sha(data)==provenance['data_sha256'][split]
            assert sha(pred)==receipts[pred.relative_to(recovered).as_posix()]
            rows=read_rows(data); predictions=align(rows,read_rows(pred))
            fields=score(rows,[None]*len(rows),[p['raw'] for p in predictions])
            for k in ('constraint_micro','constraint_core_micro','record_exact_match','json_parse_rate','malformed_prediction_count'):
                assert fields[k]==metrics['trained'][split][k],(seed,split,k)
            categories=Counter(); field_rows=Counter(); type_clauses=Counter(); combos=Counter(); ambiguous=0
            for row,p in zip(rows,predictions):
                item=describe(row['gold'],p['raw'])
                categories[item['category']]+=1
                if item['category']=='metadata_only':
                    labels=set()
                    ambiguous+=item['ambiguous_clauses']
                    for d in item['differences']:
                        labels.update(d['fields']); type_clauses[d['type']]+=1
                    field_rows.update(labels)
                    combos['+'.join(sorted(labels)) or 'ambiguous']+=1
                if item['category']!='record_exact':
                    details.append(dict(seed=seed,split=split,sample_id=row['sample_id'],group_id=row['group_id'],
                                        variant=row['variant'],query=row['query'],**item))
            assert sum(categories.values())==len(rows)
            assert abs(categories['record_exact']/len(rows)-fields['record_exact_match'])<1e-12
            summary['panels'][f'{seed}/{split}']=dict(n=len(rows),categories=dict(categories),
                metadata_field_rows=dict(field_rows),metadata_field_combinations=dict(combos),
                metadata_mismatched_clauses_by_type=dict(type_clauses),ambiguous_clauses=ambiguous,
                strict_f1=fields['constraint_micro']['f1'],core_f1=fields['constraint_core_micro']['f1'],
                data_sha256=sha(data),predictions_sha256=sha(pred))
    (out/'cases.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in details),encoding='utf-8',newline='\n')
    summary['cases_sha256']=sha(out/'cases.jsonl')
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8',newline='\n')
    compact={}
    for split in ('dev','test_tpl_ho','test_tool_ho','test_struct_ho','test_composition_ho'):
        panels=[summary['panels'][f'{s}/{split}'] for s in (42,43,44)]
        counts=Counter(); fields=Counter(); types=Counter()
        for p in panels:
            counts.update(p['categories']); fields.update(p['metadata_field_rows']); types.update(p['metadata_mismatched_clauses_by_type'])
        compact[split]=dict(n=sum(p['n'] for p in panels),categories=dict(counts),metadata_field_rows=dict(fields),types=dict(types))
    print(json.dumps(compact,indent=2))


if __name__=='__main__':
    main()
