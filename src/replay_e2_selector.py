"""Independently re-rank saved candidates; check ID coverage and paired margins."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from audit_warmup_rollouts import shape
from prepare_e2_credit_panel import PARENT, COMP
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import aligned, digest, load_jsonl
from run_e1 import strict_parse
from trust_env import check, normalize_constraint


def replay(folder,splits):
    prot=json.loads((folder/"protocol.json").read_text())
    results=json.loads((folder/"results.json").read_text())
    source=folder/"cases.jsonl"
    assert digest(source)==results["raw_sha256"]
    raw=load_jsonl(source)
    if "ids" in prot: ids=prot["ids"]
    else:
        ids=json.loads((PARENT/"action-credit-1.7B-pilot-v1/preventive-comparison-v1/protocol.json").read_text())["ids"]
    assert [r["id"] for r in raw]==ids and len(set(ids))==120
    by={}
    for split in splits:
        dp=ROOT/f"data/processed_v4/{split}.jsonl"; pp=COMP/f"trained_predictions/{split}.jsonl"
        for field,p in (("source",dp),("cache",pp)):
            recorded=prot[field]
            assert digest(p)==(recorded[split] if isinstance(recorded,dict) else recorded)
        rows=load_jsonl(dp)
        by.update({r["sample_id"]:(r,t) for r,t in zip(rows,aligned(rows,load_jsonl(pp)),strict=True)})
    counts={}
    for x in raw:
        r,p=by[x["id"]]
        t=r["task"]; gold=r["gold"]["constraints"]
        pred=[c for c in (strict_parse(p) or {}).get("constraints",[]) if normalize_constraint(c,t)]
        acts=[parse(v,sorted(t["tools"]),"names") for v in x["raw"]]
        assert len(acts)==4
        complete=[bool(a and shape(a,t) and check(t,a,[])["completed"]) for a in acts]
        ix=[i for i,ok in enumerate(complete) if ok]
        selected=dict(first=0,functional=ix[0] if ix else 0)
        for k,cs in (("pred",pred),("oracle",gold)):
            selected[k]=min(ix,key=lambda i:len(check(t,acts[i],cs)["violations"])) if ix else 0
        assert selected==x["selected"]
        for k,i in selected.items():
            assert x["safe"][k]==bool(complete[i] and check(t,acts[i],gold)["safe_success"])
        if gold:
            c=counts.setdefault(r["subset"],Counter(n=0,improved=0,regressed=0,uncovered=0,missed_available=0))
            c.update(n=1,improved=x["safe"]["pred"] and not x["safe"]["functional"],
                     regressed=x["safe"]["functional"] and not x["safe"]["pred"],
                     uncovered=not x["safe"]["oracle"],missed_available=x["safe"]["oracle"] and not x["safe"]["pred"])
    out=dict(by_split=counts,raw_sha256=digest(source),script=digest(Path(__file__)))
    (folder/"selection-replay.json").write_text(json.dumps(out,indent=2))
    print(folder.name,json.dumps(counts))


if __name__=="__main__":
    replay(PARENT/"shared-candidate-selection-dev-v1",("dev",))
    replay(PARENT/"shared-candidate-selection-transfer-v1",("test_tpl_ho","test_tool_ho"))
