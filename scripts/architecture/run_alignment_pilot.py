"""CPU-only matched loss pilot. Gold candidates make this a retrieval diagnostic."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import torch
from torch.nn import functional as F
from constraint_alignment import AlignmentHead, alignment_loss
from constraint_alignment_data import make_group, selected_groups
from audit_solver_supervision import enumerate_plans


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def encode(texts: list[str], cfg: dict, out: Path) -> dict:
    from transformers import AutoModel, AutoTokenizer
    started = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(cfg["encoder"], local_files_only=True)
    model = AutoModel.from_pretrained(cfg["encoder"], dtype=torch.float32, local_files_only=True).eval()
    model.requires_grad_(False)
    # Deterministic length buckets reduce padding, without changing pooling.
    texts = sorted(texts, key=lambda s: (len(tokenizer.encode(s)), s))
    embeddings, tokens = {}, 0
    for i in range(0, len(texts), cfg["encoder_batch_size"]):
        part = texts[i:i + cfg["encoder_batch_size"]]
        inputs = tokenizer(part, return_tensors="pt", padding=True, truncation=False)
        if inputs["input_ids"].shape[1] > cfg["max_input_tokens"]:
            raise ValueError("Encoder token limit exceeded; no silent truncation")
        with torch.inference_mode():
            hidden = model(**inputs, use_cache=False).last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1)
            pooled = F.normalize((hidden * mask).sum(1) / mask.sum(1), dim=-1).float()
        if not torch.isfinite(pooled).all():
            raise FloatingPointError("Nonfinite encoder output")
        for text, vector in zip(part, pooled):
            # Make normal tensors outside inference_mode for projection backward.
            embeddings[text] = vector.clone()
        tokens += int(inputs["attention_mask"].sum())
        if i % 40 == 0:
            progress = {"stage": "encoding", "done": min(i + len(part), len(texts)),
                        "total": len(texts), "seconds": time.monotonic() - started}
            write(out / "progress.json", progress)
            print(json.dumps(progress), flush=True)
        if i >= 40:
            estimated = (time.monotonic() - started) / (i + len(part)) * len(texts)
            if estimated > 2400:
                raise RuntimeError("Encoding projects over 40 minutes; stopping resource expansion")
    torch.save(embeddings, out / "embeddings.pt")
    model_root = Path(cfg["encoder"])
    write(out / "encoder.json", {"seconds": time.monotonic() - started, "input_tokens": tokens,
          "unique_texts": len(texts), "cache_sha256": sha(out / "embeddings.pt"),
          "model_sha256": {p.name: sha(p) for p in model_root.iterdir()
                           if p.is_file() and (p.suffix == ".safetensors" or p.name in ("config.json", "tokenizer.json"))}})
    del model
    return embeddings


def tensors(group: dict, embeddings: dict) -> tuple:
    return (torch.stack([embeddings[s] for s in group["queries"]]),
            torch.stack([embeddings[c["text"]] for c in group["candidates"]]),
            torch.tensor(group["positive"], dtype=torch.bool))


def batch(items: list[tuple]) -> tuple:
    queries = torch.cat([x[0] for x in items])
    records = torch.cat([x[1] for x in items])
    allowed = torch.zeros((len(queries), len(records)), dtype=torch.bool)
    positive = torch.zeros_like(allowed)
    qi = ri = 0
    for q, r, pos in items:
        allowed[qi:qi + len(q), ri:ri + len(r)] = True
        positive[qi:qi + len(q), ri:ri + len(r)] = pos
        qi, ri = qi + len(q), ri + len(r)
    return queries, records, allowed, positive


def downstream_table(groups: list[dict], env) -> dict:
    table = {}
    for g in groups:
        for row in g["rows"]:
            _, gold_info = env.plan(row["task"], row["gold"]["constraints"])
            for j, candidate in enumerate(g["candidates"]):
                plan, info = env.plan(row["task"], candidate["constraints"])
                check = env.check(row["task"], plan, row["gold"]["constraints"])
                faithful = bool(check["safe_success"] and info["changes"] == gold_info["changes"])
                if row["variant"] == "none":
                    faithful = faithful and not candidate["constraints"]
                table[(row["sample_id"], j)] = faithful
    return table


def evaluate(groups: list[dict], features: list[tuple], head, downstream: dict) -> dict:
    result = []
    with torch.no_grad():
        for g, (q, r, positive) in zip(groups, features):
            scores = q @ r.T if head is None else head(q, r)
            for i, row in enumerate(g["rows"]):
                choice = int(scores[i].argmax())
                pos_score = scores[i][positive[i]].max()
                negatives = [j for j, c in enumerate(g["candidates"])
                             if not positive[i, j] and c["kind"] not in ("reference", "empty")]
                # Ties count half; retrieval argmax uses the preregistered hashed order.
                wins = sum(float(pos_score > scores[i, j]) + 0.5 * float(pos_score == scores[i, j]) for j in negatives)
                result.append({"sample_id": row["sample_id"], "group_id": row["group_id"],
                    "variant": row["variant"], "choice": choice,
                    "predicate_correct": bool(positive[i, choice]),
                    "gold_candidate_faithful": downstream[(row["sample_id"], choice)],
                    "none_false_alarm": row["variant"] == "none" and bool(g["candidates"][choice]["constraints"]),
                    "hard_pair_wins": wins, "hard_pairs": len(negatives)})
    summary = {"n": len(result)}
    for variant in ("all", "explicit", "implicit", "none"):
        part = result if variant == "all" else [r for r in result if r["variant"] == variant]
        summary[variant] = {k: sum(r[k] for r in part) / len(part)
                            for k in ("predicate_correct", "gold_candidate_faithful", "none_false_alarm")}
        pairs = sum(r["hard_pairs"] for r in part)
        summary[variant]["hard_pair_accuracy"] = sum(r["hard_pair_wins"] for r in part) / pairs if pairs else None
    return {"summary": summary, "outcomes": result}


def compare(a: dict, b: dict) -> dict:
    aa = {r["sample_id"]: r for r in a["outcomes"]}
    bb = {r["sample_id"]: r for r in b["outcomes"]}
    if aa.keys() != bb.keys():
        raise ValueError("Unpaired analysis")
    grouped = {}
    for key, r in aa.items():
        grouped.setdefault(r["group_id"], []).append(int(r["predicate_correct"]) - int(bb[key]["predicate_correct"]))
    means = [sum(x) / len(x) for x in grouped.values()]
    rng = random.Random(20261125)
    values = sorted(100 * sum(rng.choices(means, k=len(means))) / len(means) for _ in range(2000))
    return {"difference_pp": 100 * sum(means) / len(means), "conditional_group_bootstrap95_pp": [values[50], values[1949]],
            "note": "Conditional on this fitted seed; exploratory development interval, not seed-population inference"}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    args.out.mkdir(parents=True)
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    if args.smoke:
        cfg.update(train_groups=2, dev_groups=2, steps=5, seeds=[42], batch_groups=2)
    torch.set_num_threads(cfg["threads"])
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    sys.path.append(str(args.project_root / "src"))
    import trust_env as env
    started = time.monotonic()
    files = [Path(__file__), ROOT / "src/constraint_alignment.py", ROOT / "src/constraint_alignment_data.py",
             Path(__file__).with_name("audit_solver_supervision.py")]
    metadata = {"utc": datetime.now(timezone.utc).isoformat(), "config": cfg, "smoke": args.smoke,
                "source_sha256": {str(f.relative_to(ROOT)): sha(f) for f in files},
                "frozen_env_sha256": sha(Path(env.__file__)), "config_sha256": sha(args.config),
                "device": "cpu", "torch": torch.__version__, "python": sys.version,
                "data_sha256": {}}
    write(args.out / "metadata.json", metadata)
    try:
        seal = json.loads((args.project_root / "configs/v6_release_sha256.json").read_text(encoding="utf-8"))["sha256"]
        for relative in ("src/trust_env.py", "data/processed_v6/train.jsonl", "data/processed_v6/dev.jsonl"):
            if sha(args.project_root / relative) != seal[relative]:
                raise ValueError(f"Frozen source mismatch: {relative}")
        splits = {}
        for split in ("train", "dev"):
            path = args.project_root / "data/processed_v6" / f"{split}.jsonl"
            metadata["data_sha256"][split] = sha(path)
            rows = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]
            splits[split] = [make_group(group, env, enumerate_plans)
                             for group in selected_groups(rows, cfg[f"{split}_groups"])]
        if {g["group_id"] for g in splits["train"]} & {g["group_id"] for g in splits["dev"]}:
            raise ValueError("Train/dev group overlap")
        train_queries = {q for g in splits["train"] for q in g["queries"]}
        if train_queries & {q for g in splits["dev"] for q in g["queries"]}:
            raise ValueError("Exact train/dev request overlap")
        write(args.out / "metadata.json", metadata)
        write(args.out / "dataset.json", splits)
        write(args.out / "dataset_audit.json", {"splits": {s: {
            "groups": len(gs), "queries": len(gs) * 3,
            "candidates": sum(len(g["candidates"]) for g in gs),
            "types": dict(Counter(c["type"] for g in gs for c in g["rows"][0]["gold"]["constraints"])),
            "excluded": dict(sum((Counter(g["audit"]["excluded"]) for g in gs), Counter()))}
            for s, gs in splits.items()}, "dataset_sha256": sha(args.out / "dataset.json"),
            "warning": "Gold-derived candidate pools: not end-to-end compilation"})
        texts = sorted({s for gs in splits.values() for g in gs
                        for s in g["queries"] + [c["text"] for c in g["candidates"]]})
        embeddings = encode(texts, cfg, args.out)
        features = {s: [tensors(g, embeddings) for g in gs] for s, gs in splits.items()}
        downstream = downstream_table(splits["dev"], env)
        frozen = evaluate(splits["dev"], features["dev"], None, downstream)
        write(args.out / "frozen_cosine.json", frozen)
        results = {}
        for seed in cfg["seeds"]:
            torch.manual_seed(seed)
            prototype = AlignmentHead(len(next(iter(embeddings.values()))), cfg["projection_hidden"],
                                      cfg["projection_dim"], cfg["temperature"])
            init = copy.deepcopy(prototype.state_dict())
            torch.save(init, args.out / f"initial_seed{seed}.pt")
            rng = random.Random(seed)
            schedule = [rng.sample(range(len(features["train"])), min(cfg["batch_groups"], len(features["train"])))
                        for _ in range(cfg["steps"])]
            write(args.out / f"schedule_seed{seed}.json", schedule)
            results[str(seed)] = {}
            for arm in cfg["arms"]:
                target = args.out / f"{arm}_seed{seed}"
                target.mkdir()
                model = copy.deepcopy(prototype)
                model.load_state_dict(init)
                opt = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"], betas=tuple(cfg["betas"]),
                                       eps=cfg["adam_epsilon"], weight_decay=cfg["weight_decay"])
                train_start = time.monotonic()
                with (target / "train.jsonl").open("w", encoding="utf-8") as log:
                    for step, selected in enumerate(schedule, 1):
                        q, r, allowed, positive = batch([features["train"][i] for i in selected])
                        opt.zero_grad(set_to_none=True)
                        loss = alignment_loss(model(q, r), allowed, positive, arm)
                        if not torch.isfinite(loss):
                            raise FloatingPointError("Nonfinite loss")
                        loss.backward()
                        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg["max_grad_norm"], error_if_nonfinite=True)
                        opt.step()
                        if any(not torch.isfinite(v).all() for v in model.parameters()):
                            raise FloatingPointError("Nonfinite parameter")
                        if step % 25 == 0 or step == cfg["steps"]:
                            progress = {"arm": arm, "seed": seed, "step": step, "loss": float(loss.detach()),
                                        "grad_norm": float(norm), "seconds": time.monotonic() - train_start}
                            log.write(json.dumps(progress, allow_nan=False) + "\n")
                            log.flush()
                            write(args.out / "progress.json", progress)
                            print(json.dumps(progress), flush=True)
                model.eval()
                result = evaluate(splits["dev"], features["dev"], model, downstream)
                result.update(train_seconds=time.monotonic() - train_start,
                              parameter_count=sum(p.numel() for p in model.parameters()),
                              initial_sha256=sha(args.out / f"initial_seed{seed}.pt"),
                              schedule_sha256=sha(args.out / f"schedule_seed{seed}.json"))
                write(target / "result.json", result)
                torch.save(model.state_dict(), target / "head.pt")
                results[str(seed)][arm] = result
        summary = {"scope": cfg["scope"], "smoke": args.smoke, "status": "completed",
                   "frozen_cosine": frozen["summary"], "seeds": {}, "elapsed_seconds": time.monotonic() - started}
        passed = True
        for seed, arms in results.items():
            comparisons = {f"contrastive_minus_{a}": compare(arms["contrastive"], arms[a]) for a in ("bce", "rank")}
            for baseline, comp in zip(("bce", "rank"), comparisons.values()):
                passed &= comp["difference_pp"] >= 3
                passed &= arms["contrastive"]["summary"]["none"]["none_false_alarm"] <= arms[baseline]["summary"]["none"]["none_false_alarm"] + 0.01
            summary["seeds"][seed] = {"arms": {a: r["summary"] for a, r in arms.items()}, "comparisons": comparisons}
        summary["screening_gate_passed"] = bool(passed and not args.smoke)
        summary["decision"] = "advance_to_end_to_end_design" if summary["screening_gate_passed"] else "do_not_scale_from_this_probe"
        write(args.out / "completion.json", summary)
        print(json.dumps({"status": "completed", "decision": summary["decision"], "seconds": summary["elapsed_seconds"]}), flush=True)
    except BaseException as exc:
        write(args.out / "failure.json", {"error": repr(exc), "seconds": time.monotonic() - started})
        raise


if __name__ == "__main__":
    main()
