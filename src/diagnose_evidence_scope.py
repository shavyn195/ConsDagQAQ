"""Post-hoc catalog-only scope derivation. Uses no reference output or checker feedback."""
import argparse
import json

from build_evidence_panel import ARMS, OUT, write_json
from run_e1 import strict_parse
from score_evidence_panel import measure


def derive(raw, catalog):
    obj = strict_parse(raw)
    if obj is None:
        return raw
    role_ids = {r["role"] for r in catalog}
    for c in obj["constraints"]:
        typ, p = c["type"], c["params"]
        if typ == "budget":
            roles = [r["role"] for r in catalog if r["paid"]]
        elif typ == "privacy":
            roles = [r["role"] for r in catalog if r["recipient"]=="external"]
        elif typ == "deadline":
            roles = ["*"]
        elif typ in ("order","tool_auth"):
            keys = ["before_role","after_role"] if typ=="order" else ["required_role"]
            roles = [p.get(k) for k in keys]
            if any(not isinstance(r,str) or r not in role_ids for r in roles):
                continue
        else:
            continue
        c["scope"] = sorted("role:"+r for r in roles)
    return json.dumps(obj)


def run(size):
    folder = OUT/size
    panel = [json.loads(s) for s in (OUT/"panel.jsonl").read_text().splitlines()]
    raw = {(x["id"],x["arm"]):x["raw"] for x in map(json.loads,(folder/"raw.jsonl").read_text().splitlines())}
    reference = json.loads((folder/"paired_scores.json").read_text())
    paired = {r["id"]:r for r in reference}
    scores, diagnostics = [], {}
    for r in panel:
        vals = {}
        for a in ARMS:
            out = raw[r["id"],a]
            new = derive(out,r["catalog"])
            vals[a] = measure(r,a,new)
            old = paired[r["id"]]["arms"][a]
            assert all(vals[a][k]==old[k] for k in ("params","span","plan_verdict","parse"))
        scores.append(dict(id=r["id"], both=vals["original"]["full"] and vals["edited"]["full"],
                           before=paired[r["id"]]["full"], both_scope=vals["original"]["scope"] and vals["edited"]["scope"],
                           neutral=vals["neutral_old"]["full"] and vals["neutral_new"]["full"]))
    for name, rows in [("overall",scores)]+[(v, [s for s in scores if s["id"] in {r["id"] for r in panel if r["variant"]==v}]) for v in ("explicit","implicit")]:
        diagnostics[name]=dict(n=len(rows),both=sum(s["both"] for s in rows),before=sum(s["before"] for s in rows),
                               gained=sum(s["both"] and not s["before"] for s in rows),lost=sum(s["before"] and not s["both"] for s in rows),
                               both_target_scope=sum(s["both_scope"] for s in rows),neutral_both=sum(s["neutral"] for s in rows))
    write_json(folder/"catalog_scope_diagnostic.json",diagnostics)
    print(size,diagnostics["overall"])


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("sizes",nargs="+")
    for size in parser.parse_args().sizes:
        run(size)
