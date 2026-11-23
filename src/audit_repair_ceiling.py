"""Gold-only diagnostic on the same raw candidates and the declared one-edit neighborhood."""
from collections import Counter,defaultdict
import json
from pathlib import Path

from audit_warmup_rollouts import shape
from full_one_edit import OUT
from eval_repair_sft import read,SPLITS
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from probe_one_edit_repair import edits
from rescore_v4_side import digest,load_jsonl
from trust_env import check


def classify(row,raw,out):
    task=row["task"];gold=row["gold"]["constraints"]
    candidates=[parse(v,sorted(task["tools"]),"names") for v in raw]
    valid=[a for a in candidates if shape(a,task) and check(task,a,[])["completed"]]
    direct=any(check(task,a,gold)["safe_success"] for a in valid)
    solved=out["safe"]["repair"]
    if solved:
        assert check(task,out["actions"]["repair"],gold)["safe_success"] and shape(out["actions"]["repair"],task)
        return "solved_original_available" if direct else "solved_by_edit"
    if not valid:return "no_complete_plan"
    if direct:return "original_available_but_missed"
    neighborhood={tuple(b) for a in valid for b in edits(task,a) if shape(b,task)}
    return ("safe_edit_available_but_missed" if any(check(task,list(b),gold)["safe_success"] for b in neighborhood)
            else "no_safe_neighbor")


def audit(folder):
    source=read(folder/"results.json");inputs=read(folder/"protocol.json")
    for f,k in (("raw.jsonl","raw"),("cases.jsonl","cases")):
        assert digest(folder/f)==source[k]
    by={}; per=defaultdict(Counter);by_variant=defaultdict(Counter)
    for sp in SPLITS:
        dp=ROOT/f"data/processed_v4/{sp}.jsonl"; assert digest(dp)==inputs["sources"][sp][0]
        by.update({r["sample_id"]:r for r in load_jsonl(dp)})
    for i,(x,y) in enumerate(zip(load_jsonl(folder/"raw.jsonl"),load_jsonl(folder/"cases.jsonl"),strict=True)):
        assert x["id"]==y["id"]==inputs["ids"][i]
        row=by[x["id"]]
        if not row["gold"]["constraints"]:continue
        label=classify(row,x["raw"],y)
        per[row["subset"]][label]+=1
        by_variant[row["subset"]+"-"+row["variant"]][label]+=1
    result=dict(by_split=per,by_variant=by_variant,raw=source["raw"],script=digest(Path(__file__)),
                scope="gold diagnoses support; allowed edits are defined by the public inference rule; none used to choose a deployed plan")
    (folder/"oracle-neighborhood.json").write_text(json.dumps(result,indent=2));print(json.dumps(per))


if __name__=="__main__":
    audit(OUT)
