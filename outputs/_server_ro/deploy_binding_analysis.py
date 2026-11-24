"""Install only new analysis files in the isolated diagnostic checkout."""
import json
from pathlib import Path
import shlex
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect, upload_file

DEST='/root/ConsDagDiagnostics20261123'
FILES=['src/analyze_v5_binding.py','tests/test_v5_binding_analysis.py',
       'scripts/analyze_v5_binding_after_run.sh']
client=connect()
try:
    with client.open_sftp() as sftp:
        for dependency in ['src/analyze_v5_seed_disagreement.py','src/rescore_v4_side.py',
                           'src/run_e1.py','src/trust_env.py','src/eval_exec.py',
                           'data/diagnostic_v5_binding_20261123/protocol.json']:
            sftp.stat(DEST+'/'+dependency)
        for relative in FILES:
            upload_file(sftp, ROOT/relative, DEST+'/'+relative)
    check=('cd '+shlex.quote(DEST)+' && bash -n scripts/analyze_v5_binding_after_run.sh'
           ' && PYTHONPATH=.testdeps:/root/ConsDagDiagnostics20261123/src '
           '/root/miniconda3/bin/python -m pytest -q tests/test_v5_binding_analysis.py')
    _,stdout,stderr=client.exec_command(check,timeout=60)
    out=stdout.read().decode(); err=stderr.read().decode()
    status=stdout.channel.recv_exit_status()
    print(out+err)
    if status: raise RuntimeError('Remote focused tests failed; worker not started')
    remote=r'''
import datetime,json,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
root=Path('/root/ConsDagDiagnostics20261123')
p=subprocess.run(['pgrep','-af','^bash scripts/analyze_v5_binding_after_run.sh$'],capture_output=True,text=True)
record={'checked_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()}
if p.returncode==0:
    record['worker']='already_running'; record['process']=p.stdout.strip()
else:
    log=(root/'outputs/v5_binding_analysis_queue.log').open('ab')
    worker=subprocess.Popen(['bash','scripts/analyze_v5_binding_after_run.sh'],cwd=root,
        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record['worker']='started'; record['pid']=worker.pid
    log.close()
train=Path('/root/ConsDagV5/outputs/e1/Qwen3-4B-v5-seed43.log')
record['training_tail']=train.read_text(errors='replace').splitlines()[-6:]
record['gpu']=subprocess.run(['nvidia-smi','--query-gpu=utilization.gpu,memory.used','--format=csv,noheader,nounits'],capture_output=True,text=True).stdout.strip()
(root/'outputs/binding_analysis_worker.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
'''
    _,stdout,stderr=client.exec_command('/root/miniconda3/bin/python - <<\'PY\'\n'+remote+'\nPY',timeout=30)
    out=stdout.read().decode(); err=stderr.read().decode()
    status=stdout.channel.recv_exit_status()
    if status: raise RuntimeError(err)
    record=json.loads(out)
    (ROOT/'outputs/v5_analysis/binding_analysis_deployment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(record,ensure_ascii=False,indent=2))
finally:
    client.close()
