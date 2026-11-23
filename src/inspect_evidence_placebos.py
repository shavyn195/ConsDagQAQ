"""Characterize neutral-label failures from saved GPU outputs, without repairing any answer."""
import argparse
from collections import Counter
import json
from build_evidence_panel import OUT, write_json
from run_e1 import strict_parse


def inspect(size):
    panel = {r["id"]:r for r in map(json.loads,(OUT/"panel.jsonl").read_text().splitlines())}
    report = {}
    for name, prefix in (("quoted",OUT),("unquoted",OUT/"unquoted_followup")):
        counts = Counter(valid=0, invalid=0, cites_archived_sentence_among_valid=0,
                         archived_sentence_verbatim_in_invalid_raw=0, too_many_objects_among_valid=0)
        for x in map(json.loads,(prefix/size/"raw.jsonl").read_text().splitlines()):
            if not x["arm"].startswith("neutral"):
                continue
            obj = strict_parse(x["raw"])
            marker = "unrelated archived request"
            if obj is None:
                counts["invalid"] += 1
                counts["archived_sentence_verbatim_in_invalid_raw"] += marker in x["raw"].lower()
            else:
                counts["valid"] += 1
                counts["cites_archived_sentence_among_valid"] += any(marker in str(c.get("evidence_span","")).lower() for c in obj["constraints"])
                counts["too_many_objects_among_valid"] += len(obj["constraints"]) > len(panel[x["id"]]["old"]["constraints"])
        assert counts["valid"] + counts["invalid"] == len(panel)*2
        report[name] = dict(counts)
    write_json(OUT/size/"placebo_errors.json",report)
    print(size,report)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("sizes",nargs="+")
    for size in parser.parse_args().sizes:
        inspect(size)
