import hashlib, json, sys, tarfile
from pathlib import Path
root=Path.cwd()
sys.path.insert(0,str(root/'scripts'))
from remote_gpu import connect
out=root/'outputs/v5_analysis'
archive=out/'gpu_binding_diagnostic_bundle.tar.gz'
files=[]
for folder in ('src','tests','data/diagnostic_v5_binding_20261123'):
 files.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
files.append(root/'scripts/run_v5_binding_after_queue.sh')
manifest={str(p.relative_to(root)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
manifest_path=out/'gpu_binding_bundle_manifest.json'
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
with tarfile.open(archive,'w:gz') as tar:
 for p in files: tar.add(p,arcname=p.relative_to(root).as_posix())
 tar.add(manifest_path,arcname='bundle_manifest.json')
client=connect()
remote='/root/ConsDagDiagnostics20261123'
try:
 with client.open_sftp() as sftp:
  try: sftp.stat(remote)
  except OSError: pass
  else: raise RuntimeError('Destination already exists; refusing duplicate staging')
  sftp.put(str(archive),'/root/consdag_gpu_binding_diagnostic_20261123.tar.gz')
 code='''import hashlib,json,tarfile,subprocess,sys,pathlib,os
root=pathlib.Path('/root/ConsDagDiagnostics20261123')
root.mkdir(exist_ok=False)
with tarfile.open('/root/consdag_gpu_binding_diagnostic_20261123.tar.gz') as t: t.extractall(root,filter='data')
manifest=json.loads((root/'bundle_manifest.json').read_text())
for name,want in manifest.items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==want, name
source=pathlib.Path('/root/ConsDagV5')
for arm in ('Qwen3-1.7B-v5-seed42','Qwen3-1.7B-v5-seed43','Qwen3-4B-v5-seed42'):
 assert (source/'outputs/e1'/arm/'adapter/adapter_config.json').is_file(),arm
 assert (source/'models'/arm.split('-v5-')[0]).is_dir(),arm
subprocess.run(['bash','-n','scripts/run_v5_binding_after_queue.sh'],cwd=root,check=True)
subprocess.run([sys.executable,'-m','pytest','-q','tests/test_v5_audit.py'],cwd=root,check=True)
log=root/'outputs/v5_binding_queue.log'
log.parent.mkdir(exist_ok=True)
with log.open('ab') as f:
 p=subprocess.Popen(['bash','scripts/run_v5_binding_after_queue.sh'],cwd=root,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
(root/'outputs/queue_pid.json').write_text(json.dumps({'pid':p.pid,'purpose':'wait for existing E1 queue; then 972 frozen-adapter diagnostic inferences; no new training'})+'\\n')
print(json.dumps({'staged_root':str(root),'worker_pid':p.pid,'bundle_files_verified':len(manifest),'log':str(log)}))
'''
 stdin,stdout,stderr=client.exec_command('/root/miniconda3/bin/python -',timeout=90)
 stdin.write(code); stdin.channel.shutdown_write()
 print(stdout.read().decode('utf-8','replace'))
 print(stderr.read().decode('utf-8','replace'))
 status=stdout.channel.recv_exit_status()
 if status: raise RuntimeError('Remote preflight failed; no successful launch confirmation')
finally: client.close()
