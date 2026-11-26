"""Prepare, conditionally queue, and collect a shared train-only planner initialization."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).parent))
from manage_structure_supplement import command, connect, PYTHON, ROOT
from remote_gpu import upload_file, download_tree, digest, remote_digest

REMOTE='/root/consdag_audits/shared-planner-sft-20261126-v1'
LOCAL=ROOT/'outputs/shared_planner_sft_20261126'
CONFIG='configs/shared_planner_sft_20261126.json'


def deploy(client,sftp,resume_prelaunch=False):
    if resume_prelaunch:
        guard='from pathlib import Path; p=Path('+repr(REMOTE)+'); assert p.is_dir(); assert not (p/"launch.json").exists(); assert not (p/"run.log").exists(); assert not (p/"results/protocol.json").exists(); assert not (p/"results/train_steps.jsonl").exists(); print("prelaunch-only recovery confirmed")'
        command(client,[PYTHON,'-c',guard])
    else:
        sftp.mkdir(REMOTE)
    paths=[CONFIG,'tests/test_shared_planner_sft.py','tests/smoke_shared_planner_torch.py']+['scripts/research_followup/'+n for n in
        ('common.py','fixed_planner.py','structure_supplement.py','format_recovery.py',
         'shared_planner_sft.py','wait_shared_planner_sft.py')]
    for name in paths:
        with redirect_stdout(io.StringIO()): upload_file(sftp,ROOT/name,REMOTE+'/'+name)
    env=['env','CUDA_VISIBLE_DEVICES=','PYTHONPATH=/root/ConsDagV6Frozen/src:/root/ConsDagSubmissionReview/src',
         'OMP_NUM_THREADS=1',PYTHON]
    code='import runpy; m=runpy.run_path('+repr(REMOTE+'/tests/test_shared_planner_sft.py')+'); fs=[f for n,f in m.items() if n.startswith("test_")]; [f() for f in fs]; print("PASS",len(fs))'
    tested=command(client,env+['-c',code])
    trained_smoke=command(client,env+[REMOTE+'/tests/smoke_shared_planner_torch.py','--config',REMOTE+'/'+CONFIG])
    preflight=command(client,env+[REMOTE+'/scripts/research_followup/shared_planner_sft.py',
        '--root','/root/ConsDagV6Frozen','--out',REMOTE+'/results','--config',REMOTE+'/'+CONFIG,'--prepare-only'])
    args=[PYTHON,REMOTE+'/scripts/research_followup/wait_shared_planner_sft.py','--root','/root/ConsDagV6Frozen',
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
    record=dict(utc=datetime.now(timezone.utc).isoformat(),tests=tested,torch_smoke=trained_smoke,preflight=preflight,launch=launch,
                remote=REMOTE,source_sha256={n:digest(ROOT/n) for n in paths})
    (LOCAL/'deployment.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)


def status(client,sftp):
    code='\n'.join(['import json,subprocess','from pathlib import Path','p=Path('+repr(REMOTE)+')',
        'r={n:json.loads((p/n).read_text()) if (p/n).exists() else None for n in ["launch.json","results/waiter_state.json","results/completion.json","results/smoke_gate.json","results/training.json"]}',
        'for n in ["calls.jsonl","train_steps.jsonl","compiler_calls.jsonl"]:',
        ' f=p/"results"/n; r[n]=sum(1 for _ in f.open()) if f.exists() else 0',
        'r["subruns"]={}',
        'for n in ["raw_sft","contract_sft"]:',
        ' d=p/"results"/n; f=d/"train_steps.jsonl"; r["subruns"][n]={"steps":sum(1 for _ in f.open()) if f.exists() else 0,"training":json.loads((d/"training.json").read_text()) if (d/"training.json").exists() else None}',
        'r["log_tail"]=(p/"run.log").read_text()[-1200:] if (p/"run.log").exists() else ""',
        'r["gpu"]=subprocess.run(["nvidia-smi","--query-gpu=timestamp,utilization.gpu,memory.used","--format=csv,noheader"],capture_output=True,text=True).stdout',
        'print(json.dumps(r))'])
    record=dict(utc=datetime.now(timezone.utc).isoformat(),**json.loads(command(client,[PYTHON,'-c',code])))
    LOCAL.mkdir(parents=True,exist_ok=True)
    (LOCAL/'status.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)


def fetch(client,sftp):
    # Model weights stay on the server; collect only small experiment records.
    LOCAL.mkdir(parents=True,exist_ok=True)
    dest=LOCAL/'results'; dest.mkdir(exist_ok=True)
    import stat
    def collect(relative=''):
        found=[]
        for item in sftp.listdir_attr(REMOTE+'/results/'+relative):
            name=(relative+'/'+item.filename).lstrip('/')
            if stat.S_ISDIR(item.st_mode):
                if item.filename not in ('adapter','partial_adapter'):found.extend(collect(name))
            elif item.filename.endswith(('.json','.jsonl')):found.append(name)
        return found
    names=collect()
    hashes={}
    for name in names:
        (dest/name).parent.mkdir(parents=True,exist_ok=True)
        sftp.get(REMOTE+'/results/'+name,str(dest/name))
        expected=remote_digest(sftp,REMOTE+'/results/'+name)
        if digest(dest/name)!=expected: raise ValueError('Live file changed or SHA mismatch: '+name)
        hashes[name]=expected
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
