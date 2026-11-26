"""Replay saved fixed-planner outputs; diagnostics never replace the registered score."""
from collections import Counter, defaultdict
import ast
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(Path(__file__).parent))
from common import read_rows, sha, evaluate_plan, summarize
from trust_env import default_plan, plan_change_count, plan


def json_array(raw):
    candidates=[raw.strip()]
    match=re.search(r'\[.*\]',raw,flags=re.DOTALL)
    if match: candidates.insert(0,match.group())
    for text in candidates:
        try: obj=json.loads(text)
        except json.JSONDecodeError: continue
        if isinstance(obj,list): return obj
    return None


def audit(raw,task):
    obj=json_array(raw)
    if obj is None: return {'format':'no_parseable_array','structural':'not_applicable','normalized_plan':None}
    kind='string_array' if obj and all(isinstance(x,str) for x in obj) else 'object_array' if obj and all(isinstance(x,dict) for x in obj) else 'other_array'
    candidate=None
    if kind=='string_array': candidate=obj
    elif kind=='object_array':
        # Diagnostic only: require an explicit consistent role/tool, never infer from display text.
        candidate=[]
        for item in obj:
            values=[item[k] for k in ('role','tool') if isinstance(item.get(k),str)]
            values=[v.removeprefix('role:') for v in values]
            if not values or len(set(values))!=1:
                candidate=None
                break
            candidate.append(values[0])
    if candidate is None: return {'format':kind,'structural':'no_unambiguous_roles','normalized_plan':None}
    candidate=[x.removeprefix('role:') for x in candidate]
    if any(x not in task['tools'] for x in candidate): reason='unknown_tool'
    else:
        try: plan_change_count(task,candidate)
        except ValueError as exc: reason=str(exc)
        else: reason='valid_after_diagnostic_normalization'
    return {'format':kind,'structural':reason,'normalized_plan':candidate if reason=='valid_after_diagnostic_normalization' else None}


def main():
    folder=ROOT/'outputs/local_planning_20261126/gpu-fixed-planner'
    protocol=json.loads((folder/'protocol.json').read_text())
    data=ROOT/'data/processed_v6/dev.jsonl'
    assert sha(data)==protocol['data_sha256']
    completion=json.loads((folder/'completion.json').read_text())
    assert sha(folder/'results.json')==completion['results_sha256']
    rows={r['sample_id']:r for r in read_rows(data)}
    calls=read_rows(folder/'calls.jsonl')
    decisions=read_rows(folder/'decisions.jsonl')
    assert len(calls)==1008 and len(decisions)==720
    # Execute the unchanged parser function body without importing its unrelated torch trainer.
    parser_source=ROOT/'src/sub_e2_monolithic.py'
    assert sha(parser_source) in protocol['source_sha256'].values()
    tree=ast.parse(parser_source.read_text(encoding='utf-8'))
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='parse_plan')
    from typing import Any
    namespace=dict(json=json,Any=Any,plan_change_count=plan_change_count)
    exec(compile(ast.Module(body=[function],type_ignores=[]),str(parser_source),'exec'),namespace)
    official_parser=namespace['parse_plan']
    saved={(r['sample_id'],r['arm']):r['plan'] for r in decisions}
    counts=defaultdict(Counter)
    normalized=defaultdict(list)
    cases=[]
    for record in calls:
        if not record['call'].endswith('_plan'): continue
        row=rows[record['sample_id']]
        arm=record['call'].removesuffix('_plan')
        assert official_parser(record['raw'],row)==saved[(record['sample_id'],arm)]
        diagnosis=audit(record['raw'],row['task'])
        counts[arm]['n']+=1
        counts[arm]['cap_hit']+=record['cap_hit']
        counts[arm]['format:'+diagnosis['format']]+=1
        counts[arm]['structure:'+diagnosis['structural']]+=1
        normalized[arm].append(evaluate_plan(row,diagnosis['normalized_plan']))
        cases.append(dict(sample_id=record['sample_id'],arm=arm,**diagnosis))
    # Known-good plans exercise structural validation rather than accepting all outputs as invalid.
    for sid in protocol['panel']:
        row=rows[sid]
        plan_change_count(row['task'],default_plan(row['task']))
        oracle,_=plan(row['task'],row['gold']['constraints'])
        assert official_parser(json.dumps(oracle),row)==oracle
        assert audit(json.dumps(oracle),row['task'])['structural']=='valid_after_diagnostic_normalization'
    result=dict(official_results_unchanged=True,source_sha256={n:sha(folder/n) for n in
            ('calls.jsonl','decisions.jsonl','protocol.json','results.json','completion.json')},
        known_good_structural_controls=144,actual_parser_body_sha256=sha(parser_source),
        actual_parser_replayed_calls=576,counts=counts,
        diagnostic_normalization_only={k:summarize(v) for k,v in normalized.items()},
        interpretation='All official neural scores are zero. Role/object normalization is post-hoc diagnostic, never a replacement primary score or proof of parser effectiveness.')
    (folder/'interface_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    (folder/'interface_audit_cases.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in cases),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
