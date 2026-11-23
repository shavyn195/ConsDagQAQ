"""Build a frozen, paired evidence intervention panel from v4 held-out groups."""
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import random
import re
import string

from audit_warmup_rollouts import shape
from build_dataset_v4 import render_mapping, scope_of
from dataset_v4_spec import E_TEMPLATES, I_TEMPLATES, WORLDS, fill_template, tool_name
from trust_env import canonical_insert, check

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/evidence_edits_v1"
TYPES = ("tool_auth", "order", "budget", "deadline")
SPLITS = ("test_tpl_ho", "test_tool_ho")
MODELS = ("0.6B", "1.7B")
ARMS = ("original", "edited", "neutral_old", "neutral_new")
N = 6  # independent groups per type and split, both language variants from each
SEED = 77341


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(2**20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def get_template(row, kind):
    pool, _, variant, idx = next(t.split(":") for t in row["template_ids"]
                                 if t.split(":")[1] == kind and t.split(":")[2] != "N")
    if variant == "E":
        return E_TEMPLATES[kind][pool][int(idx)], 0
    _, difficulty, text = I_TEMPLATES[kind][pool][int(idx)]
    return text, difficulty


def numeric_edit(text, template, difficulty, kind, old, new):
    # Match named slots, including templates in which the end time occurs first.
    pattern = "".join(re.escape(lit) + (f"(?P<{name}>.+?)" if name else "")
                      for lit, name, _, _ in string.Formatter().parse(template))
    slots = re.fullmatch(pattern, text).groupdict()
    if "limit" in slots or "hours" in slots:
        key = "limit" if "limit" in slots else "hours"
        decode = lambda s: int(s[key].replace(",", ""))
        replacement = f"{new:,}"
    elif "now" in slots:
        key = "end"
        decode = lambda s: int(s["end"][:2]) - int(s["now"][:2])
        end = int(slots["now"][:2]) + new
        if not 0 <= end < 24 or new in (end, int(slots["now"][:2])):
            return None
        replacement = f"{end:02}:00"
    else:
        key = "a"
        sign = 1 if kind == "budget" and difficulty == 3 else -1
        decode = lambda s: int(s["a"].replace(",", "")) + sign * int(s["b"].replace(",", ""))
        a = new - sign * int(slots["b"].replace(",", ""))
        if a <= 0 or new in (a, int(slots["b"].replace(",", ""))):
            return None
        replacement = f"{a:,}"
    assert decode(slots) == old
    old_slot = slots[key]
    slots[key] = replacement
    assert decode(slots) == new
    return fill_template(template, slots), old_slot, replacement


def edit(row, idx, new_params):
    target = row["gold"]["constraints"][idx]
    kind, span = target["type"], target["evidence_span"]
    template, difficulty = get_template(row, kind)
    p = target["params"]
    if kind in ("budget", "deadline"):
        values = numeric_edit(span, template, difficulty, kind, next(iter(p.values())),
                              next(iter(new_params.values())))
        if values is None:
            return None
        new_span, surface_old, surface_new = values
    else:
        def render(params):
            m = render_mapping(random.Random(0), kind, params, "team", "dataset", None, "test")
            return fill_template(template, m)
        assert render(p) == span
        new_span = render(new_params)
        key, = [k for k in p if p[k] != new_params[k]]
        surface_old, surface_new = tool_name(p[key]), tool_name(new_params[key])
    assert row["query"].count(span) == 1 and span != new_span and "{" not in new_span
    scope = scope_of(kind, new_params, row["task"])
    assert (set(scope) != set(target["scope"])) == (kind in ("order", "tool_auth"))
    new_gold = deepcopy(row["gold"])
    new_gold["constraints"][idx].update(params=new_params, evidence_span=new_span, scope=scope)
    # Matched placebo pair: change the same number/name in an explicitly historical label.
    def neutral(label):
        return row["query"] + f' An unrelated archived request had the reference label "{label}".'
    return dict(id=row["sample_id"], group=row["group_id"], subset=row["subset"],
                variant=row["variant"], kind=kind, idx=idx, difficulty=difficulty,
                catalog=row["catalog"], task=row["task"], old=row["gold"], new=new_gold,
                queries=dict(original=row["query"], edited=row["query"].replace(span, new_span),
                             neutral_old=neutral(surface_old), neutral_new=neutral(surface_new)))


def alternatives(kind, c, task, rng):
    params = c["params"]
    if kind in ("budget", "deadline"):
        key, old = next(iter(params.items()))
        steps = (50, 100, 200, 400) if kind == "budget" else (1, 2, 3, 4)
        values = [{key: old + sign * step} for step in steps for sign in (-1, 1)
                  if old + sign * step >= (100 if kind == "budget" else 1)]
    else:
        a, b = (("approval_role", "required_role") if kind == "tool_auth" else
                ("before_role", "after_role"))
        permitted = WORLDS[task["world"]]["auth_pairs" if kind == "tool_auth" else "order_pairs"]
        values = [{a: x, b: y} for x, y in permitted if x in task["tools"] and y in task["tools"]
                  and sum((params[a] != x, params[b] != y)) == 1 and
                  (kind != "tool_auth" or y != params[b])]
    rng.shuffle(values)
    return values


def feasible_plans(task, other):
    options = sorted(task["optional"])
    for stage in itertools.product(*(s["alternatives"] for s in task["stages"])):
        for finish in itertools.permutations(task["finish"]):
            for mask in itertools.product((False, True), repeat=len(options)):
                p = canonical_insert(task, list(stage + finish), list(itertools.compress(options, mask)))
                if shape(p, task) and check(task, p, other)["safe_success"]:
                    yield tuple(p)


def certificates(task, plans, old, new):
    safe, flipped = {}, None
    for p in plans:
        outcomes = [check(task, p, [c])["safe_success"] for c in (old, new)]
        for label, c, ok in zip(("old", "new"), (old, new), outcomes):
            role = c["params"].get("required_role", c["params"].get("after_role"))
            if ok and (not role or role in p):
                safe[label] = p
        if outcomes[0] != outcomes[1]:
            flipped = dict(plan=p, old=outcomes[0], new=outcomes[1])
        if len(safe) == 2 and flipped:
            return dict(witness=safe, distinguish=flipped)
    return None


def build():
    rng = random.Random(SEED)
    panel, screening, sources = [], {}, {}
    for split in SPLITS:
        source = ROOT / f"data/processed_v4/{split}.jsonl"
        sources[split] = digest(source)
        groups = defaultdict(dict)
        for line in source.read_text(encoding="utf8").splitlines():
            row = json.loads(line)
            if row["variant"] != "none" and len(row["gold"]["constraints"]) > 1:
                groups[row["group_id"]][row["variant"]] = row
        used = set()
        for kind in TYPES:
            ids = sorted(g for g, r in groups.items() if g not in used and
                         any(c["type"] == kind for c in r["explicit"]["gold"]["constraints"]))
            rng.shuffle(ids)
            audit = Counter(pool_after_excluding_used=len(ids))
            for gid in ids:
                pair = [groups[gid][v] for v in ("explicit", "implicit")]
                row = pair[0]
                gold = row["gold"]["constraints"]
                i = next(i for i, c in enumerate(gold) if c["type"] == kind)
                assert all(r["task"] == row["task"] and r["catalog"] == row["catalog"] and
                           r["gold"]["constraints"][i]["params"] == gold[i]["params"] for r in pair)
                audit["screened"] += 1
                alts = alternatives(kind, gold[i], row["task"], rng)
                plans = sorted(set(feasible_plans(row["task"], gold[:i] + gold[i+1:]))) if alts else []
                for p in alts:
                    records = [edit(r, i, p) for r in pair]
                    if not all(records):
                        continue
                    cert = certificates(row["task"], plans, gold[i], records[0]["new"]["constraints"][i])
                    if cert is not None:
                        panel.extend(dict(rec, certificate=cert) for rec in records)
                        audit["accepted"] += 1
                        used.add(gid)
                        break
                if audit["accepted"] == N:
                    break
            screening[f"{split}/{kind}"] = dict(audit)
    assert panel and len({r["id"] for r in panel}) == len(panel)
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/"panel.jsonl").open("x", encoding="utf8", newline="\n") as f:
        for rec in panel:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    write_json(OUT/"protocol.json", dict(seed=SEED, cap_groups=N, screening=screening,
               panel_sha256=digest(OUT/"panel.jsonl"), source_sha256=sources, models=MODELS,
               batch=32, max_new_tokens=384, precision="bf16", sampling="greedy",
               arms=ARMS, groups=len(panel)//2, primary="both active outputs: full multiset of strict keys and verbatim evidence, correct top-level state, no abstain",
               secondary="paired target parameters/scope/evidence, other gold constraints, neutral controls, distinguishing plan decision",
               hypothesis="After an active edit the target follows the edited gold and other constraints persist. Neutral label edits preserve the original objects."))
    print(json.dumps(screening), flush=True)


if __name__ == "__main__":
    build()
