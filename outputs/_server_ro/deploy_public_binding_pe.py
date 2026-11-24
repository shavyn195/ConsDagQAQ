"""Apply the same frozen public-name binder to cached strong-model predictions."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect, upload_file
DEST='/root/ConsDagDiagnostics20261123'
ARMS=['deepseek-v4-pro-0813-few','qwen-max-zero','qwen-max-few']
client=connect()
try:
    with client.open_sftp() as sftp:
        for rel in ['src/evaluate_v5_public_binding.py','tests/test_public_role_binding.py']:
            upload_file(sftp,ROOT/rel,DEST+'/'+rel)
        for arm in ARMS:
            for split in ['dev','test_tpl_ho','test_tool_ho','test_struct_ho']:
                local=ROOT/'outputs/e1_v5_side'/arm/(split+'.jsonl')
                upload_file(sftp,local,DEST+'/inputs/v5_pe_frozen/'+arm+'/'+split+'.jsonl')
    _,out,err=client.exec_command('cd '+DEST+' && CUDA_VISIBLE_DEVICES= PYTHONPATH=.testdeps:src /root/miniconda3/bin/python -m pytest -q tests/test_public_role_binding.py',timeout=60)
    print(out.read().decode()+err.read().decode())
    if out.channel.recv_exit_status(): raise RuntimeError('Remote tests failed')
    remote=r'''
import datetime,json,os,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
root=Path('/root/ConsDagDiagnostics20261123')
out=root/'outputs/v5_public_binding_pe_20261124.json'
pidfile=root/'outputs/v5_public_binding_pe_20261124_worker.json'
if out.exists():
    print(json.dumps({'status':'already_completed'}))
elif pidfile.exists() and Path('/proc/'+str(json.loads(pidfile.read_text())['pid'])).exists():
    print(json.dumps({'status':'already_running'}))
else:
    args=['nice','-n','10','/root/miniconda3/bin/python','-u','src/evaluate_v5_public_binding.py',
          '--data','/root/ConsDagV5/data/processed_v5','--runs','inputs/v5_pe_frozen',
          '--flat-predictions','--out',str(out)]
    for arm in ['deepseek-v4-pro-0813-few','qwen-max-zero','qwen-max-few']:
        args+=['--arm',arm]
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (root/'outputs/v5_public_binding_pe_20261124.log').open('ab') as log:
        p=subprocess.Popen(args,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record={'started_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'pid':p.pid,'command':args,'output':str(out)}
    pidfile.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))
'''
    _,out,err=client.exec_command("/root/miniconda3/bin/python - <<'PY'\n"+remote+'\nPY',timeout=30)
    result,error=out.read().decode(),err.read().decode()
    if out.channel.recv_exit_status(): raise RuntimeError(error)
    record=json.loads(result)
    (ROOT/'outputs/v5_analysis/public_binding_pe_deployment_20261124.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(result)
finally:
    client.close()
