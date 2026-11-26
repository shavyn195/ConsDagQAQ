"""Compare verified complete SFT/GRPO cells, retaining unequal-compute caveats."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from common import paired, read_rows, sha, summarize
from audit_content_controls_readout import verified

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sft', type=Path, default=ROOT / 'outputs/matched_planner_sft_inputs_20261126/results')
    parser.add_argument('--grpo', type=Path, default=ROOT / 'outputs/matched_planner_grpo_20261126/results')
    args = parser.parse_args()
    protocols = {name: verified(folder) for name, folder in [('sft', args.sft), ('grpo', args.grpo)]}
    for key in ('train_sample_ids', 'eval_sample_ids', 'initial_adapter_sha256', 'data_sha256', 'model_sha256'):
        assert protocols['sft'][key] == protocols['grpo'][key], key
    assert protocols['grpo']['compiler_cache_sha256'] == sha(args.sft / 'compiler_calls.jsonl')
    arms, costs, inputs, sources = {}, {}, {}, {}
    for name, folder in [('sft', args.sft), ('grpo', args.grpo)]:
        result = json.loads((folder / 'results.json').read_text())
        audit = json.loads((folder / 'readout_audit.json').read_text())
        assert audit['records_replayed'] == 576 and audit['arms'] == result['arms']
        records = defaultdict(list)
        for row in read_rows(folder / 'decisions.jsonl'):
            records[row['arm']].append(row['outcome'])
        for arm, rows in records.items():
            assert len(rows) == 144 and summarize(rows) == result['arms'][arm]
            assert len({r['sample_id'] for r in rows}) == 144
        arms[name] = records
        inputs[name] = {}
        for row in read_rows(folder / 'calls.jsonl'):
            key = (row['sample_id'], row['arm'].split('/')[1])
            if key in inputs[name]:
                assert inputs[name][key] == row['messages'], key
            inputs[name][key] = row['messages']
        assert len(inputs[name]) == 288
        costs[name] = dict(
            training={mode: result['runs'][mode]['training'] for mode in ('raw', 'contract')},
            evaluation={mode: result['runs'][mode]['eval_seconds'] for mode in ('raw', 'contract')},
            elapsed_seconds=result['elapsed_seconds'],
        )
        sources[name] = dict(results_sha256=sha(folder / 'results.json'), decisions_sha256=sha(folder / 'decisions.jsonl'))
    assert inputs['sft'] == inputs['grpo']
    comparisons = {}
    for training in ('raw', 'contract'):
        for inference in ('raw', 'contract'):
            left, right = arms['grpo'][training + '_grpo/' + inference], arms['sft'][training + '_sft/' + inference]
            comparisons[training + '/' + inference] = dict(grpo=summarize(left), sft=summarize(right), grpo_minus_sft=paired(left, right))
    saved = json.loads((args.grpo / 'results.json').read_text())
    assert {m: comparisons[m + '/' + m]['grpo_minus_sft'] for m in ('raw', 'contract')} == saved['grpo_minus_matched_sft']
    report = dict(comparisons=comparisons, costs=costs, sources=sources,
        matched_start_tasks_and_eval_prompts=True,
        limitations='Exploratory exposed dev, one seed. Same 24 updates, different learning rate/dropout, sampled token exposure and GPU costs; algorithm recipes, not loss-only or equal-compute comparison. No checkpoint selection.')
    (args.grpo / 'sft_grpo_comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(dict(comparisons=comparisons, limitations=report['limitations']), indent=2))


if __name__ == '__main__':
    main()
