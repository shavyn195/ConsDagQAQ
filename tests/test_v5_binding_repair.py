"""Known-answer binding and malformed-output retention checks; no model claims."""
from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from analyze_v5_binding import measure
from analyze_v5_binding_repair import repair_predictions, analyze_repair
from public_role_binding import surface_key
from run_e1 import load_jsonl


def test_opaque_catalog_alias_roundtrip_and_malformed_retention():
    # Oracle semantics expressed in unique public display names have one correct
    # opaque-ID binding; this tests wiring, not model accuracy.
    rows=load_jsonl(ROOT/'data/diagnostic_v5_binding_20261123/opaque_roles.jsonl')
    row=next(r for r in rows if any(c['type'] in ('tool_auth','order') for c in r['gold']['constraints']))
    pred=deepcopy(row['gold'])
    names={t['role']:surface_key(t['name']) for t in row['catalog']}
    for c in pred['constraints']:
        for key in ('approval_role','required_role','before_role','after_role'):
            if key in c['params']:
                c['params'][key]=names[c['params'][key]]
    got,n=repair_predictions([row],[{'sample_id':row['sample_id'],'raw':json.dumps(pred)}])
    assert n == 1
    assert measure([row],got)[0]['core_exact']
    invalid=[{'sample_id':row['sample_id'],'raw':'{invalid'}]
    got,n=repair_predictions([row],invalid)
    assert got==invalid and n==0
    assert measure([row],got)[0]['parse_failure']


def test_wrong_protocol_fails_before_reading_predictions(tmp_path):
    protocol=tmp_path/'protocol.json'
    protocol.write_text(json.dumps({'panel_protocol_sha256':'bad','binder_sha256':{}}))
    with pytest.raises(ValueError,match='panel protocol mismatch'):
        analyze_repair(ROOT/'data/diagnostic_v5_binding_20261123',tmp_path/'runs',protocol,n_boot=100)
