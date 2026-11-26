"""Isolated deployment and receipt collection for a bounded format-recovery probe."""
from contextlib import redirect_stdout
from datetime import datetime,timezone
import io
import json
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).parent))
from manage_structure_supplement import command,connect,PYTHON,ROOT
from remote_gpu import upload_file,download_tree,digest,remote_digest

REMOTE='/root/consdag_audits/fixed-planner-format-recovery-20261126-v1'
LOCAL=ROOT/'outputs/fixed_planner_format_recovery_20261126'
CONFIG='configs/fixed_planner_format_recovery_20261126.json'


def deploy(client,sftp):
    sftp.mkdir(REMOTE)
    paths=[CONFIG,'tests/test_format_recovery.py']+['scripts/research_followup/'+n for n in
        ('common.py','fixed_planner.py','structure_supplement.py','audit_fixed_interface.py',
         'format_recovery.py','wait_format_recovery.py')]
    for name in paths:
        with redirect_stdout(io.StringIO()): upload_file(sftp,ROOT/name,REMOTE+'/'+name)
    env=['env','CUDA_VISIBLE_DEVICES=','PYTHONPATH=/root/ConsDagV6Frozen/src:/root/ConsDagSubmissionReview/src',
         'OMP_NUM_THREADS=1',PYTHON]
    code='import runpy; m=runpy.run_path('+repr(REMOTE+'/tests/test_format_recovery.py')+'); fs=[f for n,f in m.items() if n.startswith("test_")]; [f() for f in fs]; print("PASS",len(fs))'
    tested=command(client,env+['-c',code])
    preflight=command(client,env+[REMOTE+'/scripts/research_followup/format_recovery.py',
        '--root','/root/ConsDagV6Frozen','--out',REMOTE+'/results','--config',REMOTE+'/'+CONFIG,'--prepare-only'])
    args=[PYTHON,REMOTE+'/scripts/research_followup/wait_format_recovery.py','--root','/root/ConsDagV6Frozen',
          '--out',REMOTE+'/results','--config',REMOTE+'/'+CONFIG]
    code='\n'.join(['import subprocess,json','from pathlib import Path','p=Path('+repr(REMOTE)+')',
        'log=(p/"run.log").open("x")',
        'child=subprocess.Popen('+repr(args)+',stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)',
        '(p/"launch.json").write_text(json.dumps(dict(pid=child.pid,args='+repr(args)+')))',
        'print(json.dumps(dict(waiter_pid=child.pid)))'])
    launch=json.loads(command(client,[PYTHON,'-c',code]))
    LOCAL.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(LOCAL/'run_source_bytes.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in paths: z.write(ROOT/name,name)
    record=dict(utc=datetime.now(timezone.utc).isoformat(),tests=tested,preflight=preflight,launch=launch,
                remote=REMOTE,source_sha256={n:digest(ROOT/n) for n in paths})
    (LOCAL/'deployment.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)


def status(client,sftp):
    code='\n'.join(['import json,subprocess','from pathlib import Path','p=Path('+repr(REMOTE)+')',
        'r={n:json.loads((p/n).read_text()) if (p/n).exists() else None for n in ["launch.json","results/waiter_state.json","results/completion.json","results/smoke_gate.json"]}',
        'f=p/"results/calls.jsonl"; r["calls"]=sum(1 for _ in f.open()) if f.exists() else 0',
        'r["log_tail"]=(p/"run.log").read_text()[-700:]',
        'r["gpu"]=subprocess.run(["nvidia-smi","--query-gpu=timestamp,utilization.gpu,memory.used","--format=csv,noheader"],capture_output=True,text=True).stdout',
        'print(json.dumps(r))'])
    record=dict(utc=datetime.now(timezone.utc).isoformat(),**json.loads(command(client,[PYTHON,'-c',code])))
    LOCAL.mkdir(parents=True,exist_ok=True)
    (LOCAL/'status.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)


def fetch(client,sftp):
    with redirect_stdout(io.StringIO()): download_tree(sftp,REMOTE+'/results',LOCAL/'results')
    hashes={}
    for f in (LOCAL/'results').rglob('*'):
        if f.is_file():
            name=f.relative_to(LOCAL/'results').as_posix()
            remote=remote_digest(sftp,REMOTE+'/results/'+name)
            if digest(f)!=remote: raise ValueError('Live file changed or SHA mismatch: '+name)
            hashes[name]=remote
    (LOCAL/'receipt.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps(dict(files_verified=len(hashes))),flush=True)


if __name__=='__main__':
    with connect() as client,client.open_sftp() as sftp:
        print('Ready: deploy, status, fetch, quit',flush=True)
        while True:
            op=input().strip()
            if op=='quit': break
            try: {'deploy':deploy,'status':status,'fetch':fetch}[op](client,sftp)
            except Exception as exc: print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
