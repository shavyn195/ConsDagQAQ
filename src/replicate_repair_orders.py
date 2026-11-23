"""Repeat the paired pilot with the same examples, two other presentation orders."""
import fcntl
import gc
import json
import random
from pathlib import Path

import torch
import eval_repair_sft as ev
import train_repair_sft as tr
from rescore_v4_side import digest, load_jsonl


def main():
    source=ev.DEST
    out=ev.PARENT/"verified-repair-sft-1.7B-orders-v1"
    out.mkdir(exist_ok=False)
    plan=dict(orders=[43,44],initialization=42,sampling_seed=91011,
              comparison="vary training example order only; both arms paired within each order",
              primary="constrained four-candidate safe coverage; secondary selected safe, N default",
              original_train=digest(source/"train-pairs.jsonl"),panel=digest(source/"panel.json"),
              train_code=digest(Path(tr.__file__)),eval_code=digest(Path(ev.__file__)),code=digest(Path(__file__)))
    (out/"protocol.json").write_text(json.dumps(plan,indent=2))
    with (ev.PARENT/"planner-probe.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        assert (source/"paired.json").is_file()
        rows=tr.training_rows()
        master=load_jsonl(source/"train-pairs.jsonl")
        assert [p["id"] for p in master]==[r["sample_id"] for r in rows]
        for order in plan["orders"]:
            fold=out/f"order-{order}"
            fold.mkdir(exist_ok=False)
            ev.DEST=tr.DEST=fold
            (fold/"warm").symlink_to(source/"warm",target_is_directory=True)
            ev.freeze()
            assert digest(fold/"panel.json")==plan["panel"]
            indices=list(range(len(rows))); random.Random(order).shuffle(indices)
            batch=[rows[i] for i in indices]; pairs=[master[i] for i in indices]
            (fold/"train-order.json").write_text(json.dumps([p["id"] for p in pairs]))
            info=[]
            for arm in ("uniform","repair"):
                print("order",order,arm,flush=True)
                info.append(tr.train_arm(arm,batch,pairs))
                gc.collect();torch.cuda.empty_cache()
            assert info[0]==info[1]
            for arm in ("uniform","repair"):
                ev.evaluate(arm)
                gc.collect();torch.cuda.empty_cache()
            tr.finish()
    reports=[ev.read(p/"paired.json") for p in (source,out/"order-43",out/"order-44")]
    (out/"all-orders.json").write_text(json.dumps(reports,indent=2))


if __name__=="__main__":
    main()
