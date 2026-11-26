"""Summarize recovered review outputs; no generation or new plan search."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from run_e1 import strict_parse
from common import read_rows, sha, summarize


def main(root: Path):
    result=root/'results'
    receipts=json.loads((root/'result_receipt.json').read_text())
    for name,expected in receipts.items():
        if sha(result/name)!=expected:
            raise ValueError('Recovered bytes differ: '+name)
    report=json.loads((result/'results.json').read_text())
    completion=json.loads((result/'completion.json').read_text())
    assert sha(result/'results.json')==completion['results_sha256']
    calls=read_rows(result/'calls.jsonl')
    decisions=read_rows(result/'decisions.jsonl')
    keys=[(r['sample_id'],r['arm']) for r in calls]
    assert len(keys)==len(set(keys))==report['calls']
    paired=set(report['completed_paired_rows'])
    for arm,expected in report['arms_on_same_completed_rows'].items():
        records=[r['outcome'] for r in decisions if r['arm']==arm and r['sample_id'] in paired]
        assert summarize(records)==expected
    arms={}
    for arm in report['all_call_cost']:
        rows=[r for r in calls if r['arm']==arm]
        cost=report['all_call_cost'][arm]
        for key in ('prompt_tokens','output_tokens','seconds'):
            assert abs(sum(r[key] for r in rows)-cost[key])<1e-6
        arms[arm]=dict(calls=len(rows),parsed_contracts=sum(strict_parse(r['raw']) is not None for r in rows),
                       applied_contracts=sum(r['applied_contract'] is not None for r in rows),
                       token_cap_hits=sum(r['cap_hit'] for r in rows),
                       deadline_hits=sum(r['deadline_hit'] for r in rows),**{k:cost[k] for k in ('prompt_tokens','output_tokens','seconds')})
    truncated={r['sample_id'] for r in calls if r['deadline_hit']}
    brief=dict(status=report['status'],receipt_files_verified=len(receipts),
               paired_rows_count=len(paired),paired_rows_without_deadline_hit=len(paired-truncated),
               task_groups_observed=len({r['outcome']['group_id'] for r in calls}),arms=arms,
               scores=report['arms_on_same_completed_rows'],
               rows=[dict(sample_id=r['sample_id'],arm=r['arm'],
                          parsed=strict_parse(r['raw']) is not None,
                          planned=r['outcome']['planned'],faithful=r['outcome']['faithful_success'],
                          cap_hit=r['cap_hit'],deadline_hit=r['deadline_hit']) for r in calls],
               scope='Exposed diagnostic only. Deadline-truncated calls remain failures in the frozen paired table.')
    (root/'readout.json').write_text(json.dumps(brief,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in brief.items() if k!='rows'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('root',type=Path)
    main(p.parse_args().root)
