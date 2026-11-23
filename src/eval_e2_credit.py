"""Greedy fixed-panel evaluation. Gold is passed only to the post-generation checker."""
import argparse
from collections import Counter, defaultdict
import fcntl
import json
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from audit_warmup_rollouts import shape
from prepare_e2_credit_panel import OUT, WARM, PARENT
from probe_e2_format import parse
from probe_e2_planner_v1 import MODEL, ROOT, prompt
from rescore_v4_side import digest, load_jsonl
from trust_env import check, default_plan


def load(adapter, trainable=False):
    tok = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token
    base = AutoModelForCausalLM.from_pretrained(MODEL, dtype=torch.bfloat16, device_map="cuda", local_files_only=True)
    model = PeftModel.from_pretrained(base, adapter, is_trainable=trainable).eval()
    return tok, model


def inputs(tok, rows):
    text = [tok.apply_chat_template([{"role":"user", "content":prompt(r)}], tokenize=False,
                                    add_generation_prompt=True, enable_thinking=False) for r in rows]
    return tok(text, padding=True, add_special_tokens=False, return_tensors="pt").to("cuda")


def decode_config(tok, sample):
    return GenerationConfig(do_sample=sample, num_return_sequences=4 if sample else 1,
                            temperature=0.8 if sample else 1.0, top_p=1., top_k=0 if sample else 50,
                            max_new_tokens=160, eos_token_id=tok.eos_token_id, pad_token_id=tok.eos_token_id,
                            bos_token_id=tok.bos_token_id)


def evaluate(tok, model, out):
    panel = json.loads((OUT/"panel.json").read_text())
    src = ROOT/"data/processed_v4/dev.jsonl"
    assert digest(src) == panel["data"]["dev"]
    rows = {r["sample_id"]:r for r in load_jsonl(src)}
    rows = [rows[k] for k in panel["dev"]]
    assert len(set(r["group_id"] for r in rows)) == len(rows)
    stats = defaultdict(Counter)
    with (out/"dev.jsonl").open("x") as f, torch.inference_mode():
        for i in range(0, len(rows), 8):
            part = rows[i:i+8]
            inp = inputs(tok, part)
            out_ids = model.generate(**inp, generation_config=decode_config(tok, False))
            for r, ids in zip(part, out_ids[:, inp.input_ids.shape[1]:], strict=True):
                raw = tok.decode(ids, skip_special_tokens=True)
                acts = parse(raw, sorted(r["task"]["tools"]), "names")
                res = check(r["task"], acts, r["gold"]["constraints"])
                done = bool(res["completed"] and shape(acts,r["task"]))
                safe = done and res["safe_success"]
                flags = dict(n=1, completed=int(done), safe=int(safe), faithful=int(safe and
                       (r["variant"] != "none" or acts==default_plan(r["task"]))), calls=len(acts or []),
                       invalid=int(acts is None), violations=len(res["violations"]))
                stats[r["variant"]].update(flags)
                print(json.dumps(dict(id=r["sample_id"],raw=raw,flags=flags)), file=f, flush=True)
    (out/"dev-scores.json").write_text(json.dumps(stats, indent=2))
    print("dev", dict(stats), flush=True)


if __name__ == "__main__":
    lock = (PARENT/"planner-probe.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    p = argparse.ArgumentParser()
    p.add_argument("--arm", default="warm")
    args = p.parse_args()
    dest = OUT/args.arm
    if args.arm == "warm":
        dest.mkdir(exist_ok=False)
    adapter = (WARM if args.arm=="warm" else dest)/"adapter"
    tok, model = load(adapter)
    evaluate(tok, model, dest)
