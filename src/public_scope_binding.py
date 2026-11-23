"""Deterministic v5 scope baseline using only the public catalog and prediction.

This is an interface baseline, not a semantic oracle or a novel learning method.
It does not recover missing constraints, change predicted parameters, or access
the hidden task, reference constraints, witness plan, or evaluator.
"""
from __future__ import annotations

from copy import deepcopy


def bind_public_scope(prediction: dict, catalog: list[dict]) -> dict:
    result = deepcopy(prediction)
    roles = {t['role'] for t in catalog}
    if len(roles) != len(catalog):
        raise ValueError('Public catalog contains duplicate role identifiers')
    for constraint in result['constraints']:
        ctype, params = constraint['type'], constraint['params']
        scope = None
        if ctype == 'budget':
            scope = sorted('role:' + t['role'] for t in catalog if t['paid'])
        elif ctype == 'deadline':
            scope = ['role:*']
        elif ctype == 'privacy':
            scope = sorted('role:' + t['role'] for t in catalog if t['recipient'] == 'external')
        elif ctype in ('tool_auth', 'order'):
            keys = ('required_role',) if ctype == 'tool_auth' else ('before_role', 'after_role')
            values = [params.get(k) for k in keys]
            # An unknown role is a semantic error; never guess a replacement.
            if all(isinstance(v, str) and v in roles for v in values):
                scope = sorted('role:' + v for v in values)
        if scope is not None:
            constraint['scope'] = scope
    return result
