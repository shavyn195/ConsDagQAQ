"""Independent, deterministic dev spot replay from the two saved v4 adapters."""
import json
from pathlib import Path

from peft import PeftModel
from pe_v4_side import fingerprint
from rescore_v4_side import ROOT, digest, load_jsonl
from run_e1 import generate_batched, load_model, target_json


def evaluate(size, rows, dest):
    trained=ROOT/'outputs/e1'/('Qwen3-'+size+'-v4')
    cfg=json.loads((trained/'metrics.json').read_text())['config']
    old=trained/'trained_predictions/dev.jsonl'
    saved={p['sample_id']:p['raw'] for p in load_jsonl(old)}
    model,tok=load_model(str(ROOT/cfg['model']),cfg['precision'])
    model=PeftModel.from_pretrained(model,trained/'adapter').eval()
    _,raw=generate_batched(model,tok,rows,cfg['max_new_tokens'],cfg['eval_batch_size'])
    obs=[dict(sample_id=r['sample_id'],raw=t,matches_saved=t==saved[r['sample_id']],
              canonical=t.strip()==target_json(r)) for r,t in zip(rows,raw,strict=True)]
    (dest/(size+'.jsonl')).write_text(''.join(json.dumps(p)+'\n' for p in obs))
    return dict(n=len(rows),matches_saved=sum(p['matches_saved'] for p in obs),canonical=sum(p['canonical'] for p in obs),
                original_hash=digest(old),adapter_hash=digest(trained/'adapter/adapter_model.safetensors'))


if __name__=='__main__':
    import torch
    src=ROOT/'data/processed_v4/dev.jsonl'
    data=load_jsonl(src)
    groups=sorted({r['group_id'] for r in data},key=lambda g:fingerprint(['consdag-dev-replay-1',g]))[:9]
    rows=[r for r in data if r['group_id'] in groups]
    assert len(rows)==27
    dest=ROOT/'outputs/dataset_audit/dev-replay-v1'
    dest.mkdir(parents=True,exist_ok=False)
    report=dict(data=digest(src),source=digest(Path(__file__)),groups=groups,models={})
    for size in ['1.7B','4B']:
        report['models'][size]=evaluate(size,rows,dest)
        torch.cuda.empty_cache()
    (dest/'scores.json').write_text(json.dumps(report,indent=2))
