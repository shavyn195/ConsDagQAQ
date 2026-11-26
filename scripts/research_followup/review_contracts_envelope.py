"""All 18 historical requests with the identical format-only prompt correction."""
import argparse
from pathlib import Path
import review_contracts as base
from review_contracts_format import messages


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','history','cases','model','protocol','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--max-tokens',type=int,default=512)
    p.add_argument('--seconds',type=int,default=5400)
    p.add_argument('--threads',type=int,default=8)
    base.messages=messages
    base.main(p.parse_args())
