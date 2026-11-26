"""Conditional, exclusive GPU handoff after a completed prompt-recovery diagnostic."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from common import sha


def dependency_action(waiter, completion, accepted=('smoke_gate_failed',)):
    if waiter.get('status') not in ('complete', 'incomplete', 'failed', 'expired_without_launch'):
        return 'wait'
    if waiter.get('status') == 'complete' and completion.get('status') in accepted:
        return 'train'
    return 'skip'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    args = p.parse_args()
    sys.path.insert(0, str(args.root/'src'))
    from run_v6_relay import GpuLock, gpu_state, idle, require_device
    cfg = json.loads(args.config.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out/'waiter_state.json'
    if path.exists(): raise ValueError('Prior waiter preserved')
    def state(status, **extra):
        record = dict(status=status, pid=os.getpid(), utc=datetime.now(timezone.utc).isoformat(), **extra)
        temp=path.with_suffix('.tmp'); temp.write_text(json.dumps(record,indent=2)); temp.replace(path)
        print(json.dumps(record),flush=True)
    def read(path): return json.loads(path.read_text()) if path.exists() else {}
    state('waiting_for_prompt_recovery')
    dependency = Path(cfg['dependency'])
    try:
        deadline = time.monotonic()+86400
        while time.monotonic()<deadline:
            previous = read(dependency/'waiter_state.json')
            completion = read(dependency/'completion.json')
            action = dependency_action(previous,completion,cfg.get('accepted_dependency_statuses',['smoke_gate_failed']))
            if action=='skip':
                state('skipped_dependency_not_accepted',dependency=previous,completion=completion)
                return
            if action=='train':
                if completion['results_sha256'] != sha(dependency/'results.json'):
                    raise ValueError('Dependency completion signature mismatch')
                gpu=gpu_state('0'); require_device(gpu)
                if idle(gpu):
                    try:
                        lock=GpuLock(gpu['uuid']); lock.__enter__()
                    except ValueError:
                        time.sleep(30); continue
                    try:
                        if not idle(gpu_state('0')): continue
                        worker=cfg.get('worker','shared_planner_sft.py')
                        if Path(worker).name!=worker or not worker.endswith('.py'):
                            raise ValueError('Worker must be a sibling Python file')
                        command=[sys.executable,str(Path(__file__).with_name(worker)),
                                 '--root',str(args.root),'--out',str(args.out),'--config',str(args.config)]
                        env={**os.environ,'CUDA_VISIBLE_DEVICES':'0','OMP_NUM_THREADS':'1',
                             'CONSDAG_V6_LOCK_FD':str(lock.fd),'CONSDAG_V6_GPU_UUID':gpu['uuid']}
                        child=subprocess.Popen(command,env=env,pass_fds=(lock.fd,),start_new_session=True)
                        state('running',child_pid=child.pid)
                        try: code=child.wait(timeout=cfg['active_seconds_cap'])
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid,signal.SIGTERM)
                            try: child.wait(timeout=15)
                            except subprocess.TimeoutExpired:
                                os.killpg(child.pid,signal.SIGKILL); child.wait()
                            state('incomplete',reason='active_budget_exhausted'); return
                        done=read(args.out/'completion.json')
                        state('complete' if code==0 and done.get('status') in ('complete','smoke_gate_failed') else 'incomplete',
                              exit_code=code,completion=done)
                        return
                    finally: lock.__exit__(None,None,None)
            time.sleep(30)
        state('expired_without_launch')
    except Exception as exc:
        state('failed',reason=f'{type(exc).__name__}: {exc}'); raise


if __name__=='__main__': main()
