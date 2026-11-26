"""One-row format diagnostic; same three review arms, explicit output envelope."""
import argparse
from pathlib import Path
import review_contracts as base
from run_e1 import SCHEMA_HINT_V4

original_messages = base.messages
original_select = base.select_panel


def messages(row, raw, original, arm):
    result = original_messages(row, raw, original, arm)
    result[0]['content'] = ('Return one constraint-contract JSON object. Its only top-level keys are '
                            'query_state and constraints. Input context is not the output object.')
    result[-1]['content'] += ('\nThe response must contain only query_state and constraints. Do not return '
        'public_task, original_plan, untrusted_compiler_output or invalid_field_locations. '
        'Use this output structure (fill values from the request):\n' + SCHEMA_HINT_V4 + '\nContract JSON:')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','history','cases','model','protocol','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--max-tokens',type=int,default=512)
    p.add_argument('--seconds',type=int,default=720)
    p.add_argument('--threads',type=int,default=8)
    base.messages = messages
    base.select_panel = lambda *a: original_select(*a)[:1]
    base.main(p.parse_args())
