"""Read completed baseline and supersede only an unstarted dependent job."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from manage_structure_supplement import command, connect, PYTHON, REMOTE as SUPPLEMENT, ROOT
from remote_gpu import download_tree, digest, remote_digest


def cancel_pending(client,sftp):
    code='\n'.join([
        'import json,os,signal,time', 'from pathlib import Path',
        'root=Path('+repr(SUPPLEMENT)+')', 'p=root/"results/waiter_state.json"',
        'state=json.loads(p.read_text())',
        'assert state["status"]=="waiting_for_fixed_planner_and_reward_probe",state',
        'assert not (root/"results/calls.jsonl").exists(),"Already has model calls; stop and inspect"',
        'pid=state["pid"]',
        'cmd=Path(f"/proc/{pid}/cmdline").read_bytes().decode().replace(chr(0)," ")',
        'assert str(root/"scripts/research_followup/wait_structure_supplement.py") in cmd',
        '(root/"results/waiter_state_before_cancel.json").write_text(json.dumps(state,indent=2))',
        'os.kill(pid,signal.SIGTERM)', 'time.sleep(1)',
        'assert not Path(f"/proc/{pid}").exists() or Path(f"/proc/{pid}/stat").read_text().split()[2]=="Z"',
        'from datetime import datetime,timezone',
        'state.update(status="cancelled_before_launch",utc=datetime.now(timezone.utc).isoformat(),reason="All 576 fixed neural plans failed strict output interface; run explicit-format smoke before spending the structural supplement budget.")',
        'p.write_text(json.dumps(state,indent=2))', 'print(json.dumps(state))'])
    print(command(client,[PYTHON,'-c',code]),flush=True)


def verify_fixed(client,sftp):
    remote='/root/consdag_audits/local-planning-20261126/gpu-fixed-planner'
    local=ROOT/'outputs/local_planning_20261126/gpu-fixed-planner'
    record={}
    for name in ('calls.jsonl','decisions.jsonl','protocol.json','completion.json','results.json','waiter_state.json'):
        expected=remote_digest(sftp,remote+'/'+name)
        if digest(local/name)!=expected: raise ValueError('SHA mismatch: '+name)
        record[name]=expected
    (local/'receipt_verification.json').write_text(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),sha256=record,all_match=True),indent=2))
    print(json.dumps(dict(verified_files=len(record),all_match=True)),flush=True)


if __name__=='__main__':
    with connect() as client,client.open_sftp() as sftp:
        print('Ready: cancel_pending, verify_fixed, quit',flush=True)
        while True:
            op=input().strip()
            if op=='quit': break
            try: {'cancel_pending':cancel_pending,'verify_fixed':verify_fixed}[op](client,sftp)
            except Exception as exc: print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
