"""Compare frozen 1.7B SFT to ten-shot PE on individually rewritten task restrictions."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from copy import deepcopy
import json
import os
from pathlib import Path
import random

from diagnose_evidence_scope import derive
from pe_v4_side import demonstrations, fingerprint, restore
from rescore_v4_side import ROOT, digest, load_jsonl, outcome
from run_cross_family_pe import MODEL, PARAMS, request
from run_e1 import chat_messages_v4, generate_batched, load_model, strict_parse
from score_evidence_panel import exact_object
from trust_env import check

OUT = ROOT/"outputs/authored_wording_v1"
SOURCE = ROOT/"configs/authored_wording_v1.txt"
ARMS = ("active","history","mixed")


def make_panel():
    base = ROOT/"data/processed_v4"
    source_rows = [r for s in ("test_tpl_ho","test_tool_ho") for r in load_jsonl(base/(s+".jsonl"))]
    indexed = {r["sample_id"]:r for r in source_rows}
    packet = ROOT/"outputs/dataset_audit/v4-implicit-human-review-v1/reviewer-A/review.csv"
    with packet.open(encoding="utf-8-sig") as f:
        review_queries = {r["query"] for r in csv.DictReader(f)}
    excluded = {r["group_id"] for r in source_rows if r["query"] in review_queries}
    excluded.update(r["group"] for r in load_jsonl(ROOT/"outputs/evidence_edits_v1/panel.jsonl"))
    panel = []
    for index, line in enumerate(SOURCE.read_text(encoding="utf8").splitlines()):
        if not line.strip():
            continue
        key, state, active, history = line.split("|")
        base_row = indexed[key]
        assert base_row["group_id"] not in excluded and len(base_row["gold"]["constraints"]) == 1
        excluded.add(base_row["group_id"])
        assert check(base_row["task"],base_row["witness_plan"],base_row["gold"]["constraints"])["safe_success"]
        assert not check(base_row["task"],base_row["default_plan"],base_row["gold"]["constraints"])["safe_success"]
        for arm in ARMS:
            r = deepcopy(base_row)
            old = r["gold"]["constraints"][0]
            r["kind"] = old["type"]
            r["arm"] = arm
            r["sample_id"] = key+"-"+arm
            r["variant"] = state if arm!="history" else "none"
            r["gold"] = dict(query_state=r["variant"],constraints=[] if arm=="history" else [dict(old,state=state,evidence_span=active)])
            comparison = [active,history] if index%2==0 else [history,active]
            r["query"] = " ".join([r["task_goal"],*({"active":[active],"history":[history],"mixed":comparison}[arm])])
            panel.append(r)
    assert len(panel)==60 and len({r["query"] for r in panel})==60
    known = {r["query"] for r in source_rows} | {r["query"] for r in load_jsonl(base/"train.jsonl")}
    assert all(r["query"] not in known for r in panel)
    random.Random(34791).shuffle(panel)
    OUT.mkdir(exist_ok=True,parents=True)
    with (OUT/"panel.jsonl").open("x",encoding="utf8") as f:
        for r in panel:
            print(json.dumps(r),file=f)
    settings = dict(panel_hash=digest(OUT/"panel.jsonl"), author="assistant, written from structured briefs; external human authorship not tested",
          groups=20, arms=ARMS, wording_hash=digest(SOURCE), selection_seed=34791, demonstration_style="PE uses same 10 training examples as previous study; SFT uses frozen v4 prompt",
          score="constrained plan safe_success; false positives on no-constraint arm; full object exact including evidence and state, with same catalog projection; paired by group",
          params=PARAMS, temperature_sft="greedy", max_tokens_sft=384)
    (OUT/"protocol.json").write_text(json.dumps(settings,indent=2))


def run(mode):
    from time import perf_counter
    rows=load_jsonl(OUT/"panel.jsonl")
    proto=json.loads((OUT/"protocol.json").read_text())
    assert proto["panel_hash"]==digest(OUT/"panel.jsonl")
    demo=demonstrations(load_jsonl(ROOT/"data/processed_v4/train.jsonl")) if mode=="pe" else []
    if mode=="pe":
        previous=json.loads((ROOT/f"outputs/e1_v4_side/{MODEL}-few/config.json").read_text())
        assert fingerprint(demo)==previous["demo_hash"] and PARAMS==previous["params"]
    def messages(r):
        system,user=chat_messages_v4(r)
        return [system,*demo,user]
    hashes={r["sample_id"]:fingerprint([PARAMS if mode=="pe" else mode,messages(r)]) for r in rows}
    path=OUT/(mode+".jsonl")
    done=restore(path,hashes)
    missing=[r for r in rows if r["sample_id"] not in done]
    if not missing:
        return
    with path.open("a",encoding="utf8") as f:
        if mode=="sft":
            from peft import PeftModel
            model,tok=load_model(str(ROOT/"models/Qwen3-1.7B"),"bf16")
            model=PeftModel.from_pretrained(model,ROOT/"outputs/e1/Qwen3-1.7B-v4/adapter").eval()
            for start in range(0,len(missing),20):
                batch=missing[start:start+20]
                t=perf_counter()
                _,raw=generate_batched(model,tok,batch,384,len(batch))
                elapsed=perf_counter()-t
                for r,ans in zip(batch,raw,strict=True):
                    k=r["sample_id"]
                    print(json.dumps(dict(sample_id=k,request_hash=hashes[k],raw=ans,batch_time_s=elapsed,batch_n=len(batch))),file=f,flush=True)
                print(mode,start+len(batch),flush=True)
        else:
            def call(r):
                k=r["sample_id"]
                t=perf_counter()
                value=request(messages(r))
                return dict(sample_id=k,request_hash=hashes[k],**value,elapsed=perf_counter()-t)
            with ThreadPoolExecutor(max_workers=4) as pool:
                for start in range(0,len(missing),4):
                    for x in pool.map(call,missing[start:start+4]):
                        print(json.dumps(x),file=f,flush=True)
                    print(mode,min(start+4,len(missing)),flush=True)


def score():
    rows=load_jsonl(OUT/"panel.jsonl")
    summary={}
    results={}
    for method in ("sft","pe"):
        answers=load_jsonl(OUT/(method+".jsonl"))
        raw={r["sample_id"]:r["raw"] for r in answers}
        assert len(answers)==len(raw)==len(rows) and set(raw)=={r["sample_id"] for r in rows}
        mapped={}
        for r in rows:
            k=r["sample_id"]
            text=raw[k]
            parsed=strict_parse(derive(text,r["catalog"]))
            ok=parsed is not None and not parsed.get("abstain",False)
            items=parsed["constraints"] if ok else []
            gold=r["gold"]["constraints"]
            full=ok and parsed["query_state"]==r["variant"] and Counter(map(exact_object,items))==Counter(map(exact_object,gold))
            obs=outcome(r,text)
            mapped[k]=dict(arm=r["arm"],group=r["group_id"],subset=r["subset"],variant=r["variant"],full=full,
                           parsed=parsed is not None, hallucination=ok and bool(items) and not gold,
                           safe=obs["safe_success"],faithful=obs["faithful_success"])
        results[method]=mapped
        summary[method]={a:dict(n=20,**{k:sum(bool(v[k]) for v in mapped.values() if v["arm"]==a)
                                  for k in ("parsed","full","safe","faithful","hallucination")}) for a in ARMS}
    summary["paired_wins"]={}
    for a in ARMS:
        keys=[k for k,v in results["sft"].items() if v["arm"]==a]
        for metric in ("full","safe","faithful"):
            summary["paired_wins"][a+"_"+metric]=dict(Counter(
                    "sft_only" if results["sft"][k][metric] and not results["pe"][k][metric] else
                    "pe_only" if results["pe"][k][metric] and not results["sft"][k][metric] else "tie" for k in keys))
    (OUT/"paired.json").write_text(json.dumps(results))
    (OUT/"scores.json").write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("build","sft","pe","score"))
    mode=p.parse_args().mode
    if mode=="build":
        make_panel()
    elif mode=="score":
        score()
    else:
        run(mode)
