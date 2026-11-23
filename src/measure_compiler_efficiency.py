"""Single-request, warm-service compiler latency, native token counts and quality."""
import argparse
from collections import Counter, defaultdict
import ctypes
import errno
import hashlib
import json
import os
from pathlib import Path
import random
import socket
import statistics
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/compiler_efficiency_v1"
SOURCE = ROOT / "outputs/authored_wording_v1/panel.jsonl"
SEED = 112249
SIZES = ["1.7B", "4B"]
API_ARMS = ["api0", "api10"]


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf8").splitlines()]


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf8")


def prepare():
    groups = defaultdict(set)
    source = rows(SOURCE)
    for r in source:
        groups[r["subset"], r["kind"]].add(r["group_id"])
    rng = random.Random(SEED)
    selected = {rng.choice(sorted(g)) for _,g in sorted(groups.items())}
    panel = [r for r in source if r["group_id"] in selected]
    warm = next(r for r in source if r["group_id"] not in selected and r["arm"]=="active")
    assert len(selected)==10 and len(panel)==30
    rng.shuffle(panel)
    OUT.mkdir(exist_ok=True)
    ids = [r["sample_id"] for r in panel]
    first = set(rng.sample(ids, len(ids)//2))
    proto = dict(ids=ids, warm=warm["sample_id"],api_zero_first=sorted(first),seed=SEED,
                 source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                 arms=SIZES+API_ARMS, batch=1, max_new_tokens=384,
                 target="client wall time to decoded text, input/output native tokens, exact including evidence with public scope; malformed counts as failure",
                 conditions="One active request per arm. Resident local bf16/unmerged LoRA. PE interleaves 0 and 10 shot within each input; one warmup per arm excluded.")
    path=OUT/"protocol.json"
    if path.exists():
        assert json.loads(path.read_text())==proto
    else:
        write(path,proto)


def forbid_inet():
    """Enforce Linux seccomp on new IPv4/IPv6 sockets for this process and its threads."""
    lib=ctypes.CDLL("libseccomp.so.2",use_errno=True)
    ptr=ctypes.c_void_p
    class Cmp(ctypes.Structure):
        _fields_=[("arg",ctypes.c_uint),("op",ctypes.c_int),("n",ctypes.c_uint64),("m",ctypes.c_uint64)]
    lib.seccomp_init.argtypes=[ctypes.c_uint32]
    lib.seccomp_init.restype=ptr
    ctx=lib.seccomp_init(0x7fff0000)
    if not ctx: raise RuntimeError("seccomp init")
    lib.seccomp_attr_set.argtypes=[ptr,ctypes.c_int,ctypes.c_uint32]
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p]
    lib.seccomp_rule_add_array.argtypes=[ptr,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint,ctypes.POINTER(Cmp)]
    lib.seccomp_load.argtypes=[ptr]
    lib.seccomp_release.argtypes=[ptr]
    try:
        assert lib.seccomp_attr_set(ctx,4,1)==0  # SCMP_FLTATR_CTL_TSYNC
        for family in (socket.AF_INET,socket.AF_INET6):
            match=Cmp(0,4,int(family),0)  # SCMP_CMP_EQ
            assert lib.seccomp_rule_add_array(ctx,0x50000|errno.EPERM,lib.seccomp_syscall_resolve_name(b"socket"),1,ctypes.byref(match))==0
        assert lib.seccomp_load(ctx)==0
    finally:
        lib.seccomp_release(ctx)
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            with socket.socket(family,socket.SOCK_STREAM):
                raise RuntimeError("IP socket guard did not hold")
        except PermissionError:
            pass


def append(path, item):
    with path.open("a",encoding="utf8") as f:
        print(json.dumps(item),file=f,flush=True)


def run_local(arm, proto, data):
    forbid_inet()
    os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
    import torch, transformers, peft
    from run_e1 import chat_messages_v4, render_chat, load_model
    started=time.perf_counter()
    base=ROOT/("models/Qwen3-"+arm)
    adapter=ROOT/f"outputs/e1/Qwen3-{arm}-v4/adapter"
    model,tok=load_model(str(base),"bf16")
    model=peft.PeftModel.from_pretrained(model,adapter).eval()
    tok.padding_side="left"
    device=next(model.parameters()).device
    torch.cuda.synchronize()
    load_s=time.perf_counter()-started
    def generate(r):
        torch.cuda.synchronize()
        t=time.perf_counter()
        msg=chat_messages_v4(r)
        encoded=render_chat(tok,msg,add_generation_prompt=True)
        ids=encoded["input_ids"].to(device)
        with torch.inference_mode():
            output=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),
                                  do_sample=False,max_new_tokens=384,pad_token_id=tok.eos_token_id)
        gen=output[0,ids.size(1):]
        raw=tok.decode(gen,skip_special_tokens=True)
        torch.cuda.synchronize()
        elapsed=time.perf_counter()-t
        return dict(raw=raw,seconds=elapsed,input=ids.size(1),output=gen.numel(),cached=None,
                    prompt_chars=sum(len(m["content"]) for m in msg))
    warm=generate(data[proto["warm"]])
    torch.cuda.reset_peak_memory_stats()
    path=OUT/(arm+".jsonl")
    done={r["id"] for r in rows(path)} if path.exists() else set()
    for i in proto["ids"]:
        if i not in done:
            append(path,dict(id=i,**generate(data[i])))
    write(OUT/(arm+"-env.json"),dict(gpu=torch.cuda.get_device_name(),torch=torch.__version__,
          transformers=transformers.__version__,peft=peft.__version__,load_seconds=load_s,
          peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved(),
          adapter_sha256=hashlib.sha256((adapter/"adapter_model.safetensors").read_bytes()).hexdigest(),
          warmup_seconds=warm["seconds"],ip_socket_probe="EPERM for AF_INET and AF_INET6, checked before model loading"))
    print(arm,"finished",flush=True)


