"""Recover completed CPU binding results and a compact live GPU status."""
import hashlib
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect, remote_digest
parser=argparse.ArgumentParser()
parser.add_argument('--pe',action='store_true')
args=parser.parse_args()
suffix='_pe' if args.pe else ''
client=connect()
try:
    with client.open_sftp() as sftp:
        remote='/root/ConsDagDiagnostics20261123/outputs/v5_public_binding'+suffix+'_20261124.json'
        try:
            sftp.stat(remote)
        except OSError:
            with sftp.open(remote[:-5]+'.log') as f:
                print(f.read().decode('utf-8','replace')[-2500:])
        else:
            local=ROOT/('outputs/v5_analysis/public_binding'+suffix+'_20261124.json')
            sftp.get(remote,str(local))
            if hashlib.sha256(local.read_bytes()).hexdigest()!=remote_digest(sftp,remote):
                raise ValueError('Binding analysis hash mismatch')
            result=json.loads(local.read_text(encoding='utf-8'))
            for a,splits in result['arms'].items():
                for s,x in splits.items():
                    print(json.dumps({'arm':a,'split':s,'status':x['status'],**({
                        'edited_records':x['edited_records'],'faithful':x['faithful'],
                        'none_fp_delta':x['none_false_positive']['difference'],
                        'none_deviation_delta':x['none_deviation']['difference']}
                        if 'faithful' in x else {})}))
    script=r'''
import datetime,json,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
root=Path('/root/ConsDagV5')
run=root/'outputs/e1/Qwen3-4B-v5-seed43'
status={'checked_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
 'gpu':subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True).stdout.strip(),
 '4b43_final_metrics':(run/'metrics.json').is_file(),
 '4b43_log_tail':(run.parent/(run.name+'.log')).read_text().splitlines()[-4:],
 'queue_tail':(root/'outputs/e1_v5_queue_manifest.jsonl').read_text().splitlines()[-3:]}
print(json.dumps(status))
'''
    _,out,err=client.exec_command("/root/miniconda3/bin/python - <<'PY'\n"+script+'\nPY',timeout=30)
    value,error=out.read().decode(),err.read().decode()
    if out.channel.recv_exit_status(): raise RuntimeError(error)
    status=json.loads(value)
    (ROOT/'outputs/v5_analysis/gpu_progress_20261124.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    print(value)
finally:
    client.close()
