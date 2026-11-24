"""Recover newly complete runs and start an isolated CPU multi-seed analysis."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect, remote_digest, upload_file
DEST='/root/ConsDagDiagnostics20261123'
ARMS=['Qwen3-4B-v5-seed43','Qwen3-1.7B-v5-seed44']
client=connect()
try:
    recovered={}
    with client.open_sftp() as sftp:
        for arm in ARMS:
            run='outputs/e1/'+arm
            sftp.stat('/root/ConsDagV5/'+run+'/metrics.json')
            for relative in ['metrics.json','trained_predictions/dev.jsonl','trained_predictions/test_tpl_ho.jsonl',
                             'trained_predictions/test_tool_ho.jsonl','trained_predictions/test_struct_ho.jsonl']:
                remote='/root/ConsDagV5/'+run+'/'+relative
                local=ROOT/run/relative
                local.parent.mkdir(parents=True,exist_ok=True)
                wanted=remote_digest(sftp,remote)
                if not local.exists() or hashlib.sha256(local.read_bytes()).hexdigest()!=wanted:
                    sftp.get(remote,str(local))
                digest=hashlib.sha256(local.read_bytes()).hexdigest()
                if digest!=wanted: raise ValueError('Recovery hash mismatch '+relative)
                recovered[arm+'/'+relative]=digest
            size,seed=arm.split('-v5-seed')
            relative='outputs/e1_v5_side/trained-'+size+'-seed'+seed+'.json'
            remote='/root/ConsDagV5/'+relative
            local=ROOT/relative
            sftp.get(remote,str(local))
            digest=hashlib.sha256(local.read_bytes()).hexdigest()
            if digest!=remote_digest(sftp,remote): raise ValueError('Side result hash mismatch')
            recovered[relative]=digest
            side=json.loads(local.read_text(encoding='utf-8'))
            print(json.dumps({'arm':arm,'splits':{s:{'faithful':x['side_v1']['constrained']['faithful_success'],
                 'strict_f1':x['v5']['constraint_micro']['f1'],'core_f1':x['v5']['constraint_core_micro']['f1']}
                 for s,x in side.items()}}))
        for relative in ['src/analyze_v5_main.py']:
            upload_file(sftp,ROOT/relative,DEST+'/'+relative)
        for arm in ['deepseek-v4-pro-0813-few','qwen-max-zero','qwen-max-few']:
            upload_file(sftp,ROOT/'outputs/e1_v5_side'/arm/'full-scores.json',
                        DEST+'/inputs/v5_pe_frozen/'+arm+'/full-scores.json')
    (ROOT/'outputs/v5_analysis/recovery_0530_20261124.json').write_text(json.dumps(recovered,indent=2)+'\n',encoding='utf-8')
    script=r'''
import datetime,json,os,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
root=Path('/root/ConsDagDiagnostics20261123')
out=root/'outputs/v5_main_0530_20261124.json'
pidfile=root/'outputs/v5_main_0530_20261124_worker.json'
if out.exists():
    print(json.dumps({'status':'already_complete'}))
elif pidfile.exists() and Path('/proc/'+str(json.loads(pidfile.read_text())['pid'])).exists():
    print(json.dumps({'status':'already_running'}))
else:
    args=['nice','-n','10','/root/miniconda3/bin/python','-u','src/analyze_v5_main.py',
          '--data','/root/ConsDagV5/data/processed_v5','--runs-root','/root/ConsDagV5',
          '--pe-root','inputs/v5_pe_frozen','--out',str(out)]
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    with (root/'outputs/v5_main_0530_20261124.log').open('ab') as log:
        proc=subprocess.Popen(args,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record={'started_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'pid':proc.pid,'command':args}
    pidfile.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record))
'''
    _,out,err=client.exec_command("/root/miniconda3/bin/python - <<'PY'\n"+script+'\nPY',timeout=30)
    value,error=out.read().decode(),err.read().decode()
    if out.channel.recv_exit_status(): raise RuntimeError(error)
    record=json.loads(value)
    (ROOT/'outputs/v5_analysis/main_0530_deployment_20261124.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(value)
finally:
    client.close()
