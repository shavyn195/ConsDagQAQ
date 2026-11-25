"""Time the existing deterministic solver under the identical oracle-record task.

The solver shares the frozen world's semantics with the scorer. This is a
reference-system baseline, not independent natural-language correctness proof.
No optimal plan or minimum-edit label is passed into inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--lattice-dir", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    sys.path.insert(0, str(args.project_root / "src"))
    import trust_env as env
    from run_v6_relay import check_release
    check_release(args.project_root)
    data = args.lattice_dir / "dev_lattice.jsonl"
    audit = json.loads((args.lattice_dir / "audit.json").read_text())
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    if digest != audit["splits"]["dev"]["lattice_sha256"]:
        raise ValueError("Lattice hash mismatch")
    rows = []
    for line in data.read_text().splitlines():
        group = json.loads(line)
        for mask, label in group["lattice"].items():
            task, constraints = group["task"], label["constraints"]
            # One untimed warmup, then three timing repeats; these are NOT seeds.
            env.plan(task, constraints)
            times = []
            for _ in range(3):
                start = time.perf_counter()
                plan, _ = env.plan(task, constraints)
                times.append(time.perf_counter() - start)
            checked = env.check(task, plan, constraints)
            changes = env.plan_change_count(task, plan)
            rows.append({"group_id": group["group_id"], "subset": mask,
                         "n": not constraints,
                         "faithful": checked["safe_success"] and changes == label["min_changes"],
                         "safe": checked["safe_success"],
                         "seconds_median": statistics.median(times),
                         "timing_repeats_seconds": times})
    constrained = [r for r in rows if not r["n"]]
    empty = [r for r in rows if r["n"]]
    result = {"scope": "oracle-record dev baseline; no raw-language claim",
              "limitations": "Known symbolic tools and checker semantics; not an arbitrary real environment. Timings exclude scoring, include solving, and use warm per-example runs; not matched concurrent timing of the neural head.",
              "lattice_sha256": digest,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "evaluator_sha256": hashlib.sha256(Path(env.__file__).read_bytes()).hexdigest(),
              "summary": {"rows": len(rows), "constrained_rows": len(constrained),
                          "faithful_constrained": sum(r["faithful"] for r in constrained) / len(constrained),
                          "n_failure_or_deviation": 1 - sum(r["faithful"] for r in empty) / len(empty),
                          "median_latency_ms": 1000 * statistics.median(r["seconds_median"] for r in rows),
                          "total_solver_seconds_median_repeat": sum(r["seconds_median"] for r in rows)},
              "outcomes": rows}
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
