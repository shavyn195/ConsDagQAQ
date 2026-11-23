"""Check catalog scope on cached test groups outside the evidence panel, without model updates."""
import json
from collections import Counter
from audit_evidence_panel import equivalent, read_object
from build_evidence_panel import MODELS, OUT, ROOT, SPLITS, digest, write_json
from diagnose_evidence_scope import derive
from rescore_v4_side import aligned, load_jsonl
from run_e1 import core_key, strict_parse


def main():
    groups={r["group"] for r in map(json.loads,(OUT/"panel.jsonl").read_text().splitlines())}
    report={}
    for size in MODELS:
        by_split={}
        for split in SPLITS:
            source=ROOT/f"data/processed_v4/{split}.jsonl"
            pred_path=ROOT/f"outputs/e1/Qwen3-{size}-v4/trained_predictions/{split}.jsonl"
            rows=load_jsonl(source)
            pred=aligned(rows,load_jsonl(pred_path))
            tally=Counter(n=0,old=0,new=0,gains=0,losses=0)
            for r,raw in zip(rows,pred,strict=True):
                if r["group_id"] in groups or r["variant"] == "none":
                    continue
                out=derive(raw,r["catalog"])
                x,y=strict_parse(raw),strict_parse(out)
                assert (x is None)==(y is None)
                if x is not None:
                    assert [core_key(c) for c in x["constraints"]]==[core_key(c) for c in y["constraints"]]
                    assert x.get("abstain",False)==y.get("abstain",False) and x["query_state"]==y["query_state"]
                old=equivalent(r["gold"],x)
                new=equivalent(r["gold"],y)
                tally.update(n=1,old=old,new=new,gains=new and not old,losses=old and not new)
            by_split[split]=dict(tally,raw_sha256=digest(pred_path))
        report[size]=by_split
    write_json(OUT/"scope_other_groups.json",report)
    print(report)


if __name__=="__main__":
    main()
