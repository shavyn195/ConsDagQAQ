"""Aggregate matched single-request benchmarks. Resample at the task, not utterance, level."""
from collections import Counter, defaultdict
import math
from random import Random
from statistics import mean, median

from measure_compiler_efficiency import API_ARMS, SIZES, OUT, SOURCE, rows, write
import json
from diagnose_evidence_scope import derive
from run_e1 import strict_parse
from score_evidence_panel import exact_object


def quantile(values, q):
    values = sorted(values)
    k = (len(values)-1)*q
    f = math.floor(k)
    return values[f] + (k-f)*(values[math.ceil(k)]-values[f])


def main():
    protocol = json.loads((OUT/"protocol.json").read_text())
    data = {r["sample_id"]:r for r in rows(SOURCE)}
    ids = protocol["ids"]
    groups = defaultdict(list)
    for i in ids:
        groups[data[i]["group_id"]].append(i)
    assert len(ids)==30 and len(groups)==10 and all(len(v)==3 for v in groups.values())
    result, by_arm = {}, {}
    for arm in [*SIZES,*API_ARMS]:
        samples = rows(OUT/(arm+".jsonl"))
        observed = {r["id"]:r for r in samples}
        assert len(samples)==len(observed)==30 and set(observed)==set(ids)
        by_arm[arm]=observed
        for r in samples:
            gold=data[r["id"]]
            p=strict_parse(derive(r["raw"],gold["catalog"]))
            r["correct"]=bool(p and not p.get("abstain",False) and p["query_state"]==gold["variant"]
                              and Counter(map(exact_object,p["constraints"]))==Counter(map(exact_object,gold["gold"]["constraints"])))
            assert r["input"]>0 and r["output"]>0 and r["seconds"]>0
            if arm in API_ARMS:
                assert r["usage"]["total_tokens"]==r["input"]+r["output"]
        valid_correct=sum(v["correct"] for v in samples)
        by_type = {}
        for condition in ("active","history","mixed"):
            subset=[r for r in samples if data[r["id"]]["arm"]==condition]
            by_type[condition]=dict(correct=sum(r["correct"] for r in subset),n=len(subset),
                                    median_s=median(r["seconds"] for r in subset))
        result[arm]=dict(n=len(samples),correct=valid_correct,
                         input_mean=mean(r["input"] for r in samples),output_mean=mean(r["output"] for r in samples),
                         input_sum=sum(r["input"] for r in samples),output_sum=sum(r["output"] for r in samples),
                         cached_sum=sum(r["cached"] for r in samples if r["cached"] is not None),
                         cache_reported_n=sum(r["cached"] is not None for r in samples),
                         median_s=median(r["seconds"] for r in samples),p95_s=quantile([r["seconds"] for r in samples],0.95),
                         total_s=sum(r["seconds"] for r in samples),mean_prompt_chars=mean(r["prompt_chars"] for r in samples),
                         seconds_per_correct=sum(r["seconds"] for r in samples)/valid_correct,by_condition=by_type)
        if arm in SIZES:
            result[arm].update(json.loads((OUT/(arm+"-env.json")).read_text()))
    assert all(by_arm["1.7B"][i]["prompt_chars"]==by_arm["4B"][i]["prompt_chars"]==by_arm["api0"][i]["prompt_chars"]
               and by_arm["1.7B"][i]["input"]==by_arm["4B"][i]["input"] for i in ids)
    paired={}
    for arm in ("4B","api0","api10"):
        delta={i:by_arm[arm][i]["seconds"]-by_arm["1.7B"][i]["seconds"] for i in ids}
        rng=Random(372)
        samples=[]
        for _ in range(5000):
            drawn=rng.choices(list(groups.values()),k=len(groups))
            samples.append(median(delta[i] for g in drawn for i in g))
        paired[arm]=dict(smaller_faster_n=sum(v>0 for v in delta.values()),paired_median_saved_seconds=median(delta.values()),
                         descriptive_group_bootstrap_95=[quantile(samples,.025),quantile(samples,.975)])
    fixed=json.loads((OUT/"fixed-generation.json").read_text())["results"]
    assert [(r["id"],r["input_hash"]) for r in fixed["4B"]]==[(r["id"],r["input_hash"]) for r in fixed["1.7B"]]
    fixed_medians={arm:median(x["seconds"] for x in entries) for arm,entries in fixed.items()}
    write(OUT/"results.json",dict(arms=result,vs_1_7B=paired,fixed512x64_medians=fixed_medians))
    for a,v in result.items():
        print(a,[v[k] for k in ("input_mean","output_mean","median_s","p95_s","correct","cached_sum","cache_reported_n")],
              v.get("peak_allocated_bytes",0)/2**30,flush=True)
    print(paired)
    print(fixed_medians)


if __name__=="__main__":
    main()
