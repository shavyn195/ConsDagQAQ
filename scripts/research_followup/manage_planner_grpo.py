"""Deploy and monitor a bounded actual GRPO pair after matched SFT completion."""
from contextlib import redirect_stdout
from datetime import datetime,timezone
import io
import json
import zipfile
import manage_shared_planner_sft as manager
from remote_gpu import upload_file,digest

manager.REMOTE='/root/consdag_audits/raw-contract-planner-grpo-20261126-v1'
manager.LOCAL=manager.ROOT/'outputs/matched_planner_grpo_20261126'
manager.CONFIG='configs/matched_planner_grpo_20261126.json'
SOURCES=['common.py','fixed_planner.py','structure_supplement.py','format_recovery.py',
    'shared_planner_sft.py','planner_reward_probe.py','planner_learning_probe.py','audit_comparison_signal.py',
    'wait_shared_planner_sft.py','planner_grpo_core.py','matched_planner_grpo.py']


def deploy(client,sftp,resume_prelaunch=False):
    remote,root=manager.REMOTE,manager.ROOT
    if resume_prelaunch:
        guard='from pathlib import Path; p=Path('+repr(remote)+'); assert p.is_dir(); assert not (p/"launch.json").exists(); assert not (p/"run.log").exists(); assert not (p/"results/protocol.json").exists(); print("prelaunch-only recovery confirmed")'
        manager.command(client,[manager.PYTHON,'-c',guard])
    else:sftp.mkdir(remote)
    paths=[manager.CONFIG,'tests/test_planner_grpo.py','tests/smoke_planner_grpo_torch.py']+['scripts/research_followup/'+n for n in SOURCES]
    for name in paths:
        with redirect_stdout(io.StringIO()):upload_file(sftp,root/name,remote+'/'+name)
    env=['env','CUDA_VISIBLE_DEVICES=','OMP_NUM_THREADS=1',
        'PYTHONPATH=/root/ConsDagV6Frozen/src:/root/ConsDagSubmissionReview/src',manager.PYTHON]
    code='import runpy; m=runpy.run_path('+repr(remote+'/tests/test_planner_grpo.py')+'); fs=[f for n,f in m.items() if n.startswith("test_")]; [f() for f in fs]; print("PASS",len(fs))'
    tests=manager.command(client,env+['-c',code])
    smoke=manager.command(client,env+[remote+'/tests/smoke_planner_grpo_torch.py'])
    args=[manager.PYTHON,remote+'/scripts/research_followup/wait_shared_planner_sft.py',
        '--root','/root/ConsDagV6Frozen','--out',remote+'/results','--config',remote+'/'+manager.CONFIG]
    code='\n'.join(['import subprocess,json','from pathlib import Path','p=Path('+repr(remote)+')',
        'log=(p/"run.log").open("x")','child=subprocess.Popen('+repr(args)+',stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)',
        '(p/"launch.json").write_text(json.dumps(dict(pid=child.pid,args='+repr(args)+')))',
        'print(json.dumps(dict(waiter_pid=child.pid)))'])
    launch=json.loads(manager.command(client,[manager.PYTHON,'-c',code]))
    manager.LOCAL.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(manager.LOCAL/'run_source_bytes.zip','w',zipfile.ZIP_DEFLATED) as z:
        for n in paths:z.write(root/n,n)
    record=dict(utc=datetime.now(timezone.utc).isoformat(),remote=remote,tests=tests,torch_smoke=smoke,launch=launch,
        preflight='CPU analytic and tiny-model checks passed; complete matched parent, cache/data/checkpoint hashes and every prompt length checked before GPU load by worker after exclusive lock.',
        source_sha256={n:digest(root/n) for n in paths})
    (manager.LOCAL/'deployment.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)


def status(client,sftp):
    code='\n'.join(['import json,subprocess','from pathlib import Path','p=Path('+repr(manager.REMOTE)+')',
        'r={n:json.loads((p/n).read_text()) if (p/n).exists() else None for n in ["launch.json","results/waiter_state.json","results/completion.json"]}',
        'f=p/"results/calls.jsonl";r["eval_calls"]=sum(1 for _ in f.open()) if f.exists() else 0',
        'r["subruns"]={}',
        'for name in ["raw_grpo","contract_grpo"]:',
        ' d=p/"results"/name; r["subruns"][name]={}',
        ' for n in ["train_steps.jsonl","rollouts.jsonl"]:',
        '  f=d/n;r["subruns"][name][n]=sum(1 for _ in f.open()) if f.exists() else 0',
        ' f=d/"training.json";r["subruns"][name]["training"]=json.loads(f.read_text()) if f.exists() else None',
        'r["log_tail"]=(p/"run.log").read_text()[-1800:] if (p/"run.log").exists() else ""',
        'r["gpu"]=subprocess.run(["nvidia-smi","--query-gpu=timestamp,utilization.gpu,memory.used","--format=csv,noheader"],capture_output=True,text=True).stdout',
        'print(json.dumps(r))'])
    record=dict(utc=datetime.now(timezone.utc).isoformat(),**json.loads(manager.command(client,[manager.PYTHON,'-c',code])))
    manager.LOCAL.mkdir(parents=True,exist_ok=True);(manager.LOCAL/'status.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)


if __name__=='__main__':
    with manager.connect() as client,client.open_sftp() as sftp:
        print('Ready: deploy, resume_prelaunch, status, fetch, quit',flush=True)
        while True:
            op=input().strip()
            if op=='quit':break
            try:
                if op=='resume_prelaunch':deploy(client,sftp,True)
                else:{'deploy':deploy,'status':status,'fetch':manager.fetch}[op](client,sftp)
            except Exception as exc:print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
