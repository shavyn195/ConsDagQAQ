"""Independently replay saved GRPO rewards and diagnose missing training signals.

This analyzes an evolving training policy, not a fixed-policy benchmark and not
evidence that a proposed alternative reward improves held-out performance.
"""
import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from common import evaluate_plan, read_rows, sha
from audit_planner_learning_readout import original_parser
from planner_reward_probe import outcome_vector
from audit_comparison_signal import vector_signal


def group_diagnostics(items):
    """One complete prompt group; no empty constraint vector credited to N."""
    rewards = [r['reward'] for r in items]
    if len(items) < 2 or len({r['draw'] for r in items}) != len(items):
        raise ValueError('Missing or duplicate draws')
    valid = all(r['signal']['valid'] for r in items)
    constrained = any(r['signal']['constraint_passes'] for r in items)
    varying = constrained and len({tuple(r['signal']['constraint_passes']) for r in items}) > 1
    comparison = vector_signal([r['signal']['constraint_passes'] for r in items]) if constrained and valid else None
    return dict(
        prompt_groups=1,
        varying_reward=int(len(set(rewards)) > 1),
        all_reward_zero=int(all(r == 0 for r in rewards)),
        all_reward_one=int(all(r == 1 for r in rewards)),
        all_plans_valid=int(valid),
        constant_reward_varying_constraints_all_valid=int(len(set(rewards)) == 1 and valid and varying),
        all_zero_reward_varying_constraints_all_valid=int(all(r == 0 for r in rewards) and valid and varying),
        constant_reward_but_pass_fraction_varies=int(len(set(rewards)) == 1 and comparison is not None and comparison['pass_rate_varies']),
        constant_reward_but_pareto_order_exists=int(len(set(rewards)) == 1 and comparison is not None and comparison['dominance_edges'] > 0),
        varying_constraints_but_no_pareto_order=int(comparison is not None and comparison['variable_but_no_dominance']),
        safe_but_nonminimal_calls=sum(r['outcome']['safe_success'] and not r['outcome']['faithful_success'] for r in items),
        valid_calls=sum(r['outcome']['planned'] for r in items),
        safe_calls=sum(r['outcome']['safe_success'] for r in items),
        faithful_calls=sum(rewards),
        calls=len(items),
    )


def audit(folder):
    receipt = json.loads((folder.parent / 'receipt.json').read_text())
    for name, expected in receipt.items():
        assert sha(folder / name) == expected, name
    done = json.loads((folder / 'completion.json').read_text())
    assert done['status'] == 'complete' and done['results_sha256'] == sha(folder / 'results.json')
    protocol = json.loads((folder / 'protocol.json').read_text())
    config = protocol['config']
    train_path = ROOT / 'data/processed_v6/train.jsonl'
    assert sha(train_path) == protocol['data_sha256']['train']
    rows = {r['sample_id']: r for r in read_rows(train_path)}
    parser, parser_sha = original_parser()
    report = dict(parser_sha256=parser_sha, modes={}, scope='Replay of saved evolving-policy train rollouts; no new inference or counterfactual training.')
    for mode in ('raw', 'contract'):
        subrun = folder / (mode + '_grpo')
        training = json.loads((subrun / 'training.json').read_text())
        records = read_rows(subrun / 'rollouts.jsonl')
        steps = read_rows(subrun / 'train_steps.jsonl')
        assert len(records) == training['rollouts'] == config['train_rows'] * config['samples_per_prompt']
        grouped = defaultdict(list)
        types = defaultdict(Counter)
        for record in records:
            row = rows[record['sample_id']]
            assert record['input'] == mode
            candidate = parser(record['raw'], row)
            outcome = evaluate_plan(row, candidate)
            signal = outcome_vector(row, candidate)
            assert candidate == record['plan'] and outcome == record['outcome']
            assert signal == record['signal'] and float(outcome['faithful_success']) == record['reward']
            assert record['variant'] == row['variant'] and record['group_id'] == row['group_id']
            assert record['completion'] and record['prefix']
            grouped[record['sample_id']].append(record)
            for i, constraint in enumerate(row['gold']['constraints']):
                count = types[constraint['type']]
                count['all_instances'] += 1
                count['invalid_plan_instances'] += int(not outcome['planned'])
                if outcome['planned']:
                    count['valid_plan_instances'] += 1
                    count['violations_among_valid'] += 1 - signal['constraint_passes'][i]
                count['passed_in_valid_plan'] += int(outcome['planned']) * signal['constraint_passes'][i]
        assert set(grouped) == set(protocol['train_sample_ids'])
        breakdown = defaultdict(Counter)
        for sid, items in grouped.items():
            assert len(items) == config['samples_per_prompt']
            assert {r['draw'] for r in items} == set(range(config['samples_per_prompt']))
            assert len({r['batch'] for r in items}) == 1
            # Recompute analytically rather than calling the training helper.
            mean = sum(r['reward'] for r in items) / len(items)
            sd = math.sqrt(sum((r['reward'] - mean) ** 2 for r in items) / len(items))
            for r in items:
                assert math.isclose(r['advantage'], (r['reward'] - mean) / (sd + config['advantage_epsilon']), abs_tol=1e-12)
            stats = group_diagnostics(items)
            row = rows[sid]
            for label in ('all', row['variant'], 'constraints=' + str(len(row['gold']['constraints']))):
                breakdown[label].update(stats)
        assert breakdown['all']['varying_reward'] == training['variable_reward_groups']
        assert breakdown['all']['all_reward_zero'] == training['zero_reward_groups']
        assert breakdown['all']['faithful_calls'] == training['reward_sum']
        assert training['sample_prompt_tokens'] == sum(len(r['prefix']) for r in records)
        assert training['sample_completion_tokens'] == sum(len(r['completion']) for r in records)
        assert training['backward_completion_tokens'] == config['num_iterations'] * training['sample_completion_tokens']
        assert len(steps) == training['steps'] == training['planned_steps'] == 24
        for i, step in enumerate(steps):
            assert step['step'] == i + 1
            assert all(math.isfinite(step[k]) for k in ('loss', 'grad_norm', 'reward_mean', 'max_ratio_delta'))
            assert all(math.isfinite(v) for v in step['metrics'].values())
            batch = [r for r in records if r['batch'] == step['batch']]
            assert len(batch) == step['rollouts']
            assert set(step['sample_ids']) == {r['sample_id'] for r in batch}
            assert math.isclose(step['reward_mean'], sum(r['reward'] for r in batch) / len(batch))
            if step['iteration'] == 0:
                assert step['max_ratio_delta'] <= config['initial_ratio_tolerance']
        report['modes'][mode] = dict(
            replayed_rollouts=len(records), breakdown=breakdown, constraint_instances=types,
            capped=sum(r['cap_hit'] for r in records),
            update_diagnostics=dict(
                steps=len(steps), max_kl=max(r['metrics']['kl'] for r in steps),
                max_ratio_delta=max(r['max_ratio_delta'] for r in steps),
                second_updates_with_policy_change=sum(r['iteration'] == 1 and r['max_ratio_delta'] > 0 for r in steps),
                reference_unchanged_reported=training['reference_unchanged']),
            cost={k:training[k] for k in ('elapsed_seconds','sample_prompt_tokens','sample_completion_tokens','backward_completion_tokens','sampling_seconds','old_reference_seconds','update_seconds')})
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.folder)
    (args.folder / 'training_readout_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
