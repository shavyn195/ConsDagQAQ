"""Read-only scoring of all transfer responses; split failures into completion and compliance."""
from collections import Counter
import json
from audit_warmup_rollouts import shape
from eval_e2_transfer_frozen import DEST, SPLITS, SEEDS, ARMS
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import digest, load_jsonl
from trust_env import check, default_plan


def main():
    cfg=json.loads((DEST/"protocol.json").read_text())
    by={}
    for sp in SPLITS:
        data=ROOT/f"data/processed_v4/{sp}.jsonl"
        assert digest(data)==cfg["data"][sp]
        by.update({r["sample_id"]:r for r in load_jsonl(data)})
    assert len(cfg["ids"])==len(set(cfg["ids"]))==240
    out={}
    for arm in ARMS:
        for seed in SEEDS:
            source=DEST/f"{arm}-{seed}.jsonl"
            obs=load_jsonl(source)
            assert [x["id"] for x in obs]==cfg["ids"]
            mid={sp:Counter() for sp in SPLITS}
            for x in obs:
                r=by[x["id"]]
                acts=parse(x["raw"],sorted(r["task"]["tools"]),"names")
                res=check(r["task"],acts,r["gold"]["constraints"])
                done=bool(res["completed"] and shape(acts,r["task"]))
                safe=bool(done and res["safe_success"])
                assert (done,safe)==(x["done"],x["safe"])
                if r["variant"]=="none":
                    mid[r["subset"]].update(none=1,default=int(safe and acts==default_plan(r["task"])))
                else:
                    mid[r["subset"]].update(constrained=1,incomplete=int(not done),violating=int(done and not safe),safe=int(safe))
            for sp,v in mid.items():
                old=json.loads(source.with_suffix(".json").read_text())[sp]
                assert v["constrained"]==v["incomplete"]+v["violating"]+v["safe"]==80
                assert v["safe"]==old["safe_constrained"] and v["default"]==old["none_faithful"]
            out[f"{arm}-{seed}"]=dict(counts=mid,raw=digest(source))
    (DEST/"rechecked-failures.json").write_text(json.dumps(out,indent=2))
    print({k:v["counts"] for k,v in out.items() if k.startswith("trace-")})


if __name__=="__main__":
    main()
