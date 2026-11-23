"""Development-only pilot. Select an interpretation using a public distinguishing plan."""
import fcntl
import hashlib
import json
from collections import Counter
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from audit_warmup_rollouts import shape
from dataset_v4_spec import POLICY_CARD
from eval_exec import record_outcome
from prepare_e2_credit_panel import COMP, PARENT
from probe_e2_planner_v1 import ROOT, MODEL
from probe_one_edit_repair import edits
from rescore_v4_side import aligned, digest, load_jsonl
from run_e1 import strict_parse
from trust_env import check, default_plan, execute, normalize_constraint, plan

OUT = PARENT / "semantic-disagreement-dev-v1"
ARMS = ("direct","random","separating")


def rules(record, task):
    if record is None:
        return None
    cs = record["constraints"]
    if any(normalize_constraint(c,task) is None for c in cs):
        return None
    return cs


def canon(cs):
    return sorted(json.dumps([c["type"],c["params"]],sort_keys=True) for c in cs)


def probes(row, records):
    task = row["task"]
    hypotheses = [rules(r,task) for r in records]
    if None in hypotheses or canon(hypotheses[0]) == canon(hypotheses[1]):
        return None
    roots = [default_plan(task), *(plan(task,c)[0] for c in hypotheses)]
    neighborhood = set()
    for start in roots:
        if not start: continue
        normalized = [a for a in start if a not in task["finish"]] + [a for a in start if a in task["finish"]]
        for v in [normalized,*edits(task,normalized)]:
            if shape(v,task) and check(task,v,[])["completed"]:
                neighborhood.add(tuple(v))
    ordered = sorted(neighborhood,key=lambda v:hashlib.sha256(json.dumps([row["sample_id"],v]).encode()).digest())
    def describe(v):
        trace = execute(task,list(v))
        return dict(actions=v,total_yuan=trace["cost"],total_minutes=trace["minutes"],external_data_transfers=trace["leaks"],
                    permits=[check(task,list(v),cs)["safe_success"] for cs in hypotheses])
    for v in ordered:
        case=describe(v)
        if case["permits"][0]!=case["permits"][1]:
            return hypotheses, describe(ordered[0]), case
    return None


def message(row,item,arm,flip):
    cs, random_case, witness = item
    order=(1,0) if flip else (0,1)
    parts=[POLICY_CARD, "User request: "+row["query"], "Which proposed constraint record most faithfully expresses the user's intent?"]
    for label,j in zip("AB",order):
        fields=[{k:c[k] for k in ("type","params","evidence_span") if k in c} for c in cs[j]]
        parts.append(label+" = "+json.dumps(fields,separators=(",",":")))
    if arm != "direct":
        case = dict(witness if arm=="separating" else random_case)
        ab=case.pop("permits")
        parts.append("A hypothetical completed plan and its observed effects: "+json.dumps(case,separators=(",",":")))
        parts.append("Would this behavior be permitted? Record A predicts "+str(ab[order[0]])+", record B predicts "+str(ab[order[1]])+".")
    parts.append("Use the user's words and stated policy. Output the letter A or B only.")
    return "\n".join(parts)


def faithful(row,rec):
    v=record_outcome(row,rec)
    return bool(rec is not None and v["safe_success"] and (v["extra_changes"]==0 if row["gold"]["constraints"] else not v["deviates_from_default"]))


def main():
    files=[ROOT/"data/processed_v4/dev.jsonl",COMP/"trained_predictions/dev.jsonl",
           ROOT/"outputs/e1_v4_side/qwen-max-zero/dev.jsonl"]
    rows=load_jsonl(files[0]); raw=[aligned(rows,load_jsonl(f)) for f in files[1:]]
    OUT.mkdir(exist_ok=False)
    protocol=dict(data=[digest(p) for p in files],script=digest(Path(__file__)),model=str(MODEL),
                  population="all 900 v4 dev rows; fallback first compiler if records invalid, same, or no separating plan found",
                  sources=["trained 0.6B","cached qwen-max zero-shot"],primary="faithful execution, identical candidates and blind 1.7B verifier",
                  arms=ARMS,limitations="extra prompt tokens for traces, random-trace control; same dev already used by E1, paired rows nest in groups")
    (OUT/"protocol.json").write_text(json.dumps(protocol,indent=2))
    records=[[strict_parse(column[i]) for column in raw] for i in range(len(rows))]
    items=[probes(r,rs) for r,rs in zip(rows,records)]
    keys=[(i,arm,flip) for i,item in enumerate(items) if item for arm in ARMS for flip in (False,True)]
    print("Eligible disagreements",len(keys)//6,"of",len(rows),flush=True)
    logits={}
    if keys:
        with (PARENT/"planner-probe.lock").open("a") as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            tok=AutoTokenizer.from_pretrained(MODEL,local_files_only=True,padding_side="left")
            if tok.pad_token_id is None:tok.pad_token=tok.eos_token
            model=AutoModelForCausalLM.from_pretrained(MODEL,dtype=torch.bfloat16,device_map="cuda",local_files_only=True).eval()
            targets=[tok.encode(x,add_special_tokens=False) for x in "AB"]
            assert all(len(v)==1 for v in targets)
            with torch.inference_mode():
                for start in range(0,len(keys),8):
                    batch=keys[start:start+8]
                    texts=[tok.apply_chat_template([dict(role="user",content=message(rows[i],items[i],a,f))],tokenize=False,add_generation_prompt=True,enable_thinking=False) for i,a,f in batch]
                    inp=tok(texts,padding=True,return_tensors="pt",add_special_tokens=False).to(model.device)
                    log=model(**inp,use_cache=False,logits_to_keep=1).logits[:,-1,:].float()
                    for key,v in zip(batch,(log[:,targets[0][0]]-log[:,targets[1][0]]).tolist(),strict=True):
                        logits[key]=v
    summary=Counter(); opportunities=Counter()
    with (OUT/"cases.jsonl").open("x") as file:
        for i,(row,rs,item) in enumerate(zip(rows,records,items,strict=True)):
            picks={a:int(logits[i,a,False]<logits[i,a,True]) if item else 0 for a in ARMS}
            score=[faithful(row,r) for r in rs]
            picks.update(first=0,second=1)
            for a,j in picks.items():summary[a]+=score[j]
            summary["unrestricted_oracle"]+=any(score)
            summary["eligible_oracle"]+=any(score) if item else score[0]
            if item:
                opportunities.update(n=1,first_only=score[0] and not score[1],second_only=score[1] and not score[0],
                                     direct_wins=score[picks["direct"]] and not score[picks["separating"]],
                                     separating_wins=score[picks["separating"]] and not score[picks["direct"]])
            margins={a:[logits[i,a,False],logits[i,a,True]] for a in ARMS} if item else {}
            print(json.dumps(dict(id=row["sample_id"],group=row["group_id"],eligible=bool(item),picks=picks,correct=score,
                                  margins=margins,probes=item[1:] if item else [])),file=file)
    out=dict(n=len(rows),correct=summary,opportunities=opportunities,raw=digest(OUT/"cases.jsonl"))
    (OUT/"results.json").write_text(json.dumps(out,indent=2));print(json.dumps(out))


if __name__=="__main__":
    main()
