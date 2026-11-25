"""Launch the isolated, single-thread CPU probe; preserve code and output hashes."""
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

REMOTE = '/root/consdag_audits/partial-contract-20261126-v1'
PYTHON = '/root/miniconda3/bin/python'
PROTOCOL = 'reports/partial_contract_probe_protocol_20261126.md'


def main():
    with connect() as client, client.open_sftp() as sftp:
        sftp.mkdir(REMOTE)  # Exclusive: never overwrite a failed or finished probe.
        paths = ['src/run_e1.py', 'src/trust_env.py', 'src/dataset_v5_spec.py', PROTOCOL]
        paths += ['scripts/research_followup/'+name for name in ('common.py', 'partial_contract.py', 'probe_partial_contract.py')]
        manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                        sha256={p: digest(ROOT/p) for p in paths}, base_commit='451844f')
        with redirect_stdout(io.StringIO()):
            for p in paths:
                upload_file(sftp, ROOT/p, REMOTE+'/'+p)
        with sftp.open(REMOTE+'/launch_manifest.json', 'w') as stream:
            stream.write(json.dumps(manifest))
        print('Uploaded and verified isolated CPU probe.', flush=True)
        args = ['timeout', '120s', 'nice', '-n', '15', 'env', 'OMP_NUM_THREADS=1', 'MKL_NUM_THREADS=1', 'OPENBLAS_NUM_THREADS=1',
                PYTHON, REMOTE+'/scripts/research_followup/probe_partial_contract.py',
                '--protocol', REMOTE+'/'+PROTOCOL, '--out', REMOTE+'/results']
        _, out, err = client.exec_command(shlex.join(args))
        stdout, stderr = out.read().decode(), err.read().decode()
        code = out.channel.recv_exit_status()
        with sftp.open(REMOTE+'/completion.json', 'w') as stream:
            stream.write(json.dumps(dict(exit_code=code, stdout=stdout, stderr=stderr,
                                        completed_utc=datetime.now(timezone.utc).isoformat())))
        local = ROOT/'outputs/partial_contract_probe_20261126'
        with redirect_stdout(io.StringIO()):
            download_tree(sftp, REMOTE+'/completion.json', local/'completion.json')
            download_tree(sftp, REMOTE+'/launch_manifest.json', local/'launch_manifest.json')
            if code == 0:
                download_tree(sftp, REMOTE+'/results', local)
        if code:
            raise RuntimeError('Remote probe failed; receipt preserved: '+stderr)
        receipt = {name: remote_digest(sftp, REMOTE+'/results/'+name) for name in ('summary.json', 'inputs.jsonl', 'per_condition.jsonl')}
        if any(digest(local/name) != h for name, h in receipt.items()):
            raise ValueError('Downloaded probe hash mismatch')
        (local/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
        print(stdout, end='', flush=True)
        print('All downloaded results match server SHA256.', flush=True)
        # A single read-only snapshot; no queue, job, or GPU-lock mutations.
        snapshot = dict(observed_utc=datetime.now(timezone.utc).isoformat())
        for label, path in {
            'queue': '/root/ConsDagV6Frozen/outputs/e1_v6/queue_state.json',
            'waiter': '/root/consdag_audits/local-planning-20261126/gpu-fixed-planner/waiter_state.json'
        }.items():
            with sftp.open(path) as stream:
                snapshot[label] = json.load(stream)
        _, out, err = client.exec_command('nvidia-smi --query-gpu=timestamp,name,utilization.gpu,memory.used,memory.total --format=csv,noheader')
        snapshot['gpu'] = dict(stdout=out.read().decode(), stderr=err.read().decode(), exit_code=out.channel.recv_exit_status())
        (local/'runtime_snapshot.json').write_text(json.dumps(snapshot, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(dict(observed_utc=snapshot['observed_utc'], gpu=snapshot['gpu'],
                             queue_status=snapshot['queue'].get('status'), waiter_status=snapshot['waiter'].get('status'))))


if __name__ == '__main__':
    main()
