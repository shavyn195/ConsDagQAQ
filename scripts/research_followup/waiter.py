"""One-shot continuation after the existing queue; never changes or preempts it."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone


def ready(queue):
    return queue.get('status') == 'complete' and queue.get('active') is None


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--groups',type=int,default=48)
    a=p.parse_args()
    sys.path.insert(0,str(a.root/'src'))
    from run_v6_relay import GpuLock, gpu_state, idle, require_device
    a.out.mkdir(parents=True,exist_ok=True)
    state_path=a.out/'waiter_state.json'
    if state_path.exists():
        raise ValueError('Existing waiter preserved')

    def state(status, **kwargs):
        value=dict(status=status,pid=os.getpid(),utc=datetime.now(timezone.utc).isoformat(),**kwargs)
        tmp=state_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(value,indent=2))
        tmp.replace(state_path)
        print(json.dumps(value),flush=True)

    cmd=[sys.executable,str(Path(__file__).with_name('fixed_planner.py')),
         '--root',str(a.root),'--out',str(a.out),'--groups',str(a.groups)]
    child=None
    try:
        state('preflight')
        subprocess.run(cmd+['--prepare-only'],env={**os.environ,'CUDA_VISIBLE_DEVICES':''},check=True,timeout=600)
        state('waiting_for_original_queue')
        while True:
            queue=json.loads((a.root/'outputs/e1_v6/queue_state.json').read_text())
            if queue.get('status') in ('failed','incomplete'):
                state('blocked_original_queue',queue_status=queue.get('status'),reason=queue.get('failure'))
                return
            if ready(queue):
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
                        time.sleep(2)
                        if not idle(gpu_state('0')):
                            continue
                        env={**os.environ,'CUDA_VISIBLE_DEVICES':'0','CONSDAG_V6_LOCK_FD':str(lock.fd),
                             'CONSDAG_V6_GPU_UUID':gpu['uuid']}
                        child=subprocess.Popen(cmd,env=env,pass_fds=(lock.fd,),start_new_session=True)
                        state('running',child_pid=child.pid,gpu=gpu)
                        try:
                            code=child.wait(timeout=7200)
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid,signal.SIGTERM)
                            try:
                                child.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                os.killpg(child.pid,signal.SIGKILL)
                                child.wait()
                            state('incomplete',reason='pilot_7200_second_budget_exhausted')
                            return
                        state('complete' if code==0 else 'failed',exit_code=code)
                        return
                    finally:
                        lock.__exit__(None,None,None)
            time.sleep(30)
    except Exception as exc:
        state('failed',reason=f'{type(exc).__name__}: {exc}')
        raise


if __name__=='__main__':
    main()
