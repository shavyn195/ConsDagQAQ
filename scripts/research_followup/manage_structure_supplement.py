"""Deploy a separate, bounded structural supplement without editing live code."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shlex
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from remote_gpu import connect, upload_file, download_tree, digest, remote_digest

REMOTE = '/root/consdag_audits/planner-structure-controls-20261126-v1'
LOCAL = ROOT/'outputs/planner_structure_controls_20261126'
PYTHON = '/root/miniconda3/bin/python'
CONFIG = 'configs/planner_structure_supplement_20261126.json'


def command(client, args):
    _, out, err = client.exec_command(shlex.join(args))
    stdout, stderr = out.read().decode(), err.read().decode()
    if out.channel.recv_exit_status():
        raise RuntimeError(stderr[-3000:])
    return stdout


def status(client, sftp):
    code = '\n'.join([
        'import json,subprocess', 'from pathlib import Path', 'r={}',
        'for label,root in '+repr({'fixed':'/root/consdag_audits/local-planning-20261126/gpu-fixed-planner',
                                  'probe':'/root/consdag_audits/planner-reward-signal-20261126-v1/results',
                                  'supplement':REMOTE+'/results'})+'.items():',
        ' p=Path(root)',
        ' r[label]={n:json.loads((p/n).read_text()) if (p/n).exists() else None for n in ["waiter_state.json","completion.json"]}',
        ' for n in ["calls.jsonl","decisions.jsonl"]:',
        '  f=p/n; r[label][n]=sum(1 for _ in f.open()) if f.exists() else 0',
        'r["fixed_log_tail"]=Path("/root/consdag_audits/local-planning-20261126/gpu.log").read_text()[-1200:]',
        'r["gpu"]=subprocess.run(["nvidia-smi","--query-gpu=timestamp,utilization.gpu,memory.used,memory.total","--format=csv,noheader"],capture_output=True,text=True).stdout',
        'print(json.dumps(r))'])
    record = dict(utc=datetime.now(timezone.utc).isoformat(), **json.loads(command(client,[PYTHON,'-c',code])))
    LOCAL.mkdir(parents=True, exist_ok=True)
    (LOCAL/'status.json').write_text(json.dumps(record,indent=2), encoding='utf-8')
    print(json.dumps(record), flush=True)


def deploy(client, sftp):
    # Exclusive directory creation prevents accidental duplicate deployment.
    sftp.mkdir(REMOTE)
    paths = [CONFIG, 'tests/test_structure_supplement.py'] + [
        'scripts/research_followup/'+name for name in
        ('common.py','fixed_planner.py','structure_supplement.py','wait_structure_supplement.py')]
    for name in paths:
        with redirect_stdout(io.StringIO()):
            upload_file(sftp, ROOT/name, REMOTE+'/'+name)
    env = ['env','CUDA_VISIBLE_DEVICES=',
           'PYTHONPATH=/root/ConsDagV6Frozen/src:/root/ConsDagSubmissionReview/src',
           'OMP_NUM_THREADS=1','MKL_NUM_THREADS=1',PYTHON]
    code = 'import runpy; m=runpy.run_path('+repr(REMOTE+'/tests/test_structure_supplement.py')+'); ts=[f for n,f in m.items() if n.startswith("test_")]; [f() for f in ts]; print("PASS",len(ts))'
    tests = command(client,env+['-c',code])
    preflight = command(client,env+[REMOTE+'/scripts/research_followup/structure_supplement.py',
        '--root','/root/ConsDagV6Frozen','--out',REMOTE+'/results','--config',REMOTE+'/'+CONFIG,'--prepare-only'])
    args = [PYTHON,REMOTE+'/scripts/research_followup/wait_structure_supplement.py',
            '--root','/root/ConsDagV6Frozen','--out',REMOTE+'/results','--config',REMOTE+'/'+CONFIG]
    code = '\n'.join(['import subprocess,json','from pathlib import Path','p=Path('+repr(REMOTE)+')',
        'log=(p/"run.log").open("x")',
        'child=subprocess.Popen('+repr(args)+',stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)',
        '(p/"launch.json").write_text(json.dumps(dict(pid=child.pid,args='+repr(args)+')))',
        'print(json.dumps(dict(waiter_pid=child.pid)))'])
    result = json.loads(command(client,[PYTHON,'-c',code]))
    LOCAL.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(LOCAL/'run_source_bytes.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in paths:
            archive.write(ROOT/name,name)
    record = dict(utc=datetime.now(timezone.utc).isoformat(), remote=REMOTE, tests=tests,
                  preflight=preflight,launch=result,source_sha256={p:digest(ROOT/p) for p in paths})
    (LOCAL/'deployment.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record),flush=True)


def fetch(client, sftp):
    with redirect_stdout(io.StringIO()):
        download_tree(sftp,REMOTE+'/results',LOCAL/'results')
    hashes={}
    for file in (LOCAL/'results').rglob('*'):
        if file.is_file():
            name=file.relative_to(LOCAL/'results').as_posix()
            expected=remote_digest(sftp,REMOTE+'/results/'+name)
            if digest(file)!=expected:
                raise ValueError('Live change or hash mismatch: '+name)
            hashes[name]=expected
    (LOCAL/'receipt.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps(dict(files_verified=len(hashes))),flush=True)


if __name__ == '__main__':
    with connect() as client, client.open_sftp() as sftp:
        print('Ready: status, deploy, fetch, quit',flush=True)
        while True:
            op=input().strip()
            if op=='quit': break
            try:
                {'status':status,'deploy':deploy,'fetch':fetch}[op](client,sftp)
            except Exception as exc:
                print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
