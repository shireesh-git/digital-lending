"""
Generate test-documents folder for PNCR001 (PNC Roads & Infra Ltd).
Creates annual report PDFs, synthetic RM upload PDFs, and platform document pack.
Also copies annual reports to 'downloaded document/CAM/' for bootstrap_reference_documents().
"""
from __future__ import annotations
import json, shutil, sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

# ── Constants ────────────────────────────────────────────────────────────────
ENTITY_ID = "PNCR001"
COMPANY   = "PNC ROADS & INFRA LTD"
CIN       = "L45201DL1999PLC195937"
PAN       = "AABCP1234R"

DEST = ROOT / "test-documents" / "PNCR001_PNC_Roads"
CAM_DIR = ROOT / "downloaded document" / "CAM"

FINANCIALS = {
    "FY2025": dict(revenue=8650, other_income=185, total_income=8835,
                   raw_material=4152, employee_cost=519, other_expenses=2160,
                   ebitda=2004, depreciation=520, ebit=1484, finance_cost=610,
                   pbt=1059, tax=150, pat=909,
                   total_assets=15610, fixed_assets=6800, current_assets=5850,
                   investments=2960, equity=5185, lt_debt=5618, st_debt=2407,
                   total_debt=8025, current_liabilities=4425,
                   receivables=1640, inventory=1970, cash=680, payables=2450,
                   ocf=1850, capex=780, fcff=1070),
    "FY2024": dict(revenue=7956, other_income=152, total_income=8108,
                   raw_material=3978, employee_cost=477, other_expenses=2068,
                   ebitda=1585, depreciation=445, ebit=1140, finance_cost=490,
                   pbt=802, tax=144, pat=658,
                   total_assets=12632, fixed_assets=5200, current_assets=4880,
                   investments=2552, equity=4285, lt_debt=4180, st_debt=2102,
                   total_debt=6282, current_liabilities=3865,
                   receivables=1505, inventory=1810, cash=520, payables=2210,
                   ocf=1420, capex=650, fcff=770),
    "FY2023": dict(revenue=7208, other_income=120, total_income=7328,
                   raw_material=3604, employee_cost=433, other_expenses=1802,
                   ebitda=1489, depreciation=380, ebit=1109, finance_cost=420,
                   pbt=809, tax=229, pat=580,
                   total_assets=10645, fixed_assets=4350, current_assets=4120,
                   investments=2175, equity=3628, lt_debt=3115, st_debt=1678,
                   total_debt=4793, current_liabilities=3224,
                   receivables=1360, inventory=1640, cash=380, payables=1980,
                   ocf=1250, capex=580, fcff=670),
}
FY2026_PROV = dict(revenue=10200, ebitda=2448, pat=1100,
                   total_debt=9200, equity=6100, total_assets=18500)

# ── Styles ───────────────────────────────────────────────────────────────────
_SS = getSampleStyleSheet()
TITLE = ParagraphStyle("T", parent=_SS["Heading1"], fontSize=18, spaceAfter=12,
                       textColor=colors.HexColor("#1a3a6a"), alignment=TA_CENTER)
SUBTITLE = ParagraphStyle("ST", parent=_SS["Normal"], fontSize=12, spaceAfter=8,
                          textColor=colors.HexColor("#444"), alignment=TA_CENTER)
HEADING = ParagraphStyle("H", parent=_SS["Heading2"], fontSize=13,
                         spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#1a3a6a"))
BODY = ParagraphStyle("B", parent=_SS["Normal"], fontSize=10, leading=14, spaceAfter=6)
BOLD = ParagraphStyle("Bo", parent=BODY, fontName="Helvetica-Bold")
NOTE = ParagraphStyle("N", parent=BODY, fontSize=9, textColor=colors.HexColor("#888"))


def _pdf(fp, els):
    fp.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(fp), pagesize=A4,
                      leftMargin=2*cm, rightMargin=2*cm,
                      topMargin=2*cm, bottomMargin=2*cm).build(els)

