"""Bounded matched-input SFT continuation; no GRPO or gold auxiliary inputs."""
import json
import manage_planner_learning_probe as queue
manager=queue.manager
manager.REMOTE='/root/consdag_audits/matched-planner-sft-inputs-20261126-v1'
manager.LOCAL=manager.ROOT/'outputs/matched_planner_sft_inputs_20261126'
manager.CONFIG='configs/matched_planner_sft_inputs_20261126.json'
queue.TEST_FILES=['tests/test_matched_planner_sft.py','tests/test_shared_planner_sft.py']
queue.SOURCE_FILES+=['shared_planner_sft.py','matched_planner_sft.py']
queue.EXTRA_FILES=['tests/smoke_shared_planner_torch.py']
queue.RUN_TORCH_SMOKE=True

if __name__=='__main__':
    with manager.connect() as client,client.open_sftp() as sftp:
        print('Ready: deploy, resume_prelaunch, status, fetch, quit',flush=True)
        while True:
            op=input().strip()
            if op=='quit':break
            try:
                if op=='resume_prelaunch':queue.deploy(client,sftp,resume_prelaunch=True)
                else:{'deploy':queue.deploy,'status':manager.status,'fetch':manager.fetch}[op](client,sftp)
            except Exception as exc:print(json.dumps(dict(error=type(exc).__name__,message=str(exc))),flush=True)
