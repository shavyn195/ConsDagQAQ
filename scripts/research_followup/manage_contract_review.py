"""Deploy the isolated CPU review and recover completed 4B artifacts."""
from contextlib import redirect_stdout
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shlex
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect, upload_file, download_tree, digest, remote_digest

REMOTE='/root/consdag_audits/contract-review-4b-cpu-20261126-v1'
PYTHON='/root/miniconda3/bin/python'
LOCAL=ROOT/'outputs/contract_review_4b_cpu_20261126'
CONFIG='configs/contract_review_cpu_20261126.json'
ENTRY='scripts/research_followup/review_contracts.py'
FORMAT=False
ENVELOPE=False


def command(client, args):
    _,stdout,stderr=client.exec_command(shlex.join(args))
    out,err=stdout.read().decode(),stderr.read().decode()
    code=stdout.channel.recv_exit_status()
    if code:
        raise RuntimeError(f'Remote command exited {code}: {err[-3000:]}')
    return out


def recover_4b(client,sftp):
    base='/root/ConsDagV6Frozen/outputs/e1_v6'
    target=ROOT/'outputs/v6_4b_recovery_20261126'
    receipts={}
    for seed in (42,43,44):
        remote=base+f'/Qwen3-4B-v6-seed{seed}'
        with sftp.open(remote+'/completion.json') as stream:
            done=json.load(stream)
        if done['status']!='complete':
            raise ValueError('4B run not complete: '+str(seed))
        names=['completion.json','metrics.json','provenance.json','token_coverage.json']
        names += [n for n in done['artifact_sha256'] if n.startswith('trained_predictions/')]
        for name in names:
            h=remote_digest(sftp,remote+'/'+name)
            expected=done['artifact_sha256'].get(name)
            if expected is not None and h!=expected:
                raise ValueError('Completion receipt mismatch: '+name)
            local=target/f'seed{seed}'/name
            if not local.exists() or digest(local)!=h:
                with redirect_stdout(io.StringIO()):
                    download_tree(sftp,remote+'/'+name,local)
            if digest(local)!=h:
                raise ValueError('Recovery mismatch: '+name)
            receipts[f'seed{seed}/'+name]=h
    (target/'receipt.json').write_text(json.dumps(dict(observed_utc=datetime.now(timezone.utc).isoformat(),sha256=receipts),indent=2),encoding='utf-8')
    print(json.dumps(dict(recovered_4b_seeds=[42,43,44],verified_files=len(receipts))),flush=True)


