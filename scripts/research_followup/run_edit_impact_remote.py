"""Run the bounded CPU probe in a new isolated directory and verify receipts."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shlex
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect, mkdirs, upload_file, download_tree, digest, remote_digest

REMOTE='/root/consdag_audits/edit-impact-20261126-v3'
PYTHON='/root/miniconda3/bin/python'


def main():
    with connect() as client, client.open_sftp() as sftp:
        with redirect_stdout(io.StringIO()):
            download_tree(sftp,'/root/consdag_audits/edit-impact-20261126/completion.json',
                          ROOT/'outputs/edit_impact_probe_20261126/first_attempt_failure.json')
        # mkdir is exclusive: failed/finished launches remain reviewable.
        sftp.mkdir(REMOTE)
        paths=[Path('src')/n for n in ('run_e1.py','trust_env.py','dataset_v5_spec.py')]
        paths += [Path('scripts/research_followup')/n for n in ('common.py','audit_history.py','probe_edit_impact.py')]
        paths += [Path('reports/edit_impact_probe_protocol_20261126.md'),Path('reports/edit_impact_abstention_protocol_20261126.md'),Path('outputs/history_audit_20261126/summary.json')]
        manifest={str(p):digest(ROOT/p) for p in paths}
        with redirect_stdout(io.StringIO()):
            for p in paths:
                upload_file(sftp,ROOT/p,REMOTE+'/'+p.as_posix())
        print('Uploaded and SHA256-verified '+str(len(paths))+' probe files.',flush=True)
        with sftp.open(REMOTE+'/launch_manifest.json','w') as f:
            f.write(json.dumps(dict(created_utc=datetime.now(timezone.utc).isoformat(),sha256=manifest)))
        args=['timeout','300s','nice','-n','15','env','OMP_NUM_THREADS=1','MKL_NUM_THREADS=1','OPENBLAS_NUM_THREADS=1',
              PYTHON,REMOTE+'/scripts/research_followup/probe_edit_impact.py',
              '--data','/root/ConsDagSubmissionReview/data/processed_v5',
              '--compilers','/root/ConsDagV5/outputs/e1',
              '--replay','/root/consdag_audits/local-planning-20261126',
              '--prior',REMOTE+'/outputs/history_audit_20261126/summary.json',
              '--out',REMOTE+'/results']
        _,out,err=client.exec_command(shlex.join(args))
        stdout=out.read().decode();stderr=err.read().decode();code=out.channel.recv_exit_status()
        print(stdout,flush=True)
        with sftp.open(REMOTE+'/completion.json','w') as f:
            f.write(json.dumps(dict(exit_code=code,stdout=stdout,stderr=stderr,completed_utc=datetime.now(timezone.utc).isoformat())))
        if code:
            raise RuntimeError('Probe failed: '+stderr)
        local=ROOT/'outputs/edit_impact_probe_20261126_v3'
        with redirect_stdout(io.StringIO()):
            download_tree(sftp,REMOTE+'/results',local)
            download_tree(sftp,REMOTE+'/completion.json',local/'completion.json')
            download_tree(sftp,REMOTE+'/launch_manifest.json',local/'launch_manifest.json')
        receipts={p.name:remote_digest(sftp,REMOTE+'/results/'+p.name) for p in local.iterdir() if p.name in ('summary.json','per_sample.jsonl')}
        if any(digest(local/n)!=h for n,h in receipts.items()):
            raise ValueError('Remote receipt mismatch')
        (local/'receipt.json').write_text(json.dumps(receipts,indent=2),encoding='utf-8')
        print('Completed; downloaded results match server hashes.',flush=True)
        snapshot={'observed_utc':datetime.now(timezone.utc).isoformat()}
        for label,path in {
            'queue':'/root/ConsDagV6Frozen/outputs/e1_v6/queue_state.json',
            'waiter':'/root/consdag_audits/local-planning-20261126/gpu-fixed-planner/waiter_state.json'
        }.items():
            with sftp.open(path) as f:
                snapshot[label]=json.load(f)
        commands={
            'gpu':'nvidia-smi --query-gpu=timestamp,name,utilization.gpu,memory.used,memory.total --format=csv,noheader',
            'processes':"ps -eo pid,etime,args | grep -E 'run_e1_v6.py|waiter.py|fixed_planner.py' | grep -v grep"
        }
        for label,command in commands.items():
            _,out,err=client.exec_command(command)
            snapshot[label]=dict(stdout=out.read().decode(),stderr=err.read().decode(),exit_code=out.channel.recv_exit_status())
        (local/'runtime_snapshot.json').write_text(json.dumps(snapshot,indent=2),encoding='utf-8')
        print(json.dumps(snapshot),flush=True)


if __name__=='__main__':
    main()
