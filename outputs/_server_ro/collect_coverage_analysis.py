"""Recover completed audit evidence and completed 4B splits with SHA checks."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from remote_gpu import connect, remote_digest

client = connect()
try:
    with client.open_sftp() as sftp:
        output='/root/ConsDagDiagnostics20261123/outputs/v5_coverage_20261124.json'
        try:
            sftp.stat(output)
        except OSError:
            with sftp.open('/root/ConsDagDiagnostics20261123/outputs/v5_coverage_20261124.log') as f:
                print(f.read().decode('utf-8','replace')[-4000:])
        else:
            local=ROOT/'outputs/v5_analysis/coverage_20261124.json'
            sftp.get(output,str(local))
            if hashlib.sha256(local.read_bytes()).hexdigest() != remote_digest(sftp,output):
                raise ValueError('Audit transfer hash mismatch')
            report=json.loads(local.read_text(encoding='utf-8'))
            print(json.dumps({'coverage':{s:{k:v for k,v in r.items() if k in ('groups','constraint_count_per_group','groups_with_unseen_type_combination','roles_unseen_in_training_catalog','directed_role_pairs')} for s,r in report['coverage'].items()},
                              'arms':{a:{s:{k:v for k,v in r.items() if k not in ('failure_examples','prediction_sha256')}
                                         for s,r in info['splits'].items()} for a,info in report['arms'].items()},
                              'token_budgets':report['token_budgets']},ensure_ascii=False))
        run='outputs/e1/Qwen3-4B-v5-seed43'
        transfer={}
        for relative in ['metrics.json','trained_predictions/dev.jsonl','trained_predictions/test_tpl_ho.jsonl',
                         'trained_predictions/test_tool_ho.jsonl','trained_predictions/test_struct_ho.jsonl']:
            remote='/root/ConsDagV5/'+run+'/'+relative
            try:
                sftp.stat(remote)
            except OSError:
                continue
            local=ROOT/run/relative
            local.parent.mkdir(parents=True,exist_ok=True)
            sftp.get(remote,str(local))
            digest=hashlib.sha256(local.read_bytes()).hexdigest()
            if digest != remote_digest(sftp,remote):
                raise ValueError('4B transfer hash mismatch')
            transfer[relative]={'bytes':local.stat().st_size,'sha256':digest}
        (ROOT/'outputs/v5_analysis/4b43_recovery_20261124.json').write_text(json.dumps(transfer,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'recovered_4b43':transfer}))
finally:
    client.close()
