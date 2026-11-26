"""Queue a sampled diagnostic after the completed shared planner evaluation."""
from contextlib import redirect_stdout
from datetime import datetime,timezone
import io
import json
import zipfile
import manage_shared_planner_sft as manager
from remote_gpu import upload_file,digest

manager.REMOTE='/root/consdag_audits/planner-learning-signal-20261126-v2'
manager.LOCAL=manager.ROOT/'outputs/planner_learning_signal_20261126'
manager.CONFIG='configs/planner_learning_probe_20261126.json'
TEST_FILES=['tests/test_planner_learning_probe.py','tests/test_comparison_signal.py']
SOURCE_FILES=['common.py','fixed_planner.py','structure_supplement.py','format_recovery.py',
    'planner_reward_probe.py','planner_learning_probe.py','audit_comparison_signal.py','wait_shared_planner_sft.py']
EXTRA_FILES=[]
RUN_TORCH_SMOKE=False

def deploy(client,sftp,resume_prelaunch=False):
    remote,root=manager.REMOTE,manager.ROOT
    if resume_prelaunch:
        code='from pathlib import Path; p=Path('+repr(remote)+'); assert p.is_dir(); assert not (p/"launch.json").exists(); assert not (p/"run.log").exists(); assert not (p/"results/protocol.json").exists(); print("prelaunch-only recovery confirmed")'
        manager.command(client,[manager.PYTHON,'-c',code])
    else:
        sftp.mkdir(remote)
    paths=[manager.CONFIG]+TEST_FILES+EXTRA_FILES+['scripts/research_followup/'+n for n in SOURCE_FILES]
    for n in paths:
        with redirect_stdout(io.StringIO()): upload_file(sftp,root/n,remote+'/'+n)
    code='import runpy; fs=[]; '+ '; '.join('fs.extend(f for n,f in runpy.run_path('+repr(remote+'/'+n)+').items() if n.startswith("test_"))' for n in TEST_FILES)+'; [f() for f in fs]; print("PASS",len(fs))'
    tests=manager.command(client,['env','CUDA_VISIBLE_DEVICES=','OMP_NUM_THREADS=1',
        'PYTHONPATH=/root/ConsDagV6Frozen/src:/root/ConsDagSubmissionReview/src',manager.PYTHON,'-c',code])
    torch_smoke=None
    if RUN_TORCH_SMOKE:
        torch_smoke=manager.command(client,['env','CUDA_VISIBLE_DEVICES=','OMP_NUM_THREADS=1',
            'PYTHONPATH=/root/ConsDagV6Frozen/src:/root/ConsDagSubmissionReview/src',manager.PYTHON,
            remote+'/tests/smoke_shared_planner_torch.py','--config',remote+'/'+manager.CONFIG])
    args=[manager.PYTHON,remote+'/scripts/research_followup/wait_shared_planner_sft.py','--root','/root/ConsDagV6Frozen',
        '--out',remote+'/results','--config',remote+'/'+manager.CONFIG]
    code='\n'.join(['import subprocess,json','from pathlib import Path','p=Path('+repr(remote)+')',
        'log=(p/"run.log").open("x")','child=subprocess.Popen('+repr(args)+',stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)',
        '(p/"launch.json").write_text(json.dumps(dict(pid=child.pid,args='+repr(args)+')))',
        'print(json.dumps(dict(waiter_pid=child.pid)))'])
    launch=json.loads(manager.command(client,[manager.PYTHON,'-c',code]))
    manager.LOCAL.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(manager.LOCAL/'run_source_bytes.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in paths: z.write(root/n,n)
    record=dict(utc=datetime.now(timezone.utc).isoformat(),tests=tests,torch_smoke=torch_smoke,launch=launch,remote=remote,
        preflight='Data/model/final-adapter hashes and all prompt lengths are checked by worker before GPU load; deferred until final adapter and parent completion exist.',
        source_sha256={n:digest(root/n) for n in paths})
    (manager.LOCAL/'deployment.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)

if __name__=='__main__':
    with manager.connect() as client,client.open_sftp() as sftp:
        print('Ready: deploy, status, fetch, quit',flush=True)
        while True:
            op=input().strip()
            if op=='quit': break
            try: {'deploy':deploy,'status':manager.status,'fetch':manager.fetch}[op](client,sftp)
            except Exception as exc: print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
