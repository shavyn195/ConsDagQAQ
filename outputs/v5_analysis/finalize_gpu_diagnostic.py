import sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'scripts'))
from remote_gpu import connect
client=connect()
try:
 code='''import json,subprocess,sys,pathlib,os
root=pathlib.Path('/root/ConsDagDiagnostics20261123')
log=root/'outputs/testdeps_install.log'
log.parent.mkdir(exist_ok=True)
with log.open('w') as f:
 subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--target',str(root/'.testdeps'),'pytest'],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
env=dict(os.environ,PYTHONPATH=str(root/'.testdeps'))
subprocess.run([sys.executable,'-m','pytest','-q','tests/test_v5_audit.py'],cwd=root,env=env,check=True)
with (root/'outputs/v5_binding_queue.log').open('ab') as f:
 p=subprocess.Popen(['bash','scripts/run_v5_binding_after_queue.sh'],cwd=root,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
meta={'pid':p.pid,'purpose':'wait for existing E1 queue; then 972 frozen-adapter diagnostic inferences; no new training'}
(root/'outputs/queue_pid.json').write_text(json.dumps(meta)+'\\n')
print(json.dumps(meta))
'''
 stdin,stdout,stderr=client.exec_command('/root/miniconda3/bin/python -',timeout=180)
 stdin.write(code); stdin.channel.shutdown_write()
 print(stdout.read().decode('utf-8','replace')); print(stderr.read().decode('utf-8','replace'))
 raise SystemExit(stdout.channel.recv_exit_status())
finally: client.close()
