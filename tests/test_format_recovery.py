import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts/research_followup'))
from format_recovery import explicit_messages,smoke_gate,string_array
from audit_fixed_interface import audit


def test_format_gate_does_not_select_on_parser_success():
    cfg=dict(smoke_groups=2,arms=['direct','sft','oracle_core'],smoke_min_string_arrays_per_arm=5,
             smoke_min_valid_direct_and_oracle=3)
    records=[dict(arm=a,string_array=True,outcome=dict(planned=i<3,faithful_success=a=='direct'))
             for a in cfg['arms'] for i in range(6)]
    assert smoke_gate(records,cfg)['passed']
    for r in records: r['outcome']['faithful_success']=not r['outcome']['faithful_success']
    assert smoke_gate(records,cfg)['passed']
    records[0]['string_array']=False; records[1]['string_array']=False
    assert not smoke_gate(records,cfg)['passed']


def test_no_posthoc_object_acceptance_in_string_schema():
    assert string_array('["a","b"]')
    assert not string_array('[{"role":"a"}]')
    assert not string_array('[]')


def test_diagnostic_does_not_invent_roles_from_display_text():
    assert audit('[{"display_name":"a"}]',{})['normalized_plan'] is None
    assert audit('[{"role":"a","tool":"b"}]',{})['normalized_plan'] is None