def run_api(proto,data):
    from pe_v4_side import demonstrations
    from run_cross_family_pe import request, MODEL
    from run_e1 import chat_messages_v4
    demo=demonstrations(rows(ROOT/"data/processed_v4/train.jsonl"))
    def call(i,arm):
        t=time.perf_counter()
        sys,user=chat_messages_v4(data[i])
        messages=[sys,*(demo if arm=="api10" else []),user]
        resp=request(messages)
        elapsed=time.perf_counter()-t
        usage=resp["usage"]
        assert resp["model"]==MODEL
        return dict(id=i,seconds=elapsed,input=usage["prompt_tokens"],output=usage["completion_tokens"],
            cached=usage.get("prompt_tokens_details",{}).get("cached_tokens"),raw=resp["raw"],
            finish=resp["finish"],usage=usage,prompt_chars=sum(len(m["content"]) for m in messages))
    for a in API_ARMS:
        if not (OUT/(a+"-warm.json")).exists():
            write(OUT/(a+"-warm.json"),call(proto["warm"],a))
    done={a:{r["id"] for r in rows(OUT/(a+".jsonl"))} if (OUT/(a+".jsonl")).exists() else set() for a in API_ARMS}
    for i in proto["ids"]:
        for a in (API_ARMS if i in proto["api_zero_first"] else list(reversed(API_ARMS))):
            if i not in done[a]:
                append(OUT/(a+".jsonl"),call(i,a))
    print("API finished",flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=["prepare","api",*SIZES])
    mode=parser.parse_args().mode
    if mode=="prepare":
        prepare()
        return
    proto=json.loads((OUT/"protocol.json").read_text())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==proto["source_sha256"]
    data={r["sample_id"]:r for r in rows(SOURCE)}
    if mode=="api":
        run_api(proto,data)
    else:
        run_local(mode,proto,data)


if __name__=="__main__":
    main()
