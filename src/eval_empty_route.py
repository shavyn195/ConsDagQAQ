"""Route only a well-formed explicit empty record to the public default plan."""
import argparse
from collections import Counter
import json
from pathlib import Path
from audit_warmup_rollouts import shape
from confirm_one_edit import OUT as SMALL
from eval_repair_sft import SPLITS,read
from full_one_edit import OUT as LARGE
from prepare_e2_credit_panel import COMP
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import aligned,digest,load_jsonl
from run_e1 import strict_parse
from trust_env import check,default_plan


def route(p,t,previous):
    obj=strict_parse(p)
    empty=(obj is not None and obj["query_state"]=="none" and obj["constraints"]==[]
           and obj.get("abstain",False) is False)
    return (default_plan(t) if empty else previous),empty


def main(folder):
    rows={}
    prot=read(folder/"protocol.json")
    for sp in SPLITS:
        src=ROOT/f"data/processed_v4/{sp}.jsonl";pc=COMP/f"trained_predictions/{sp}.jsonl"
        data=load_jsonl(src)
        assert [digest(src),digest(pc)]==prot["sources"][sp]
        rows.update({r["sample_id"]:(r,p) for r,p in zip(data,aligned(data,load_jsonl(pc)),strict=True)})
    file=folder/"cases.jsonl"; xs=load_jsonl(file)
    assert digest(file)==read(folder/"results.json")["cases"] and [x["id"] for x in xs]==prot["ids"]
    report={sp:Counter() for sp in SPLITS}
    for x in xs:
        r,p=rows[x["id"]];t=r["task"]
        old=x["actions"]["repair"]
        a,eligible=route(p,t,old)
        gold=r["gold"]["constraints"]
        c=report[r["subset"]]
        safe=bool(shape(a,t) and check(t,a,gold)["safe_success"]); before=x["safe"]["repair"]
        if gold:
            c.update(constrained=1,old_safe=int(before),routed_safe=int(safe),false_empty=int(eligible),
                     wins=int(safe and not before),losses=int(before and not safe))
        else:
            c.update(none=1,old_default=int(old==default_plan(t)),new_default=int(a==default_plan(t)),true_empty=int(eligible))
    out=dict(by_split=report,source=digest(file),code=digest(Path(__file__)),
             note="post hoc on 120-panel; rule locked before reading full outcomes, nested panels; no live latency/savings inferred")
    tag=folder/"empty-route.json";tag.write_text(json.dumps(out,indent=2));print(json.dumps(report))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--full",action="store_true");args=parser.parse_args()
    main(LARGE if args.full else SMALL)
