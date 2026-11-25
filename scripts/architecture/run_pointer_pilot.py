"""CPU-only four-arm development pilot; never changes or reserves the GPU.

Frozen Qwen object-text embeddings are cached once. Numeric parameters and
execution state use explicit channels. Full labels are consumed only by the
teacher-target builder and scorer, never by the policy-input function.
"""
from __future__ import annotations

import argparse
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

from constraint_pointer import ConstraintPointer, collate, policy_input
from constraint_set_learning import optimal_next_actions, positive_set_nll
import trust_env as env


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def examples(path: Path, limit: int) -> list[dict]:
    rows = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]
    result = []
    for row in rows[:limit]:
        for mask, label in row["lattice"].items():
            result.append(dict(label, task=row["task"], group_id=row["group_id"], subset=mask))
    return result


def intervention(example: dict, name: str) -> dict:
    result = copy.deepcopy(example)
    if name == "duplicate":
        result["constraints"] *= 2
    elif name == "rename_reorder":
        task = result["task"]
        roles = list(task["catalog"])
        rng = random.Random(example["group_id"])
        shuffled = roles[:]
        rng.shuffle(shuffled)
        mapping = {r: f"tool_{i:03d}" for i, r in enumerate(shuffled)}
        task["tool_descriptions"] = {mapping[r]: r.replace("_", " ") for r in roles}
        task["catalog"] = [mapping[r] for r in reversed(roles)]
        task["tools"] = {mapping[r]: s for r, s in task["tools"].items()}
        for stage in task["stages"]:
            stage["alternatives"] = [mapping[r] for r in stage["alternatives"]]
            stage["default"] = mapping[stage["default"]]
        task["finish"] = [mapping[r] for r in task["finish"]]
        task["optional"] = {mapping[r]: [mapping.get(t, t) for t in ts] for r, ts in task["optional"].items()}
        for c in result["constraints"]:
            for key in ("approval_role", "required_role", "before_role", "after_role"):
                if key in c["params"]:
                    old = env._role(c["params"][key])
                    c["params"][key] = mapping[old]
            c["scope"] = ["role:" + mapping.get(env._role(r), env._role(r)) for r in c.get("scope", [])]
        result["plan"] = [mapping[r] for r in result["plan"]]
        result["optimal_plans"] = [[mapping[r] for r in p] for p in result["optimal_plans"]]
    elif name != "original":
        raise ValueError(name)
    return result


def make_prefixes(data: list[dict]) -> list[tuple]:
    result = []
    for ex in data:
        # Both losses see exactly the same representative-plan prefixes.
        # Alternative correct plans change targets, not the sampled inputs.
        plan = ex["plan"]
        for k in range(len(plan) + 1):
            item = policy_input(ex["task"], ex["constraints"], plan[:k])
            accepted = optimal_next_actions(ex["optimal_plans"], plan[:k])
            single = plan[k] if k < len(plan) else None
            positives = [item.actions.index(a) for a in accepted]
            if any(not item.allowed[i] for i in positives):
                raise AssertionError("Structure mask excluded a teacher-accepted action")
            result.append((item, item.actions.index(single), positives))
        # Broader audit: every accepted plan, not only the sampled prefix,
        # must remain reachable under the constraint-independent mask.
        for accepted_plan in ex["optimal_plans"]:
            for k in range(len(accepted_plan) + 1):
                item = policy_input(ex["task"], ex["constraints"], accepted_plan[:k])
                a = accepted_plan[k] if k < len(accepted_plan) else None
                if not item.allowed[item.actions.index(a)]:
                    raise AssertionError("Accepted full plan excluded by mask")
    return result


def object_embeddings(texts: list[str], model_path: Path, out: Path) -> dict[str, torch.Tensor]:
    from transformers import AutoModel, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    model = AutoModel.from_pretrained(str(model_path), dtype=torch.float32, local_files_only=True).eval()
    model.requires_grad_(False)
    result, tokens = {}, 0
    start = time.monotonic()
    with torch.inference_mode():
        for i in range(0, len(texts), 8):
            part = texts[i:i + 8]
            inputs = tokenizer(part, return_tensors="pt", padding=True, truncation=False)
            if inputs["input_ids"].shape[1] > 128:
                raise ValueError("Object description unexpectedly exceeds 128 tokens")
            tokens += int(inputs["attention_mask"].sum())
            hidden = model(**inputs, use_cache=False).last_hidden_state
            mask = inputs["attention_mask"].unsqueeze(-1)
            pooled = (hidden * mask).sum(1) / mask.sum(1)
            pooled = torch.nn.functional.normalize(pooled.float(), dim=-1)
            for text, vector in zip(part, pooled):
                result[text] = vector.clone()
    if any(not torch.isfinite(v).all() for v in result.values()):
        raise FloatingPointError("Non-finite frozen encoder output")
    torch.save(result, out / "object_embeddings.pt")
    write_json(out / "encoder.json", {"model": str(model_path), "device": "cpu", "precision": "float32",
               "unique_texts": len(texts), "input_tokens": tokens, "seconds": time.monotonic() - start,
               "pooling": "mean last hidden state over non-padding tokens, L2 normalized",
               "model_files": {p.name: sha(p) for p in sorted(model_path.iterdir())
                               if p.is_file() and (p.suffix == ".safetensors" or p.name in ("config.json", "tokenizer.json"))},
               "cache_sha256": sha(out / "object_embeddings.pt")})
    del model
    return result


