"""Replay the proposed repair on an unmodified train trajectory file, on CPU."""
import json
from collections import Counter
from pathlib import Path
from prepare_e2_credit_panel import OUT
from probe_e2_planner_v1 import DATA
from rescore_v4_side import digest, load_jsonl
from e2_preventive_credit import score_with_prevention, preventive_advantages


def main():
    dest = OUT/"prevention-train-v1.json"
    source = OUT/"trace-s42/rollouts.jsonl"
    panel = json.loads((OUT/"panel.json").read_text())
    assert digest(DATA)==panel["data"]["train"]
    rows = {r["sample_id"]:r for r in load_jsonl(DATA)}
    records = load_jsonl(source)
    assert [r["id"] for r in records]==panel["train"]
    counts, bytype = Counter(), Counter()
    for g in records:
        t = rows[g["id"]]["task"]
        cs = g["cs"]
        scores = [score_with_prevention(t,r["actions"],cs) for r in g["rollouts"]]
        sizes = [len(r["token_ids"]) for r in g["rollouts"]]
        maps = [{int(k):v for k,v in r["role_positions"].items()} for r in g["rollouts"]]
        assignments=0
        for r,s,mp in zip(g["rollouts"],scores,maps,strict=True):
            assert r["bad"]==s["bad"] and r["done"]==s["done"]
            for i,j in s["protect"].items():
                if mp.get(j) and any(x["done"] and i in x["bad"] for x in scores):
                    bytype[cs[i]["type"]]+=1
                    assignments+=1
        a,v,_=preventive_advantages(scores,sizes,maps,len(cs),"protect")
        b,w,_=preventive_advantages(scores,sizes,maps,len(cs),"protect_shifted")
        assert a==b==g["rewards"]
        changed = any(abs(x-y)>1e-7 for va,wa in zip(v,w,strict=True) for x,y in zip(va,wa,strict=True))
        counts.update(groups=1,changed_groups=int(changed),assignments=assignments,rollouts=len(scores))
    data=dict(counts=counts,by_type=bytype,source=digest(source),code=digest(Path(__file__)),
              mechanism=digest(Path(__file__).with_name("e2_preventive_credit.py")),
              gate="Require >=8/128 train groups with nonidentical matched vs shifted positive credit; no dev/test used.")
    dest.write_text(json.dumps(data,indent=2))
    print(json.dumps(data))


if __name__=="__main__":
    main()
