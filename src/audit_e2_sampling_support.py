"""Diagnose on-policy sampling coverage on completed v1 traces using train gold only after generation."""
from collections import Counter
from itertools import product
from pathlib import Path
import json
from audit_warmup_rollouts import shape
from prepare_e2_credit_panel import OUT
from probe_e2_format import parse
from probe_e2_planner_v1 import DATA
from rescore_v4_side import digest, load_jsonl
from trust_env import check


def main():
    panel=json.loads((OUT/"panel.json").read_text())
    assert digest(DATA)==panel["data"]["train"]
    rows={r["sample_id"]:r for r in load_jsonl(DATA)}
    report={}
    for arm,seed in product(("function","trace","action","shifted"),(42,43,44)):
        folder=OUT/f"{arm}-s{seed}"
        assert (folder/"done.json").is_file()
        path=folder/"rollouts.jsonl"
        records=load_jsonl(path)
        assert [x["id"] for x in records]==panel["train"]
        counts=Counter()
        for entry in records:
            row=rows[entry["id"]]
            cs=row["gold"]["constraints"]
            if not cs:
                continue
            goldsafe=[]; predsafe=[]; success=[]; plans=set()
            assert len(entry["rollouts"])==4
            for raw in entry["rollouts"]:
                actions=parse(raw["raw"],sorted(row["task"]["tools"]),"names")
                assert actions==raw["actions"]
                plans.add(tuple(actions) if actions is not None else None)
                res=check(row["task"],actions,cs)
                done=bool(res["completed"] and shape(actions,row["task"]))
                pred=check(row["task"],actions,entry["cs"])
                assert done==raw["done"] and (not done or pred["violations"]==raw["bad"])
                success.append(done)
                goldsafe.append(bool(done and res["safe_success"]))
                predsafe.append(bool(done and pred["safe_success"]))
            both=any(goldsafe) and any(d and not g for d,g in zip(success,goldsafe,strict=True))
            counts.update(groups=1,unique_plans_sum=len(plans),one_plan_group=len(plans)==1,
                          groups_any_gold_safe=any(goldsafe),groups_all_gold_safe=all(goldsafe),
                          groups_no_gold_safe=not any(goldsafe),groups_safe_and_unsafe_completed=both,
                          groups_only_failures=not any(success),groups_pred_gold_disagree=predsafe!=goldsafe,
                          gold_safe_rollouts=sum(goldsafe),rollouts=len(success))
        assert counts["groups"]==96 and counts["groups_any_gold_safe"]+counts["groups_no_gold_safe"]==96
        report[f"{arm}-{seed}"]=dict(counts=counts,sha256=digest(path))
    out=OUT/"train-sampling-coverage-v1.json"
    out.write_text(json.dumps(dict(source=digest(Path(__file__)),runs=report,
        scope="Descriptive realized on-policy support. A missing fully safe rollout does not imply zero partial-constraint gradient or prove the cause of limited gains."),indent=2))
    print({k:[v["counts"][u] for u in ("groups_no_gold_safe","groups_safe_and_unsafe_completed","one_plan_group","groups_pred_gold_disagree")] for k,v in report.items()})


if __name__=="__main__":
    main()
