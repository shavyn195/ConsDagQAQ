"""Resolve exact normalized public display-name aliases to catalog IDs.

Exploratory interface baseline: no fuzzy matching, learned threshold, hidden
reference, task state, or constraint invention. Ambiguous aliases stay invalid.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import re


def surface_key(text: str) -> str:
    words = re.findall(r'[a-z0-9]+', text.lower())
    if words and words[0] in ('a', 'an', 'the'):
        words = words[1:]
    return '_'.join(words)


def bind_public_roles(prediction: dict, catalog: list[dict]) -> dict:
    roles = {t['role'] for t in catalog}
    if len(roles) != len(catalog):
        raise ValueError('Duplicate public catalog IDs')
    aliases = defaultdict(set)
    for tool in catalog:
        for label in (tool['role'], tool['name']):
            key = surface_key(label)
            if key:
                aliases[key].add(tool['role'])
    bound = deepcopy(prediction)
    for c in bound['constraints']:
        keys = {'tool_auth': ('approval_role', 'required_role'),
                'order': ('before_role', 'after_role')}.get(c['type'])
        if keys is None:
            continue
        old = [c['params'].get(k) for k in keys]
        if not all(isinstance(v, str) for v in old):
            continue
        new = []
        for value in old:
            candidates = aliases.get(surface_key(value), set())
            new.append(next(iter(candidates)) if value not in roles and len(candidates) == 1 else value)
        # Reject a partial or degenerate binding; preserve both original fields.
        if len(set(new)) == 2 and all(v in roles for v in new):
            for key, value in zip(keys, new):
                c['params'][key] = value
    return bound
