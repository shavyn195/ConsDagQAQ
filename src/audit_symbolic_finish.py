"""Compare under identical final-stage requirements, verifying edits with predicted rules only."""
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
from trust_env import check,normalize_constraint,default_plan


def normalized(t,p,cs):
    if not p or shape(p,t):return p
    edit=[a for a in p if a not in t["finish"]]+[a for a in p if a in t["finish"]]
    if shape(edit,t) and check(t,edit,cs)["safe_success"]:
        return edit
    return p


def main(folder):
    cache={}; prot=read(folder/"protocol.json")
    for sp in SPLITS:
        dp=ROOT/f"data/processed_v4/{sp}.jsonl";pc=COMP/f"trained_predictions/{sp}.jsonl"
        rows=load_jsonl(dp)
        assert [digest(dp),digest(pc)]==prot["sources"][sp]
        cache.update({r["sample_id"]:(r,p) for r,p in zip(rows,aligned(rows,load_jsonl(pc)),strict=True)})
    path=folder/"cases.jsonl"
    assert digest(path)==read(folder/"results.json")["cases"]
    totals={s:Counter() for s in SPLITS}
    pair_ids=[]
    for x in load_jsonl(path):
        r,p=cache[x["id"]];pair_ids.append(x["id"]); t=r["task"]
        cs=[c for c in (strict_parse(p) or {}).get("constraints",[]) if normalize_constraint(c,t) is not None]
        old=x["actions"]["symbolic"];new=normalized(t,old,cs)
        gold=r["gold"]["constraints"];c=totals[r["subset"]]
        if gold:
            old_res=check(t,old,gold);new_res=check(t,new,gold)
            old_ok=bool(shape(old,t) and old_res["safe_success"]);new_ok=bool(shape(new,t) and new_res["safe_success"])
            assert old_ok==x["safe"]["symbolic"]
            c.update(n=1,adjusted=(new!=old),env_original=old_res["safe_success"],orig=old_ok,normalized=new_ok,
                     hybrid=x["safe"]["repair"],hybrid_only=bool(x["safe"]["repair"] and not new_ok),
                     normalized_only=bool(new_ok and not x["safe"]["repair"]))
        else:c.update(none=1,normalized_default=new==default_plan(t))
    assert pair_ids==prot["ids"]
    report=dict(by_split=totals,script=digest(Path(__file__)),source=digest(path))
    (folder/"normalized-symbolic.json").write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--full",action="store_true")
    main(LARGE if p.parse_args().full else SMALL)
