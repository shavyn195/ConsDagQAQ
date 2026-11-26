import copy
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts/research_followup'))
from structure_supplement import core_payload, compiler_index, complete_group_ids
from wait_structure_supplement import dependency_ready


def test_projection_preserves_parameters_and_never_turns_invalid_into_none():
    # A numeric budget 12.5 must survive verbatim; an unknown type invalidates the whole interface.
    source={'constraints':[{'type':'budget','params':{'max_total_cost_cny':12.5},'scope':['private-metadata']}]}
    original=copy.deepcopy(source)
    assert core_payload(source,{})=={'interface_status':'valid','constraints':[{'type':'budget','params':{'max_total_cost_cny':12.5}}]}
    assert source==original
    source['constraints'].append({'type':'unknown','params':{}})
    assert core_payload(source,{})=={'interface_status':'invalid','constraints':None}
    assert core_payload(None,{})['interface_status']=='invalid'
    assert core_payload({'constraints':[]},{})=={'interface_status':'valid','constraints':[]}


def test_exact_compiler_calls_required():
    calls=[dict(sample_id='a',call=kind,raw=kind) for kind in ('pe_first','sft_first')]
    assert len(compiler_index(calls,{'a'}))==2
    for invalid in (calls[:1],calls+[calls[0]]):
        try: compiler_index(invalid,{'a'})
        except ValueError: pass
        else: raise AssertionError('Missing/duplicate reference calls must be rejected')


def test_partial_triplet_cannot_enter_paired_estimate():
    # One complete E/I/N group with two arms needs all six decisions, not just E and I.
    rows=[dict(group_id='g',sample_id=v,variant=v) for v in ('explicit','implicit','none')]
    records=[dict(sample_id=r['sample_id'],arm=a) for r in rows for a in ('x','y')]
    assert complete_group_ids(records,rows,['x','y'])=={'g'}
    assert complete_group_ids(records[:-1],rows,['x','y'])==set()


def test_wait_for_active_probe_but_do_not_require_its_hypothesis_to_succeed():
    queue={'status':'complete','active':None}
    done={'status':'complete'}
    assert dependency_ready(queue,done,done,done)
    assert not dependency_ready(queue,done,done,{'status':'running'})
    assert not dependency_ready(queue,{'status':'incomplete'},done,done)
    # The separate inference probe is not an input to structural comparisons.
    assert dependency_ready(queue,done,done,{'status':'incomplete'})
