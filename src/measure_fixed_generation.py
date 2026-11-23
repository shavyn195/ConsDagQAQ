"""Control for output-length differences on the two local decoders, warm batch one."""
import hashlib
import json
from time import perf_counter

from measure_compiler_efficiency import OUT, SOURCE, ROOT, forbid_inet, rows, write


def main():
    import os
    forbid_inet()
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",HF_HUB_DISABLE_TELEMETRY="1")
    import torch
    from peft import PeftModel
    from run_e1 import chat_messages_v4, load_model, render_chat
    import gc
    proto=json.loads((OUT/"protocol.json").read_text())
    data={r["sample_id"]:r for r in rows(SOURCE)}
    seen=set()
    ids=[]
    for sample in proto["ids"]:
        gid=data[sample]["group_id"]
        if gid not in seen:
            seen.add(gid)
            ids.append(sample)
    assert len(ids)==10
    lengths=[512,64]
    results={}
    tokens={}
    # Reverse model order compared with the natural-completion timing.
    for size in ["4B","1.7B"]:
        model,tok=load_model(str(ROOT/f"models/Qwen3-{size}"),"bf16")
        model=PeftModel.from_pretrained(model,ROOT/f"outputs/e1/Qwen3-{size}-v4/adapter").eval()
        part=[]
        for i in [proto["warm"],*ids]:
            prompt=render_chat(tok,chat_messages_v4(data[i]),add_generation_prompt=True)["input_ids"]
            assert prompt.size(1)>=lengths[0]
            prompt=prompt[:,-lengths[0]:].contiguous().to(next(model.parameters()).device)
            token_hash=hashlib.sha256(prompt.cpu().numpy().tobytes()).hexdigest()
            if size=="4B": tokens[i]=token_hash
            else: assert tokens[i]==token_hash, i
            mask=torch.ones_like(prompt)
            torch.cuda.synchronize()
            t=perf_counter()
            with torch.inference_mode():
                out=model.generate(input_ids=prompt,attention_mask=mask,do_sample=False,min_new_tokens=64,max_new_tokens=64,
                                   pad_token_id=tok.eos_token_id)
            torch.cuda.synchronize()
            elapsed=perf_counter()-t
            assert out.size(1)==576
            if i!=proto["warm"]: part.append(dict(id=i,input_hash=token_hash,seconds=elapsed))
        results[size]=part
        del model,tok,prompt,mask,out
        gc.collect()
        torch.cuda.empty_cache()
    write(OUT/"fixed-generation.json",dict(input_tokens=512,output_tokens=64,results=results))
    print("Fixed-length measurements complete",flush=True)


if __name__=="__main__":
    main()
