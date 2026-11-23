"""Inference-only paired intervention on the frozen 1.7B compiler's policy card."""
import json
import re
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import run_e1
from dataset_v4_spec import POLICY_CARD, PII_CLASSES
from rescore_v4_side import ROOT, digest, load_jsonl, outcome

OUT = ROOT / 'outputs/dataset_audit/privacy-card-v1'
SOURCE = ROOT / 'data/processed_v4/test_tpl_ho.jsonl'
TRAINED = ROOT / 'outputs/e1/Qwen3-1.7B-v4'
CLEAN, replacements = re.subn(r' \(e\.g\. [^()]+\)', '', POLICY_CARD)
assert replacements == len(PII_CLASSES)


def cohort():
    selected = []
    for r in load_jsonl(SOURCE):
        if r['variant'] != 'implicit':
            continue
        for c, h in zip(r['gold']['constraints'], r['hint_meta'], strict=True):
            if c['type'] == 'privacy' and h['difficulty'] >= 2:
                cls, = c['params']['protected_data_classes']
                fields = PII_CLASSES[cls]['fields']['test']
                assert any(v in c['evidence_span'] for v in fields)
                selected.append(r)
    assert selected and len({r['sample_id'] for r in selected}) == len(selected)
    return selected


def privacy_key(cs):
    return sorted(json.dumps(c.get('params'), sort_keys=True) for c in cs if c.get('type') == 'privacy')


def metrics(row, raw):
    obj = run_e1.strict_parse(raw)
    o = outcome(row, raw)
    return {'privacy_params': bool(obj and privacy_key(obj['constraints']) == privacy_key(row['gold']['constraints'])),
            'faithful_success': o['faithful_success'], 'exact_with_evidence': o['exact_with_evidence']}


def main():
    from peft import PeftModel
    rows = cohort()
    cfg = json.loads((TRAINED/'metrics.json').read_text())['config']
    OUT.mkdir(exist_ok=False, parents=True)
    meta = dict(model=cfg['model'], precision=cfg['precision'], adapter=digest(TRAINED/'adapter/adapter_model.safetensors'),
                data=digest(SOURCE), source=digest(Path(__file__)), ids=[r['sample_id'] for r in rows],
                hypothesis='Removing the enumerated field examples can reduce exact privacy parameter recovery.',
                policy_cards={'original':POLICY_CARD, 'no_field_examples':CLEAN}, max_new_tokens=cfg['max_new_tokens'],
                eval_batch_size=cfg['eval_batch_size'], seed=cfg['seed'])
    (OUT/'config.json').write_text(json.dumps(meta, indent=2))
    model, tok = run_e1.load_model(str(ROOT/cfg['model']),cfg['precision'])
    model = PeftModel.from_pretrained(model, TRAINED/'adapter').eval()
    arms = {}
    for name,card in meta['policy_cards'].items():
        # All other prompt content, row order, checkpoint and decoding settings are identical.
        with patch('dataset_v4_spec.POLICY_CARD',card):
            _, texts = run_e1.generate_batched(model,tok,rows,cfg['max_new_tokens'],cfg['eval_batch_size'])
        arms[name] = []
        with (OUT/(name+'.jsonl')).open('x',encoding='utf8') as f:
            for row, raw in zip(rows, texts, strict=True):
                scores = metrics(row,raw)
                arms[name].append(scores)
                print(json.dumps(dict(sample_id=row['sample_id'],raw=raw,metrics=scores)),file=f)
    report={'n_groups':len(rows),'transition_counts':{}}
    for k in arms['original'][0]:
        report['transition_counts'][k]=dict(Counter(
            f'{int(o[k])}->{int(c[k])}' for o,c in zip(arms['original'],arms['no_field_examples'],strict=True)))
    (OUT/'scores.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    main()
