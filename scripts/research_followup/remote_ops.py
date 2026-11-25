"""Task-scoped deployment; interactive credentials stay in remote_gpu.connect memory."""
import argparse
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from remote_gpu import connect, upload_file, download_tree, digest, remote_digest

REMOTE = '/root/consdag_audits/local-planning-20261126'
CODE = REMOTE+'/code-v2'
PYTHON = '/root/miniconda3/bin/python'


def command(client, text):
    _, out, err = client.exec_command(text)
    stdout = out.read().decode()
    stderr = err.read().decode()
    code = out.channel.recv_exit_status()
    print(stdout, end='')
    if stderr:
        print(stderr, file=sys.stderr, end='')
    if code:
        raise RuntimeError('Remote command failed with exit '+str(code))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['cpu', 'heldout', 'fetch', 'gpu', 'status', 'snapshot', 'verify'])
    a = p.parse_args()
    with connect() as client, client.open_sftp() as sftp:
        if a.action in ('cpu', 'heldout', 'gpu'):
            label = 'cpu-v2' if a.action=='cpu' else a.action
            try:
                sftp.stat(REMOTE+'/'+label+'.launch')
            except FileNotFoundError:
                pass
            else:
                raise ValueError('Launch already exists; inspect its state instead of relaunching')
            files = [f for f in sorted(Path(__file__).parent.glob('*.py')) if f.name != 'remote_ops.py']
            # Never overwrite the code used by an already prepared or active experiment.
            for file in files:
                old = remote_digest(sftp, CODE+'/'+file.name)
                if old is not None and old != digest(file):
                    raise ValueError('Remote code differs: preserve '+CODE+' and use a new versioned experiment')
            for file in files:
                upload_file(sftp, file, CODE+'/'+file.name)
            if a.action in ('cpu', 'heldout'):
                args = [PYTHON, CODE+'/replay.py', '--source','/root/ConsDagSubmissionReview/src',
                    '--data','/root/ConsDagSubmissionReview/data/processed_v5',
                    '--monolithic','/root/ConsDagSubmissionReview/outputs/submission/e2_monolithic_public_contract',
                    '--compiler','/root/ConsDagV5/outputs/e1/Qwen3-1.7B-v5-seed42',
                    '--out', REMOTE+('/cpu-dev-v2' if a.action=='cpu' else '/cpu-heldout')]
                if a.action=='heldout':
                    args += ['--splits','test_tpl_ho','test_tool_ho','test_struct_ho']
            else:
                args = [PYTHON, CODE+'/waiter.py', '--root','/root/ConsDagV6Frozen',
                        '--out', REMOTE+'/gpu-fixed-planner', '--groups','48']
            log = REMOTE+'/'+label+'.log'
            pid = REMOTE+'/'+label+'.pid'
            # Exclusive launch marker prevents duplicate launch; retain failures for inspection.
            command(client, 'mkdir '+shlex.quote(REMOTE+'/'+label+'.launch')+' && { nohup nice -n 15 env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 '+
                    shlex.join(args)+' > '+shlex.quote(log)+' 2>&1 < /dev/null & printf "%s\\n" "$!" > '+shlex.quote(pid)+'; }')
            # The script records its own PID/state; show exact matching process and logs next.
            command(client, 'ps -eo pid,etime,args | grep '+shlex.quote(CODE+'/'+('waiter.py' if a.action=='gpu' else 'replay.py'))+' | grep -v grep')
        elif a.action == 'fetch':
            for name in ('cpu-dev', 'cpu-dev-v2', 'cpu-heldout', 'gpu-fixed-planner'):
                try:
                    sftp.stat(REMOTE+'/'+name)
                except OSError:
                    continue
                download_tree(sftp, REMOTE+'/'+name, ROOT/'outputs/local_planning_20261126'/name)
            for name in ('metrics.json','completion.json','provenance.json'):
                download_tree(sftp, '/root/ConsDagV6Frozen/outputs/e1_v6/Qwen3-4B-v6-seed43/'+name,
                              ROOT/'outputs/local_planning_20261126/v6-4b-seed43'/name)
        elif a.action == 'verify':
            from datetime import datetime, timezone
            code = '\n'.join([
                'import hashlib,json',
                'from pathlib import Path',
                'root=Path('+repr(REMOTE)+')',
                'files={}',
                'for folder in ("cpu-dev","cpu-dev-v2","cpu-heldout"):',
                '    for f in (root/folder).iterdir():',
                '        if f.is_file(): files[str(f.relative_to(root))]=hashlib.sha256(f.read_bytes()).hexdigest()',
                'f=root/"gpu-fixed-planner/protocol.json"',
                'files[str(f.relative_to(root))]=hashlib.sha256(f.read_bytes()).hexdigest()',
                'for name in ("metrics.json","completion.json","provenance.json"):',
                '    f=Path("/root/ConsDagV6Frozen/outputs/e1_v6/Qwen3-4B-v6-seed43")/name',
                '    files["v6-4b-seed43/"+name]=hashlib.sha256(f.read_bytes()).hexdigest()',
                'print(json.dumps(files))',
            ])
            _, out, err = client.exec_command(shlex.join([PYTHON,'-c',code]))
            raw, error = out.read().decode(), err.read().decode()
            if out.channel.recv_exit_status():
                raise RuntimeError(error)
            remote_hashes = json.loads(raw)
            local_root = ROOT/'outputs/local_planning_20261126'
            matched = {name: digest(local_root/name)==value for name,value in remote_hashes.items()}
            record = dict(observed_at_utc=datetime.now(timezone.utc).isoformat(),
                          remote_sha256=remote_hashes, matched=matched, all_match=all(matched.values()))
            (local_root/'receipt_verification.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
            if not record['all_match']:
                raise ValueError('Downloaded artifacts differ from remote: '+str([k for k,v in matched.items() if not v]))
            print(json.dumps(dict(verified_files=len(matched), all_match=True)))
        elif a.action == 'snapshot':
            from datetime import datetime, timezone
            snapshot = {'observed_at_utc': datetime.now(timezone.utc).isoformat()}
            for label, remote in {
                'original_queue': '/root/ConsDagV6Frozen/outputs/e1_v6/queue_state.json',
                'waiter': REMOTE+'/gpu-fixed-planner/waiter_state.json',
            }.items():
                with sftp.open(remote) as handle:
                    snapshot[label] = json.load(handle)
            commands = {
                'gpu': 'nvidia-smi --query-gpu=timestamp,name,utilization.gpu,memory.used,memory.total --format=csv,noheader',
                'waiter_process': 'ps -p '+str(int(snapshot['waiter']['pid']))+' -o pid=,etime=,args=',
                'heldout_log': 'tail -n 2 '+shlex.quote(REMOTE+'/heldout.log'),
            }
            for label, text in commands.items():
                _, out, err = client.exec_command(text)
                snapshot[label] = {'stdout': out.read().decode(), 'stderr': err.read().decode(),
                                   'exit_code': out.channel.recv_exit_status()}
            snapshot['source_sha256'] = {
                name: remote_digest(sftp, '/root/ConsDagV6Frozen/src/'+name)
                for name in ('run_e1_v6.py','eval_exec_v6.py','eval_exec.py','dataset_v5_spec.py','run_v6_relay.py')
            }
            target = ROOT/'outputs/local_planning_20261126/runtime_snapshot.json'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(snapshot,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({k:v for k,v in snapshot.items() if k!='heldout_log'},indent=2))
        else:
            command(client, 'date -Is; nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader; cat /root/ConsDagV6Frozen/outputs/e1_v6/queue_state.json; tail -n 8 '+REMOTE+'/cpu-v2.log; test ! -e '+REMOTE+'/gpu.log || tail -n 8 '+REMOTE+'/gpu.log')


if __name__ == '__main__':
    main()
