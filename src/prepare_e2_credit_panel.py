"""Freeze one train-only compiler cache and an untouched-by-policy dev panel for E2."""
from pathlib import Path
import fcntl
import json
import random

from peft import PeftModel
from probe_e2_format import choose
from probe_e2_planner_v1 import ROOT, select
from rescore_v4_side import digest, load_jsonl
from run_e1 import generate_batched, load_model

PARENT = ROOT / "outputs/e2_v4"
OUT = PARENT / "action-credit-1.7B-pilot-v1"
COMP = ROOT / "outputs/e1/Qwen3-0.6B-v4"
WARM = PARENT / "planner-warmup-1.7B-v1"


def panel(rows, excluded, n, seed):
    rng = random.Random(seed)
    order = list(rows)
    rng.shuffle(order)
    picked = []
    for variant, quota in (("explicit", n * 3 // 8), ("implicit", n * 3 // 8), ("none", n // 4)):
        part = []
        for r in order:
            if r["variant"] == variant and r["group_id"] not in excluded:
                part.append(r)
                excluded.add(r["group_id"])
                if len(part) == quota:
                    break
        assert len(part) == quota
        picked.extend(part)
    rng.shuffle(picked)
    return picked


def main():
    lock = (PARENT / "planner-probe.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    data = ROOT / "data/processed_v4"
    train, dev = (load_jsonl(data / (s + ".jsonl")) for s in ("train", "dev"))
    idx = {r["sample_id"]: r for r in train}
    excluded = {r["group_id"] for r in select(train) + choose(train)}
    for directory, keys in [(WARM, ("demos", "probes")), (PARENT / "multiconstraint-gate-opportunity-v1", ("groups",)),
                            (PARENT / "frozen-record-choice-v1", ("ids",))]:
        cfg = json.loads((directory / "config.json").read_text())
        excluded.update(idx[k]["group_id"] for key in keys for k in cfg[key])
    tr = panel(train, excluded, 128, 10541)
    de = panel(dev, {r["group_id"] for r in train}, 160, 10542)
    OUT.mkdir(exist_ok=False)
    cfg = {"train": [r["sample_id"] for r in tr], "dev": [r["sample_id"] for r in de],
           "data": {s: digest(data / (s + ".jsonl")) for s in ("train", "dev")},
           "compiler": digest(COMP / "adapter/adapter_model.safetensors"),
           "warm": digest(WARM / "adapter/adapter_model.safetensors"), "code": digest(Path(__file__)),
           "description": "Policy-train IDs from compiler training split; dev disjoint. Pilot, not a blind paper test."}
    (OUT / "panel.json").write_text(json.dumps(cfg, indent=2))
    model, tok = load_model(str(ROOT / "models/Qwen3-0.6B"), "bf16")
    model = PeftModel.from_pretrained(model, COMP / "adapter").eval()
    with (OUT / "compiler.jsonl").open("x") as f:
        for i in range(0, len(tr), 16):
            batch = tr[i:i + 16]
            _, raw = generate_batched(model, tok, batch, 384, 16)
            for row, response in zip(batch, raw, strict=True):
                print(json.dumps({"id": row["sample_id"], "raw": response}), file=f, flush=True)
            print(f"compiled {i+len(batch)}/{len(tr)}", flush=True)
    (OUT / "cache-ready.json").write_text(json.dumps({"n": len(tr), "sha256": digest(OUT / "compiler.jsonl")}))


if __name__ == "__main__":
    main()
