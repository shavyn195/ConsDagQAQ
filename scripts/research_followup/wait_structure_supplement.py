"""Sequential supplement: finish baseline and bounded probe before taking the GPU."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

TERMINAL_PROBE={'complete','incomplete','failed','blocked_dependency','expired_without_launch'}


def dependency_ready(queue, fixed, completion, probe):
    return (queue.get('status')=='complete' and queue.get('active') is None
            and fixed.get('status')=='complete' and completion.get('status')=='complete'
            and probe.get('status') in TERMINAL_PROBE)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True)
    a=p.parse_args()
    sys.path.insert(0,str(a.root/'src'))
    from run_v6_relay import GpuLock, gpu_state, idle, require_device
    cfg=json.loads(a.config.read_text())
    a.out.mkdir(parents=True,exist_ok=True)
    path=a.out/'waiter_state.json'
    if path.exists(): raise ValueError('Existing waiter preserved')
    def read(p): return json.loads(p.read_text()) if p.exists() else {}
    def state(status,**extra):
        record=dict(status=status,pid=os.getpid(),utc=datetime.now(timezone.utc).isoformat(),**extra)
        tmp=path.with_suffix('.tmp')
        tmp.write_text(json.dumps(record,indent=2))
        tmp.replace(path)
        print(json.dumps(record),flush=True)
    args=[sys.executable,str(Path(__file__).with_name('structure_supplement.py')),
          '--root',str(a.root),'--out',str(a.out),'--config',str(a.config)]
    try:
        state('waiting_for_fixed_planner_and_reward_probe')
        deadline=time.monotonic()+86400
        while time.monotonic()<deadline:
            queue=read(a.root/'outputs/e1_v6/queue_state.json')
            fixed=read(Path(cfg['previous'])/'waiter_state.json')
            done=read(Path(cfg['previous'])/'completion.json')
            probe=read(Path(cfg['reward_probe'])/'waiter_state.json')
            if queue.get('status') in ('failed','incomplete') or fixed.get('status') in ('failed','incomplete','blocked_original_queue'):
                state('blocked_dependency',queue=queue.get('status'),fixed=fixed)
                return
            if dependency_ready(queue,fixed,done,probe):
                gpu=gpu_state('0')
                require_device(gpu)
                if idle(gpu):
                    try:
                        lock=GpuLock(gpu['uuid'])
                        lock.__enter__()
                    except ValueError:
                        time.sleep(30)
                        continue
                    try:
                        if not idle(gpu_state('0')): continue
                        env={**os.environ,'CUDA_VISIBLE_DEVICES':'0','OMP_NUM_THREADS':'1',
                             'CONSDAG_V6_LOCK_FD':str(lock.fd),'CONSDAG_V6_GPU_UUID':gpu['uuid']}
                        child=subprocess.Popen(args,env=env,pass_fds=(lock.fd,),start_new_session=True)
                        state('running',child_pid=child.pid,probe_terminal_status=probe['status'])
                        try:
                            code=child.wait(timeout=cfg['active_seconds_cap'])
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid,signal.SIGTERM)
                            try: child.wait(timeout=15)
                            except subprocess.TimeoutExpired:
                                os.killpg(child.pid,signal.SIGKILL)
                                child.wait()
                            state('incomplete',reason='3600_second_active_budget')
                            return
                        final=read(a.out/'completion.json')
                        state('complete' if code==0 and final.get('status')=='complete' else 'incomplete',
                              exit_code=code,completion=final)
                        return
                    finally:
                        lock.__exit__(None,None,None)
            time.sleep(30)
        state('expired_without_launch')
    except Exception as exc:
        state('failed',reason=f'{type(exc).__name__}: {exc}')
        raise


if __name__=='__main__':
    main()
