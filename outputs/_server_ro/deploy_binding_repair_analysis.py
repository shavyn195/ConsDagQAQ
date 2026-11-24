"""Deploy the separately frozen CPU repair analysis and launch its waiter."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect, upload_file, remote_digest
DEST='/root/ConsDagDiagnostics20261123'
client=connect()
try:
    with client.open_sftp() as sftp:
        for dep in ['src/public_role_binding.py','src/public_scope_binding.py','data/diagnostic_v5_binding_20261123/protocol.json']:
            if remote_digest(sftp,DEST+'/'+dep)!=hashlib.sha256((ROOT/dep).read_bytes()).hexdigest():
                raise ValueError('Existing frozen dependency differs: '+dep)
        for rel in ['src/analyze_v5_binding_repair.py','scripts/analyze_v5_binding_repair_after_run.sh',
                    'tests/test_v5_binding_repair.py','configs/v5_binding_repair_analysis.json']:
            upload_file(sftp,ROOT/rel,DEST+'/'+rel)
    command=('cd '+DEST+' && bash -n scripts/analyze_v5_binding_repair_after_run.sh'
             ' && CUDA_VISIBLE_DEVICES= PYTHONPATH=.testdeps:src /root/miniconda3/bin/python -m pytest -q tests/test_v5_binding_repair.py')
    _,out,err=client.exec_command(command,timeout=60)
    print(out.read().decode()+err.read().decode())
    if out.channel.recv_exit_status(): raise RuntimeError('Remote tests failed')
    remote=r'''
import datetime,json,os,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
root=Path('/root/ConsDagDiagnostics20261123')
exists=subprocess.run(['pgrep','-af','^bash scripts/analyze_v5_binding_repair_after_run.sh$'],capture_output=True,text=True)
record={'checked_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()}
if exists.returncode==0:
    record.update(status='already_running',process=exists.stdout.strip())
else:
    with (root/'outputs/v5_binding_repair_analysis_queue.log').open('ab') as log:
        worker=subprocess.Popen(['bash','scripts/analyze_v5_binding_repair_after_run.sh'],cwd=root,
            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    record.update(status='started',pid=worker.pid)
(root/'outputs/v5_binding_repair_analysis_worker.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
'''
    _,out,err=client.exec_command("/root/miniconda3/bin/python - <<'PY'\n"+remote+'\nPY',timeout=30)
    value,error=out.read().decode(),err.read().decode()
    if out.channel.recv_exit_status(): raise RuntimeError(error)
    (ROOT/'outputs/v5_analysis/binding_repair_deployment_20261124.json').write_text(json.dumps(json.loads(value),indent=2)+'\n',encoding='utf-8')
    print(value)
finally:
    client.close()
