"""Quick test: verify that the rupee fix and cover page spacing works."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Minimal CAM markdown with ₹ characters to test
test_md = """# INDIAN BANK — Corporate Banking Division

**CIN:** L45201DL1999PLC195937 | BSE / NSE: BSE, NSE | NSE: PNCINFRA  
**PAN:** AABCP1234R  
Sector: Infrastructure — Road & Highway Construction — EPC  
Case Type: NTB | Facility: Term Loan  
Amount Requested: ₹ 1,500.00 Cr  
Recommendation: REFER  
Risk Grade: C (Score: 58.6)  
Date: 2026-04-07  

## TABLE OF CONTENTS
1. Executive Summary

# 1. Executive Summary

| Parameter | Details | Source / Remarks |
| --- | --- | --- |
| Amount Requested (₹ Cr) | 1500.0 | RM Submission |
| Revenue (₹ Cr) | 8650.0 | Audited Financials |

The facility of ₹ 1,500.00 Cr is for EPC projects. Total assets: ₹ 15,610.0 Cr.
"""

from src.api.main import _generate_pdf

pdf_bytes = _generate_pdf(test_md, "PNC INFRATECH LIMITED")
out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "test_rupee_fix.pdf")
with open(out_path, "wb") as f:
    f.write(pdf_bytes)

print(f"PDF generated: {len(pdf_bytes)} bytes -> {out_path}")

# Verify no ₹ remains in the PDF text
import pdfplumber
pdf = pdfplumber.open(out_path)
for i, page in enumerate(pdf.pages):
    text = page.extract_text() or ""
    rupee_count = text.count("₹")
    square_count = text.count("■")
    rs_count = text.count("Rs.")
    if rupee_count or square_count or rs_count:
        print(f"Page {i+1}: ₹={rupee_count}, ■={square_count}, Rs.={rs_count}")
    if i == 0:
        print(f"Cover page text preview:\n{text[:500]}")
pdf.close()
print("Done!")
