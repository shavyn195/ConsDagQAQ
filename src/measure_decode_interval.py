"""Time generation steps 2 through 64 on identical tokenized prompts and a single GPU."""
import gc
import hashlib
import json
import os
from statistics import median
from time import perf_counter

from measure_compiler_efficiency import OUT, ROOT, SOURCE, forbid_inet, rows, write


def main():
    forbid_inet()
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    import torch
    import transformers
    from peft import PeftModel
    from transformers import StoppingCriteria, StoppingCriteriaList
    from run_e1 import chat_messages_v4, load_model, render_chat

    class TokenClock(StoppingCriteria):
        def __init__(self):
            self.times = {}

        def __call__(self, input_ids, scores, **kwargs):
            steps = input_ids.shape[-1] - 512
            if steps in (1, 64):
                torch.cuda.synchronize()
                self.times[steps] = perf_counter()
            return False

    parent = json.loads((OUT/"fixed-generation.json").read_text())
    sources = {r["sample_id"]: r for r in rows(SOURCE)}
    ids = [r["id"] for r in parent["results"]["4B"]]
    hashes = {r["id"]:r["input_hash"] for r in parent["results"]["4B"]}
    warm = json.loads((OUT/"protocol.json").read_text())["warm"]
    assert len({sources[i]["group_id"] for i in ids}) == len(ids) == 10
    assert sources[warm]["group_id"] not in {sources[i]["group_id"] for i in ids}
    output = OUT/"decode-interval"
    output.mkdir(exist_ok=True)
    order = [(1,"1.7B"),(1,"4B"),(2,"4B"),(2,"1.7B")]
    metadata = dict(order=order, ids=ids, warm=warm, dtype="bf16", batch=1,
                    gpu=torch.cuda.get_device_name(), torch=torch.__version__,
                    transformers=transformers.__version__, input_tokens=512, output_tokens=64,
                    timed_steps=63, method="synchronized wall-clock timestamps after appending tokens 1 and 64",
                    script_sha256=hashlib.sha256(open(__file__,"rb").read()).hexdigest())
    if (output/"protocol.json").exists():
        assert json.loads((output/"protocol.json").read_text()) == json.loads(json.dumps(metadata))
    else:
        write(output/"protocol.json",metadata)
    for rep,size in order:
        path=output/f"round-{rep}-{size}.json"
        if path.exists():
            continue
        model,tok=load_model(str(ROOT/f"models/Qwen3-{size}"),"bf16")
        model=PeftModel.from_pretrained(model,ROOT/f"outputs/e1/Qwen3-{size}-v4/adapter").eval()
        observed=[]
        for i in [warm,*(ids if rep==1 else reversed(ids))]:
            prompt=render_chat(tok,chat_messages_v4(sources[i]),add_generation_prompt=True)["input_ids"][:,-512:].contiguous()
            h=hashlib.sha256(prompt.numpy().tobytes()).hexdigest()
            if i!=warm:
                assert h==hashes[i]
            prompt=prompt.to(next(model.parameters()).device)
            mask=torch.ones_like(prompt)
            clock=TokenClock()
            torch.cuda.synchronize()
            start=perf_counter()
            with torch.inference_mode():
                generated=model.generate(input_ids=prompt,attention_mask=mask,do_sample=False,use_cache=True,
                                         min_new_tokens=64,max_new_tokens=64,pad_token_id=tok.eos_token_id,
                                         stopping_criteria=StoppingCriteriaList([clock]))
            assert generated.shape==(1,576) and set(clock.times)=={1,64}
            after_first=clock.times[64]-clock.times[1]
            assert 0 < after_first < clock.times[64]-start
            if i!=warm:
                observed.append(dict(id=i,input_hash=h,first_s=clock.times[1]-start,decode63_s=after_first,
                                     output_hash=hashlib.sha256(generated[0,512:].cpu().numpy().tobytes()).hexdigest()))
        write(path,observed)
        print(rep,size,len(observed),median(r["decode63_s"] for r in observed),flush=True)
        del model,tok,prompt,mask,generated
        gc.collect()
        torch.cuda.empty_cache()
    records={}
    all_rounds={}
    for size in ("1.7B","4B"):
        per_round=[{r["id"]:r for r in json.loads((output/f"round-{rep}-{size}.json").read_text())} for rep in (1,2)]
        assert all(set(one)==set(ids) for one in per_round)
        all_rounds[size]=per_round
        records[size]={i:median(one[i]["decode63_s"] for one in per_round) for i in ids}
    s,l=(median(records[size].values()) for size in ("1.7B","4B"))
    result=dict(n_prompts=len(ids),repetitions=2,timed_steps=63,median_decode63_s={"1.7B":s,"4B":l},
                median_ms_per_token={"1.7B":s*1000/63,"4B":l*1000/63},
                median_rate_tokens_s={"1.7B":63/s,"4B":63/l},speed_ratio=l/s,latency_reduction=1-s/l,
                prompt_wins=sum(records["1.7B"][i]<records["4B"][i] for i in ids),
                round_wins=[sum(all_rounds["1.7B"][j][i]["decode63_s"]<all_rounds["4B"][j][i]["decode63_s"] for i in ids) for j in (0,1)],
                deterministic_by_size={size:sum(pair[0][i]["output_hash"]==pair[1][i]["output_hash"] for i in ids) for size,pair in all_rounds.items()})
    write(output/"result.json",result)
    print(result,flush=True)


if __name__=="__main__":
    main()
