"""v5 强模型 PE 臂（零示例 / 十示例），与训练臂同 prompt、同评分；只写 outputs/e1_v5_side/<model>-<style>/。

与 run_cross_family_pe.py 同一请求与缓存协议：请求指纹 = (参数, 完整 messages)，断点续跑只复用指纹一致的缓存；
返回的模型名必须与请求一致；全量完成后用 rescore_v4_side.rescore（--data data/processed_v5）打分。
CPU / API 任务，不占 GPU。
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError

from pe_v4_side import DEFAULT_URL, demonstrations, fingerprint, restore
from rescore_v4_side import ROOT, digest, load_jsonl, rescore
from run_e1 import chat_messages_v4, eval_subsets


def request(params: dict, messages: list[dict]) -> dict:
    req = urllib.request.Request(DEFAULT_URL, data=json.dumps(dict(params, messages=messages)).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + os.environ["DASHSCOPE_API_KEY"]})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=110) as response:
                d = json.load(response)
            if d.get("model") != params["model"]:
                raise ValueError("Different model returned: " + str(d.get("model")))
            choice = d["choices"][0]
            raw = choice["message"].get("content") or ""
            if not isinstance(raw, str):
                raise ValueError("Unexpected response payload")
            return dict(raw=raw, model=d["model"], finish=choice.get("finish_reason"), usage=d.get("usage"))
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** (attempt + 1))
    raise RuntimeError("unreachable")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True, help="e.g. deepseek-v4-pro-0813 or qwen-max")
    p.add_argument("--style", choices=["zero", "few"], required=True)
    p.add_argument("--data", type=Path, default=ROOT / "data/processed_v5")
    p.add_argument("--workers", type=int, default=8)
    args = p.parse_args()
    params = dict(model=args.model, temperature=0, max_tokens=384)
    if args.model.startswith("deepseek"):
        params["enable_thinking"] = False
    out = ROOT / "outputs/e1_v5_side" / f"{args.model}-{args.style}"
    out.mkdir(parents=True, exist_ok=True)
    subsets = eval_subsets(args.data)
    rows = {s: load_jsonl(args.data / f"{s}.jsonl") for s in subsets}
    demo = demonstrations(load_jsonl(args.data / "train.jsonl")) if args.style == "few" else []
    conf = dict(params=params, url=DEFAULT_URL, demo_hash=fingerprint(demo), style=args.style,
                data={s: digest(args.data / f"{s}.jsonl") for s in ["train", *subsets]},
                modules={n: digest(Path(__file__).with_name(n + ".py"))
                         for n in ("dataset_v5_spec", "run_e1", "rescore_v4_side", "pe_v4_side", "eval_exec", "trust_env")},
                source=digest(Path(__file__)))
    manifest = out / "config.json"
    if manifest.exists() and json.loads(manifest.read_text(encoding="utf-8")) != conf:
        raise ValueError("Run fingerprint changed; use a new output directory")
    manifest.write_text(json.dumps(conf, indent=2, ensure_ascii=False), encoding="utf-8")
    for subset, cohort in rows.items():
        path = out / f"{subset}.jsonl"

        def messages(r: dict) -> list[dict]:
            system, user = chat_messages_v4(r)
            return [system, *demo, user]

        keys = {r["sample_id"]: fingerprint([params, messages(r)]) for r in cohort}
        missing = [r for r in cohort if r["sample_id"] not in restore(path, keys)]
        with path.open("a", encoding="utf-8") as f, ThreadPoolExecutor(max_workers=args.workers) as pool:
            for start in range(0, len(missing), args.workers):
                jobs = {pool.submit(request, params, messages(r)): r["sample_id"]
                        for r in missing[start:start + args.workers]}
                errors = []
                for job in as_completed(jobs):
                    try:
                        pred = job.result()
                    except Exception as exc:  # 记录后整批失败，不写半成品分数
                        errors.append(exc)
                        continue
                    sid = jobs[job]
                    print(json.dumps(dict(sample_id=sid, request_hash=keys[sid], **pred), ensure_ascii=False),
                          file=f, flush=True)
                if errors:
                    raise errors[0]
        saved = restore(path, keys)
        if set(saved) != set(keys) or any(v.get("model") != args.model for v in saved.values()):
            raise ValueError(f"Incomplete cohort or foreign model in {path}")
        print(subset, "complete", len(saved), flush=True)
    report = rescore(args.data, out)
    (out / "full-scores.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("scored", out)


if __name__ == "__main__":
    main()
