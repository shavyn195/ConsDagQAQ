"""New post-diagnostic SFT run; the skipped conditional v1 stays immutable."""
import json
import manage_shared_planner_sft as manager

manager.REMOTE='/root/consdag_audits/shared-planner-learning-20261126-v2'
manager.LOCAL=manager.ROOT/'outputs/shared_planner_learning_20261126'
manager.CONFIG='configs/shared_planner_learning_20261126.json'

if __name__=='__main__':
    with manager.connect() as client,client.open_sftp() as sftp:
        print('Ready: deploy, resume_prelaunch, status, fetch, quit',flush=True)
        while True:
            op=input().strip()
            if op=='quit': break
            try:
                if op=='resume_prelaunch': manager.deploy(client,sftp,resume_prelaunch=True)
                else: {'deploy':manager.deploy,'status':manager.status,'fetch':manager.fetch}[op](client,sftp)
            except Exception as exc:
                print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
