"""Test OCR quality on multiple Infosys PDFs."""
import time
import os
from src.engines.document_ocr_engine import extract_text_pymupdf

base = "/app/downloaded document/CAM"
files = [f for f in os.listdir(base) if f.startswith("Infy") and f.endswith(".pdf")]
files.sort()

total_start = time.time()
for fname in files:
    fpath = os.path.join(base, fname)
    s = time.time()
    r = extract_text_pymupdf(fpath, ocr_fallback=False)
    dt = time.time() - s
    pc = r["page_count"]
    tl = len(r["text"])
    tc = len(r["tables"])
    qs = r["quality_score"]
    print(f"  {fname}: {dt:.1f}s | pages={pc} | text={tl} | tables={tc} | quality={qs}")

total = time.time() - total_start
print(f"TOTAL: {total:.1f}s for {len(files)} files")
