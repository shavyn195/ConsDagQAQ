"""批量提取 literature 下全部 PDF 的文本与结构。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "literature" / "library"))

from extract_pdf import extract_pdf  # noqa: E402

LIT = ROOT / "literature"
OUT = LIT / "extracted"

pdfs = sorted(LIT.rglob("*.pdf"))
print(f"found {len(pdfs)} pdfs", flush=True)
ok = fail = 0
for pdf in pdfs:
    rel = pdf.relative_to(LIT)
    out_dir = OUT / rel.parent / pdf.stem
    try:
        extract_pdf(str(pdf), str(out_dir))
        ok += 1
    except Exception as exc:  # noqa: BLE001
        fail += 1
        print(f"FAIL {rel}: {exc}", flush=True)
print(f"done ok={ok} fail={fail}", flush=True)
