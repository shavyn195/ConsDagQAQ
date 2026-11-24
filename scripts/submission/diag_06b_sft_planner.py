"""一次性诊断：0.6B 编译器 × SFT-order42 规划器的 safe/faithful/过编辑分解。"""
import sys
import types
from pathlib import Path

fake = types.ModuleType("fcntl")
fake.LOCK_EX = 1
fake.flock = lambda *a, **k: None
fake.lockf = lambda *a, **k: None
sys.modules["fcntl"] = fake
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from probe_e2_format import parse  # noqa: E402
from probe_one_edit_repair import choose  # noqa: E402
from rescore_v4_side import aligned, load_jsonl  # noqa: E402
from run_e1 import strict_parse  # noqa: E402
from trust_env import check, normalize_constraint, plan as symbolic_plan, plan_change_count  # noqa: E402

root = ROOT
cands = {x["id"]: x["raw"] for x in
         load_jsonl(root / "outputs/e2_v4/verified-one-edit-full-holdouts-v1/raw.jsonl")}
stats = {"safe": 0, "faithful": 0, "n": 0, "planned": 0, "over_edited": 0, "under_edited": 0}
for sp in ["test_tpl_ho", "test_tool_ho"]:
    data = load_jsonl(root / f"data/processed_v4/{sp}.jsonl")
    preds = load_jsonl(root / f"outputs/e1/Qwen3-0.6B-v4/trained_predictions/{sp}.jsonl")
    raw = aligned(data, preds)
    for row, response in zip(data, raw):
        if not row["gold"]["constraints"]:
            continue
        task = row["task"]
        gold = row["gold"]["constraints"]
        pred = strict_parse(response)
        got = [c for c in pred["constraints"] if normalize_constraint(c, task) is not None] if pred else []
        actions = [parse(v, sorted(task["tools"]), "names") for v in cands[row["sample_id"]]]
        _, fixed, _, _, _ = choose(task, actions, got, row["sample_id"])
        stats["n"] += 1
        stats["planned"] += fixed is not None
        env = check(task, fixed, gold)
        stats["safe"] += env["safe_success"]
        if env["safe_success"]:
            changes = plan_change_count(task, fixed)
            _, gold_info = symbolic_plan(task, gold)
            extra = changes - gold_info["changes"]
            stats["faithful"] += extra == 0
            stats["over_edited"] += extra > 0
            stats["under_edited"] += extra < 0
n = stats["n"]
print(f"n={n} planned={stats['planned']} safe={stats['safe']} ({stats['safe']/n:.4f}) "
      f"faithful={stats['faithful']} ({stats['faithful']/n:.4f}) "
      f"over_edited={stats['over_edited']} under_edited={stats['under_edited']}")
