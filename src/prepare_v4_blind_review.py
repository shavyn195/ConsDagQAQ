"""Make two separately shuffled annotator packets without model outputs or answer keys."""
import csv
import hashlib
import json
from pathlib import Path
import random
from dataset_v4_spec import POLICY_CARD
from run_e1 import catalog_lines

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/dataset_audit/v4-implicit-human-review-v1"
KINDS=("budget","deadline","privacy","tool_auth","order")


def main():
    files=[ROOT/"data/processed_v4"/(s+".jsonl") for s in ("test_tpl_ho","test_tool_ho")]
    rows=[json.loads(line) for f in files for line in f.read_text().splitlines()]
    rng=random.Random(410893)
    rng.shuffle(rows)
    chosen=[]
    seen=set()
    for variant,quota in [("implicit",50),("explicit",10),("none",50)]:
        for typ in (KINDS if variant!="none" else (None,)):
            # Equal representation of the two available held-out splits. Multi-label
            # items are eligible; type is an allocation stratum, not an annotator hint.
            for subset in ("test_tpl_ho","test_tool_ho"):
                pool=[r for r in rows if r["subset"]==subset and r["group_id"] not in seen
                      and r["variant"]==variant and (not typ or any(c["type"]==typ for c in r["gold"]["constraints"]))]
                assert len(pool)>=quota//2,(subset,variant,typ,len(pool))
                for r in pool[:quota//2]:
                    seen.add(r["group_id"])
                    chosen.append((r,typ))
    assert len(seen)==len(chosen)==350
    OUT.mkdir(exist_ok=False)
    key={r["sample_id"]:dict(group=r["group_id"],variant=r["variant"],subset=r["subset"],stratum=k,gold=r["gold"]) for r,k in chosen}
    guide=("Independently read the request, public tool catalog and shared policy card. Do not consult "
           "a model, source dataset, or the other reviewer. Mark one of determinate, no_constraint, ambiguous. "
           "Enter every supported type and its parameter values as JSON, plus verbatim text evidence. "
           "For ambiguous mark what cannot be determined; do not guess a parameter or treat ambiguous as no_constraint. "
           "Budget is total CNY; deadline is hours; privacy needs data classes and forbidden recipients; "
           "authorization needs approval role and required role; order needs before and after role. "
           "Keep initial answers unchanged during later adjudication.\n\nPublic policy card:\n"+POLICY_CARD)
    for label,seed in [("A",93469),("B",53089)]:
        folder=OUT/("reviewer-"+label)
        folder.mkdir()
        part=chosen.copy()
        random.Random(seed).shuffle(part)
        with (folder/"review.csv").open("x",encoding="utf-8-sig",newline="") as f:
            w=csv.writer(f)
            w.writerow(["id","query","public_catalog","decision","types_and_params_json","evidence","ambiguity_reason"])
            for i,(r,_) in enumerate(part):
                ident=f"{label}{i+1:03d}"
                key[r["sample_id"]][label]=ident
                w.writerow([ident,r["query"],catalog_lines(r),"","","",""])
        (folder/"instructions.txt").write_text(guide,encoding="utf8")
    private=OUT/"private"
    private.mkdir()
    (private/"alignment.json").write_text(json.dumps(key,ensure_ascii=False))
    (OUT/"manifest.json").write_text(json.dumps(dict(pending_human_review=True,n=len(key),implicit=250,
        explicit=50,none=50,per_split=175,source={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
        packet_sha256={k:hashlib.sha256((OUT/f"reviewer-{k}"/"review.csv").read_bytes()).hexdigest() for k in ("A","B")},
        sampling="Group-disjoint type-stratified allocation; not population-weighted. Do not send private/ to raters."),indent=2))
    print(f"{len(key)} unique groups, two packets, no human judgments yet")


if __name__=="__main__":
    main()
