"""Wait for the active structural supplement, then run the gated format recovery."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    a=p.parse_args()
    sys.path.insert(0,str(a.root/'src'))
    from run_v6_relay import GpuLock,gpu_state,idle,require_device
    cfg=json.loads(a.config.read_text())
    a.out.mkdir(parents=True,exist_ok=True)
    path=a.out/'waiter_state.json'
    if path.exists(): raise ValueError('Existing waiter preserved')
    def state(status,**extra):
        value=dict(status=status,pid=os.getpid(),utc=datetime.now(timezone.utc).isoformat(),**extra)
        tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(value,indent=2)); tmp.replace(path)
        print(json.dumps(value),flush=True)
    def read(p): return json.loads(p.read_text()) if p.exists() else {}
    state('waiting_for_structural_supplement')
    try:
        deadline=time.monotonic()+86400
        while time.monotonic()<deadline:
            previous=read(Path(cfg['dependency'])/'waiter_state.json')
            if previous.get('status') in ('complete','incomplete','failed','cancelled_before_launch'):
                gpu=gpu_state('0'); require_device(gpu)
                if idle(gpu):
                    try:
                        lock=GpuLock(gpu['uuid']); lock.__enter__()
                    except ValueError:
                        time.sleep(30); continue
                    try:
                        if not idle(gpu_state('0')): continue
                        args=[sys.executable,str(Path(__file__).with_name('format_recovery.py')),
                              '--root',str(a.root),'--out',str(a.out),'--config',str(a.config)]
                        env={**os.environ,'CUDA_VISIBLE_DEVICES':'0','OMP_NUM_THREADS':'1',
                             'CONSDAG_V6_LOCK_FD':str(lock.fd),'CONSDAG_V6_GPU_UUID':gpu['uuid']}
                        child=subprocess.Popen(args,env=env,pass_fds=(lock.fd,),start_new_session=True)
                        state('running',child_pid=child.pid)
                        try: code=child.wait(timeout=cfg['active_seconds_cap'])
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid,signal.SIGTERM)
                            try: child.wait(timeout=15)
                            except subprocess.TimeoutExpired:
                                os.killpg(child.pid,signal.SIGKILL); child.wait()
                            state('incomplete',reason='one_hour_active_budget'); return
                        done=read(a.out/'completion.json')
                        state('complete' if code==0 and done.get('status') in ('complete','smoke_gate_failed') else 'incomplete',
                              exit_code=code,completion=done)
                        return
                    finally: lock.__exit__(None,None,None)
            time.sleep(30)
        state('expired_without_launch')
    except Exception as exc:
        state('failed',reason=f'{type(exc).__name__}: {exc}'); raise


if __name__=='__main__': main()
