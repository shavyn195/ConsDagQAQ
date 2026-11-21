"""按创新点目录批量下载文献库 PDF（arXiv 官方源）。

用法：python scripts/fetch_library.py [--proxy http://127.0.0.1:7897]
输出：literature/library/<类别>/<arxiv_id>_<slug>.pdf 与 manifest.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "literature" / "library"

PAPERS: dict[str, list[tuple[str, str]]] = {
    "00_base": [
        ("2511.10037", "BeyondReAct"),
    ],
    "01_constraint_compiler": [
        ("2509.25586", "ATLAS"),
        ("2510.08992", "ConstraintsOfThought"),
        ("2602.20424", "ImplicitIntelligence"),
        ("2604.17886", "PRefine"),
        ("2606.05622", "AdaPlanBench"),
        ("2607.04854", "CARL"),
        ("2608.19861", "PolicyGuide"),
        ("2610.00797", "Sapien"),
        ("2610.11030", "NOMOS"),
        ("2610.23190", "LangNCO"),
        ("2610.25552", "SCA"),
        ("2610.36570", "CASEL"),
        ("2610.41040", "CGAP"),
        ("2610.41089", "CIRCE"),
        ("2611.09364", "SafeOrchestrate"),
    ],
    "02_objective_factorization": [
        ("2607.07435", "RLVP"),
        ("2607.02599", "AgentLTL"),
        ("2605.23382", "PARPO"),
        ("2611.12865", "ShortcutsBoundaries"),
        ("2602.05863", "ConstrainedGRPO"),
        ("2603.01620", "ToolRLA"),
        ("2603.25111", "SEVerA"),
        ("2605.08327", "InteractiveCritiqueRevision"),
        ("2607.22649", "STAIF"),
        ("2607.29246", "DontMixRewards"),
        ("2609.00213", "AggregationRewardHacking"),
        ("2609.27421", "CounterfactualConstraintDistill"),
        ("2609.39154", "DAGent"),
        ("2610.09219", "CM-DPO"),
        ("2610.19525", "RewardHackingVerifiableIF"),
        ("2610.21404", "TAG"),
        ("2611.16304", "StateAlign"),
        ("2611.17880", "SOTERIA"),
    ],
    "03_paired_benchmark": [
        ("2505.19030", "RECAST"),
        ("2603.03205", "MOSAIC"),
        ("2605.17558", "Firefly"),
        ("2606.21140", "MatchingMatters"),
        ("2607.03957", "NormWorldsCF"),
        ("2607.29175", "ExecutionFirst"),
        ("2609.09072", "ToolLoop"),
        ("2610.16859", "ANCHOR"),
        ("2610.18090", "AM-Bench"),
        ("2610.26359", "DiscoveryProbabilityGraph"),
        ("2610.28819", "LIFT"),
        ("2610.34634", "AgentProofBench"),
        ("2610.35981", "EffectWorld"),
        ("2611.14925", "ToolTurns"),
    ],
    "04_credit_assignment": [
        ("2605.03327", "TIDE"),
        ("2609.12424", "GranularityAdaptiveCredit"),
        ("2610.00838", "SHARPO"),
        ("2610.29292", "ContrastiveAttributionTopology"),
    ],
    "05_review_queue": [
        ("2409.16299", "HyperAgent-SE"),
        ("2510.10611", "HyperAgent-Hypergraph"),
        ("2510.24663", "OrchDAG"),
        ("2603.19461", "HyperAgentsSurvey"),
    ],
}

TAU_REC_URL = "https://www.taubench.com/community/tau-rec.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
}


def fetch(session: requests.Session, url: str, dest: Path, expect_pdf: bool) -> str:
    for attempt in range(1, 4):
        try:
            resp = session.get(url, headers=HEADERS, timeout=90)
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}")
            body = resp.content
            if expect_pdf and not body.startswith(b"%PDF"):
                raise RuntimeError(f"not pdf ({len(body)} bytes, {body[:24]!r})")
            if len(body) < 20_000:
                raise RuntimeError(f"too small ({len(body)} bytes)")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            return "ok"
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                return f"fail: {exc}"
            time.sleep(3 * attempt)
    return "fail"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proxy", default="http://127.0.0.1:7897")
    parser.add_argument("--only", default="", help="只下载指定类别")
    args = parser.parse_args()

    proxies = {"http": args.proxy, "https": args.proxy}
    session = requests.Session()
    session.trust_env = False
    session.proxies.update(proxies)

    manifest: list[dict[str, str]] = []
    total = ok = 0
    for category, items in PAPERS.items():
        if args.only and category != args.only:
            continue
        for arxiv_id, slug in items:
            total += 1
            dest = LIB / category / f"{arxiv_id}_{slug}.pdf"
            if dest.exists() and dest.stat().st_size > 20_000:
                status = "cached"
            else:
                status = fetch(session, f"https://arxiv.org/pdf/{arxiv_id}", dest, True)
                time.sleep(1.0)
            ok += int(status in {"ok", "cached"})
            print(json.dumps({"cat": category, "id": arxiv_id, "status": status,
                              "mb": round(dest.stat().st_size / 1024**2, 2) if dest.exists() else 0}),
                  flush=True)
            manifest.append({"category": category, "arxiv_id": arxiv_id, "slug": slug,
                             "file": str(dest.relative_to(ROOT)) if dest.exists() else "",
                             "status": status})

    if not args.only:
        dest = LIB / "03_paired_benchmark" / "tau-rec_webpage.html"
        status = "cached" if dest.exists() else fetch(session, TAU_REC_URL, dest, False)
        ok += int(status in {"ok", "cached"})
        total += 1
        print(json.dumps({"cat": "03_paired_benchmark", "id": "tau-rec", "status": status}), flush=True)
        manifest.append({"category": "03_paired_benchmark", "arxiv_id": "none", "slug": "tau-rec",
                         "file": str(dest.relative_to(ROOT)) if dest.exists() else "", "status": status})

    (LIB / "manifest.json").write_text(
        json.dumps({"total": total, "ok": ok, "items": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"total": total, "ok": ok}), flush=True)
    sys.exit(0 if ok == total else 1)


if __name__ == "__main__":
    main()
