"""Run the existing frozen CPU audit on newly completed arms and recover it."""
import hashlib
import json
from pathlib import Path
import shlex
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from remote_gpu import connect, remote_digest

DEST = '/root/ConsDagDiagnostics20261123'
NAME = 'coverage_newseeds_20261124'
client = connect()
try:
    with client.open_sftp() as sftp:
        for rel in ['src/audit_v5_coverage.py', 'src/public_scope_binding.py',
                    'src/audit_v5_measurement.py', 'src/trust_env.py', 'src/run_e1.py',
                    'src/rescore_v4_side.py']:
            if remote_digest(sftp, DEST + '/' + rel) != hashlib.sha256((ROOT / rel).read_bytes()).hexdigest():
                raise ValueError('Frozen source mismatch: ' + rel)
        try:
            sftp.stat(DEST + '/outputs/' + NAME + '.json')
            complete = True
        except OSError:
            complete = False
    if not complete:
        args = ['nice', '-n', '10', '/root/miniconda3/bin/python', '-u',
                'src/audit_v5_coverage.py', '--data', '/root/ConsDagV5/data/processed_v5',
                '--runs', '/root/ConsDagV5/outputs/e1',
                '--arm', 'Qwen3-1.7B-v5-seed44', '--arm', 'Qwen3-4B-v5-seed43',
                '--out', 'outputs/' + NAME + '.json']
        command = ('cd ' + shlex.quote(DEST)
                   + ' && CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 '
                   + shlex.join(args) + ' > outputs/' + NAME + '.log 2>&1')
        _, stdout, stderr = client.exec_command(command, timeout=180)
        stdout.read()
        error = stderr.read().decode('utf-8', 'replace')
        if stdout.channel.recv_exit_status():
            raise RuntimeError('Remote audit failed; inspect saved log. ' + error)
    with client.open_sftp() as sftp:
        remote = DEST + '/outputs/' + NAME + '.json'
        local = ROOT / 'outputs/v5_analysis' / (NAME + '.json')
        sftp.get(remote, str(local))
        if hashlib.sha256(local.read_bytes()).hexdigest() != remote_digest(sftp, remote):
            raise ValueError('Transfer hash mismatch')
    result = json.loads(local.read_text(encoding='utf-8'))
    print(json.dumps({arm: {split: data['flags_among_faithful_failures']
                           for split, data in body['splits'].items()}
                      for arm, body in result['arms'].items()}, ensure_ascii=False))
finally:
    client.close()
