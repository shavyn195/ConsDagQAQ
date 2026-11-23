"""Count witness/strict-interface disagreements without modifying any source examples."""
from collections import Counter
import json
from pathlib import Path
from audit_warmup_rollouts import shape
from prepare_e2_credit_panel import PARENT
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import digest,load_jsonl
from trust_env import check,default_plan


def main():
    out=PARENT/"strict-witness-paired-audit-v1"
    out.mkdir(exist_ok=False)
    totals={};sources={}
    with (out/"exceptions.jsonl").open("x") as f:
        for sp in ("train","dev","test_tpl_ho","test_tool_ho"):
            path=ROOT/f"data/processed_v4/{sp}.jsonl";sources[sp]=digest(path)
            tally=Counter(); affected=set()
            for r in load_jsonl(path):
                t=r["task"];cs=r["gold"]["constraints"]
                a=r["witness_plan"] if cs else default_plan(t)
                good=check(t,a,cs)["safe_success"]
                strict=bool(shape(a,t) and good)
                norm=([x for x in a if x not in t["finish"]]+[x for x in a if x in t["finish"]]) if not strict else a
                repaired=bool(shape(norm,t) and check(t,norm,cs)["safe_success"])
                tally.update(n=1,constrained=bool(cs),environment_ok=bool(good),strict_ok=strict,normalized_ok=repaired)
                if not strict:
                    affected.add(r["group_id"])
                    print(json.dumps(dict(id=r["sample_id"],group=r["group_id"],orig=a,
                                          normalized=norm,environment_ok=good,verified=repaired)),file=f)
            tally.update(affected_groups=len(affected));totals[sp]=tally
    report=dict(source=sources,code=digest(Path(__file__)),by_split=totals,exceptions=digest(out/"exceptions.jsonl"))
    (out/"results.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(totals))


if __name__=="__main__":
    main()
