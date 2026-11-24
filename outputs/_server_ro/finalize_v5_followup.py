"""Recover multi-seed statistics; measure the frozen binder on newly completed runs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect,remote_digest
parser=argparse.ArgumentParser()
parser.add_argument('--start-binding',action='store_true')
args=parser.parse_args()
DEST='/root/ConsDagDiagnostics20261123'
client=connect()
try:
    if args.start_binding:
        remote=r'''
import datetime,json,os,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
root=Path('/root/ConsDagDiagnostics20261123')
out=root/'outputs/v5_binding_newseeds_20261124.json'
pidfile=root/'outputs/v5_binding_newseeds_20261124_worker.json'
if out.exists():
    print(json.dumps({'status':'already_complete'}))
elif pidfile.exists() and Path('/proc/'+str(json.loads(pidfile.read_text())['pid'])).exists():
    print(json.dumps({'status':'already_running'}))
else:
    args=['nice','-n','10','/root/miniconda3/bin/python','-u','src/evaluate_v5_public_binding.py',
          '--data','/root/ConsDagV5/data/processed_v5','--runs','/root/ConsDagV5/outputs/e1',
          '--arm','Qwen3-1.7B-v5-seed44','--arm','Qwen3-4B-v5-seed43','--out',str(out)]
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (root/'outputs/v5_binding_newseeds_20261124.log').open('ab') as log:
        proc=subprocess.Popen(args,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record={'started_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'pid':proc.pid,'command':args}
    pidfile.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))
'''
        _,out,err=client.exec_command("/root/miniconda3/bin/python - <<'PY'\n"+remote+'\nPY',timeout=30)
        value,error=out.read().decode(),err.read().decode()
        if out.channel.recv_exit_status():raise RuntimeError(error)
        print(value)
    with client.open_sftp() as sftp:
        for name in ['v5_main_0530_20261124','v5_binding_newseeds_20261124']:
            remote=DEST+'/outputs/'+name+'.json'
            try:
                sftp.stat(remote)
            except OSError:
                try:
                    with sftp.open(DEST+'/outputs/'+name+'.log') as f:
                        print(name, 'PENDING', f.read().decode('utf-8','replace')[-1200:])
                except OSError:
                    print(name,'NOT_STARTED')
                continue
            local=ROOT/'outputs/v5_analysis'/(name+'.json')
            sftp.get(remote,str(local))
            if hashlib.sha256(local.read_bytes()).hexdigest()!=remote_digest(sftp,remote):
                raise ValueError('Analysis transfer mismatch')
            r=json.loads(local.read_text(encoding='utf-8'))
            if 'decisions' in r:
                print(json.dumps({'table':{a:v for a,v in r['table'].items() if 'LoRA' in a},
                    'H2_1.7B':r['decisions']['H2_noninferiority_vs_deepseek_1.7B'],
                    'H2_4B':r['decisions']['H2_noninferiority_vs_deepseek_4B']},ensure_ascii=False))
            else:
                print(json.dumps({a:{s:{'faithful':v['faithful'],'none_deviation':v['none_deviation']['difference']}
                    for s,v in splits.items()} for a,splits in r['arms'].items()},ensure_ascii=False))
finally:
    client.close()
