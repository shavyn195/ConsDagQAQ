"""Isolated deployment and monitoring; credentials remain in SSH helper memory."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from remote_gpu import connect, upload_file, download_tree, digest, remote_digest
REMOTE = '/root/consdag_audits/planner-reward-signal-20261126-v1'
LOCAL = ROOT/'outputs/planner_reward_signal_20261126'
PYTHON = '/root/miniconda3/bin/python'
CONFIG = 'configs/planner_reward_probe_20261126.json'


def command(client,args):
    _, out, err = client.exec_command(shlex.join(args))
    stdout, stderr = out.read().decode(), err.read().decode()
    if out.channel.recv_exit_status():
        raise RuntimeError(stderr[-3000:])
    return stdout


def deploy(client,sftp):
    sftp.mkdir(REMOTE)
    paths = [CONFIG, 'tests/test_planner_reward_probe.py'] + [
        'scripts/research_followup/'+name for name in
        ('common.py','fixed_planner.py','planner_reward_probe.py','wait_reward_probe.py')]
    for name in paths:
        with redirect_stdout(io.StringIO()):
            upload_file(sftp,ROOT/name,REMOTE+'/'+name)
    env = ['env','CUDA_VISIBLE_DEVICES=',
           'PYTHONPATH=/root/ConsDagV6Frozen/src:/root/ConsDagSubmissionReview/src',
           'OMP_NUM_THREADS=1','MKL_NUM_THREADS=1',PYTHON]
    test_code = 'import runpy; m=runpy.run_path('+repr(REMOTE+'/tests/test_planner_reward_probe.py')+'); tests=[f for n,f in m.items() if n.startswith("test_")]; [f() for f in tests]; print("PASS",len(tests))'
    tested = command(client,env+['-c',test_code])
    preflight = command(client,env+[REMOTE+'/scripts/research_followup/planner_reward_probe.py',
                '--root','/root/ConsDagV6Frozen','--out',REMOTE+'/results',
                '--config',REMOTE+'/'+CONFIG,'--prepare-only'])
    args = [PYTHON,REMOTE+'/scripts/research_followup/wait_reward_probe.py',
            '--root','/root/ConsDagV6Frozen',
            '--previous','/root/consdag_audits/local-planning-20261126/gpu-fixed-planner',
            '--out',REMOTE+'/results','--config',REMOTE+'/'+CONFIG]
    code = '\n'.join(['import subprocess,json','from pathlib import Path',
        'root=Path('+repr(REMOTE)+')','log=(root/"run.log").open("x")',
        'p=subprocess.Popen('+repr(args)+',stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)',
        '(root/"launch.json").write_text(json.dumps(dict(pid=p.pid,args='+repr(args)+')))',
        'print(json.dumps(dict(waiter_pid=p.pid)))'])
    result = json.loads(command(client,[PYTHON,'-c',code]))
    LOCAL.mkdir(parents=True,exist_ok=True)
    record = dict(utc=datetime.now(timezone.utc).isoformat(), remote=REMOTE, tests=tested,
                  preflight=preflight,launch=result,source_sha256={p:digest(ROOT/p) for p in paths})
    (LOCAL/'deployment.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record),flush=True)


def status(client,sftp):
    code='\n'.join(['import json,subprocess','from pathlib import Path','p=Path('+repr(REMOTE)+')',
        'r={n:json.loads((p/n).read_text()) if (p/n).exists() else None for n in ["launch.json","results/waiter_state.json","results/completion.json"]}',
        'f=p/"results/calls.jsonl"','r["calls"]=len(f.read_text().splitlines()) if f.exists() else 0',
        'r["log_tail"]=(p/"run.log").read_text()[-1500:]',
        'r["process"]=subprocess.run(["ps","-p",str(r["launch.json"]["pid"]),"-o","pid=,etime=,args="],capture_output=True,text=True).stdout',
        'print(json.dumps(r))'])
    record = json.loads(command(client,[PYTHON,'-c',code]))
    LOCAL.mkdir(parents=True,exist_ok=True)
    (LOCAL/'status.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),**record),indent=2))
    print(json.dumps(record),flush=True)


def fetch(client,sftp):
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
    with connect() as client,client.open_sftp() as sftp:
        print('Ready: deploy, status, fetch, quit',flush=True)
        while True:
            op=input().strip()
            if op=='quit': break
            try:
                {'deploy':deploy,'status':status,'fetch':fetch}[op](client,sftp)
            except Exception as exc:
                print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
