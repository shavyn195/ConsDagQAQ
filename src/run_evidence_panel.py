"""GPU replay of four frozen input arms. Write every raw answer before scoring."""
import gc
import json
import platform
import random
import time

import peft
import torch
import transformers

from build_evidence_panel import ARMS, MODELS, OUT, ROOT, SEED, digest, write_json
from run_e1 import generate_batched, load_model


def main():
    proto = json.loads((OUT/"protocol.json").read_text())
    assert digest(OUT/"panel.jsonl") == proto["panel_sha256"]
    panel = [json.loads(line) for line in (OUT/"panel.jsonl").read_text().splitlines()]
    rows = [(r["id"], arm, dict(query=r["queries"][arm], catalog=r["catalog"]))
            for r in panel for arm in ARMS]
    random.Random(SEED).shuffle(rows)
    for size in MODELS:
        ad = ROOT / f"outputs/e1/Qwen3-{size}-v4/adapter"
        base = ROOT / f"models/Qwen3-{size}"
        out = OUT / size
        out.mkdir(exist_ok=True)
        files = [*ad.glob("adapter*"), *base.glob("*.safetensors"), *base.glob("*.index.json"),
                 *base.glob("*config.json"), *base.glob("tokenizer.json"),
                 *(ROOT/"src"/s for s in ("run_e1.py", "trust_env.py", "dataset_v4_spec.py",
                   "build_dataset_v4.py", "audit_warmup_rollouts.py", "build_evidence_panel.py",
                   "run_evidence_panel.py"))]
        manifest = dict(model=size, panel_sha256=proto["panel_sha256"], batch=proto["batch"],
                        max_new_tokens=proto["max_new_tokens"], precision=proto["precision"],
                        hardware=torch.cuda.get_device_name(), torch=torch.__version__,
                        python=platform.python_version(), peft=peft.__version__, transformers=transformers.__version__,
                        sha256={str(f.relative_to(ROOT)):digest(f) for f in files if f.is_file()})
        manifest_path = out/"inference.json"
        if manifest_path.exists():
            if json.loads(manifest_path.read_text()) != manifest:
                raise RuntimeError("resume manifest mismatch")
        else:
            write_json(manifest_path, manifest)
        rawpath = out/"raw.jsonl"
        done = [json.loads(line) for line in rawpath.read_text().splitlines()] if rawpath.exists() else []
        start = len(done)
        assert [(r["id"], r["arm"]) for r in done] == [r[:2] for r in rows[:start]]
        if start == len(rows):
            continue
        model, tok = load_model(str(base), proto["precision"])
        model = peft.PeftModel.from_pretrained(model, ad).eval()
        print(size, "GPU", manifest["hardware"], "start", start, "total", len(rows), flush=True)
        with rawpath.open("a", encoding="utf8") as file:
            for i in range(start, len(rows), proto["batch"]):
                batch = rows[i:i + proto["batch"]]
                _, raw = generate_batched(model, tok, [x[2] for x in batch],
                                          proto["max_new_tokens"], proto["batch"])
                assert len(raw) == len(batch)
                for (sample, arm, _), answer in zip(batch, raw):
                    file.write(json.dumps(dict(id=sample, arm=arm, raw=answer)) + "\n")
                file.flush()
                print(size, i+len(batch), "/", len(rows), "time", time.strftime("%T"), flush=True)
        del model, tok
        gc.collect()
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
