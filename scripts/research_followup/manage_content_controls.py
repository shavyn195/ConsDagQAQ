"""Queue matched generic/PE SFT controls after the active GRPO pair."""
from datetime import datetime,timezone
import json
import manage_planner_learning_probe as queue
manager=queue.manager
manager.REMOTE='/root/consdag_audits/matched-generic-pe-planner-sft-20261126-v1'
manager.LOCAL=manager.ROOT/'outputs/matched_content_controls_20261126'
manager.CONFIG='configs/matched_content_controls_20261126.json'
queue.TEST_FILES=['tests/test_matched_content_controls.py','tests/test_shared_planner_sft.py']
queue.SOURCE_FILES+=['shared_planner_sft.py','matched_content_controls.py']
queue.EXTRA_FILES=['tests/smoke_shared_planner_torch.py']
queue.RUN_TORCH_SMOKE=True


def status(client,sftp):
    code='\n'.join(['import json,subprocess','from pathlib import Path','p=Path('+repr(manager.REMOTE)+')',
        'r={n:json.loads((p/n).read_text()) if (p/n).exists() else None for n in ["launch.json","results/waiter_state.json","results/completion.json","results/first_stage_complete.json"]}',
        'for name in ["first_stage_calls.jsonl","calls.jsonl"]:',
        ' f=p/"results"/name;r[name]=sum(1 for _ in f.open()) if f.exists() else 0',
        'r["subruns"]={}',
        'for name in ["generic_sft","pe_sft"]:',
        ' d=p/"results"/name; f=d/"train_steps.jsonl";r["subruns"][name]={"steps":sum(1 for _ in f.open()) if f.exists() else 0}',
        ' f=d/"training.json";r["subruns"][name]["training"]=json.loads(f.read_text()) if f.exists() else None',
        'r["log_tail"]=(p/"run.log").read_text()[-1400:] if (p/"run.log").exists() else ""',
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
                if op=='resume_prelaunch':queue.deploy(client,sftp,resume_prelaunch=True)
                else:{'deploy':queue.deploy,'status':status,'fetch':manager.fetch}[op](client,sftp)
            except Exception as exc:print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
