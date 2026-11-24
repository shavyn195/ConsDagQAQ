"""Deploy and start the CPU-only exploratory alias baseline."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect, upload_file
DEST='/root/ConsDagDiagnostics20261123'
REMOTE=r'''
import datetime,json,os,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
root=Path('/root/ConsDagDiagnostics20261123')
output=root/'outputs/v5_public_binding_20261124.json'
pidfile=root/'outputs/v5_public_binding_20261124_worker.json'
if output.exists():
    print(json.dumps({'status':'already_complete'}))
elif pidfile.exists() and Path('/proc/'+str(json.loads(pidfile.read_text())['pid'])).exists():
    print(json.dumps({'status':'already_running',**json.loads(pidfile.read_text())}))
else:
    args=['nice','-n','10','/root/miniconda3/bin/python','-u','src/evaluate_v5_public_binding.py',
          '--data','/root/ConsDagV5/data/processed_v5','--runs','/root/ConsDagV5/outputs/e1',
          '--out',str(output)]
    for arm in ['Qwen3-1.7B-v5-seed42','Qwen3-1.7B-v5-seed43','Qwen3-4B-v5-seed42','Qwen3-4B-v5-seed43']:
        args+=['--arm',arm]
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (root/'outputs/v5_public_binding_20261124.log').open('ab') as log:
        proc=subprocess.Popen(args,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record={'started_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'pid':proc.pid,'command':args,'output':str(output)}
    pidfile.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))
'''
client=connect()
try:
    with client.open_sftp() as sftp:
        for path in ['src/public_role_binding.py','src/evaluate_v5_public_binding.py','tests/test_public_role_binding.py']:
            upload_file(sftp,ROOT/path,DEST+'/'+path)
    _,out,err=client.exec_command('cd '+DEST+' && PYTHONPATH=.testdeps:src CUDA_VISIBLE_DEVICES= /root/miniconda3/bin/python -m pytest -q tests/test_public_role_binding.py',timeout=60)
    print(out.read().decode()+err.read().decode())
    if out.channel.recv_exit_status(): raise RuntimeError('Tests failed')
    _,out,err=client.exec_command("/root/miniconda3/bin/python - <<'PY'\n"+REMOTE+'\nPY',timeout=30)
    value,error=out.read().decode(),err.read().decode()
    if out.channel.recv_exit_status(): raise RuntimeError(error)
    record=json.loads(value)
    (ROOT/'outputs/v5_analysis/public_binding_deployment_20261124.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(value)
finally:
    client.close()
