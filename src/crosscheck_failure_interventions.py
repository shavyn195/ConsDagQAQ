"""Replay two frozen compiler caches on two frozen candidate pools, then classify residual failures."""
from collections import Counter, defaultdict
from pathlib import Path
import json

from audit_repair_ceiling import classify
from audit_warmup_rollouts import shape
from eval_repair_sft import read, SPLITS
from full_one_edit import OUT as FIRST
from prepare_e2_credit_panel import PARENT
from probe_e2_format import parse
from probe_e2_planner_v1 import ROOT
from probe_one_edit_repair import choose
from rescore_v4_side import aligned, digest, load_jsonl
from run_e1 import strict_parse
from trust_env import check, normalize_constraint


def alternate(row, raw, response):
    task = row["task"]
    actions = [parse(v, sorted(task["tools"]), "names") for v in raw]
    parsed = strict_parse(response)
    rules = [c for c in (parsed or {}).get("constraints", []) if normalize_constraint(c, task) is not None]
    _, fixed, _, _, _ = choose(task, actions, rules, row["sample_id"])
    return bool(shape(fixed, task) and check(task, fixed, row["gold"]["constraints"])["safe_success"])


def main():
    folders = (FIRST, PARENT / "verified-one-edit-full-order44-v1")
    out = PARENT / "failure-interventions-2x2-v1"
    a, b = [read(f / "protocol.json") for f in folders]
    assert a["adapter"] != b["adapter"] and all(a[k] == b[k] for k in a if k != "adapter")
    raw = []; scored = []; provenance = {}
    for folder in folders:
        report = read(folder / "results.json")
        for name, target in (("raw",raw),("cases",scored)):
            path = folder / (name + ".jsonl")
            assert digest(path) == report[name]
            provenance[f"{folder.name}/{name}"] = report[name]
            target.append(load_jsonl(path))
    data = {}
    for split in SPLITS:
        dp = ROOT/f"data/processed_v4/{split}.jsonl"
        pc = ROOT/f"outputs/e1_v4_side/deepseek-v4-pro-0813-few/{split}.jsonl"
        rows = load_jsonl(dp)
        assert digest(dp) == a["sources"][split][0]
        provenance[split] = [digest(dp),digest(pc)]
        data.update({r["sample_id"]:(r,p) for r,p in zip(rows,aligned(rows,load_jsonl(pc)),strict=True)})
    out.mkdir(exist_ok=False)
    (out/"protocol.json").write_text(json.dumps(dict(sources=provenance, code=digest(Path(__file__)),
        design="Exploratory factorial replay. Common four-candidate budget, semantic repair rule, same query IDs and gold evaluator. Two fixed uniform-SFT training orders and two frozen compiler caches. No empty routing."),indent=2))
    cells=Counter(); residual=defaultdict(Counter); contrasts=defaultdict(Counter)
    with (out/"rows.jsonl").open("x") as f:
        for k,r0,r1,s0,s1 in zip(a["ids"],*raw,*scored,strict=True):
            row,p=data[k]; assert all(x["id"]==k for x in (r0,r1,s0,s1))
            if not row["gold"]["constraints"]: continue
            flags = {"p0_c0":bool(s0["safe"]["repair"]), "p1_c0":bool(s1["safe"]["repair"]),
                     "p0_c1":alternate(row,r0["raw"],p), "p1_c1":alternate(row,r1["raw"],p)}
            cells.update(flags)
            label=classify(row,r0["raw"],s0)
            if not flags["p0_c0"]:
                residual[label].update(n=1,compiler_only=flags["p0_c1"],pool_only=flags["p1_c0"],both_changes=flags["p1_c1"])
                if label in ("no_complete_plan","no_safe_neighbor"): assert not flags["p0_c1"]
            for col in ("p0_c1","p1_c0","p1_c1"):
                contrasts[col].update(wins=flags[col] and not flags["p0_c0"],losses=flags["p0_c0"] and not flags[col])
            print(json.dumps(dict(id=k,group=row["group_id"],split=row["subset"],variant=row["variant"],initial_status=label,values=flags)),file=f)
    assert sum(v["n"] for v in residual.values())==1400-cells["p0_c0"]
    report=dict(n=1400,cells=cells,paired_vs_initial=contrasts,interventions_on_initial_failures=residual,rows=digest(out/"rows.jsonl"))
    (out/"results.json").write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)


if __name__=="__main__":
    main()
