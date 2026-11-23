"""CPU replay of complete pilot arms: independently check responsibility and matched credit."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from transformers import AutoTokenizer
from bind_public_scope import bind
from e2_credit import advantages
from prepare_e2_credit_panel import OUT, ROOT
from probe_e2_planner_v1 import MODEL
from rescore_v4_side import digest, load_jsonl
from run_e1 import strict_parse
from trust_env import check, execute, normalize_constraint
from audit_warmup_rollouts import shape


def audit(arm, seed):
    run = OUT / f"{arm}-s{seed}"
    cfg = json.loads((run/"config.json").read_text())
    panel = json.loads((OUT/"panel.json").read_text())
    train = ROOT/"data/processed_v4/train.jsonl"
    assert digest(OUT/"panel.json") == cfg["panel"] and digest(train) == panel["data"]["train"]
    cache = OUT/"compiler.jsonl"
    assert digest(cache) == cfg["compiler_cache"]
    by = {r["sample_id"]:r for r in load_jsonl(train)}
    raw, steps, pred = map(load_jsonl, [run/"rollouts.jsonl",run/"progress.jsonl",cache])
    assert all([x["id"] for x in records] == panel["train"] for records in (raw, steps, pred))
    tok = AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    sums = Counter()
    kinds = Counter()
    for entry, step, p in zip(raw, steps, pred, strict=True):
        row = by[entry["id"]]
        task = row["task"]
        obj = strict_parse(bind(p["raw"],row["catalog"])) or {}
        cs = [c for c in obj.get("constraints",[]) if normalize_constraint(c,task)]
        assert cs == entry["cs"]
        roll = entry["rollouts"]
        assert len(roll)==4
        remaps = [{int(k):v for k,v in r["role_positions"].items()} for r in roll]
        scores, sizes, expected_moves = [], [], 0
        for r, mp in zip(roll, remaps, strict=True):
            ids = r["token_ids"]
            decoded = tok.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            assert decoded == r["raw"]
            try:
                acts = json.loads(decoded)
            except ValueError:
                acts = None
            if not isinstance(acts,list) or not acts or not all(isinstance(x,str) and x in task["tools"] for x in acts):
                acts = None
            assert acts == r["actions"]
            ok = bool(acts and shape(acts,task) and check(task,acts,[])["completed"])
            bad = check(task,acts,cs)["violations"] if ok else []
            assert ok == r["done"] and bad == r["bad"]
            loc = {int(k):v for k,v in r["loc"].items()}
            expected = {}
            for k in bad:
                c = normalize_constraint(cs[k],task)
                if c["type"] in ("order","tool_auth"):
                    expected[k] = acts.index(c["second"])
                elif c["type"] == "privacy":
                    hits = [j for j,cls in execute(task,acts)["leaks"] if cls in c["classes"]]
                    if len(hits)==1:
                        expected[k] = hits[0]
            assert loc == expected
            for k,j in loc.items():
                if not mp.get(j) or all(k in o["bad"] for o in roll):
                    continue
                token_indexes = mp[j]
                # The union of generated tokens may also include a quote/punctuation boundary.
                text = tok.decode([ids[i] for i in token_indexes],clean_up_tokenization_spaces=False)
                assert acts[j] in text, (row["sample_id"],acts[j],text)
                kinds[cs[k]["type"]] += 1
                expected_moves += 1
            sizes.append(len(ids))
            scores.append(dict(done=ok,bad=bad,loc=loc))
        scalar, trace, _ = advantages(scores,sizes,remaps,len(cs),"trace")
        _, localized, moved = advantages(scores,sizes,remaps,len(cs),"action")
        _, shifted, wrong_moved = advantages(scores,sizes,remaps,len(cs),"shifted")
        assert expected_moves == moved == wrong_moved
        assert scalar == entry["rewards"] and step["relocated"] == (0 if arm=="trace" else moved)
        assert all(math.isclose(sum(v)/len(v),t[0],abs_tol=1e-7)
                   for v,t in zip(localized+shifted,trace+trace,strict=True))
        different = any(any(abs(u-v)>1e-7 for u,v in zip(a,b,strict=True))
                        for a,b in zip(localized,shifted,strict=True))
        sums.update(groups=1,rollouts=len(roll),assignments=moved,
                    moved_groups=int(moved>0),action_vs_shifted_distinct_groups=int(different))
    return dict(arm=arm,seed=seed,counts=sums,assignment_types=kinds,
                rollout_sha256=digest(run/"rollouts.jsonl"),progress_sha256=digest(run/"progress.jsonl"),
                code_sha256=digest(Path(__file__)))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--arm",choices=("trace","action","shifted"),required=True)
    p.add_argument("--seed",type=int,default=42)
    args=p.parse_args()
    data=audit(args.arm,args.seed)
    path=OUT/f"credit-replay-{args.arm}-s{args.seed}.json"
    path.write_text(json.dumps(data,indent=2))
    print(json.dumps(data["counts"]))
