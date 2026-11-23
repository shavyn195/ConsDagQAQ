"""CPU-only frozen-data coverage, token-budget, and prediction-error audit.

Coverage counts task groups once using E records. Prediction diagnostics retain
all E/I/N records, use gold only for offline measurement, and are descriptive,
not causal evidence. The optional public-scope baseline consumes no gold.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from audit_v5_measurement import executable_key
from public_scope_binding import bind_public_scope
from rescore_v4_side import aligned, outcome
from run_e1 import (chat_messages, constraint_key, core_key, eval_subsets,
                    load_jsonl, render_chat, score, strict_parse, target_json)

ROLE_FIELDS = ('approval_role', 'required_role', 'before_role', 'after_role')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pair_key(c: dict) -> tuple | None:
    params = c['params']
    if c['type'] == 'tool_auth':
        return (c['type'], params.get('approval_role'), params.get('required_role'))
    if c['type'] == 'order':
        return (c['type'], params.get('before_role'), params.get('after_role'))
    return None


def coverage(rows: list[dict], train_rows: list[dict]) -> dict:
    groups = [r for r in rows if r['variant'] == 'explicit']
    if len({r['group_id'] for r in groups}) != len(groups):
        raise ValueError('Duplicate E records for a task group')
    train = [r for r in train_rows if r['variant'] == 'explicit']
    train_roles = {t['role'] for r in train for t in r['catalog']}
    train_pairs = {pair_key(c) for r in train for c in r['gold']['constraints'] if pair_key(c)}
    combos = lambda r: '+'.join(sorted(c['type'] for c in r['gold']['constraints']))
    train_combos = {combos(r) for r in train}
    pairs, role_groups, types, combinations, sizes = (Counter() for _ in range(5))
    numeric = defaultdict(list)
    for row in groups:
        cs = row['gold']['constraints']
        combinations[combos(row)] += 1
        sizes[len(cs)] += 1
        role_groups.update({v for c in cs for k, v in c['params'].items() if k in ROLE_FIELDS})
        for c in cs:
            types[c['type']] += 1
            pair = pair_key(c)
            if pair:
                pairs[pair] += 1
            for key, value in c['params'].items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    numeric[c['type'] + ':' + key].append(value)
    catalogs = {t['role'] for r in groups for t in r['catalog']}
    return {
        'records': len(rows), 'groups': len(groups),
        'constraint_count_per_group': dict(sizes), 'type_group_counts': dict(types),
        'type_combinations': dict(sorted(combinations.items())),
        'groups_with_unseen_type_combination': sum(v for k, v in combinations.items() if k not in train_combos),
        'public_roles': sorted(catalogs), 'roles_unseen_in_training_catalog': sorted(catalogs - train_roles),
        'parameter_role_group_counts': dict(sorted(role_groups.items())),
        'directed_role_pairs': [{'type': k[0], 'first': k[1], 'second': k[2],
                                 'groups': v, 'exact_pair_seen_in_train': k in train_pairs}
                                for k, v in sorted(pairs.items())],
        'numeric_parameters': {k: {'min': min(v), 'max': max(v), 'unique': len(set(v))}
                               for k, v in sorted(numeric.items())},
        'counting_unit': 'one explicit record per task group; E/I are not independent coverage samples',
    }


def error_flags(row: dict, parsed: dict | None, train_roles: set[str]) -> set[str]:
    if parsed is None:
        return {'parse_failure'}
    gold, got = row['gold']['constraints'], parsed['constraints']
    flags = set()
    gold_types, got_types = Counter(c['type'] for c in gold), Counter(c['type'] for c in got)
    if gold_types - got_types:
        flags.add('missing_constraint_type')
    if got_types - gold_types:
        flags.add('extra_constraint_type')
    catalog = {t['role'] for t in row['catalog']}
    emitted = {c['params'][k] for c in got for k in ROLE_FIELDS
               if isinstance(c['params'].get(k), str)}
    if emitted - catalog:
        flags.add('parameter_role_absent_from_public_catalog')
    if (emitted - catalog) & train_roles:
        flags.add('training_role_name_intrusion')
    if parsed['query_state'] != row['variant']:
        flags.add('query_state_error')
    for c in gold:
        matches = [p for p in got if p['type'] == c['type']]
        if len(matches) != 1:
            continue
        p = matches[0]
        if core_key(c) != core_key(p):
            flags.add('same_type_parameter_error')
        keys = ('approval_role', 'required_role') if c['type'] == 'tool_auth' else (
            ('before_role', 'after_role') if c['type'] == 'order' else None)
        if keys and c['params'].get(keys[0]) != c['params'].get(keys[1]):
            if (p['params'].get(keys[0]), p['params'].get(keys[1])) == (
                    c['params'].get(keys[1]), c['params'].get(keys[0])):
                flags.add('reversed_role_pair')
        for field in ('scope', 'severity', 'state', 'evidence_span'):
            a, b = c.get(field), p.get(field)
            if field == 'scope':
                a = sorted(a) if isinstance(a, list) else a
                b = sorted(b) if isinstance(b, list) else b
            if a != b:
                flags.add(field + '_error')
    core_equal = Counter(map(core_key, gold)) == Counter(map(core_key, got))
    world_equal = Counter(executable_key(c, row['task']) for c in gold) == Counter(
        executable_key(c, row['task']) for c in got)
    if not core_equal and world_equal:
        flags.add('different_contract_same_executable_predicates')
    return flags


def prediction_audit(rows: list[dict], predictions: list[dict], train_roles: set[str]) -> dict:
    raw = aligned(rows, predictions)
    counts, failed_counts, groups, group_flags = Counter(), Counter(), set(), defaultdict(set)
    categories, examples, rewritten = defaultdict(Counter), [], []
    for row, text in zip(rows, raw):
        parsed = strict_parse(text)
        flags = error_flags(row, parsed, train_roles)
        original = outcome(row, text)
        # The intervention's entire allowed input is explicit here.
        changed = bind_public_scope(parsed, row['catalog']) if parsed is not None else None
        rewritten_text = json.dumps(changed, ensure_ascii=False) if changed is not None else text
        rewritten.append(rewritten_text)
        altered = outcome(row, rewritten_text)
        if original['faithful_success'] != altered['faithful_success']:
            raise AssertionError('Scope-only baseline unexpectedly changed execution outcome')
        if row['gold']['constraints']:
            counts['constrained_records'] += 1
            groups.add(row['group_id'])
            counts['faithful_success'] += int(original['faithful_success'])
            counts['valid_faithful_success'] += int(parsed is not None and original['faithful_success'])
            counts.update(flags)
            group_flags[row['group_id']].update(flags)
            if not original['faithful_success']:
                failed_counts.update(flags)
                failed_counts['records'] += 1
                if len(examples) < 8:
                    examples.append({'sample_id': row['sample_id'], 'flags': sorted(flags),
                                     'gold': row['gold'], 'predicted': parsed})
            for key in (row['variant'], 'constraints=' + str(len(row['gold']['constraints']))):
                categories[key]['records'] += 1
                categories[key]['faithful_success'] += int(original['faithful_success'])
        else:
            counts['none_records'] += 1
            counts['none_parse_failure'] += parsed is None
            counts['none_false_positive'] += bool(parsed is not None and parsed['constraints'])
            counts['none_deviation'] += bool(original['deviates_from_default'])
    baseline_score = score(rows, [None] * len(rows), raw)
    bound_score = score(rows, [None] * len(rows), rewritten)
    def selected(s):
        return {k: s[k] for k in ('constraint_micro', 'constraint_core_micro', 'record_exact_match')}
    return {'counts': dict(counts), 'constrained_groups': len(groups),
            'groups_with_flag': dict(Counter(f for fs in group_flags.values() for f in fs)),
            'flags_among_faithful_failures': dict(failed_counts),
            'by_variant_or_constraint_count': {k: dict(v) for k, v in categories.items()},
            'public_scope_baseline': {'before': selected(baseline_score), 'after': selected(bound_score),
                'faithful_changes': 0, 'uses_gold': False,
                'meaning': 'scope field correction only; no semantic or execution improvement'},
            'failure_examples': examples,
            'interpretation': 'nonexclusive descriptive flags, not causal attribution; no inferential p-values'}


def length_summary(values: list[int]) -> dict:
    ordered = sorted(values)
    return {'n': len(ordered), 'min': ordered[0], 'max': ordered[-1],
            'median': ordered[len(ordered)//2], 'p95': ordered[int(.95*(len(ordered)-1))]}


def token_audit(data: dict[str, list[dict]], model: Path, seq_limit: int, generation_limit: int) -> dict:
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(model), local_files_only=True)
    result = {'model': str(model), 'max_seq_len': seq_limit, 'max_new_tokens': generation_limit,
              'method': 'exact run_e1 prefix and completion tokenization, CPU only', 'splits': {},
              'tokenizer_sha256': {p.name: sha256(p) for p in model.iterdir() if p.is_file() and
                                  (p.name.startswith('token') or p.name.startswith('chat_template'))}}
    for split, rows in data.items():
        prefix_lengths, target_lengths, totals, dropped = [], [], [], []
        for row in rows:
            prefix = render_chat(tokenizer, chat_messages(row), add_generation_prompt=True)['input_ids']
            target = tokenizer(target_json(row) + tokenizer.eos_token, add_special_tokens=False)['input_ids']
            n_prefix, n_target = int(prefix.shape[-1]), len(target)
            prefix_lengths.append(n_prefix)
            target_lengths.append(n_target)
            totals.append(n_prefix+n_target)
            if n_prefix+n_target > seq_limit:
                dropped.append(row['sample_id'])
        result['splits'][split] = {'prefix': length_summary(prefix_lengths),
            'target_including_eos': length_summary(target_lengths), 'total': length_summary(totals),
            'records_exceeding_training_length': len(dropped), 'exceeding_ids': dropped,
            'targets_exceeding_generation_limit': sum(n > generation_limit for n in target_lengths),
            'note': 'Training length cutoff only applies to train; eval total is diagnostic.'}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--runs', required=True, type=Path)
    parser.add_argument('--arm', action='append', required=True)
    parser.add_argument('--tokenizer-model', action='append', default=[], type=Path)
    parser.add_argument('--max-seq-len', type=int, default=1280)
    parser.add_argument('--max-new-tokens', type=int, default=384)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    splits = ['train'] + eval_subsets(args.data)
    data = {s: load_jsonl(args.data / (s + '.jsonl')) for s in splits}
    data_hashes = {s: sha256(args.data / (s + '.jsonl')) for s in splits}
    expected = json.loads((args.data / 'generation_report.json').read_text())['sha256']
    if any(data_hashes.get(k) != v for k, v in expected.items()):
        raise ValueError('Frozen dataset hash mismatch')
    train_roles = {t['role'] for r in data['train'] for t in r['catalog']}
    report = {'checked_at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
              'source_sha256': data_hashes, 'code_sha256': {p.name: sha256(p) for p in (
                  Path(__file__), Path(__file__).with_name('public_scope_binding.py'),
                  Path(__file__).with_name('run_e1.py'), Path(__file__).with_name('trust_env.py'),
                  Path(__file__).with_name('rescore_v4_side.py'))},
              'coverage': {s: coverage(rows, data['train']) for s, rows in data.items()},
              'arms': {}, 'token_budgets': []}
    for arm in args.arm:
        root = args.runs / arm
        result = {'final_metrics_present': (root / 'metrics.json').is_file(), 'splits': {}}
        for split in splits[1:]:
            path = root / 'trained_predictions' / (split + '.jsonl')
            if not path.exists():
                result['splits'][split] = {'status': 'pending'}
                continue
            result['splits'][split] = {'status': 'complete_split', 'prediction_sha256': sha256(path),
                                       **prediction_audit(data[split], load_jsonl(path), train_roles)}
        report['arms'][arm] = result
        print(json.dumps({'finished_prediction_audit': arm}), flush=True)
    for model in args.tokenizer_model:
        report['token_budgets'].append(token_audit(data, model, args.max_seq_len, args.max_new_tokens))
        print(json.dumps({'finished_tokenizer_audit': str(model)}), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'saved': str(args.out)}), flush=True)


if __name__ == '__main__':
    main()