def score_policy(model: ConstraintPointer, data: list[dict], embeddings: dict, out: Path) -> dict:
    model.eval()
    outcomes = []
    started = time.monotonic()
    with torch.inference_mode():
        for ex in data:
            prefix = []
            start = time.monotonic()
            terminated = False
            for _ in range(len(ex["task"]["catalog"]) + 1):
                item = policy_input(ex["task"], ex["constraints"], prefix)
                inputs = collate([item], embeddings)
                allowed = inputs.pop("allowed")
                logits = model(**inputs)
                if not torch.isfinite(logits[allowed]).all():
                    raise FloatingPointError("Non-finite evaluation logits")
                action = item.actions[int(logits.masked_fill(~allowed, -torch.inf).argmax())]
                if action is None:
                    terminated = True
                    break
                prefix.append(action)
            checked = env.check(ex["task"], prefix if terminated else None, ex["constraints"])
            try:
                changes = env.plan_change_count(ex["task"], prefix)
            except ValueError:
                changes = None
            outcomes.append({"group_id": ex["group_id"], "subset": ex["subset"], "n": not ex["constraints"],
                             "plan": prefix, "terminated": terminated, "changes": changes,
                             "safe": checked["safe_success"], "completed": checked["completed"],
                             "violations": checked["violations"],
                             "faithful": checked["safe_success"] and changes == ex["min_changes"],
                             "seconds": time.monotonic() - start})
    def rate(rows, key):
        return sum(bool(r[key]) for r in rows) / len(rows) if rows else None
    nonempty = [r for r in outcomes if not r["n"]]
    empty = [r for r in outcomes if r["n"]]
    summary = {"rows": len(outcomes), "groups": len({r["group_id"] for r in outcomes}),
               "faithful": rate(outcomes, "faithful"), "faithful_constrained": rate(nonempty, "faithful"),
               "safe": rate(outcomes, "safe"), "completion": rate(outcomes, "completed"),
               "n_failure_or_deviation": 1 - rate(empty, "faithful") if empty else None,
               "mean_calls": sum(len(r["plan"]) for r in outcomes) / len(outcomes),
               "seconds": time.monotonic() - started}
    write_json(out, {"summary": summary, "outcomes": outcomes})
    return summary


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--lattice-dir", type=Path, required=True)
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--config", type=Path, default=ROOT / "configs/architecture_pilot_20261125.json")
    p.add_argument("--steps", type=int, default=1000)
    p.add_argument("--train-groups", type=int, default=256)
    p.add_argument("--dev-groups", type=int, default=300)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--smoke", action="store_true")
    args = p.parse_args()
    if not 1 <= args.steps <= 1000 or not 1 <= args.threads <= 4:
        raise ValueError("Pilot cap: 1,000 updates/arm, at most four CPU threads")
    args.out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    from run_v6_relay import check_release
    check_release(args.project_root)
    audit = json.loads((args.lattice_dir / "audit.json").read_text(encoding="utf-8"))
    for split in ("train", "dev"):
        if sha(args.lattice_dir / f"{split}_lattice.jsonl") != audit["splits"][split]["lattice_sha256"]:
            raise ValueError("Supervision lattice does not match the audited hash")
        if sha(args.project_root / "data/processed_v6" / f"{split}.jsonl") != audit["splits"][split]["data_sha256"]:
            raise ValueError("Lattice source data does not match the frozen release")
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    fixed = cfg["fixed"]
    start = time.monotonic()
    metadata = {"started_utc": datetime.now(timezone.utc).isoformat(), "device": "cpu", "threads": args.threads,
                "engineering_smoke": args.smoke, "steps_per_arm": args.steps,
                "config": cfg, "torch_version": torch.__version__,
                "evaluator_sha256": sha(Path(env.__file__)),
                "supervision_audit_sha256": sha(args.lattice_dir / "audit.json"),
                "source_sha256": {str(path.relative_to(ROOT)): sha(path) for path in
                                   [Path(__file__), ROOT / "src/constraint_pointer.py", ROOT / "src/constraint_set_learning.py"]},
                "data_sha256": {name: sha(args.lattice_dir / name) for name in ("train_lattice.jsonl", "dev_lattice.jsonl")}}
    write_json(args.out / "metadata.json", metadata)
    train = examples(args.lattice_dir / "train_lattice.jsonl", args.train_groups)
    dev = examples(args.lattice_dir / "dev_lattice.jsonl", args.dev_groups)
    if {x["group_id"] for x in train} & {x["group_id"] for x in dev}:
        raise ValueError("Training/development group leakage")
    prefixes = make_prefixes(train)
    make_prefixes(dev)  # Reachability audit only; no dev target is optimized.
    development = {name: [intervention(ex, name) for ex in dev]
                   for name in ("original", "rename_reorder", "duplicate")}
    texts = sorted({text for ex in train + dev for text in policy_input(ex["task"], ex["constraints"], []).texts})
    embeddings = object_embeddings(texts, args.model, args.out)
    write_json(args.out / "inputs.json", {"train_examples": len(train), "train_prefixes": len(prefixes),
               "dev_examples": len(dev), "dev_groups": len({x["group_id"] for x in dev}),
               "structural_reachability": "all accepted plans checked on selected train and dev",
               "scope": "oracle predicate records; no raw query, compiler, API, or test split",
               "probes": list(development), "missing_probes": ["numerical threshold changes", "resource-coupled OOD"]})
    results = {}
    try:
        for arm in cfg["arms"]:
            name = arm["name"]
            arm_dir = args.out / name
            arm_dir.mkdir()
            torch.manual_seed(cfg["seed_pilot"])
            rng = random.Random(cfg["seed_pilot"])
            model = ConstraintPointer(next(iter(embeddings.values())).numel(), width=fixed["head_width"],
                                      heads=fixed["head_attention_heads"], layers=fixed["head_layers"],
                                      graph=arm["attention"] == "typed_graph")
            optimizer = torch.optim.AdamW(model.parameters(), lr=fixed["learning_rate"],
                                          weight_decay=fixed["weight_decay"], betas=tuple(fixed["betas"]), eps=fixed["adam_epsilon"])
            train_start = time.monotonic()
            with (arm_dir / "loss.jsonl").open("w", encoding="utf-8") as log:
                for step in range(1, args.steps + 1):
                    model.train()
                    selected = [prefixes[rng.randrange(len(prefixes))] for _ in range(fixed["batch_size_prefixes"])]
                    inputs = collate([x[0] for x in selected], embeddings)
                    allowed = inputs.pop("allowed")
                    positive = torch.zeros_like(allowed)
                    for j, (_, single, many) in enumerate(selected):
                        positive[j, [single] if arm["target"] == "one_optimal_plan" else many] = True
                    optimizer.zero_grad(set_to_none=True)
                    loss = positive_set_nll(model(**inputs), allowed, positive)
                    if not torch.isfinite(loss):
                        raise FloatingPointError("Non-finite training loss")
                    loss.backward()
                    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), fixed["max_grad_norm"], error_if_nonfinite=True)
                    optimizer.step()
                    if any(not torch.isfinite(v).all() for v in model.parameters()):
                        raise FloatingPointError("Non-finite trained parameter")
                    if step == 1 or step % 20 == 0 or step == args.steps:
                        event = {"arm": name, "step": step, "loss": float(loss.detach()),
                                 "grad_norm": float(norm), "elapsed_seconds": time.monotonic() - train_start}
                        log.write(json.dumps(event, allow_nan=False) + "\n"); log.flush()
                        print(json.dumps(event), flush=True)
                    if step == 100:
                        projected = (time.monotonic() - train_start) * args.steps / step * len(cfg["arms"])
                        if projected > 2400:
                            raise RuntimeError("CPU preflight projects >40 minutes training; stop before scaling")
            torch.save(model.state_dict(), arm_dir / "model.pt")
            results[name] = {"parameters": sum(v.numel() for v in model.parameters()),
                             "train_seconds": time.monotonic() - train_start,
                             "development": {probe: score_policy(model, data, embeddings, arm_dir / f"{probe}.json")
                                             for probe, data in development.items()}}
            write_json(args.out / "results_partial.json", results)
            print(json.dumps({"arm_complete": name, "results": results[name]}), flush=True)
        write_json(args.out / "completion.json", {"status": "complete", "engineering_smoke": args.smoke,
                   "elapsed_seconds": time.monotonic() - start, "results": results})
    except Exception as exc:
        write_json(args.out / "failure.json", {"error": f"{type(exc).__name__}: {exc}",
                   "completed_arms": list(results), "elapsed_seconds": time.monotonic() - start})
        raise


if __name__ == "__main__":
    main()
