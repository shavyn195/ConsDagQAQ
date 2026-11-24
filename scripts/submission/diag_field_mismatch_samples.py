"""抽查 scope/params 字段错误实例，确认字段比对口径反映真实差异而非匹配伪影。"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def load_jsonl(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


rows = {r["sample_id"]: r for r in load_jsonl(ROOT / "data/processed_v5/test_tool_ho.jsonl")}
preds = {p["sample_id"]: p["prediction"] for p in load_jsonl(
    ROOT / "outputs/e1/Qwen3-1.7B-v5-seed42/trained_predictions/test_tool_ho.jsonl")}

shown = {"scope": 0, "params": 0}
for sid, row in rows.items():
    if row["variant"] not in ("explicit", "implicit"):
        continue
    gold = row["gold"]["constraints"]
    pred = [c for c in (preds.get(sid, {}).get("constraints") or []) if isinstance(c, dict)]
    for g in gold:
        p = next((c for c in pred if c.get("type") == g.get("type")), None)
        if p is None:
            continue
        gs, ps = g.get("scope"), p.get("scope")
        if isinstance(gs, list) and isinstance(ps, list):
            same = sorted(gs) == sorted(ps)
        else:
            same = gs == ps
        if not same and shown["scope"] < 3:
            shown["scope"] += 1
            print(f"--- scope mismatch {sid} type={g['type']}")
            print(f"    gold scope : {gs}")
            print(f"    pred scope : {ps}")
            print(f"    gold params: {json.dumps(g['params'], ensure_ascii=False, sort_keys=True)}")
            print(f"    pred params: {json.dumps(p.get('params'), ensure_ascii=False, sort_keys=True)}")
        if json.dumps(g.get("params"), sort_keys=True, default=str) != json.dumps(p.get("params"), sort_keys=True, default=str) and shown["params"] < 4:
            shown["params"] += 1
            print(f"--- params mismatch {sid} type={g['type']}")
            print(f"    gold params: {json.dumps(g['params'], ensure_ascii=False, sort_keys=True)}")
            print(f"    pred params: {json.dumps(p.get('params'), ensure_ascii=False, sort_keys=True)}")
