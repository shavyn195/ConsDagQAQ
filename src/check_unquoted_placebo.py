"""Post-hoc matched replay with only the delimiters around a historical label removed."""
import gc
import json
import random
import time
from pathlib import Path

import peft
import torch

from build_evidence_panel import MODELS, OUT, ROOT, SEED, digest, write_json
from run_e1 import generate_batched, load_model
from score_evidence_panel import measure, semantic_output

DIRECTORY = OUT/"unquoted_followup"


def queries(panel):
    rows = []
    for r in panel:
        for arm in ("neutral_old","neutral_new"):
            original = r["queries"][arm]
            start = len(r["queries"]["original"])
            suffix = original[start:]
            assert suffix.count('"') == 2 and suffix.endswith('".')
            q = original[:start] + suffix.replace('"',"")
            rows.append((r["id"],arm,dict(query=q,catalog=r["catalog"])))
    random.Random(SEED).shuffle(rows)
    return rows


def score(size, panel):
    by_id = {r["id"]:r for r in panel}
    raw_path = DIRECTORY/size/"raw.jsonl"
    raw = [json.loads(s) for s in raw_path.read_text().splitlines()]
    keyed = {(x["id"],x["arm"]):x["raw"] for x in raw}
    assert len(keyed) == len(raw) == len(panel)*2
    results = {}
    for arm in ("neutral_old","neutral_new"):
        vals = [measure(r, arm, keyed[r["id"], arm]) for r in panel]
        results[arm] = {key:sum(v[key] for v in vals) for key in ("parse","full","params","other","plan_verdict")}
    results["both_full"] = sum(all(measure(r,a,keyed[r["id"],a])["full"] for a in ("neutral_old","neutral_new")) for r in panel)
    results["both_parse"] = sum(all(measure(r,a,keyed[r["id"],a])["parse"] for a in ("neutral_old","neutral_new")) for r in panel)
    result_eq = [(semantic_output(keyed[i,"neutral_old"]), semantic_output(keyed[i,"neutral_new"])) for i in by_id]
    results.update(same_output=sum(x is not None and x == y for x,y in result_eq),
                   n=len(panel), raw_sha256=digest(raw_path))
    write_json(DIRECTORY/size/"summary.json", results)
    print(size,results,flush=True)


def main():
    proto = json.loads((OUT/"protocol.json").read_text())
    assert digest(OUT/"panel.jsonl") == proto["panel_sha256"]
    panel = [json.loads(s) for s in (OUT/"panel.jsonl").read_text().splitlines()]
    rows = queries(panel)
    DIRECTORY.mkdir(exist_ok=True)
    design = dict(parent=proto["panel_sha256"], intervention="Only delete the two double quotes from each neutral suffix",
                  trigger="Malformed quoted-label outputs observed in 0.6B. Exploratory follow-up; primary is unchanged.",
                  ids=[(s,a) for s,a,_ in rows], models=MODELS, decoding="same greedy bf16, 384 new tokens, batch 32",
                  code_sha256=digest(Path(__file__)))
    if (DIRECTORY/"protocol.json").exists():
        assert json.loads((DIRECTORY/"protocol.json").read_text()) == json.loads(json.dumps(design))
    else:
        write_json(DIRECTORY/"protocol.json", design)
    for size in MODELS:
        folder = DIRECTORY/size
        folder.mkdir(exist_ok=True)
        path = folder/"raw.jsonl"
        done = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
        assert [(d["id"],d["arm"]) for d in done] == [r[:2] for r in rows[:len(done)]]
        if len(done) != len(rows):
            ad = ROOT/f"outputs/e1/Qwen3-{size}-v4/adapter"
            manifest = json.loads((OUT/size/"inference.json").read_text())
            assert all(digest(ROOT/f)==h for f,h in manifest["sha256"].items() if "adapter" in Path(f).name or f.endswith("run_e1.py"))
            model,tok = load_model(str(ROOT/f"models/Qwen3-{size}"),"bf16")
            model = peft.PeftModel.from_pretrained(model,ad).eval()
            with path.open("a",encoding="utf8") as file:
                for i in range(len(done),len(rows),proto["batch"]):
                    batch = rows[i:i+proto["batch"]]
                    _, raw = generate_batched(model,tok,[r[2] for r in batch],proto["max_new_tokens"],proto["batch"])
                    for (sample, arm, _), ans in zip(batch,raw,strict=True):
                        file.write(json.dumps(dict(id=sample,arm=arm,raw=ans))+"\n")
                    file.flush()
                    print(size,i+len(batch),"/",len(rows),time.strftime("%T"),flush=True)
            del model,tok
            gc.collect()
            torch.cuda.empty_cache()
        score(size,panel)


if __name__=="__main__":
    main()
