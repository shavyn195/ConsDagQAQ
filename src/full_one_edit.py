"""Full paired E/I/N coverage of the frozen one-edit method, including prior panels."""
import fcntl
import json
from collections import Counter,defaultdict
from pathlib import Path
import torch
from confirm_one_edit import score
import confirm_one_edit
from eval_e2_credit import decode_config,inputs,load
from eval_repair_sft import DEST,SPLITS,read
from prepare_e2_credit_panel import PARENT,COMP
from probe_e2_planner_v1 import ROOT
from rescore_v4_side import load_jsonl,aligned,digest
import probe_one_edit_repair as rule


OUT=PARENT/"verified-one-edit-full-holdouts-v1"


def main():
    pack=[];hashes={}; ids=[]
    for sp in SPLITS:
        d=ROOT/f"data/processed_v4/{sp}.jsonl";p=COMP/f"trained_predictions/{sp}.jsonl"
        rows=load_jsonl(d)
        hashes[sp]=[digest(d),digest(p)]
        assert len(rows)==1050 and len(set(r["group_id"] for r in rows))==350
        pack.extend(zip(rows,aligned(rows,load_jsonl(p)),strict=True))
    groups=defaultdict(set)
    for r,_ in pack:
        ids.append(r["sample_id"]);groups[r["group_id"]].add(r["variant"])
    assert len(groups)==700 and all(v=={"explicit","implicit","none"} for v in groups.values())
    assert len(ids)==len(set(ids))==2100
    adapter=DEST/"uniform/adapter"
    config=dict(code=digest(Path(__file__)),scoring=digest(Path(confirm_one_edit.__file__)),rule=digest(Path(rule.__file__)),
                sources=hashes,adapter=digest(adapter/"adapter_model.safetensors"),ids=ids,seed=96230,
                sample="all 2100 rows of two previously used E1 splits, includes earlier panels; not an independent replication",
                primary="strict constraint-safe task success: repair vs rerank, by split and by E/I",
                secondary="default-only edit and full symbolic, hash control; N default; report actual token and neighbor costs",
                draws=4,max_new_tokens=160,temperature=.8,batch=4)
    OUT.mkdir(exist_ok=True)
    with (OUT/"run.lock").open("a") as single:
        fcntl.flock(single,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pp=OUT/"protocol.json"
        if pp.exists(): assert config==read(pp)
        else:
            with pp.open("x") as f:json.dump(config,f)
        rawpath=OUT/"raw.jsonl"; rows=load_jsonl(rawpath) if rawpath.exists() else []
        assert [x["id"] for x in rows]==ids[:len(rows)] and len(rows)%4==0
        with (PARENT/"planner-probe.lock").open("a") as gpu:
            fcntl.flock(gpu,fcntl.LOCK_EX)
            tok,model=load(adapter)
            with rawpath.open("a") as f,torch.inference_mode():
                for i in range(len(rows),len(pack),4):
                    batch=pack[i:i+4];inp=inputs(tok,[r for r,_ in batch])
                    torch.manual_seed(config["seed"]+i)
                    oo=model.generate(**inp,generation_config=decode_config(tok,True))[:,inp.input_ids.shape[1]:].cpu().tolist()
                    assert len(oo)==4*len(batch)
                    chunk=[]
                    for j,(r,pred) in enumerate(batch):
                        part=oo[j*4:j*4+4]
                        part=[a[:a.index(tok.eos_token_id)+1] if tok.eos_token_id in a else a for a in part]
                        chunk.append(json.dumps(dict(id=r["sample_id"],raw=tok.batch_decode(part,skip_special_tokens=True),tokens=sum(map(len,part)))))
                    f.write("\n".join(chunk)+"\n");f.flush()
                    if (i+4)%32==0:print("predictions",i+4,"/2100",flush=True)
            del model,tok
            torch.cuda.empty_cache()
        totals=defaultdict(Counter); bygroup=defaultdict(dict)
        with (OUT/"cases.jsonl").open("w") as f:
            for (r,p),x in zip(pack,load_jsonl(rawpath),strict=True):
                assert x["id"]==r["sample_id"]
                result=score(r,p,x["raw"]);result.update(group=r["group_id"],variant=r["variant"],split=r["subset"])
                key=r["subset"]+"-"+r["variant"]
                totals[key].update(result["flags"]);totals[key].update(generated_tokens=x["tokens"])
                bygroup[r["group_id"]][r["variant"]]=result
                print(json.dumps(result),file=f)
        matched=defaultdict(Counter)
        for group,v in bygroup.items():
            sp=v["explicit"]["split"]
            for m in v["explicit"]["safe"]:
                e=v["explicit"]["safe"][m];i=v["implicit"]["safe"][m]
                matched[sp+"-"+m].update(groups=1,both=e and i,explicit_only=e and not i,implicit_only=i and not e,neither=not e and not i)
        result=dict(by_split_variant=totals,by_paired_group=matched,raw=digest(rawpath),cases=digest(OUT/"cases.jsonl"))
        (OUT/"results.json").write_text(json.dumps(result,indent=2));print("complete: 2100",flush=True)


if __name__=="__main__":
    main()