def launch(client,sftp):
    if ENVELOPE:
        smoke=ROOT/'outputs/contract_review_4b_format_20261126'
        for name,expected in json.loads((smoke/'result_receipt.json').read_text()).items():
            if digest(smoke/'results'/name)!=expected:
                raise ValueError('Format gate receipt mismatch: '+name)
        checked_smoke=json.loads((smoke/'readout.json').read_text())
        if checked_smoke['status']!='complete' or any(v['parsed_contracts']!=1 for v in checked_smoke['arms'].values()):
            raise ValueError('Format gate failed; do not launch the expanded diagnostic')
    # Exclusive directory: preserve any earlier failed/completed run.
    sftp.mkdir(REMOTE)
    paths=['scripts/research_followup/review_contracts.py','scripts/research_followup/common.py',
           'src/run_e1.py','src/trust_env.py','src/dataset_v5_spec.py','src/dataset_v4_spec.py',
           CONFIG,'outputs/natural_privacy_loss_audit_20261126/cases.jsonl',
           'tests/test_review_contracts.py','scripts/research_followup/review_contracts_format.py']
    if ENVELOPE:
        paths.append(ENTRY)
    for p in paths:
        with redirect_stdout(io.StringIO()):
            upload_file(sftp,ROOT/p,REMOTE+'/'+p)
    # Preflight checks the exact data and prompts on the server, without model inference.
    code='\n'.join([
        'import sys,json,os', 'from pathlib import Path',
        'sys.path.insert(0,'+repr(REMOTE+'/scripts/research_followup')+')',
        'from review_contracts import select_panel',
        'from review_contracts_format import messages' if (FORMAT or ENVELOPE) else 'from review_contracts import messages',
        'from transformers import AutoTokenizer', 'from run_e1 import render_chat',
        'model=Path("/root/ConsDagV6Frozen/models/Qwen3-4B")',
        'assert model.is_dir()',
        'rows=select_panel(Path("/root/ConsDagV5"),Path("/root/consdag_audits/local-planning-20261126/cpu-heldout"),Path('+repr(REMOTE+'/outputs/natural_privacy_loss_audit_20261126/cases.jsonl')+'))',
        'assert len(rows)==18',
        'rows=rows[:1]' if FORMAT else 'assert len(rows)==18',
        'tok=AutoTokenizer.from_pretrained(str(model),local_files_only=True)',
        'lengths=[render_chat(tok,messages(p["row"],p["compiler_raw"],p["original"],arm),add_generation_prompt=True)["input_ids"].numel() for p in rows for arm in ("invalid_fields","full_binding","fresh_compile")]',
        'assert max(lengths)+512<=tok.model_max_length',
        'mem=dict(line.split(":",1) for line in Path("/proc/meminfo").read_text().splitlines())',
        'assert int(mem["MemAvailable"].split()[0])>32*1024*1024',
        'print(json.dumps(dict(preflight="PASS",rows=len(rows),calls=len(lengths),max_prompt_tokens=max(lengths),cpus=os.cpu_count(),load=os.getloadavg())))'])
    checked=command(client,[PYTHON,'-c',code])
    tested=command(client,[PYTHON,'-m','unittest','discover','-s',REMOTE+'/tests','-p','test_review_contracts.py'])
    config=json.loads((ROOT/CONFIG).read_text(encoding='utf-8'))
    args=['timeout','--signal=TERM','--kill-after=30s',str(config['process_timeout_seconds'])+'s','nice','-n','15','env',
          'CUDA_VISIBLE_DEVICES=','OMP_NUM_THREADS=8','MKL_NUM_THREADS=8','OPENBLAS_NUM_THREADS=1',
          PYTHON,REMOTE+'/'+ENTRY,
          '--source','/root/ConsDagV5','--history','/root/consdag_audits/local-planning-20261126/cpu-heldout',
          '--cases',REMOTE+'/outputs/natural_privacy_loss_audit_20261126/cases.jsonl',
          '--model','/root/ConsDagV6Frozen/models/Qwen3-4B',
          '--protocol',REMOTE+'/'+CONFIG,'--out',REMOTE+'/results',
          '--seconds',str(config['active_seconds_cap'])]
    launch_code='\n'.join(['import subprocess,json', 'from pathlib import Path',
        'root=Path('+repr(REMOTE)+')',
        'log=(root/"run.log").open("x")',
        'p=subprocess.Popen('+repr(args)+',stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)',
        '(root/"launch.json").write_text(json.dumps(dict(pid=p.pid,args='+repr(args)+')))',
        'print(json.dumps(dict(launched=True,pid=p.pid)))'])
    result=json.loads(command(client,[PYTHON,'-c',launch_code]))
    LOCAL.mkdir(parents=True,exist_ok=True)
    receipt=dict(created_utc=datetime.now(timezone.utc).isoformat(),remote=REMOTE,
                 preflight=checked,tests=tested,launch=result,source_sha256={p:digest(ROOT/p) for p in paths})
    (LOCAL/'deployment.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(checked.strip(),flush=True)
    print(json.dumps(result),flush=True)


def status(client,sftp):
    code='\n'.join(['import json,subprocess', 'from pathlib import Path',
       'root=Path('+repr(REMOTE)+')', 'r={}',
       'for name in ("launch.json","results/state.json","results/completion.json"):',
       '    p=root/name', '    r[name]=json.loads(p.read_text()) if p.exists() else None',
       'p=root/"results/calls.jsonl"',
       'r["completed_calls"]=len(p.read_text().splitlines()) if p.exists() else 0',
       'r["log_tail"]=(root/"run.log").read_text()[-2500:]',
       'r["process"]=subprocess.run(["ps","-p",str(r["launch.json"]["pid"]),"-o","pid=,etime=,args="],capture_output=True,text=True).stdout',
       'print(json.dumps(r))'])
    value=json.loads(command(client,[PYTHON,'-c',code]))
    LOCAL.mkdir(parents=True,exist_ok=True)
    (LOCAL/'latest_status.json').write_text(json.dumps(dict(observed_utc=datetime.now(timezone.utc).isoformat(),**value),indent=2),encoding='utf-8')
    print(json.dumps(dict(state=value['results/state.json'],completion=value['results/completion.json'],
                          completed_calls=value['completed_calls'],process_alive=bool(value['process']),
                          log_tail='\n'.join(value['log_tail'].splitlines()[-3:]))),flush=True)


def runtime(client,sftp):
    value=dict(observed_utc=datetime.now(timezone.utc).isoformat())
    for key,path in {'queue':'/root/ConsDagV6Frozen/outputs/e1_v6/queue_state.json',
        'waiter':'/root/consdag_audits/local-planning-20261126/gpu-fixed-planner/waiter_state.json'}.items():
        with sftp.open(path) as stream: value[key]=json.load(stream)
    value['gpu']=command(client,['nvidia-smi','--query-gpu=timestamp,utilization.gpu,memory.used,memory.total','--format=csv,noheader'])
    code='\n'.join(['import json,subprocess,os',
        'from pathlib import Path',
        'rows=subprocess.run(["ps","-eo","pid=,ppid=,etimes=,args="],capture_output=True,text=True).stdout.splitlines()',
        'rows=[r for r in rows if r.split()[0]!=str(os.getpid()) and any(k in r for k in ("run_e1_v6.py","run_v6_relay.py","fixed_planner.py","waiter.py"))]',
        'print(json.dumps(rows))'])
    value['active_processes']=json.loads(command(client,[PYTHON,'-c',code]))
    value['compute_processes']=command(client,['nvidia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader'])
    active=value['queue'].get('active')
    if active:
        name=f"{active['model']}-v6-seed{active['seed']}.log"
        path='/root/ConsDagV6Frozen/outputs/e1_v6/'+name
        with sftp.open(path) as stream:
            stream.seek(max(0,stream.stat().st_size-4000))
            value['active_log_tail']=stream.read().decode('utf-8','replace')
    LOCAL.mkdir(parents=True,exist_ok=True)
    (LOCAL/'runtime_snapshot.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
    print(json.dumps(value),flush=True)


def sources(client,sftp):
    receipt=json.loads((LOCAL/'deployment.json').read_text(encoding='utf-8'))
    actual={}
    for name,expected in receipt['source_sha256'].items():
        with sftp.open(REMOTE+'/'+name,'rb') as stream:
            data=stream.read()
        import hashlib
        if hashlib.sha256(data).hexdigest()!=expected:
            raise ValueError('Deployed source changed: '+name)
        actual[name]=data
    with zipfile.ZipFile(LOCAL/'run_source_bytes.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in actual.items():
            archive.writestr(name,data)
    print(json.dumps(dict(verified_run_sources=len(actual))),flush=True)


def fetch(client,sftp):
    with redirect_stdout(io.StringIO()):
        download_tree(sftp,REMOTE+'/results',LOCAL/'results')
    receipt={}
    for path in (LOCAL/'results').rglob('*'):
        if path.is_file():
            name=path.relative_to(LOCAL/'results').as_posix()
            h=remote_digest(sftp,REMOTE+'/results/'+name)
            if digest(path)!=h:
                raise ValueError('Concurrent change or download mismatch: '+name)
            receipt[name]=h
    (LOCAL/'result_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(dict(fetched=len(receipt))),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--probe',choices=['main','format','envelope'],default='main')
    parser.add_argument('--action',choices=['launch','status','fetch','recover4b','runtime','sources'])
    args=parser.parse_args()
    if args.probe=='format':
        FORMAT=True
        REMOTE='/root/consdag_audits/contract-review-4b-format-20261126-v1'
        LOCAL=ROOT/'outputs/contract_review_4b_format_20261126'
        CONFIG='configs/contract_review_format_20261126.json'
        ENTRY='scripts/research_followup/review_contracts_format.py'
    elif args.probe=='envelope':
        ENVELOPE=True
        REMOTE='/root/consdag_audits/contract-review-4b-envelope-20261126-v1'
        LOCAL=ROOT/'outputs/contract_review_4b_envelope_20261126'
        CONFIG='configs/contract_review_envelope_20261126.json'
        ENTRY='scripts/research_followup/review_contracts_envelope.py'
    with connect() as client,client.open_sftp() as sftp:
        actions={'launch':launch,'status':status,'fetch':fetch,'recover4b':recover_4b,'runtime':runtime,'sources':sources}
        if args.action:
            actions[args.action](client,sftp)
            raise SystemExit(0)
        # Commands accepted after login; no credential file, no repeated login needed.
        print('Ready: launch, status, fetch, recover4b, runtime, sources, quit',flush=True)
        while True:
            try:
                op=input().strip()
            except EOFError:
                break
            if op=='quit': break
            try:
                actions[op](client,sftp)
            except Exception as exc:
                print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
