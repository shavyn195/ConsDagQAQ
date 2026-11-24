"""Read step logs and checkpoint availability without modifying the server."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from remote_gpu import connect

REMOTE=r'''
import datetime,json,subprocess
from pathlib import Path
from zoneinfo import ZoneInfo
root=Path('/root/ConsDagV5')
result={'checked_at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'runs':{}}
for seed in [42,43]:
    name=f'Qwen3-4B-v5-seed{seed}'
    run=root/'outputs/e1'/name
    log=root/'outputs/e1'/(name+'.log')
    points=[]; evaluations=[]
    if log.exists():
        for line in log.read_text(errors='replace').splitlines():
            try: value=json.loads(line)
            except ValueError: continue
            if not isinstance(value,dict): continue
            if 'optimizer_step' in value: points.append(value)
            if value.get('tag')=='trained': evaluations.append(value)
    result['runs'][name]={'step_7800':[p for p in points if p['optimizer_step']==7800],
      'near_7800':[p for p in points if 7400<=p['optimizer_step']<=8000],
      'latest_training':points[-1:] if points else [], 'trained_eval':evaluations,
      'files':[{'path':str(p.relative_to(run)),'bytes':p.stat().st_size} for p in run.rglob('*') if p.is_file()] if run.exists() else []}
source=(root/'src/run_e1.py').read_text().splitlines()
result['remote_checkpoint_and_eval_calls']=[{'line':i,'text':line.strip()} for i,line in enumerate(source,1) if any(t in line for t in ['save_pretrained','torch.save','checkpoint','results["trained"]','train(model','optimizer_step": done'])]
result['gpu']=subprocess.run(['nvidia-smi','--query-gpu=name,utilization.gpu,memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,timeout=15).stdout.strip()
print(json.dumps(result,ensure_ascii=False))
'''
client=connect()
try:
    _,out,err=client.exec_command('/root/miniconda3/bin/python - <<\'PY\'\n'+REMOTE+'\nPY',timeout=60)
    raw=out.read().decode('utf-8','replace'); errors=err.read().decode('utf-8','replace')
    status=out.channel.recv_exit_status()
    if status: raise RuntimeError(errors)
    result=json.loads(raw)
    target=ROOT/'outputs/v5_analysis/step7800_checkpoint_check.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
finally:
    client.close()
