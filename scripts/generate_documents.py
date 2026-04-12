"""
Generate sample corporate documents for the 4 test companies.
Creates realistic document content in the document store.
Run this script once to populate storage/documents/.
"""

import json
import sys
from pathlib import Path

_root = str(Path(__file__).parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.services.document_store import doc_store
from src.services.external_systems import (
    mca_company_master, mca_directors, mca_charges,
    gstin_details, gstin_turnover, bureau_commercial_report,
    rating_action, market_intelligence, crilc_report,
    epfo_compliance, itr_filing_status,
    _ENTITY_TO_IDS,
)


def _make_text(content: str) -> bytes:
    return content.encode("utf-8")


def _make_json(data: dict) -> bytes:
    return json.dumps(data, indent=2, default=str).encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
# KYC DOCUMENTS
# ══════════════════════════════════════════════════════════════════════════════

KYC_TEMPLATES = {
    "BMFG001": {
        "pan_card.txt": """
═══════════════════════════════════════════
         INCOME TAX DEPARTMENT
         PERMANENT ACCOUNT NUMBER
═══════════════════════════════════════════
Name:    BHARAT MANUFACTURING LTD
PAN:     AABCB1234F
Father's Name: N/A (Company)
DOI:     15/04/2008
Status:  Active
Category: Company
Jurisdiction: Mumbai
═══════════════════════════════════════════
        [Digital PAN Card Copy]
═══════════════════════════════════════════
""",
        "certificate_of_incorporation.txt": """
═══════════════════════════════════════════════════
  MINISTRY OF CORPORATE AFFAIRS — GOVERNMENT OF INDIA
  CERTIFICATE OF INCORPORATION
═══════════════════════════════════════════════════

Certificate No: 185432
CIN: L29100MH2008PLC185432

I hereby certify that BHARAT MANUFACTURING LIMITED
is this day incorporated under the Companies Act, 2013
and that the company is limited by shares.

Given under my hand at Mumbai this Fifteenth day of April,
Two Thousand and Eight.

Registrar of Companies
Maharashtra, Mumbai

Company Type: Public Limited Company
Authorized Capital: ₹1,000,00,00,000 (One Thousand Crore)
""",
        "board_resolution.txt": """
═══════════════════════════════════════════════════
  BOARD RESOLUTION — BHARAT MANUFACTURING LTD
  CIN: L29100MH2008PLC185432
═══════════════════════════════════════════════════

Date: 15-Jan-2026

RESOLVED THAT the company hereby applies for credit
facilities from [Bank Name], totalling ₹150 Crore,
comprising:
  - Term Loan: ₹100 Crore
  - Working Capital (Cash Credit): ₹50 Crore

The Managing Director, Mr. Rajesh K. Mehta (DIN: 00112233),
and CFO, Ms. Kavita Sharma, are jointly authorized to:
  1. Submit the loan application and all supporting documents
  2. Execute all security documents
  3. Accept the terms and conditions of the sanction

Sd/-
Rajesh K. Mehta          Sunita R. Mehta
Managing Director        Whole-time Director

Sd/-
Kavita Sharma
Company Secretary
""",
        "gst_registration.txt": """
═══════════════════════════════════════════════════
         GST REGISTRATION CERTIFICATE
═══════════════════════════════════════════════════
GSTIN:          27AABCB1234F1Z5
Legal Name:     BHARAT MANUFACTURING LTD
Trade Name:     BHARAT MFG
PAN:            AABCB1234F
State:          Maharashtra
Date of Reg:    01-Jul-2017
Status:         Active
Type:           Regular Taxpayer
Constitution:   Public Limited Company
Nature:         Manufacturing, Export
═══════════════════════════════════════════════════
""",
    },
    "PINF001": {
        "pan_card.txt": """
═══════════════════════════════════════════
         INCOME TAX DEPARTMENT
         PERMANENT ACCOUNT NUMBER
═══════════════════════════════════════════
Name:    PINNACLE INFRA PROJECTS LTD
PAN:     AABCP5678G
DOI:     22/08/2005
Status:  Active
Category: Company
Jurisdiction: Delhi
═══════════════════════════════════════════
""",
        "certificate_of_incorporation.txt": """
═══════════════════════════════════════════════════
  MINISTRY OF CORPORATE AFFAIRS — GOVERNMENT OF INDIA
  CERTIFICATE OF INCORPORATION
═══════════════════════════════════════════════════

CIN: L45200DL2005PLC134567

PINNACLE INFRA PROJECTS LIMITED
incorporated under Companies Act, 2013.
Limited by shares.

Registered at: New Delhi
Date: 22nd August 2005

Authorized Capital: ₹2,000,00,00,000 (Two Thousand Crore)
""",
        "gst_registration.txt": """
═══════════════════════════════════════════════════
         GST REGISTRATION CERTIFICATE
═══════════════════════════════════════════════════
GSTIN:          07AABCP5678G1Z8
Legal Name:     PINNACLE INFRA PROJECTS LTD
State:          Delhi
Status:         Active
Type:           Regular Taxpayer
Constitution:   Public Limited Company
Nature:         Works Contract, Construction
═══════════════════════════════════════════════════
""",
    },
    "SPHR001": {
        "pan_card.txt": """
═══════════════════════════════════════════
         INCOME TAX DEPARTMENT
         PERMANENT ACCOUNT NUMBER
═══════════════════════════════════════════
Name:    SUNRISE PHARMA PVT LTD
PAN:     AABCS9012H
DOI:     10/06/2012
Status:  Active
Category: Company
Jurisdiction: Ahmedabad
═══════════════════════════════════════════
""",
        "certificate_of_incorporation.txt": """
═══════════════════════════════════════════════════
  MINISTRY OF CORPORATE AFFAIRS — GOVERNMENT OF INDIA
  CERTIFICATE OF INCORPORATION
═══════════════════════════════════════════════════

CIN: U24230GJ2012PTC068945

SUNRISE PHARMA PRIVATE LIMITED
incorporated under Companies Act, 2013.
Limited by shares.

Registered at: Gujarat
Date: 10th June 2012

Authorized Capital: ₹500,00,00,000 (Five Hundred Crore)
""",
    },
    "OLOG001": {
        "pan_card.txt": """
═══════════════════════════════════════════
         INCOME TAX DEPARTMENT
         PERMANENT ACCOUNT NUMBER
═══════════════════════════════════════════
Name:    OMEGA LOGISTICS PVT LTD
PAN:     AABCO3456J
DOI:     25/03/2010
Status:  Active
Category: Company
Jurisdiction: Bangalore
═══════════════════════════════════════════
""",
        "certificate_of_incorporation.txt": """
═══════════════════════════════════════════════════
  MINISTRY OF CORPORATE AFFAIRS — GOVERNMENT OF INDIA
  CERTIFICATE OF INCORPORATION
═══════════════════════════════════════════════════

CIN: U63090KA2010PTC052345

OMEGA LOGISTICS PRIVATE LIMITED
incorporated under Companies Act, 2013.
Limited by shares.

Registered at: Karnataka
Date: 25th March 2010

Authorized Capital: ₹250,00,00,000 (Two Hundred Fifty Crore)
""",
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# FINANCIAL DOCUMENTS — Audited Balance Sheet Summaries
# ══════════════════════════════════════════════════════════════════════════════

FINANCIALS_TEMPLATES = {
    "BMFG001": {
        "audited_bs_fy2024.txt": """
═══════════════════════════════════════════════════════════════════
  BHARAT MANUFACTURING LTD — AUDITED FINANCIAL STATEMENTS FY2024
  CIN: L29100MH2008PLC185432    Auditor: Deloitte Haskins & Sells
═══════════════════════════════════════════════════════════════════

                    BALANCE SHEET (₹ Crore)
─────────────────────────────────────────────────────────────────
EQUITY & LIABILITIES           FY2024      FY2023      FY2022
─────────────────────────────────────────────────────────────────
Share Capital                   62.50       62.50       62.50
Reserves & Surplus             622.50      517.50      445.00
Total Equity                   685.00      580.00      507.50
Long-term Debt                 425.00      380.00      340.00
Short-term Debt                280.00      250.00      220.00
Current Liabilities            385.00      340.00      310.00
  - Trade Payables             210.00      185.00      168.00
  - Other CL                   175.00      155.00      142.00
TOTAL                        1,710.00    1,530.00    1,365.00
─────────────────────────────────────────────────────────────────
ASSETS
─────────────────────────────────────────────────────────────────
Net Fixed Assets               685.00      620.00      565.00
CWIP                            55.00       35.00       20.00
Intangibles                     12.00       10.00        8.00
Investments                     38.00       30.00       25.00
Current Assets                 620.00      545.00      487.00
  - Inventory                  195.00      170.00      155.00
  - Trade Receivables          285.00      245.00      220.00
  - Cash & Equivalents          45.00       40.00       32.00
  - Other CA                    95.00       90.00       80.00
TOTAL                        1,710.00    1,530.00    1,365.00
─────────────────────────────────────────────────────────────────

              PROFIT & LOSS (₹ Crore)
─────────────────────────────────────────────────────────────────
Revenue (Operating)          1,850.00    1,620.00    1,490.00
Other Income                    22.50       18.50       15.00
Total Income                 1,872.50    1,638.50    1,505.00
─────────────────────────────────────────────────────────────────
Raw Material Cost            1,017.50      891.00      819.50
Employee Cost                  185.00      162.00      149.00
Other Expenses                 222.00      194.40      179.00
EBITDA                         448.00      391.10      357.50
Depreciation                    92.50       82.00       72.00
EBIT                           355.50      309.10      285.50
Finance Cost                    67.00       62.00       58.00
PBT                            288.50      247.10      227.50
Tax Expense                     72.13       61.78       56.88
PAT                            216.37      185.32      170.62
─────────────────────────────────────────────────────────────────

                  CASH FLOW (₹ Crore)
─────────────────────────────────────────────────────────────────
Operating Cash Flow            325.00      285.00      260.00
Investing Cash Flow           -145.00      -95.00      -85.00
Financing Cash Flow           -165.00     -175.00     -160.00
Net Change in Cash              15.00       15.00       15.00
─────────────────────────────────────────────────────────────────

AUDITOR'S OPINION: Unmodified / Clean
QUALIFIED: No
EMPHASIS OF MATTER: None material

Signed: Partner, Deloitte Haskins & Sells
Date: 28 September 2024
""",
    },
    "PINF001": {
        "audited_bs_fy2024.txt": """
═══════════════════════════════════════════════════════════════════
  PINNACLE INFRA PROJECTS LTD — AUDITED FINANCIAL STATEMENTS FY2024
  CIN: L45200DL2005PLC134567   Auditor: B S R & Co. LLP
═══════════════════════════════════════════════════════════════════

                    BALANCE SHEET (₹ Crore)
─────────────────────────────────────────────────────────────────
EQUITY & LIABILITIES           FY2024      FY2023      FY2022
─────────────────────────────────────────────────────────────────
Total Equity                   550.00      625.00      680.00
Long-term Debt                 950.00      800.00      720.00
Short-term Debt                580.00      520.00      480.00
Current Liabilities            620.00      555.00      520.00
TOTAL                        2,800.00    2,600.00    2,500.00
─────────────────────────────────────────────────────────────────

              PROFIT & LOSS (₹ Crore)
─────────────────────────────────────────────────────────────────
Revenue (Operating)          2,180.00    2,540.00    2,380.00
EBITDA                         298.00      381.00      357.00
Finance Cost                   155.00      128.00      112.00
PBT                             24.50       90.00      120.00
PAT                             12.25       67.50       90.00
─────────────────────────────────────────────────────────────────

AUDITOR'S OPINION: Modified — Going Concern emphasis
EMPHASIS OF MATTER: NHAI contract termination (₹850 Cr project)
""",
    },
    "SPHR001": {
        "audited_bs_fy2024.txt": """
═══════════════════════════════════════════════════════════════════
  SUNRISE PHARMA PVT LTD — AUDITED FINANCIAL STATEMENTS FY2024
  CIN: U24230GJ2012PTC068945   Auditor: S R Batliboi & Co.
═══════════════════════════════════════════════════════════════════

                    BALANCE SHEET (₹ Crore)
─────────────────────────────────────────────────────────────────
Total Equity                   260.00      230.00      205.00
Total Debt                     195.00      175.00      155.00
Current Liabilities            110.00       95.00       85.00
TOTAL                          635.00      565.00      502.00
─────────────────────────────────────────────────────────────────

Revenue (Operating)            418.00      382.00      348.00
EBITDA                          86.50       74.50       66.00
PAT                             52.82       45.80       40.50
─────────────────────────────────────────────────────────────────

AUDITOR'S OPINION: Unmodified
EMPHASIS OF MATTER: FDA observation on group entity Sunrise Biotech
""",
    },
    "OLOG001": {
        "audited_bs_fy2024.txt": """
═══════════════════════════════════════════════════════════════════
  OMEGA LOGISTICS PVT LTD — AUDITED FINANCIAL STATEMENTS FY2024
  CIN: U63090KA2010PTC052345   Auditor: Price Waterhouse & Co.
═══════════════════════════════════════════════════════════════════

                    BALANCE SHEET (₹ Crore)
─────────────────────────────────────────────────────────────────
Total Equity                   180.00      165.00      150.00
Total Debt                     248.00      215.00      190.00
Current Liabilities            152.00      135.00      120.00
TOTAL                          715.00      640.00      575.00
─────────────────────────────────────────────────────────────────

Revenue (Operating)            575.00      518.00      470.00
EBITDA                          69.00       62.00       56.00
PAT                             19.00       16.20       14.00
─────────────────────────────────────────────────────────────────

AUDITOR'S OPINION: Unmodified
EMPHASIS OF MATTER: None
""",
    },
}


def generate_all_documents():
    """Generate all sample documents and store them via DocumentStore."""
    entities = ["BMFG001", "PINF001", "SPHR001", "OLOG001"]
    ids_map = _ENTITY_TO_IDS

    for eid in entities:
        doc_store.init_company_folder(eid)
        ids = ids_map.get(eid, {})
        cin = ids.get("cin", "")
        pan = ids.get("pan", "")
        gstin = ids.get("gstin", "")

        # ── KYC Documents ────────────────────────────────────────
        for fname, content in KYC_TEMPLATES.get(eid, {}).items():
            doc_store.store_document(eid, "kyc", fname, _make_text(content))

        # ── Financial Documents ──────────────────────────────────
        for fname, content in FINANCIALS_TEMPLATES.get(eid, {}).items():
            doc_store.store_document(eid, "financials", fname, _make_text(content))

        # ── MCA Documents (from external API) ────────────────────
        if cin:
            doc_store.store_document(eid, "mca", "company_master.json",
                _make_json(mca_company_master(cin)))
            doc_store.store_document(eid, "mca", "director_details.json",
                _make_json(mca_directors(cin)))
            doc_store.store_document(eid, "mca", "charges_register.json",
                _make_json(mca_charges(cin)))

        # ── GST Documents ────────────────────────────────────────
        if gstin:
            doc_store.store_document(eid, "gst", "gstin_profile.json",
                _make_json(gstin_details(gstin)))
        if pan:
            doc_store.store_document(eid, "gst", "gst_turnover.json",
                _make_json(gstin_turnover(pan)))

        # ── Bureau Documents ─────────────────────────────────────
        if pan:
            doc_store.store_document(eid, "bureau", "commercial_bureau_report.json",
                _make_json(bureau_commercial_report(pan)))
            doc_store.store_document(eid, "bureau", "crilc_report.json",
                _make_json(crilc_report(pan)))

        # ── Rating Documents ─────────────────────────────────────
        r = rating_action(eid)
        if r.get("source_status") == "success":
            doc_store.store_document(eid, "ratings", "credit_rating.json",
                _make_json(r))

        # ── Market Intelligence ──────────────────────────────────
        m = market_intelligence(eid)
        if m.get("source_status") == "success":
            doc_store.store_document(eid, "misc", "market_intelligence.json",
                _make_json(m))

        # ── EPFO / ITR ───────────────────────────────────────────
        if pan:
            doc_store.store_document(eid, "legal", "epfo_compliance.json",
                _make_json(epfo_compliance(pan)))
            doc_store.store_document(eid, "financials", "itr_filing_status.json",
                _make_json(itr_filing_status(pan)))

        print(f"[OK] {eid} — documents generated")

    # Summary
    for eid in entities:
        docs = doc_store.list_company_documents(eid)
        total = sum(len(v.get("files", [])) for v in docs.get("categories", {}).values())
        print(f"  {eid}: {total} documents across {len(docs.get('categories', {}))} categories")


if __name__ == "__main__":
    generate_all_documents()
