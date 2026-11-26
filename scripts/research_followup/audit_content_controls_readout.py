"""Re-score matched generic/PE controls against the unchanged planner evaluator."""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from common import evaluate_plan, read_rows, sha, summarize, paired
from audit_planner_learning_readout import original_parser
from matched_content_controls import require_same_recipe
from trust_env import check


def verified(folder):
    receipt = json.loads((folder.parent / 'receipt.json').read_text())
    for name, expected in receipt.items():
        assert sha(folder / name) == expected, name
    done = json.loads((folder / 'completion.json').read_text())
    assert done['status'] == 'complete' and done['results_sha256'] == sha(folder / 'results.json')
    return json.loads((folder / 'protocol.json').read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', type=Path, required=True)
    parser.add_argument('--matched', type=Path, default=ROOT / 'outputs/matched_planner_sft_inputs_20261126/results')
    args = parser.parse_args()
    protocol = verified(args.folder)
    prior = verified(args.matched)
    require_same_recipe(protocol['config'], prior['config'])
    assert protocol['train_sample_ids'] == prior['train_sample_ids']
    assert protocol['eval_sample_ids'] == prior['eval_sample_ids']
    assert protocol['initial_adapter_sha256'] == prior['initial_adapter_sha256']
    data = ROOT / 'data/processed_v6/dev.jsonl'
    assert sha(data) == protocol['data_sha256']['dev']
    rows = {r['sample_id']: r for r in read_rows(data)}
    calls = read_rows(args.folder / 'calls.jsonl')
    decisions = read_rows(args.folder / 'decisions.jsonl')
    keyed = {(r['sample_id'], r['arm']): r for r in decisions}
    assert len(calls) == len(decisions) == len(keyed) == 864
    parse, parser_sha = original_parser()
    arms = defaultdict(list)
    details = defaultdict(lambda: defaultdict(Counter))
    for call in calls:
        row = rows[call['sample_id']]
        saved = keyed[(call['sample_id'], call['arm'])]
        candidate = parse(call['raw'], row)
        outcome = evaluate_plan(row, candidate)
        assert candidate == saved['plan'] and outcome == saved['outcome']
        arms[call['arm']].append(outcome)
        for label in (row['variant'], 'constraints=' + str(len(row['gold']['constraints']))):
            d = details[call['arm']][label]
            d['n'] += 1
            for k in ('planned', 'safe_success', 'faithful_success'):
                d[k] += int(outcome[k])
        details[call['arm']]['all']['cap_hits'] += int(call['cap_hit'])
        if candidate is not None:
            checked = check(row['task'], candidate, row['gold']['constraints'])
            for i, constraint in enumerate(row['gold']['constraints']):
                d = details[call['arm']]['type=' + constraint['type']]
                d['valid_plan_instances'] += 1
                d['violated'] += int(i in checked['violations'])
    result = json.loads((args.folder / 'results.json').read_text())
    for arm, outputs in arms.items():
        assert len(outputs) == 144 and {r['sample_id'] for r in outputs} == set(prior['eval_sample_ids'])
        assert summarize(outputs) == result['arms'][arm]
    first = read_rows(args.folder / 'first_stage_calls.jsonl')
    assert len(first) == len({(r['sample_id'], r['mode']) for r in first}) == 192
    baseline_steps = read_rows(args.matched / 'raw_sft/train_steps.jsonl')
    for mode in ('generic', 'pe'):
        steps = read_rows(args.folder / (mode + '_sft/train_steps.jsonl'))
        assert len(steps) == len(baseline_steps) == 24
        assert [r['sample_ids'] for r in steps] == [r['sample_ids'] for r in baseline_steps]
        assert all(math.isfinite(r['loss']) and math.isfinite(r['grad_norm']) for r in steps)
    references = defaultdict(list)
    for r in read_rows(args.matched / 'decisions.jsonl'):
        references[r['arm']].append(r['outcome'])
    comparison = {mode: paired(references['contract_sft/contract'], arms[mode + '_sft/' + mode]) for mode in ('generic', 'pe')}
    assert comparison == result['contract_vs_matched_controls']
    audit = dict(replayed=len(calls), parser_sha256=parser_sha, breakdown=details,
        contract_vs_controls=comparison,
        first_stage={mode:dict(calls=sum(r['mode'] == mode for r in first),
            capped=sum(r['mode'] == mode and r['cap_hit'] for r in first)) for mode in ('generic', 'pe')},
        same_training_order=True,
        scope='Saved complete exploratory dev panels only; fixed original parser and scores; no new model calls.')
    (args.folder / 'readout_audit.json').write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
