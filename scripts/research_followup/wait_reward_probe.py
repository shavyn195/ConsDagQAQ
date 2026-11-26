"""Run the bounded inference probe after both existing experiments succeed."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def dependency_ready(queue, previous, completion):
    return (queue.get('status') == 'complete' and queue.get('active') is None
            and previous.get('status') == 'complete' and completion.get('status') == 'complete')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--previous', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    a = p.parse_args()
    sys.path.insert(0, str(a.root/'src'))
    from run_v6_relay import GpuLock, gpu_state, idle, require_device
    cfg = json.loads(a.config.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    path = a.out/'waiter_state.json'
    if path.exists():
        raise ValueError('Previous waiter state preserved')
    def state(status, **extra):
        value = dict(status=status, pid=os.getpid(), utc=datetime.now(timezone.utc).isoformat(), **extra)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(value, indent=2))
        tmp.replace(path)
        print(json.dumps(value), flush=True)
    def read(path):
        return json.loads(path.read_text()) if path.exists() else {}
    command = [sys.executable, str(Path(__file__).with_name('planner_reward_probe.py')),
               '--root', str(a.root), '--out', str(a.out), '--config', str(a.config)]
    try:
        state('waiting_for_original_queue_and_fixed_planner')
        deadline = time.monotonic() + 24*3600
        while time.monotonic() < deadline:
            queue = read(a.root/'outputs/e1_v6/queue_state.json')
            previous = read(a.previous/'waiter_state.json')
            done = read(a.previous/'completion.json')
            if queue.get('status') in ('failed','incomplete') or previous.get('status') in ('failed','incomplete','blocked_original_queue'):
                state('blocked_dependency', queue_status=queue.get('status'), previous=previous)
                return
            if dependency_ready(queue,previous,done):
                gpu = gpu_state('0')
                require_device(gpu)
                if idle(gpu):
                    try:
                        lock = GpuLock(gpu['uuid'])
                        lock.__enter__()
                    except ValueError:
                        time.sleep(30)
                        continue
                    try:
                        if not idle(gpu_state('0')):
                            continue
                        env = {**os.environ, 'CUDA_VISIBLE_DEVICES':'0',
                               'CONSDAG_V6_LOCK_FD':str(lock.fd), 'CONSDAG_V6_GPU_UUID':gpu['uuid']}
                        child = subprocess.Popen(command, env=env, pass_fds=(lock.fd,), start_new_session=True)
                        state('running', child_pid=child.pid)
                        try:
                            code = child.wait(timeout=cfg['active_seconds_cap'])
                        except subprocess.TimeoutExpired:
                            os.killpg(child.pid, signal.SIGTERM)
                            try:
                                child.wait(timeout=15)
                            except subprocess.TimeoutExpired:
                                os.killpg(child.pid, signal.SIGKILL)
                                child.wait()
                            state('incomplete', reason='1800_second_active_budget')
                            return
                        done = read(a.out/'completion.json')
                        state('complete' if code == 0 and done.get('status') == 'complete' else 'incomplete', exit_code=code, completion=done)
                        return
                    finally:
                        lock.__exit__(None,None,None)
            time.sleep(30)
        state('expired_without_launch', reason='24_hour_queue_deadline')
    except Exception as exc:
        state('failed', reason=f'{type(exc).__name__}: {exc}')
        raise


if __name__ == '__main__':
    main()
