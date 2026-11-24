"""Information-complete monolithic control, separate from the live E2 arm.

Reuses the frozen E2 training/evaluation loops. Adds the same public policy and
tool names as the compiler, plus the complete task supplied to its consumer.
Checks every training row fits before allocating GPU and saves raw plans.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from dataset_v5_spec import POLICY_CARD

ROOT = Path(__file__).resolve().parents[1]


def public_messages(row):
    task = row["task"]
    names = {t["role"]: t["name"] for t in row["catalog"]}
    public = {
        "data_class": task["data_class"],
        "stages": task["stages"], "finish": task["finish"], "optional": task["optional"],
        "tools": {role: [names[role], spec["cost_cny"], spec["duration_min"], spec["recipient"], spec["clears_pii"]]
                  for role, spec in task["tools"].items()},
    }
    prompt = (
        "Produce a JSON array of tool roles completing the task under the user constraints. "
        "Choose exactly one tool per stage in stage order, then every finish tool; optional tools may be inserted. "
        "No duplicates. Minimize edits: each stage substitution, optional insertion and finish-pair inversion costs 1. "
        "No constraints: use all stage defaults and listed finish order. Costs and durations add. "
        "PII activates after acquisition; clears_pii removes it; external tools leak active PII. "
        "Precedence requires the first role before the second whenever the second appears.\n"
        + POLICY_CARD + "\n"
        "Tool values=[display_name,cost_cny,duration_min,recipient,clears_pii]. Public task: "
        + json.dumps(public, ensure_ascii=False, separators=(",", ":"))
        + "\nUser query: " + row["query"] + "\nPlan JSON:"
    )
    return [{"role": "system", "content": "Output a JSON array only."}, {"role": "user", "content": prompt}]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    import sub_e2_monolithic as base
    from transformers import AutoTokenizer
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepare-only", action="store_true")
    p.add_argument("--model", default=str(ROOT / "models/Qwen3-1.7B"))
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs/submission/e2_monolithic_public_contract")
    p.add_argument("--max-seq-len", type=int, default=1280)
    a = p.parse_args()
    data_dir = ROOT / "data/processed_v5"
    tok = AutoTokenizer.from_pretrained(a.model, local_files_only=True)
    data = {s: base.load_jsonl(data_dir / f"{s}.jsonl") for s in ("train", *base.SPLITS)}
    coverage = {}
    for split, rows in data.items():
        lengths = []
        answers = []
        for row in rows:
            prefix = base.render_chat(tok, public_messages(row), add_generation_prompt=True)["input_ids"][0].numel()
            target = len(tok(base.monolithic_target(row) + tok.eos_token, add_special_tokens=False)["input_ids"])
            lengths.append(prefix + target)
            answers.append(target)
        coverage[split] = {"rows": len(rows), "max_total_tokens": max(lengths), "max_target_tokens": max(answers),
                           "over_limit": sum(n > a.max_seq_len for n in lengths)}
    protocol = {"revision": "20261125-public-contract-v1", "seed": 42, "precision": "bf16",
                "max_seq_len": a.max_seq_len, "max_new_tokens": 384, "model": a.model,
                "coverage": coverage, "data_sha256": {s: sha(data_dir / f"{s}.jsonl") for s in data},
                "source_sha256": {n: sha(Path(__file__).with_name(n)) for n in (
                    Path(__file__).name, "sub_e2_monolithic.py", "run_e1.py", "trust_env.py", "dataset_v5_spec.py")},
                "evaluation_context_limit": int(tok.model_max_length),
                "note": "max_seq_len is a training cap; evaluation keeps full inputs, as in the frozen baseline. Same training rows, updates and LoRA recipe; compute costs are measured, not assumed equal"}
    a.out_dir.mkdir(parents=True, exist_ok=True)
    path = a.out_dir / "public_protocol.json"
    if path.exists() and json.loads(path.read_text()) != protocol:
        raise ValueError("Public-control protocol changed; preserve old output and use another directory")
    path.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    print(json.dumps(protocol), flush=True)
    if (coverage["train"]["over_limit"] or any(c["max_target_tokens"] > 384 for c in coverage.values())
            or any(c["max_total_tokens"] + 384 > tok.model_max_length for c in coverage.values())):
        raise ValueError("Length coverage failed; no training started")
    if a.prepare_only:
        return
    if (a.out_dir / "adapter").exists() or (a.out_dir / "metrics.json").exists():
        raise ValueError("Existing run preserved; no silent restart")
    base.informed_chat_messages = public_messages
    original_generate = base.generate_batched_prompted

    def save_raw(model, tokenizer, rows, max_new_tokens, batch_size, args):
        predictions, raw = original_generate(model, tokenizer, rows, max_new_tokens, batch_size, args)
        if len(raw) != len(rows):
            raise ValueError("Evaluation coverage differs")
        split = rows[0]["subset"]
        dest = a.out_dir / "raw_predictions"
        dest.mkdir(exist_ok=True)
        with (dest / f"{split}.jsonl").open("x", encoding="utf-8") as f:
            for row, text in zip(rows, raw):
                f.write(json.dumps({"sample_id": row["sample_id"], "raw": text}, ensure_ascii=False) + "\n")
        return predictions, raw

    base.generate_batched_prompted = save_raw
    base.main(["--prompt-mode", "informed", "--model", a.model, "--data-dir", str(data_dir),
               "--out-dir", str(a.out_dir), "--seed", "42", "--precision", "bf16",
               "--max-seq-len", str(a.max_seq_len), "--pipeline-run", str(ROOT / "outputs/e1/Qwen3-1.7B-v5-seed42")])
    metrics_path = a.out_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text())
    metrics["prompt_mode"] = "public_contract"
    metrics["public_protocol_sha256"] = sha(path)
    metrics["preregistered_rule"] = (
        "Exploratory fair-input correction, seed42 only. Report paired group CI and signed difference; "
        "an inconclusive superiority test is not evidence of equivalence. Preserve the old decision rule as history.")
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
