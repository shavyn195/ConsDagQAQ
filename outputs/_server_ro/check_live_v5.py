"""Read the existing server queue and save a dated local status snapshot."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from remote_gpu import connect

REMOTE = r'''
import datetime,json,re,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

root=Path('/root/ConsDagV5')
def command(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=20)
    return {'exit_code':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
result={'checked_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
 'gpu':command(['nvidia-smi','--query-gpu=name,utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits']),
 'gpu_processes':command(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv,noheader,nounits']),
 'processes':[], 'runs':[], 'queue_tail':[], 'diagnostics':{}}
targets={'src/run_e1.py','scripts/run_e1_queue_v5.sh','scripts/run_v5_binding_after_queue.sh','src/run_v5_diagnostic_panel.py'}
for p in Path('/proc').iterdir():
    if not p.name.isdigit(): continue
    try:
        args=[x.decode('utf-8','replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
        if targets.intersection(args):
            result['processes'].append({'pid':int(p.name),'args':args,'cwd':str((p/'cwd').resolve())})
    except (OSError,PermissionError): pass
manifest=root/'outputs/e1_v5_queue_manifest.jsonl'
if manifest.exists():
    result['queue_tail']=[json.loads(x) for x in manifest.read_text().splitlines()[-20:] if x.strip()]
splits=['dev','test_tpl_ho','test_tool_ho','test_struct_ho']
for run in sorted((root/'outputs/e1').glob('*-v5-seed*')):
    if not run.is_dir(): continue
    log=run.parent/(run.name+'.log')
    row={'name':run.name,'metrics_exists':(run/'metrics.json').exists(),'adapter_exists':(run/'adapter/adapter_config.json').exists(),
         'failure_files':[p.name for p in run.glob('*fail*')], 'trained_prediction_files':[]}
    if log.exists():
        lines=log.read_text(errors='replace').splitlines()
        points=[]
        for line in lines:
            try:
                obj=json.loads(line)
                if isinstance(obj,dict) and 'optimizer_step' in obj: points.append(obj)
            except ValueError: pass
        row['last_training_points']=points[-5:]
        row['error_lines']=[x[:800] for x in lines if re.search(r'"loss"\s*:\s*(?:NaN|Infinity)|Traceback|out of memory|non-finite|FloatingPointError|nonfinite',x,re.I)][-8:]
        row['log_tail']=[x[:700] for x in lines[-5:]]
        row['log_mtime']=datetime.datetime.fromtimestamp(log.stat().st_mtime,ZoneInfo('Asia/Shanghai')).isoformat()
    pred=run/'trained_predictions'
    if pred.exists():
        row['trained_prediction_files']=[{'name':p.name,'bytes':p.stat().st_size,'lines':sum(1 for _ in p.open())} for p in pred.glob('*.jsonl')]
    if row['metrics_exists']:
        metrics=json.loads((run/'metrics.json').read_text())
        row['metrics_keys']=list(metrics.keys())
    result['runs'].append(row)
droot=Path('/root/ConsDagDiagnostics20261123/outputs')
if droot.exists():
    result['diagnostics']['files']=[str(p.relative_to(droot)) for p in droot.rglob('*') if p.is_file() and p.suffix in ('.json','.log','.jsonl')]
    result['diagnostics']['log_tails']={str(p.relative_to(droot)):p.read_text(errors='replace').splitlines()[-8:] for p in droot.rglob('*.log')}
print(json.dumps(result,ensure_ascii=False))
'''

client=connect()
try:
    _,stdout,stderr=client.exec_command('/root/miniconda3/bin/python - <<\'PY\'\n'+REMOTE+'\nPY',timeout=60)
    output=stdout.read().decode('utf-8','replace')
    error=stderr.read().decode('utf-8','replace')
    code=stdout.channel.recv_exit_status()
    if code:
        raise RuntimeError(f'Remote read-only status failed: {code}: {error}')
    snapshot=json.loads(output)
    target=ROOT/'outputs/v5_analysis/gpu_status_latest.json'
    target.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(snapshot,ensure_ascii=False,indent=2))
finally:
    client.close()
