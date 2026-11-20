"""按固定 arXiv 编号下载论文并提取文本，保留可复查的本地副本。"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fitz
import requests

ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "literature" / "papers"
TEXT_DIR = ROOT / "literature" / "paper_texts"

PAPERS = {
    # 仅保留已核对标题与手册所指的论文；无法确认的条目不按错误编号下载。
    "ATLAS": "2509.25586",
    "CARL": "2607.04854",
    "RLVP": "2607.07435",
    "ReAct": "2210.03629",
    "AgentGym-RL": "2509.08755",
    "rStar2-Agent": "2508.20722",
    "ToolRL": "2504.13958",
    "Beyond-ReAct": "2511.10037",
}


def fetch(item):
    name, arxiv_id = item
    pdf_path = PDF_DIR / f"{name}_{arxiv_id}.pdf"
    text_path = TEXT_DIR / f"{name}_{arxiv_id}.txt"
    try:
        if not pdf_path.exists() or pdf_path.stat().st_size < 10_000:
            response = requests.get(
                f"https://arxiv.org/pdf/{arxiv_id}", timeout=120
            )
            if response.status_code != 200 or not response.content.startswith(b"%PDF"):
                return name, arxiv_id, f"HTTP {response.status_code}", "not-pdf"
            pdf_path.write_bytes(response.content)
        if not text_path.exists():
            with fitz.open(pdf_path) as document:
                text = "\n\n".join(
                    f"===== PAGE {index + 1} =====\n{page.get_text()}"
                    for index, page in enumerate(document)
                )
            text_path.write_text(text, encoding="utf-8")
        return name, arxiv_id, "ok", f"{pdf_path.stat().st_size / 1e6:.2f}MB"
    except Exception as exc:
        return name, arxiv_id, type(exc).__name__, str(exc)[:180]


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as executor:
        for result in executor.map(fetch, PAPERS.items()):
            print(*result, sep=" | ", flush=True)


if __name__ == "__main__":
    main()