def _tbl(data, cw=None):
    s = TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a3a6a")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"), ("ALIGN", (0,0), (0,-1), "LEFT"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#ccc")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f0f4fa")]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ])
    t = Table(data, colWidths=cw, repeatRows=1); t.setStyle(s)
    return t

def _hdr(title):
    return [Paragraph(COMPANY, TITLE),
            Paragraph(f"CIN: {CIN}  |  PAN: {PAN}", SUBTITLE),
            Paragraph(title, SUBTITLE), Spacer(1,16)]

def _rmhdr(title, src):
    return [Paragraph(title, TITLE),
            Paragraph(f"Company: {COMPANY}", BOLD),
            Paragraph(f"Entity ID: {ENTITY_ID}  |  CIN: {CIN}", BODY),
            Paragraph(f"Source: {src}", NOTE),
            Paragraph("Synthetic PDF for workflow continuity.", NOTE),
            Spacer(1,12)]

def _f(v):
    return f"{v:,}" if isinstance(v, int) else f"{v:,.2f}" if isinstance(v, float) else str(v)

# ── Annual Reports ───────────────────────────────────────────────────────────

def gen_annual_report(period, d, fp):
    els = _hdr(f"Annual Report — {period}")
    yr = int(period[2:])
    prev_key = f"FY{yr-1}"
    prev = FINANCIALS.get(prev_key, {})

    els.append(Paragraph("Board of Directors", HEADING))
    for nm, rl in [("Yogesh Kumar Jain","Chairman & MD"), ("Naveen Kumar Jain","Whole-Time Director"),
                    ("Chandra Prakash Jain","ED Projects"), ("Ruchi Bisht","Independent Director")]:
        els.append(Paragraph(f"<b>{nm}</b> — {rl}", BODY))

    els.append(Paragraph("Company Overview", HEADING))
    els.append(Paragraph(
        f"PNC Roads & Infra Ltd is a leading infrastructure EPC company specializing in road and highway "
        f"construction. During {period}, the company reported revenue of INR {_f(d['revenue'])} Crores.", BODY))

    els.append(Paragraph("Statement of Profit & Loss (INR Crores)", HEADING))
    pnl = [["Particulars", period, prev_key or "Prev"],
           ["Revenue from Operations", _f(d["revenue"]), _f(prev.get("revenue","—"))],
           ["Other Income", _f(d["other_income"]), _f(prev.get("other_income","—"))],
           ["Total Income", _f(d["total_income"]), _f(prev.get("total_income","—"))],
           ["Raw Material / Construction Cost", _f(d["raw_material"]), ""],
           ["Employee Benefit Expenses", _f(d["employee_cost"]), ""],
           ["Other Expenses", _f(d["other_expenses"]), ""],
           ["EBITDA", _f(d["ebitda"]), _f(prev.get("ebitda","—"))],
           ["Depreciation", _f(d["depreciation"]), ""],
           ["EBIT", _f(d["ebit"]), ""],
           ["Finance Cost", _f(d["finance_cost"]), ""],
           ["Profit Before Tax", _f(d["pbt"]), ""],
           ["Tax Expense", _f(d["tax"]), ""],
           ["Profit After Tax", _f(d["pat"]), _f(prev.get("pat","—"))]]
    els.append(_tbl(pnl, [220,100,100]))

    els.append(PageBreak())
    els.append(Paragraph("Balance Sheet (INR Crores)", HEADING))
    bs = [["Particulars", f"31-Mar-{yr}"],
          ["Shareholders' Equity", _f(d["equity"])],
          ["Long-Term Borrowings", _f(d["lt_debt"])],
          ["Short-Term Borrowings", _f(d["st_debt"])],
          ["Total Debt", _f(d["total_debt"])],
          ["Current Liabilities", _f(d["current_liabilities"])],
          ["Total Equity & Liabilities", _f(d["total_assets"])],
          ["", ""],
          ["Fixed Assets (Net Block + CWIP)", _f(d["fixed_assets"])],
          ["Investments", _f(d["investments"])],
          ["Trade Receivables", _f(d["receivables"])],
          ["Inventories", _f(d["inventory"])],
          ["Cash & Bank Balances", _f(d["cash"])],
          ["Other Current Assets", _f(d["current_assets"] - d["receivables"] - d["inventory"] - d["cash"])],
          ["Total Assets", _f(d["total_assets"])]]
    els.append(_tbl(bs, [300,140]))

    els.append(Paragraph("Cash Flow Summary (INR Crores)", HEADING))
    els.append(_tbl([["", period],
                     ["Operating Cash Flow", _f(d["ocf"])],
                     ["Capital Expenditure", f"({_f(d['capex'])})"],
                     ["Free Cash Flow", _f(d["fcff"])]], [300,140]))

    de = d["total_debt"]/d["equity"]
    els.append(Paragraph("Key Ratios", HEADING))
    els.append(_tbl([["Ratio","Value"],
                     ["Debt-to-Equity", f"{de:.2f}x"],
                     ["Current Ratio", f"{d['current_assets']/d['current_liabilities']:.2f}x"],
                     ["EBITDA Margin", f"{d['ebitda']/d['revenue']*100:.1f}%"],
                     ["Net Profit Margin", f"{d['pat']/d['revenue']*100:.1f}%"],
                     ["Interest Coverage", f"{d['ebitda']/d['finance_cost']:.2f}x"],
                     ["ROE", f"{d['pat']/d['equity']*100:.1f}%"]], [300,140]))

    els.append(Paragraph("Auditor: S.R. Batliboi & Co. LLP, Chartered Accountants", NOTE))
    _pdf(fp, els)

def gen_unaudited(fp):
    els = _hdr("Unaudited Results — H1 FY2026")
    d = FY2026_PROV
    els.append(_tbl([["Particulars","H1 FY2026 (Annualized)"],
                     ["Revenue", _f(d["revenue"])],
                     ["EBITDA", _f(d["ebitda"])],
                     ["PAT", _f(d["pat"])],
                     ["Total Debt", _f(d["total_debt"])],
                     ["Equity", _f(d["equity"])],
                     ["Total Assets", _f(d["total_assets"])],
                     ["Debt/Equity", f"{d['total_debt']/d['equity']:.2f}x"]], [300,140]))
    els.append(Spacer(1,10))
    els.append(Paragraph("Provisional / management estimates subject to audit.", NOTE))
    _pdf(fp, els)

# ── Synthetic RM Upload PDFs ─────────────────────────────────────────────────

def gen_bank_statements(fp):
    els = _rmhdr("Bank Statements — 6 Months","Borrower / Bank")
    els.append(_tbl([["Month","Opening (Cr)","Credit (Cr)","Debit (Cr)","Closing (Cr)"],
        ["Oct 2025","245.30","892.45","871.20","266.55"],
        ["Nov 2025","266.55","915.80","898.35","284.00"],
        ["Dec 2025","284.00","1,042.15","1,018.70","307.45"],
        ["Jan 2026","307.45","978.60","962.10","323.95"],
        ["Feb 2026","323.95","1,105.25","1,080.55","348.65"],
        ["Mar 2026","348.65","1,230.40","1,195.80","383.25"]]))
    els.append(Paragraph("Account: HDFC Bank Current A/c ending 4578", BODY))
    els.append(Paragraph("Avg monthly credit turnover: INR 1,027 Cr. No cheque returns.", BODY))
    _pdf(fp, els)

def gen_board_resolution(fp):
    els = _rmhdr("Board Resolution — Borrowing Powers","Company Secretary")
    els.append(Paragraph("CERTIFIED TRUE COPY", HEADING))
    els.append(Paragraph(
        "RESOLVED THAT pursuant to Sections 179 and 180 of the Companies Act, 2013, consent is "
        "hereby accorded to borrow up to INR 2,500 Crores from banks/FIs for business operations.", BODY))
    els.append(Paragraph(
        "RESOLVED FURTHER THAT Shri Yogesh Kumar Jain (MD) and Shri Naveen Kumar Jain (WTD) "
        "are jointly and severally authorized to negotiate, finalize and execute all documents.", BODY))
    els.append(Spacer(1,16))
    els.append(Paragraph("Date: 15 January 2026  |  Place: Lucknow", BODY))
    els.append(Paragraph("For PNC Roads & Infra Ltd — Sd/- Company Secretary", BOLD))
    _pdf(fp, els)

def gen_cersai_search(fp):
    els = _rmhdr("CERSAI Search Report","Registry / Compliance")
    els.append(_tbl([["Asset","Charge Holder","Amt (Cr)","Date","Status"],
        ["BOT Rights NH-44","State Bank of India","850","12-Jun-2023","Active"],
        ["Equipment Fleet","HDFC Bank","180","25-Sep-2024","Active"],
        ["Office, Lucknow","Punjab National Bank","95","10-Mar-2022","Active"]]))
    els.append(Paragraph("Total charges: 3 | Value: INR 1,125 Cr. No disputed charges.", BODY))
    _pdf(fp, els)

def gen_cma_projection(fp):
    els = _rmhdr("CMA Data / Financial Projections","Finance Team / CA Firm")
    els.append(_tbl([["Particulars","FY2025 (A)","FY2026 (P)","FY2027 (P)","FY2028 (P)"],
        ["Revenue","8,650","10,200","12,240","14,688"],
        ["EBITDA","2,004","2,448","3,060","3,672"],
        ["EBITDA Margin","23.2%","24.0%","25.0%","25.0%"],
        ["PAT","909","1,100","1,450","1,800"],
        ["Total Debt","8,025","9,200","8,800","8,000"],
        ["Equity","5,185","6,100","7,350","8,950"],
        ["Debt/Equity","1.55x","1.51x","1.20x","0.89x"],
        ["DSCR","1.42x","1.55x","1.72x","1.90x"],
        ["Interest Coverage","3.29x","3.40x","3.80x","4.20x"]]))
    els.append(Paragraph("Assumptions: ~20% revenue CAGR from order book execution; "
                         "EBITDA margin improvement; debt reduction from FY2027 via HAM annuities.", BODY))
    _pdf(fp, els)

def gen_credit_facility(fp):
    els = _rmhdr("Existing Credit Facility Details","Treasurer")
    els.append(_tbl([["Lender","Facility","Sanctioned (Cr)","O/S (Cr)","Rate","Maturity"],
        ["SBI","Term Loan","2,800","2,240","8.95%","Mar-2029"],
        ["HDFC Bank","Working Capital","1,200","890","9.10%","Revolving"],
        ["PNB","Term Loan","1,600","1,380","9.25%","Jun-2030"],
        ["ICICI Bank","BG/LC","800","520","2.50%","Annual"],
        ["Axis Bank","Working Capital","600","410","9.05%","Revolving"]]))
    els.append(Paragraph("Total sanctioned: INR 7,000 Cr | Outstanding: INR 5,440 Cr. No SMA.", BODY))
    _pdf(fp, els)

def gen_insurance(fp):
    els = _rmhdr("Insurance Policies Schedule","Risk Management")
    els.append(_tbl([["Policy Type","Insurer","Sum Insured (Cr)","Validity"],
        ["Contractor's All Risk","New India Assurance","2,500","Apr 2025–Mar 2026"],
        ["Marine Cargo","ICICI Lombard","350","Apr 2025–Mar 2026"],
        ["Workmen Compensation","Oriental Insurance","100","Apr 2025–Mar 2026"],
        ["Fire & Special Perils","United India Insurance","450","Apr 2025–Mar 2026"]]))
    _pdf(fp, els)

def gen_internal_credit_notes(fp):
    els = _rmhdr("Internal Credit Analyst Notes","Credit Risk Dept")
    els.append(Paragraph("Assessment: PNC Roads & Infra Ltd", HEADING))
    els.append(Paragraph("Strengths:", BOLD))
    for s in ["Order book INR 27,700 Cr (3.2x revenue) — 3+ yr visibility",
              "NH-44 section completed ahead of schedule — proven execution",
              "CARE AA-/Stable rating reflects adequate credit profile",
              "EBITDA margins improving: 19.9% (FY23) → 23.2% (FY25)"]:
        els.append(Paragraph(f"• {s}", BODY))
    els.append(Paragraph("Concerns:", BOLD))
    for c in ["D/E at 1.55x — above infra median of 1.2x",
              "Input cost volatility (bitumen, steel) impacts margins",
              "Geographic concentration in UP/MP",
              "BOT/HAM monetization timeline uncertain"]:
        els.append(Paragraph(f"• {c}", BODY))
    _pdf(fp, els)

def gen_property_documents(fp):
    els = _rmhdr("Property Documents & Title Reports","Legal / Valuers")
    els.append(_tbl([["Property","Location","Area","Value (Cr)","Encumbrance"],
        ["Registered Office","Gomti Nagar, Lucknow","2.5 ac","180","Mortgaged to PNB"],
        ["Project Site Office","NH-44 Agra Bypass","0.8 ac","25","Leasehold NHAI"],
        ["Equipment Yard","Kanpur Industrial","5.2 ac","120","Clear"],
        ["Batching Plant","Jhansi, UP","3.0 ac","85","Clear"]]))
    _pdf(fp, els)

def gen_site_visit(fp):
    els = _rmhdr("Site Visit Report","RM / Branch Manager")
    els.append(Paragraph("Date: 20 February 2026", BODY))
    els.append(Paragraph("Visited By: Rajesh Sharma (RM) & Ajay Verma (CO)", BODY))
    els.append(Paragraph("Sites: NH-44 project site, Registered Office", BODY))
    els.append(Paragraph("Observations:", HEADING))
    for o in ["NH-44 site active — 200+ workers, paving operations underway",
              "28 pavers, 15 batching plants operational; equipment in good condition",
              "Finance team cooperative; office well-maintained",
              "Raw material stockyard adequate for 3 months",
              "Work quality satisfactory per NHAI specifications"]:
        els.append(Paragraph(f"• {o}", BODY))
    els.append(Paragraph("Recommendation: Operations consistent with reported revenue. No concerns.", BODY))
    _pdf(fp, els)

def gen_undertakings(fp):
    els = _rmhdr("Key Undertakings & Declarations","Authorized Signatory")
    points = [
        "Not a willful defaulter with any bank/FI.",
        "No pending criminal proceedings against promoters/directors.",
        "Not declared as fraud by any regulatory authority.",
        "All statutory dues (GST, TDS, PF, ESI) paid regularly.",
        "Minimum current ratio of 1.25x maintained at all times.",
        "DSCR not less than 1.30x on proposed facility.",
        "No change in management/shareholding >10% without bank approval.",
    ]
    for i, p in enumerate(points, 1):
        els.append(Paragraph(f"{i}. {p}", BODY))
    els.append(Spacer(1,16))
    els.append(Paragraph("For PNC Roads & Infra Ltd — Sd/- Yogesh Kumar Jain, MD", BOLD))
    els.append(Paragraph(f"Date: 01 March 2026  |  Place: Lucknow", NOTE))
    _pdf(fp, els)

def gen_valuation_report(fp):
    els = _rmhdr("Valuation Report — Collateral Assessment","Empanelled Valuer")
    els.append(_tbl([["Asset","Market Value (Cr)","FSV (Cr)","Date"],
        ["BOT Rights NH-44","1,400","980","15-Mar-2025"],
        ["Equipment Fleet","520","312","28-Feb-2025"],
        ["Office & Land, Lucknow","180","126","10-Jan-2025"]]))
    els.append(Paragraph("Total MV: INR 2,100 Cr | FSV: INR 1,418 Cr", BOLD))
    els.append(Paragraph("Coverage on INR 1,500 Cr: 1.40x (MV) / 0.95x (FSV)", BODY))
    _pdf(fp, els)

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"Generating PNCR001 test documents → {DEST}")

    # 1) Annual Reports
    ar = DEST / "annual-reports"
    for period, d in FINANCIALS.items():
        yr = period[2:]
        prev = str(int(yr) - 1)
        fn = f"PNCR_AR_{prev}-{yr[-2:]}.pdf"
        gen_annual_report(period, d, ar / fn)
        print(f"  ✓ annual-reports/{fn}")
    gen_unaudited(ar / "PNCR_Unaudited-2025-26.pdf")
    print("  ✓ annual-reports/PNCR_Unaudited-2025-26.pdf")

    # 2) Synthetic RM Documents
    oi = DEST / "optional-inputs"
    rm_docs = [
        ("synthetic_bank_statements.pdf", gen_bank_statements),
        ("synthetic_board_resolution_borrowing.pdf", gen_board_resolution),
        ("synthetic_cersai_search.pdf", gen_cersai_search),
        ("synthetic_cma_projection.pdf", gen_cma_projection),
        ("synthetic_credit_facility_details.pdf", gen_credit_facility),
        ("synthetic_insurance_policies.pdf", gen_insurance),
        ("synthetic_internal_credit_notes.pdf", gen_internal_credit_notes),
        ("synthetic_property_documents.pdf", gen_property_documents),
        ("synthetic_site_visit_report.pdf", gen_site_visit),
        ("synthetic_undertakings.pdf", gen_undertakings),
        ("synthetic_valuation_report.pdf", gen_valuation_report),
    ]
    for fn, gen in rm_docs:
        gen(oi / fn)
        print(f"  ✓ optional-inputs/{fn}")

    # 3) Copy annual reports to 'downloaded document/CAM/' for bootstrap
    CAM_DIR.mkdir(parents=True, exist_ok=True)
    for pdf in ar.glob("PNCR*.pdf"):
        shutil.copy2(pdf, CAM_DIR / pdf.name)
    print(f"  ✓ Copied {len(list(ar.glob('PNCR*.pdf')))} PDFs to downloaded document/CAM/")

    # 4) Platform document pack (copy from storage if exists, else create stubs)
    pack = DEST / "platform-document-pack"
    storage_src = ROOT / "storage" / "documents" / ENTITY_ID

    if storage_src.exists():
        # Copy from storage
        if pack.exists():
            shutil.rmtree(pack)
        shutil.copytree(storage_src, pack)
        print(f"  ✓ Platform doc pack copied from storage/documents/{ENTITY_ID}/")
    else:
        # Create minimal structure
        for cat in ["kyc","financials","bureau","legal","collateral","ratings",
                     "gst","mca","banking","exchange","request","misc"]:
            (pack / cat).mkdir(parents=True, exist_ok=True)
        # Copy some RM PDFs into relevant categories
        copy_map = {
            "banking/bank_statement_6m.pdf": "synthetic_bank_statements.pdf",
            "banking/existing_facility_details.pdf": "synthetic_credit_facility_details.pdf",
            "collateral/valuation_report.pdf": "synthetic_valuation_report.pdf",
            "kyc/board_resolution_borrowing.pdf": "synthetic_board_resolution_borrowing.pdf",
            "request/request_note.pdf": "synthetic_cma_projection.pdf",
        }
        for rel, src_name in copy_map.items():
            src = oi / src_name
            if src.exists():
                shutil.copy2(src, pack / rel)
        # Copy annual reports into financials
        for pdf in ar.glob("*.pdf"):
            shutil.copy2(pdf, pack / "financials" / pdf.name)
        # Metadata
        (pack / "metadata.json").write_text(json.dumps({
            "entity_id": ENTITY_ID, "company_name": COMPANY,
            "generated": date.today().isoformat(),
            "source": "synthetic_seed"
        }, indent=2))
        print("  ✓ Platform doc pack created with stub structure")

    total = sum(1 for _ in DEST.rglob("*") if _.is_file())
    print(f"\n✅ Done — {total} files generated for PNCR001")


if __name__ == "__main__":
    main()
