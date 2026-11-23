"""Ten-shot cross-family PE: locked 90-row panel nested in the frozen v4 evaluation."""
import json
import os
import time
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError

from pe_v4_side import DEFAULT_URL, demonstrations, fingerprint, restore
from rescore_v4_side import ROOT, SUBSETS, aligned, digest, load_jsonl, outcome, rescore, summarise
from run_e1 import chat_messages_v4, score

MODEL = 'deepseek-v4-pro-0813'
OUT = ROOT / 'outputs/e1_v4_side' / (MODEL + '-few')
DATA = ROOT / 'data/processed_v4'
PARAMS = dict(model=MODEL, temperature=0, max_tokens=384, enable_thinking=False)
PANELSALT = 'consdag-pe-family-panel-20261122'


def select_panel(rows, n=10):
    if len({r['sample_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate source IDs')
    groups = sorted({r['group_id'] for r in rows}, key=lambda g: fingerprint([PANELSALT,g]))[:n]
    result = [r for r in rows if r['group_id'] in groups]
    if len(groups) != n or any(sorted(r['variant'] for r in result if r['group_id']==g)
                                != ['explicit','implicit','none'] for g in groups):
        raise ValueError('Incomplete panel groups')
    return result


def request(messages):
    req = urllib.request.Request(DEFAULT_URL, data=json.dumps(dict(PARAMS,messages=messages)).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['DASHSCOPE_API_KEY']})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=110) as response:
                d = json.load(response)
            if d.get('model') != MODEL:
                raise ValueError('Different model returned: '+str(d.get('model')))
            choice = d['choices'][0]
            raw = choice['message'].get('content')
            if raw is None: raw = ''
            if not isinstance(raw,str): raise ValueError('Unexpected response payload')
            return dict(raw=raw, model=d['model'], finish=choice.get('finish_reason'), usage=d.get('usage'))
        except HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt == 2: raise
        except (URLError,TimeoutError):
            if attempt == 2: raise
        time.sleep(2**(attempt+1))


def panel_report(rows_by):
    report={}
    dirs={MODEL:OUT, 'qwen-max-10':ROOT/'outputs/e1_v4_side/qwen-max-few',
          'qwen-max-0':ROOT/'outputs/e1_v4_side/qwen-max-zero'}
    dirs.update({size:ROOT/'outputs/e1'/('Qwen3-'+size+'-v4')/'trained_predictions'
                 for size in ['0.6B','1.7B','4B']})
    for subset,rows in rows_by.items():
        ids={r['sample_id'] for r in rows}
        report[subset]={}
        for name,folder in dirs.items():
            preds=[v for v in load_jsonl(folder/(subset+'.jsonl')) if v['sample_id'] in ids]
            raw=aligned(rows,preds)
            obs=[outcome(r,t) for r,t in zip(rows,raw)]
            report[subset][name]=dict(strict_f1=score(rows,[None]*len(rows),raw)['constraint_micro']['f1'],
                constrained=summarise([o for o in obs if o['gold_count']]),
                none=summarise([o for o in obs if not o['gold_count']]),
                finishes=dict(Counter(p.get('finish','not_logged') for p in preds)),
                empty=sum(not p['raw'].strip() for p in preds))
    return report


def write_json(path,data):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)


def main():
    import fcntl
    OUT.mkdir(parents=True,exist_ok=True)
    lock=(OUT/'.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    rows={k:load_jsonl(DATA/(k+'.jsonl')) for k in SUBSETS}
    panel={k:select_panel(v) for k,v in rows.items()}
    demo=demonstrations(load_jsonl(DATA/'train.jsonl'))
    conf=dict(params=PARAMS,url=DEFAULT_URL,demo_hash=fingerprint(demo),
              modules={name:digest(Path(__file__).with_name(name+'.py')) for name in
                       ('dataset_v4_spec','run_e1','rescore_v4_side','pe_v4_side','eval_exec','trust_env')},
              data={k:digest(DATA/(k+'.jsonl')) for k in ['train',*SUBSETS]},
              panel={k:[r['sample_id'] for r in v] for k,v in panel.items()},source=digest(Path(__file__)))
    manifest=OUT/'config.json'
    if manifest.exists() and json.loads(manifest.read_text())!=conf: raise ValueError('Run fingerprint changed')
    write_json(manifest,conf)
    for stage,selected in [('panel',panel),('full',rows)]:
        for subset,cohort in selected.items():
            path=OUT/(subset+'.jsonl')
            def messages(r):
                system,user=chat_messages_v4(r)
                return [system,*demo,user]
            keys={r['sample_id']:fingerprint([PARAMS,messages(r)]) for r in rows[subset]}
            done=restore(path,keys)
            missing=[r for r in cohort if r['sample_id'] not in done]
            def call(r):
                k=r['sample_id']
                return dict(sample_id=k,request_hash=keys[k],**request(messages(r)))
            with path.open('a',encoding='utf-8') as f, ThreadPoolExecutor(max_workers=8) as pool:
                for start in range(0,len(missing),8):
                    jobs=[pool.submit(call,r) for r in missing[start:start+8]]
                    errors=[]
                    for job in as_completed(jobs):
                        try: pred=job.result()
                        except Exception as e:
                            errors.append(e); continue
                        print(json.dumps(pred,ensure_ascii=False),file=f,flush=True)
                    if errors: raise errors[0]
            saved=restore(path,keys)
            if (not {r['sample_id'] for r in cohort}.issubset(saved)
                    or any(p.get('model') != MODEL for p in saved.values())):
                raise ValueError('Incomplete cohort or incorrect cached model')
            print(stage,subset,'complete',len(cohort),flush=True)
        report=panel_report(panel) if stage=='panel' else rescore(DATA,OUT)
        write_json(OUT/(stage+'-scores.json'),report)
        print(stage,'scored',flush=True)


if __name__=='__main__':
    main()
