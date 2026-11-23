"""Run the frozen zero/few-shot v4 comparison on the official qwen-max API (CPU)."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError

from rescore_v4_side import ROOT, SUBSETS, digest, load_jsonl, rescore
from run_e1 import chat_messages_v4, target_json
from run_qwen_max_e1 import DEFAULT_URL, request_completion


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def demonstrations(train):
    used = set()
    demo = []
    for kind in ("budget", "deadline", "privacy", "tool_auth", "order"):
        for v in ("explicit", "implicit"):
            row = next(r for r in train if r["variant"] == v and r["group_id"] not in used
                       and [c["type"] for c in r["gold"]["constraints"]] == [kind])
            used.add(row["group_id"])
            demo += [chat_messages_v4(row)[1], {"role":"assistant","content":target_json(row)}]
    return demo


def restore(path, requests):
    cached = {}
    if path.exists():
        for pred in load_jsonl(path):
            key = pred["sample_id"]
            if (key in cached or key not in requests or requests[key] != pred.get("request_hash")
                    or not isinstance(pred.get("raw"),str)):
                raise ValueError("Duplicate, stale or foreign cached prediction: " + key)
            cached[key] = pred
    return cached


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--style", choices=["zero","few"], required=True)
    args = p.parse_args()
    key = os.environ["DASHSCOPE_API_KEY"]
    data = ROOT / "data/processed_v4"
    out = ROOT / "outputs/e1_v4_side" / ("qwen-max-" + args.style)
    out.mkdir(parents=True, exist_ok=True)
    import fcntl  # deployment host is Linux
    lock = (out / ".lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    demo = demonstrations(load_jsonl(data/"train.jsonl")) if args.style == "few" else []
    config = {"model":"qwen-max","endpoint":DEFAULT_URL,"temperature":0,"max_tokens":384,
              "style":args.style,"demo_hash":fingerprint(demo),
              "data_sha256":{s:digest(data/(s+".jsonl")) for s in ["train",*SUBSETS]},
              "runner":digest(Path(__file__))}
    manifest = out/"config.json"
    if manifest.exists():
        if json.loads(manifest.read_text()) != config:
            raise ValueError("Experiment config changed: use a new output directory")
    else:
        with manifest.open("x") as f:
            json.dump(config,f,indent=2)
    for subset in SUBSETS:
        messages = {}
        for r in load_jsonl(data/(subset+".jsonl")):
            sysmsg, user = chat_messages_v4(r)
            messages[r["sample_id"]] = [sysmsg,*demo,user]
        hashes = {k:fingerprint([config,v]) for k,v in messages.items()}
        path = out/(subset+".jsonl")
        cached = restore(path, hashes)
        missing = [k for k in messages if k not in cached]
        def request(k):
            raw,_ = request_completion(api_key=key,url=DEFAULT_URL,model="qwen-max",
                messages=messages[k],max_tokens=384,timeout=90,retries=2)
            return {"sample_id":k,"request_hash":hashes[k],"raw":raw}
        with path.open("a",encoding="utf8") as f, ThreadPoolExecutor(max_workers=2) as pool:
            for i in range(0,len(missing),2):
                for pred in pool.map(request,missing[i:i+2]):
                    f.write(json.dumps(pred,ensure_ascii=False)+"\n")
                    f.flush()
        print(subset,"complete",len(messages),flush=True)
    report = rescore(data,out)
    tmp = out/"scores.tmp"
    tmp.write_text(json.dumps(report,indent=2))
    tmp.replace(out/"scores.json")


if __name__ == "__main__":
    main()
