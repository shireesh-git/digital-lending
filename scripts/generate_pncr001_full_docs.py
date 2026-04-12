"""
PNCR001 Comprehensive Document Generator — v2
Creates the full platform-document-pack matching INFY001 coverage:
  - Real annual reports (from website download)
  - Synthetic PDFs: banking, bureau, collateral, exchange, gst, kyc, ratings, request
  - Synthetic JSON: bureau, financials, gst, kyc, legal, mca, misc, ratings
  - Road construction projections & CMA data
"""
from __future__ import annotations
import json, shutil, sys, os
from pathlib import Path
from datetime import date, datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, PageBreak)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

# ── Constants ──────────────────────────────────────────────
ENTITY_ID   = "PNCR001"
COMPANY     = "PNC ROADS & INFRA LTD"
COMPANY_REG = "PNC Infratech Limited"
CIN         = "L45201DL1999PLC195937"
PAN         = "AABCP1234R"
GSTIN       = "09AABCP1234R1Z6"
BSE_CODE    = "539150"
NSE_SYMBOL  = "PNCINFRA"
ISIN        = "INE195J01029"

TEST_DOCS = ROOT / "test-documents" / "PNCR001_PNC_Roads"
REAL_AR    = TEST_DOCS / "annual-reports-real"   # downloaded from website
PACK       = TEST_DOCS / "platform-document-pack"
STORAGE    = ROOT / "storage" / "documents" / ENTITY_ID
CAM_DIR    = ROOT / "downloaded document" / "CAM"

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

DIRECTORS = [
    {"name": "YOGESH KUMAR JAIN",  "din": "00056994", "desig": "Chairman & Managing Director", "share_pct": 45.2},
    {"name": "NAVEEN KUMAR JAIN",  "din": "00057760", "desig": "Whole-Time Director",          "share_pct": 12.8},
    {"name": "CHANDRA PRAKASH JAIN","din": "07889421", "desig": "Executive Director (Projects)","share_pct": 5.1},
    {"name": "RUCHI BISHT",        "din": "09823456", "desig": "Independent Director",          "share_pct": 0.0},
    {"name": "ARUN KUMAR SINGH",   "din": "08901234", "desig": "Independent Director",          "share_pct": 0.0},
]

ORDER_BOOK = [
    {"project": "6L Chakeri-Allahabad NH-2 (HAM)", "employer": "NHAI", "state": "UP",
     "length_km": 145, "value_cr": 2850, "status": "Under Construction", "completion": "Sep 2027"},
    {"project": "4L Challakere-Hariyur NH-150A (HAM)", "employer": "NHAI", "state": "Karnataka",
     "length_km": 56, "value_cr": 1620, "status": "Under Construction", "completion": "Dec 2027"},
    {"project": "4L Unnao-Lalganj NH-232A (HAM)", "employer": "NHAI", "state": "UP",
     "length_km": 70, "value_cr": 1480, "status": "Under Construction", "completion": "Mar 2028"},
    {"project": "8L Delhi-Vadodara Expressway Pkg 29 (EPC)", "employer": "NHAI", "state": "Gujarat",
     "length_km": 23, "value_cr": 3200, "status": "Under Construction", "completion": "Jun 2027"},
    {"project": "6L Kanpur-Lucknow Expressway Pkg-1 (HAM)", "employer": "NHAI", "state": "UP",
     "length_km": 18, "value_cr": 2400, "status": "Under Construction", "completion": "Dec 2026"},
    {"project": "6L Kanpur-Lucknow Expressway Pkg-2 (HAM)", "employer": "NHAI", "state": "UP",
     "length_km": 45, "value_cr": 4500, "status": "Under Construction", "completion": "Mar 2027"},
    {"project": "4L Sonauli-Gorakhpur NH-29E (HAM)", "employer": "NHAI", "state": "UP",
     "length_km": 80, "value_cr": 1850, "status": "Under Construction", "completion": "Jun 2028"},
    {"project": "6L MH/KN Border NH-150C Pkg-II (HAM)", "employer": "NHAI", "state": "Karnataka",
     "length_km": 71, "value_cr": 3520, "status": "Recently Awarded", "completion": "Sep 2028"},
    {"project": "4L Lucknow Ring Road Pkg-I (EPC)", "employer": "NHAI", "state": "UP",
     "length_km": 32, "value_cr": 1080, "status": "Under Construction", "completion": "Oct 2026"},
    {"project": "4L Mathura Bypass NH-530B Pkg 1B (HAM)", "employer": "NHAI", "state": "UP",
     "length_km": 33, "value_cr": 1250, "status": "Under Construction", "completion": "Mar 2027"},
    {"project": "4L Hardoi Bypass NH-731 Pkg-III (HAM)", "employer": "NHAI", "state": "UP",
     "length_km": 54, "value_cr": 1430, "status": "Under Construction", "completion": "Sep 2027"},
    {"project": "4L Meerut-Nazibabad NH-119 (HAM)", "employer": "NHAI", "state": "UP",
     "length_km": 54, "value_cr": 1620, "status": "Under Construction", "completion": "Dec 2027"},
]

# ── PDF Styles ─────────────────────────────────────────────
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

def _hdr(title, src=""):
    return [Paragraph(COMPANY, TITLE),
            Paragraph(f"CIN: {CIN}  |  PAN: {PAN}", SUBTITLE),
            Paragraph(title, SUBTITLE),
            *([Paragraph(f"Source: {src}", NOTE)] if src else []),
            Spacer(1,16)]

def _f(v):
    return f"{v:,}" if isinstance(v, int) else f"{v:,.2f}" if isinstance(v, float) else str(v)

def _write_json(fp, data):
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(data, indent=2, ensure_ascii=False))

# ══════════════════════════════════════════════════════════════════
#  BANKING
# ══════════════════════════════════════════════════════════════════

def gen_bank_statement_6m(fp):
    els = _hdr("Bank Statements — 6 Months (Oct 2025 – Mar 2026)", "Borrower / HDFC Bank")
    els.append(Paragraph("Account: HDFC Bank Current A/c No. XXXX-XXXX-4578<br/>"
                         "Branch: Gomti Nagar, Lucknow", BODY))
    els.append(_tbl([
        ["Month","Opening (Cr)","Credits (Cr)","Debits (Cr)","Closing (Cr)","Peak Bal"],
        ["Oct 2025","245.30","892.45","871.20","266.55","412.80"],
        ["Nov 2025","266.55","915.80","898.35","284.00","445.20"],
        ["Dec 2025","284.00","1,042.15","1,018.70","307.45","510.30"],
        ["Jan 2026","307.45","978.60","962.10","323.95","485.60"],
        ["Feb 2026","323.95","1,105.25","1,080.55","348.65","528.40"],
        ["Mar 2026","348.65","1,230.40","1,195.80","383.25","620.15"],
    ]))
    els.append(Spacer(1,10))
    els.append(Paragraph("Avg monthly credit turnover: INR 1,027 Cr", BOLD))
    els.append(Paragraph("Cheque returns: NIL  |  Inward bounces: NIL  |  ECS failures: NIL", BODY))
    els.append(Paragraph("All NHAI milestone payments routed through this account.", BODY))

    els.append(PageBreak())
    els.append(Paragraph("Top Credit Sources", HEADING))
    els.append(_tbl([
        ["Source","Monthly Avg (Cr)","Share"],
        ["NHAI — RA Bill Payments","520","50.6%"],
        ["NHAI — Mobilization Advance","185","18.0%"],
        ["HAM Annuity Receivables","142","13.8%"],
        ["Sub-contractor Refunds","95","9.2%"],
        ["Interest & Other Income","85","8.4%"],
    ]))
    _pdf(fp, els)

def gen_bank_statement_fy(fp):
    els = _hdr("Bank Statement — FY2025 Annual Summary", "HDFC Bank")
    els.append(_tbl([
        ["Quarter","Credits (Cr)","Debits (Cr)","Avg Balance (Cr)"],
        ["Q1 FY2025 (Apr-Jun)","2,480","2,410","285"],
        ["Q2 FY2025 (Jul-Sep)","2,680","2,615","350"],
        ["Q3 FY2025 (Oct-Dec)","2,850","2,788","286"],
        ["Q4 FY2025 (Jan-Mar)","3,314","3,238","351"],
        ["TOTAL FY2025","11,324","11,051","318"],
    ]))
    els.append(Paragraph("Annual turnover is 1.31x of reported revenue (INR 8,650 Cr).", BODY))
    _pdf(fp, els)

def gen_existing_facility(fp):
    els = _hdr("Existing Credit Facility Details", "Borrower / Treasurer")
    els.append(Paragraph("<b>Fund Based Facilities</b>", HEADING))
    els.append(_tbl([
        ["Lender","Type","Sanctioned","Outstanding","Rate","Maturity","Security"],
        ["SBI","Term Loan","2,800","2,240","8.95%","Mar 2029","BOT Rights NH-44"],
        ["PNB","Term Loan","1,600","1,380","9.25%","Jun 2030","Equipment + mortgage"],
        ["HDFC Bank","CC/OD","1,200","890","9.10%","Revolving","Stock & receivables"],
        ["Axis Bank","CC/OD","600","410","9.05%","Revolving","Book debts"],
    ]))
    els.append(Spacer(1,8))
    els.append(Paragraph("<b>Non-Fund Based Facilities</b>", HEADING))
    els.append(_tbl([
        ["Lender","Type","Sanctioned","Utilized","Commission"],
        ["ICICI Bank","BG/LC","800","520","2.50%"],
        ["IndusInd","BG","400","280","2.25%"],
        ["SBI","LC","350","210","1.80%"],
    ]))
    els.append(Spacer(1,8))
    els.append(Paragraph("Total fund-based: INR 6,200 Cr | O/S: INR 4,920 Cr", BOLD))
    els.append(Paragraph("Total non-fund: INR 1,550 Cr | Utilized: INR 1,010 Cr", BOLD))
    els.append(Paragraph("SMA Status: SMA-0 across all facilities. No NPA history.", BODY))
    _pdf(fp, els)

def gen_sanction_letter(fp):
    els = _hdr("Sanction Letter — SBI Term Loan", "State Bank of India")
    els.append(Paragraph("Ref: SBIN/CF/2023/TL/04578", BODY))
    els.append(Paragraph("Date: 12 June 2023", BODY))
    els.append(Spacer(1,8))
    els.append(Paragraph("Dear Sir/Madam,", BODY))
    els.append(Paragraph(
        f"We are pleased to sanction the following facility to {COMPANY}:", BODY))
    els.append(_tbl([
        ["Parameter","Details"],
        ["Facility","Term Loan"],
        ["Amount","INR 2,800 Crores"],
        ["Purpose","NHAI highway projects (HAM/EPC)"],
        ["Tenor","72 months"],
        ["Interest","MCLR + 0.70% = 8.95% (Floating)"],
        ["Repayment","20 quarterly installments after 12m moratorium"],
        ["Security","Assignment of BOT rights NH-44; Personal guarantee of promoters"],
        ["Conditions","DSCR > 1.30x; D/E < 2.0x; Min promoter holding 40%"],
    ], [180, 280]))
    els.append(Spacer(1,12))
    els.append(Paragraph("For State Bank of India", BOLD))
    els.append(Paragraph("Sd/- General Manager, Infrastructure Finance", NOTE))
    _pdf(fp, els)

# ══════════════════════════════════════════════════════════════════
#  BUREAU
# ══════════════════════════════════════════════════════════════════

def gen_commercial_bureau_report(fp):
    els = _hdr("Commercial Credit Bureau Report", "CIBIL / Experian")
    els.append(Paragraph("Report Date: 01 March 2026", BODY))
    els.append(_tbl([
        ["Parameter","Value"],
        ["CIBIL MSME Rank","CMR-3 (Low Risk)"],
        ["Credit Score","742"],
        ["Total Exposure","INR 6,282 Cr"],
        ["No. of Lenders","8"],
        ["Willful Defaulter","No"],
        ["SMA Status","SMA-0"],
        ["DPD Status","Standard (0 DPD)"],
        ["Suit Filed","NIL"],
        ["Overdue Amount","NIL"],
    ]))
    els.append(Paragraph("Credit History:", HEADING))
    els.append(_tbl([
        ["Period","Total O/S (Cr)","DPD","Status"],
        ["Mar 2026","6,282","0","Standard"],
        ["Dec 2025","5,920","0","Standard"],
        ["Sep 2025","5,650","0","Standard"],
        ["Jun 2025","5,310","0","Standard"],
        ["Mar 2025","4,793","0","Standard"],
    ]))
    els.append(Paragraph("No adverse observations in last 36 months.", BODY))
    _pdf(fp, els)

def gen_crilc_json(fp):
    _write_json(fp, {
        "source": "rbi_crilc",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-03-31",
        "payload": {
            "total_exposure_cr": 7850,
            "fund_based_cr": 6200,
            "non_fund_based_cr": 1550,
            "derivative_exposure_cr": 100,
            "sma_category": "SMA-0",
            "dpd_bucket": "0",
            "asset_classification": "Standard",
            "provision_pct": 0.40,
            "lender_count": 8,
            "consortium_lead": "State Bank of India",
            "wilful_defaulter": False,
            "fraud_flag": False,
            "restructured": False,
        }
    })

def gen_crilc_report(fp):
    els = _hdr("CRILC Report — Large Exposure Summary", "RBI / CRILC Portal")
    els.append(Paragraph("Reporting Date: 31 March 2026", BODY))
    els.append(_tbl([
        ["Lender","Fund (Cr)","Non-Fund (Cr)","Total (Cr)","SMA","DPD"],
        ["SBI","2,800","350","3,150","SMA-0","0"],
        ["PNB","1,600","—","1,600","SMA-0","0"],
        ["HDFC Bank","1,200","—","1,200","SMA-0","0"],
        ["ICICI Bank","—","800","800","—","0"],
        ["Axis Bank","600","—","600","SMA-0","0"],
        ["IndusInd","—","400","400","—","0"],
        ["TOTAL","6,200","1,550","7,750","",""],
    ]))
    els.append(Paragraph("All accounts Standard. No SMA-1 or SMA-2 observations.", BODY))
    _pdf(fp, els)

# ══════════════════════════════════════════════════════════════════
#  COLLATERAL
# ══════════════════════════════════════════════════════════════════

def gen_valuation_report(fp):
    els = _hdr("Collateral Valuation Report", "M/s. Gupta & Associates, Approved Valuers")
    els.append(Paragraph("Valuation Date: 15 March 2026", BODY))
    els.append(_tbl([
        ["Asset","Location","Area","Market Value (Cr)","FSV (Cr)","Encumbrance"],
        ["BOT Rights NH-44","Agra-Allahabad","145 km","1,400","980","SBI TL"],
        ["Equipment Fleet","Multiple sites","210 units","520","312","HDFC CC"],
        ["Office & Land","Gomti Nagar, Lucknow","2.5 ac","180","126","PNB TL"],
        ["Batching Plant","Jhansi, UP","3.0 ac","85","60","Clear"],
        ["Equipment Yard","Kanpur","5.2 ac","120","84","Clear"],
        ["HAM Annuity Rights","6 concessions","—","2,800","1,960","Partial pledge"],
    ]))
    els.append(Spacer(1,8))
    els.append(Paragraph("Total Market Value: INR 5,105 Cr  |  Total FSV: INR 3,522 Cr", BOLD))
    els.append(Paragraph(f"Coverage on INR 1,500 Cr proposed: 3.40x (MV) / 2.35x (FSV)", BODY))
    els.append(Paragraph("Valuation Method: Income approach for BOT/HAM; Replacement cost for equipment", NOTE))
    _pdf(fp, els)

# ══════════════════════════════════════════════════════════════════
#  EXCHANGE
# ══════════════════════════════════════════════════════════════════

def gen_corp_governance_report(fp):
    els = _hdr("Corporate Governance Report", "BSE/NSE Filing")
    els.append(_tbl([
        ["Parameter","Details"],
        ["BSE Code", BSE_CODE],
        ["NSE Symbol", NSE_SYMBOL],
        ["ISIN", ISIN],
        ["Face Value","INR 2/-"],
        ["Authorized Cap","INR 200 Cr"],
        ["Paid-Up Cap","INR 51.3 Cr (256.5 Cr shares)"],
        ["Listing","BSE + NSE"],
        ["Index","BSE SmallCap, Nifty Infrastructure"],
        ["Registrar","MUFG Intime India Pvt Ltd"],
        ["Auditors","S.R. Batliboi & Co. LLP"],
    ]))
    els.append(Paragraph("Board Composition:", HEADING))
    for d in DIRECTORS:
        els.append(Paragraph(f"• {d['name']} (DIN: {d['din']}) — {d['desig']}", BODY))
    els.append(Paragraph("Board meets quarterly. AGM held September 2025.", BODY))
    _pdf(fp, els)

def gen_quarterly_results(fp):
    els = _hdr("Quarterly Results — Q3 FY2026 (Oct-Dec 2025)", "BSE Filing")
    els.append(_tbl([
        ["Particulars (INR Cr)","Q3 FY26","Q2 FY26","Q3 FY25","9M FY26","9M FY25"],
        ["Revenue","2,850","2,680","2,350","7,910","6,480"],
        ["Other Income","52","48","38","148","115"],
        ["Total Expenses","2,210","2,095","1,880","6,165","5,180"],
        ["EBITDA","640","585","470","1,745","1,300"],
        ["Depreciation","145","138","120","415","340"],
        ["Finance Cost","175","165","148","505","425"],
        ["PBT","372","330","240","973","650"],
        ["Tax","93","82","60","243","163"],
        ["PAT","279","248","180","730","488"],
        ["EPS (INR)","10.88","9.67","7.02","28.46","19.02"],
    ]))
    els.append(Paragraph("Notes:", HEADING))
    els.append(Paragraph("• Revenue growth 21.3% YoY driven by Kanpur-Lucknow Expressway execution", BODY))
    els.append(Paragraph("• EBITDA margin improved to 22.5% from 20.0% in Q3 FY25", BODY))
    els.append(Paragraph("• Order book at INR 27,680 Cr as of 31 Dec 2025", BODY))
    _pdf(fp, els)

# ══════════════════════════════════════════════════════════════════
#  FINANCIALS
# ══════════════════════════════════════════════════════════════════

def gen_audited_financial_statements(fp):
    els = _hdr("Audited Financial Statements — FY2025", "S.R. Batliboi & Co. LLP")
    d = FINANCIALS["FY2025"]
    p = FINANCIALS["FY2024"]

    els.append(Paragraph("Independent Auditor's Report", HEADING))
    els.append(Paragraph(
        "We have audited the financial statements of PNC Infratech Limited for FY2025. "
        "In our opinion, the financial statements give a true and fair view. "
        "We report an unmodified opinion.", BODY))

    els.append(Paragraph("Statement of Profit & Loss (INR Crores)", HEADING))
    els.append(_tbl([
        ["Particulars", "FY2025", "FY2024"],
        ["Revenue from Operations", _f(d["revenue"]), _f(p["revenue"])],
        ["Other Income", _f(d["other_income"]), _f(p["other_income"])],
        ["Total Income", _f(d["total_income"]), _f(p["total_income"])],
        ["Construction / Material Cost", _f(d["raw_material"]), _f(p["raw_material"])],
        ["Employee Benefit Expenses", _f(d["employee_cost"]), _f(p["employee_cost"])],
        ["Other Expenses", _f(d["other_expenses"]), _f(p["other_expenses"])],
        ["EBITDA", _f(d["ebitda"]), _f(p["ebitda"])],
        ["Depreciation & Amortisation", _f(d["depreciation"]), _f(p["depreciation"])],
        ["Finance Costs", _f(d["finance_cost"]), _f(p["finance_cost"])],
        ["Profit Before Tax", _f(d["pbt"]), _f(p["pbt"])],
        ["Tax Expense", _f(d["tax"]), _f(p["tax"])],
        ["Profit After Tax", _f(d["pat"]), _f(p["pat"])],
    ], [220, 100, 100]))

    els.append(PageBreak())
    els.append(Paragraph("Balance Sheet as at 31 March 2025 (INR Crores)", HEADING))
    els.append(_tbl([
        ["Particulars", "31-Mar-2025", "31-Mar-2024"],
        ["Share Capital", "51.3", "51.3"],
        ["Reserves & Surplus", _f(d["equity"]-51), _f(p["equity"]-51)],
        ["Total Equity", _f(d["equity"]), _f(p["equity"])],
        ["", "", ""],
        ["Long-Term Borrowings", _f(d["lt_debt"]), _f(p["lt_debt"])],
        ["Short-Term Borrowings", _f(d["st_debt"]), _f(p["st_debt"])],
        ["Current Liabilities & Prov.", _f(d["current_liabilities"]), _f(p["current_liabilities"])],
        ["Total Liabilities", _f(d["total_assets"]-d["equity"]), _f(p["total_assets"]-p["equity"])],
        ["Total Equity & Liabilities", _f(d["total_assets"]), _f(p["total_assets"])],
        ["", "", ""],
        ["Fixed Assets (Net Block + CWIP)", _f(d["fixed_assets"]), _f(p["fixed_assets"])],
        ["Investments (Non-Current)", _f(d["investments"]), _f(p["investments"])],
        ["Trade Receivables", _f(d["receivables"]), _f(p["receivables"])],
        ["Inventories / WIP", _f(d["inventory"]), _f(p["inventory"])],
        ["Cash & Bank Balances", _f(d["cash"]), _f(p["cash"])],
        ["Other Assets", _f(d["current_assets"]-d["receivables"]-d["inventory"]-d["cash"]),
         _f(p["current_assets"]-p["receivables"]-p["inventory"]-p["cash"])],
        ["Total Assets", _f(d["total_assets"]), _f(p["total_assets"])],
    ], [220, 110, 110]))

    els.append(Paragraph("Cash Flow Statement (INR Crores)", HEADING))
    els.append(_tbl([
        ["", "FY2025", "FY2024"],
        ["Cash from Operations", _f(d["ocf"]), _f(p["ocf"])],
        ["Cash used in Investing", f"({_f(d['capex'])})", f"({_f(p['capex'])})"],
        ["Cash from Financing", _f(d["cash"]-p["cash"]+d["capex"]-d["ocf"]),
         _f(p["cash"]-380+p["capex"]-p["ocf"])],
        ["Net Change in Cash", _f(d["cash"]-p["cash"]), _f(p["cash"]-380)],
    ], [220, 110, 110]))
    _pdf(fp, els)

def gen_debt_schedule_xlsx(fp):
    """Create debt schedule as JSON (xlsx not needed for pipeline processing)."""
    fp = fp.with_suffix(".json")
    _write_json(fp, {
        "title": "Debt Repayment Schedule — PNC Roads & Infra Ltd",
        "as_of_date": "2026-03-31",
        "currency": "INR Crores",
        "facilities": [
            {"lender": "SBI", "type": "Term Loan", "original": 2800, "outstanding": 2240,
             "rate_pct": 8.95, "repayment": "Quarterly", "maturity": "Mar 2029",
             "annual_repayment": [560, 560, 560, 560]},
            {"lender": "PNB", "type": "Term Loan", "original": 1600, "outstanding": 1380,
             "rate_pct": 9.25, "repayment": "Quarterly", "maturity": "Jun 2030",
             "annual_repayment": [276, 276, 276, 276, 276]},
            {"lender": "HDFC Bank", "type": "CC/OD", "original": 1200, "outstanding": 890,
             "rate_pct": 9.10, "repayment": "Revolving", "maturity": "Rolling"},
            {"lender": "Axis Bank", "type": "CC/OD", "original": 600, "outstanding": 410,
             "rate_pct": 9.05, "repayment": "Revolving", "maturity": "Rolling"},
        ],
        "total_outstanding": 4920,
        "annual_debt_service": {
            "FY2027": {"principal": 836, "interest": 610, "total": 1446},
            "FY2028": {"principal": 836, "interest": 535, "total": 1371},
            "FY2029": {"principal": 836, "interest": 460, "total": 1296},
            "FY2030": {"principal": 552, "interest": 385, "total": 937},
        }
    })

def gen_itr_auto_fetch(fp):
    _write_json(fp, {
        "source": "itr_auto_fetch",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:55:00",
        "source_status": "success",
        "payload": {
            "pan": PAN,
            "assessment_year": "2025-26",
            "itr_type": "ITR-6",
            "filing_date": "2025-09-28",
            "total_income_cr": 1059,
            "tax_paid_cr": 150,
            "refund_status": "NIL",
            "previous_years": [
                {"ay": "2024-25", "total_income_cr": 802, "tax_cr": 144, "filed": "2024-09-30"},
                {"ay": "2023-24", "total_income_cr": 809, "tax_cr": 229, "filed": "2023-09-28"},
            ]
        }
    })

def gen_provisional_financials(fp):
    els = _hdr("Provisional Financials — FY2026 (Annualized)", "Management Estimates")
    d = FY2026_PROV
    els.append(Paragraph("These are management estimates subject to statutory audit.", NOTE))
    els.append(_tbl([
        ["Particulars","9M FY26 (Actual)","FY2026 (Annualized)","FY2025 (Audited)"],
        ["Revenue (Cr)","7,910","10,200","8,650"],
        ["EBITDA (Cr)","1,745","2,448","2,004"],
        ["EBITDA Margin","22.1%","24.0%","23.2%"],
        ["PAT (Cr)","730","1,100","909"],
        ["Total Debt (Cr)","—","9,200","8,025"],
        ["Equity (Cr)","—","6,100","5,185"],
        ["Debt/Equity","—","1.51x","1.55x"],
        ["Interest Coverage","—","3.40x","3.29x"],
    ], [180, 100, 100, 100]))
    els.append(Paragraph("Revenue growth driven by accelerated execution on HAM portfolio.", BODY))
    _pdf(fp, els)

def gen_unaudited_results(fp):
    els = _hdr("Unaudited Financial Results — H1 FY2026", "Board Approved")
    els.append(_tbl([
        ["Particulars (INR Cr)","H1 FY2026","H1 FY2025","Growth"],
        ["Revenue","5,060","4,130","22.5%"],
        ["EBITDA","1,105","825","34.0%"],
        ["EBITDA Margin","21.8%","20.0%",""],
        ["PAT","452","308","46.7%"],
        ["Total Debt","8,800","6,800",""],
        ["D/E Ratio","1.52x","1.56x",""],
    ], [180, 100, 100, 80]))
    els.append(Paragraph("Results reviewed by statutory auditors. No qualifications.", NOTE))
    _pdf(fp, els)

# ══════════════════════════════════════════════════════════════════
#  GST
# ══════════════════════════════════════════════════════════════════

def gen_gst_registration(fp):
    els = _hdr("GST Registration Certificate", "CBIC / GST Portal")
    els.append(_tbl([
        ["Field","Details"],
        ["GSTIN", GSTIN],
        ["Legal Name", COMPANY_REG],
        ["Trade Name", COMPANY],
        ["Type","Regular"],
        ["State","Uttar Pradesh (09)"],
        ["Date of Registration","01-Jul-2017"],
        ["Status","Active"],
        ["Principal Place","PNC Tower, Civil Lines, Agra, UP 282002"],
    ]))
    _pdf(fp, els)

def gen_gstr1_summary(fp):
    els = _hdr("GSTR-1 Summary — FY2025", "GST Portal")
    els.append(_tbl([
        ["Month","Taxable Value (Cr)","IGST (Cr)","CGST (Cr)","SGST (Cr)","Total (Cr)"],
        ["Apr 2024","685","62","31","31","124"],
        ["May 2024","710","64","32","32","128"],
        ["Jun 2024","695","63","31","31","125"],
        ["Jul 2024","740","67","33","33","133"],
        ["Aug 2024","725","65","33","33","131"],
        ["Sep 2024","735","66","33","33","132"],
        ["Oct 2024","760","68","34","34","136"],
        ["Nov 2024","745","67","34","34","135"],
        ["Dec 2024","780","70","35","35","140"],
        ["Jan 2025","755","68","34","34","136"],
        ["Feb 2025","720","65","32","32","129"],
        ["Mar 2025","800","72","36","36","144"],
        ["TOTAL","8,650","807","398","398","1,593"],
    ]))
    els.append(Paragraph("All returns filed on time. No discrepancies reported.", BODY))
    _pdf(fp, els)

def gen_gstr3b_summary(fp):
    els = _hdr("GSTR-3B Summary — FY2025", "GST Portal")
    els.append(_tbl([
        ["Quarter","Output Tax (Cr)","ITC Claimed (Cr)","Net Payable (Cr)","Paid On Time"],
        ["Q1 FY25","377","345","32","Yes"],
        ["Q2 FY25","396","362","34","Yes"],
        ["Q3 FY25","411","375","36","Yes"],
        ["Q4 FY25","409","374","35","Yes"],
        ["TOTAL","1,593","1,456","137",""],
    ]))
    _pdf(fp, els)

def gen_probe42_gst_details(fp):
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_gst_details_by_identifier",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "gstin": GSTIN,
            "legal_name": COMPANY_REG,
            "trade_name": COMPANY,
            "registration_date": "2017-07-01",
            "status": "Active",
            "gst_type": "Regular",
            "state": "Uttar Pradesh",
            "state_code": "09",
            "principal_place": "PNC Tower, 3/22 D, Civil Lines, Agra, UP 282002",
            "nature_of_business": ["Works Contract", "Manufacturing", "Services"],
            "filing_frequency": "Monthly",
            "annual_turnover": {
                "FY2025": 8650, "FY2024": 7956, "FY2023": 7208
            },
            "filing_status": {
                "FY2025": {"gstr1": "All Filed", "gstr3b": "All Filed", "annual_return": "Filed"},
                "FY2024": {"gstr1": "All Filed", "gstr3b": "All Filed", "annual_return": "Filed"},
            },
            "compliance_score": 95,
        }
    })

# ══════════════════════════════════════════════════════════════════
#  KYC
# ══════════════════════════════════════════════════════════════════

def gen_certificate_of_incorporation(fp):
    els = _hdr("Certificate of Incorporation", "MCA / Registrar of Companies")
    els.append(_tbl([
        ["Field","Details"],
        ["Company Name", COMPANY_REG],
        ["CIN", CIN],
        ["Date of Incorporation","26-Sep-2007"],
        ["State","Uttar Pradesh"],
        ["ROC","ROC-Kanpur Nagar"],
        ["Category","Company limited by Shares"],
        ["Sub-Category","Indian Non-Government Company"],
        ["Class","Public"],
        ["Authorized Capital","INR 200,00,00,000"],
        ["Paid-up Capital","INR 51,30,00,000"],
    ]))
    els.append(Paragraph("This is a certified copy from the Registrar of Companies, Kanpur Nagar.", NOTE))
    _pdf(fp, els)

def gen_pan_card(fp):
    els = _hdr("PAN Card", "Income Tax Department")
    els.append(_tbl([
        ["Field","Details"],
        ["PAN", PAN],
        ["Name", COMPANY_REG],
        ["Status","Active"],
        ["Date of Issue","15-Oct-2007"],
        ["Category","Company"],
    ]))
    _pdf(fp, els)

def gen_board_resolution_borrowing(fp):
    els = _hdr("Board Resolution — Borrowing Powers", "Company Secretary")
    els.append(Paragraph("CERTIFIED TRUE COPY OF BOARD RESOLUTION", HEADING))
    els.append(Paragraph(
        f"At the Meeting of the Board of Directors of {COMPANY_REG} held on "
        "15th January 2026 at the Registered Office, the following Resolutions were passed:", BODY))
    els.append(Spacer(1,8))
    els.append(Paragraph(
        "RESOLVED THAT pursuant to Sections 179 and 180(1)(c) of the Companies Act, 2013, "
        "consent is hereby accorded to borrow from time to time any sum or sums of money "
        "not exceeding INR 2,500 Crores (Rupees Two Thousand Five Hundred Crores) from "
        "banks, financial institutions, or other entities.", BODY))
    els.append(Spacer(1,6))
    els.append(Paragraph(
        "RESOLVED FURTHER THAT Shri Yogesh Kumar Jain, Chairman & MD (DIN: 00056994) "
        "and Shri Naveen Kumar Jain, Whole-Time Director (DIN: 00057760) be and are hereby "
        "jointly and severally authorized to negotiate, finalize and execute all documents, "
        "deeds, and instruments as may be required.", BODY))
    els.append(Spacer(1,16))
    els.append(Paragraph("Date: 15 January 2026  |  Place: Agra", BODY))
    els.append(Paragraph("For PNC Infratech Limited", BOLD))
    els.append(Paragraph("Sd/- Tapan Jain, Company Secretary  |  M.No.: ACS-XXXXX", NOTE))
    _pdf(fp, els)

def gen_probe42_kyc_details(fp):
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_kyc_by_identifier",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "cin": CIN,
            "company_name": COMPANY_REG,
            "date_of_incorporation": "2007-09-26",
            "pan": PAN,
            "registered_office": "PNC Tower, 3/22 D, Civil Lines, Agra Delhi Bypass Road, NH 2, Agra, UP 282002",
            "email": "complianceofficer@pncinfratech.com",
            "category": "Company limited by Shares",
            "sub_category": "Indian Non-Government Company",
            "class": "Public",
            "authorized_capital_cr": 200,
            "paid_up_capital_cr": 51.3,
            "listing_status": "Listed",
            "stock_exchange": "BSE, NSE",
            "bse_code": BSE_CODE,
            "nse_symbol": NSE_SYMBOL,
            "industry": "Construction - Civil - Roads",
            "nic_code": "42101",
            "directors": [
                {"name": d["name"], "din": d["din"], "designation": d["desig"],
                 "appointment_date": "2007-09-26" if i < 3 else "2022-04-15"}
                for i, d in enumerate(DIRECTORS)
            ],
            "company_status": "Active",
        }
    })

# ══════════════════════════════════════════════════════════════════
#  LEGAL
# ══════════════════════════════════════════════════════════════════

def gen_epfo_auto_fetch(fp):
    _write_json(fp, {
        "source": "epfo_auto_fetch",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:55:00",
        "payload": {
            "establishment_name": COMPANY_REG,
            "establishment_code": "UPAGRXXXX",
            "total_employees": 12500,
            "active_members": 11800,
            "compliance_status": "Regular",
            "last_filing_month": "Feb-2026",
            "monthly_contribution_lakhs": 185,
            "challan_status_6m": [
                {"month": "Sep-2025", "paid": True, "amount_lakhs": 178},
                {"month": "Oct-2025", "paid": True, "amount_lakhs": 180},
                {"month": "Nov-2025", "paid": True, "amount_lakhs": 182},
                {"month": "Dec-2025", "paid": True, "amount_lakhs": 184},
                {"month": "Jan-2026", "paid": True, "amount_lakhs": 183},
                {"month": "Feb-2026", "paid": True, "amount_lakhs": 185},
            ],
            "no_pending_dues": True,
        }
    })

def gen_probe42_epfo_details(fp):
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_epfo_details_by_identifier",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "cin": CIN,
            "establishment_count": 28,
            "total_employees": 12500,
            "employee_trend": [
                {"year": 2025, "count": 12500},
                {"year": 2024, "count": 11200},
                {"year": 2023, "count": 9800},
            ],
            "compliance": "Regular — No defaults in last 36 months",
        }
    })

def gen_probe42_suit_filed(fp):
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_suit_filed_cases_by_identifier",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "cin": CIN,
            "total_cases": 3,
            "as_petitioner": 2,
            "as_respondent": 1,
            "cases": [
                {"court": "NCLAT Delhi", "type": "Arbitration", "amount_cr": 45,
                 "status": "Pending", "party": "Sub-contractor dispute",
                 "filed_date": "2024-03-15", "role": "Petitioner"},
                {"court": "High Court Allahabad", "type": "Civil", "amount_cr": 12,
                 "status": "Pending", "party": "Land acquisition dispute",
                 "filed_date": "2023-08-20", "role": "Petitioner"},
                {"court": "Consumer Forum UP", "type": "Consumer", "amount_cr": 0.8,
                 "status": "Disposed", "party": "Employment matter",
                 "filed_date": "2022-11-10", "role": "Respondent"},
            ],
            "total_disputed_amount_cr": 57.8,
            "material_impact": "Not material relative to company size",
        }
    })

def gen_probe42_legal_history(fp):
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_legal_history_by_identifier",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "cin": CIN,
            "criminal_cases": 0,
            "civil_cases": 3,
            "tax_cases": 1,
            "regulatory_matters": 0,
            "details": [
                {"type": "Civil", "court": "NCLAT", "amount_cr": 45, "status": "Pending"},
                {"type": "Civil", "court": "HC Allahabad", "amount_cr": 12, "status": "Pending"},
                {"type": "Tax", "court": "ITAT Agra", "amount_cr": 8.5,
                 "status": "Favorable — department appeal dismissed"},
            ],
            "wilful_defaulter": False,
            "fraud_classification": False,
            "insolvency_proceedings": False,
        }
    })

# ══════════════════════════════════════════════════════════════════
#  MCA
# ══════════════════════════════════════════════════════════════════

def gen_mca_master_data(fp):
    _write_json(fp, {
        "cin": CIN,
        "company_name": COMPANY_REG,
        "roc": "ROC-KANPUR NAGAR",
        "registration_number": "033481",
        "category": "Company limited by shares",
        "sub_category": "Indian Non-Government company",
        "class_of_company": "Public",
        "date_of_incorporation": "2007-09-26",
        "authorized_capital": 20000000000,
        "paid_up_capital": 5130000000,
        "activity_description": "Construction of roads and motorways",
        "registered_office": "PNC Tower, 3/22 D, Civil Lines, Agra, UP 282002",
        "email": "complianceofficer@pncinfratech.com",
        "listing_status": "Listed",
        "last_agm_date": "2025-09-28",
        "last_bs_date": "2025-03-31",
        "company_status": "Active",
    })

def gen_probe42_base_details(fp):
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_base_details_by_identifier",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "cin": CIN,
            "company_name": COMPANY_REG,
            "date_of_incorporation": "2007-09-26",
            "company_status": "Active",
            "company_type": "Public Limited Company",
            "industry": "Construction - Roads & Highways",
            "nic_code": "42101",
            "authorized_capital_cr": 200,
            "paid_up_capital_cr": 51.3,
            "listing": {"bse": BSE_CODE, "nse": NSE_SYMBOL},
            "registered_address": "PNC Tower, 3/22 D, Civil Lines, Agra, UP 282002",
            "directors_count": 5,
            "charges_count": 8,
            "subsidiaries_count": 14,
        }
    })

def gen_probe42_director_network(fp):
    directors_data = []
    for d in DIRECTORS:
        directors_data.append({
            "din": d["din"],
            "name": d["name"],
            "designation": d["desig"],
            "appointment_date": "2007-09-26" if d["share_pct"] > 0 else "2022-04-15",
            "shareholding_pct": d["share_pct"],
            "other_directorships": [
                {"cin": f"U45200UP20{i:02d}PLC{10000+i:05d}", "company": f"PNC {nm} Pvt Ltd",
                 "designation": "Director", "status": "Active"}
                for i, nm in enumerate(["Highways", "Buildcon", "Infra Projects"][:2 if d["share_pct"]>0 else 0])
            ]
        })
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_director_network_by_din",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "cin": CIN,
            "directors": directors_data,
            "total_directors": len(DIRECTORS),
            "independent_directors": 2,
            "executive_directors": 3,
        }
    })

def gen_probe42_open_charges(fp):
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_open_charges_by_identifier",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "cin": CIN,
            "total_charges": 8,
            "open_charges": 5,
            "satisfied_charges": 3,
            "charges": [
                {"charge_id": "100234567", "holder": "State Bank of India",
                 "amount_cr": 2800, "date_created": "2023-06-12",
                 "status": "Open", "assets": "BOT Concession Rights NH-44"},
                {"charge_id": "100234568", "holder": "Punjab National Bank",
                 "amount_cr": 1600, "date_created": "2023-09-15",
                 "status": "Open", "assets": "Equipment fleet + Office Lucknow"},
                {"charge_id": "100234569", "holder": "HDFC Bank Ltd",
                 "amount_cr": 1200, "date_created": "2024-01-20",
                 "status": "Open", "assets": "Stock & book debts (pari passu)"},
                {"charge_id": "100234570", "holder": "ICICI Bank Ltd",
                 "amount_cr": 800, "date_created": "2024-03-10",
                 "status": "Open", "assets": "Bank guarantees"},
                {"charge_id": "100234571", "holder": "Axis Bank Ltd",
                 "amount_cr": 600, "date_created": "2024-06-01",
                 "status": "Open", "assets": "Book debts"},
            ]
        }
    })

# ══════════════════════════════════════════════════════════════════
#  MISC
# ══════════════════════════════════════════════════════════════════

def gen_company_profile_web(fp):
    _write_json(fp, {
        "source": "web_scrape",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:50:00",
        "payload": {
            "company_name": COMPANY_REG,
            "website": "https://www.pncinfratech.com",
            "industry": "Infrastructure - Roads & Highways",
            "about": (
                "PNC Infratech Limited is one of the leading Indian infrastructure "
                "companies specializing in road and highway construction. The company "
                "provides end-to-end infrastructure solutions including design, engineering, "
                "procurement, construction, and O&M services on EPC, DBFOT, HAM, and "
                "BOT formats."
            ),
            "headquarters": "Agra, Uttar Pradesh",
            "founded": 2007,
            "employees": 12500,
            "iso_certification": "ISO 9001:2015",
            "key_clients": ["NHAI", "UPEIDA", "MPRDC", "UPSHA"],
            "segments": ["EPC Highways", "BOT/HAM Highways", "Water Projects", "Industrial Area Development"],
            "order_book_cr": 27680,
            "order_book_multiple": 3.2,
            "vision": "To become among the top 3 infrastructure companies in India",
            "strengths": [
                "Integrated construction capabilities from mining to commissioning",
                "17+ years track record of timely project completion",
                "NHAI AAAA rating",
                "Large fleet of sophisticated machinery and plants",
                "Strong promoter group with 63% shareholding",
            ],
        }
    })

def gen_market_auto_fetch(fp):
    _write_json(fp, {
        "source": "market_auto_fetch",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T09:00:00",
        "source_status": "success",
        "payload": {
            "nse_symbol": NSE_SYMBOL,
            "bse_code": BSE_CODE,
            "isin": ISIN,
            "last_price": 385.60,
            "change_pct": 1.24,
            "52w_high": 458.90,
            "52w_low": 278.40,
            "market_cap_cr": 9885,
            "pe_ratio": 10.88,
            "book_value": 202.10,
            "pb_ratio": 1.91,
            "dividend_yield_pct": 0.78,
            "face_value": 2,
            "shares_outstanding_cr": 25.63,
            "promoter_holding_pct": 63.1,
            "fii_holding_pct": 12.4,
            "dii_holding_pct": 18.2,
            "public_holding_pct": 6.3,
            "avg_volume_30d": 2850000,
        }
    })

def gen_probe42_bundle(fp):
    """Create a lightweight bundle that has actual data (not errors)."""
    _write_json(fp, {
        "source": "probe42_bundle",
        "entity_key": ENTITY_ID,
        "cin": CIN,
        "pan": PAN,
        "gstin": GSTIN,
        "company_name": COMPANY_REG,
        "cache_timestamp": "2026-04-06T08:54:03Z",
        "tools_status": {
            "get_base_details_by_identifier": "success",
            "get_kyc_by_identifier": "success",
            "get_gst_details_by_identifier": "success",
            "get_epfo_details_by_identifier": "success",
            "get_suit_filed_cases_by_identifier": "success",
            "get_credit_ratings_by_identifier": "success",
            "get_legal_history_by_identifier": "success",
            "get_open_charges_by_identifier": "success",
            "get_data_status": "success",
            "get_director_network_by_din": "success",
        },
        "summary": {
            "company_status": "Active",
            "listing_status": "Listed",
            "industry": "Construction - Roads & Highways",
            "directors_count": 5,
            "ratings_count": 2,
            "legal_case_count": 3,
            "total_disputed_amount_cr": 57.8,
            "charges_count": 8,
            "employees": 12500,
            "gst_compliance_score": 95,
        }
    })

def gen_probe42_data_status(fp):
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_data_status",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "cin": CIN,
            "data_availability": {
                "base_details": True,
                "kyc": True,
                "gst": True,
                "epfo": True,
                "legal_cases": True,
                "credit_ratings": True,
                "open_charges": True,
                "director_network": True,
                "financial_statements": True,
            },
            "last_updated": {
                "mca": "2026-03-15",
                "gst": "2026-03-31",
                "epfo": "2026-02-28",
                "court_records": "2026-01-31",
            }
        }
    })

# ══════════════════════════════════════════════════════════════════
#  RATINGS
# ══════════════════════════════════════════════════════════════════

def gen_credit_rating_report(fp):
    els = _hdr("Credit Rating Report", "CARE Ratings Limited")
    els.append(Paragraph("Rating Action", HEADING))
    els.append(_tbl([
        ["Facility","Amount (Cr)","Rating","Outlook","Action"],
        ["Long-Term Bank Facilities","6,200","CARE AA-","Stable","Reaffirmed"],
        ["Short-Term Bank Facilities","1,550","CARE A1+","—","Reaffirmed"],
    ]))
    els.append(Paragraph("Rating Rationale:", HEADING))
    for r in [
        "Experienced management with 17+ year track record in road EPC",
        "Strong order book of INR 27,680 Cr providing 3.2x revenue visibility",
        "Diversified project portfolio across HAM, BOT, and EPC segments",
        "Healthy EBITDA margins of 23.2% in FY2025 (industry avg ~18%)",
        "Comfortable debt service coverage with DSCR of 1.42x",
        "Listed entity with adequate access to capital markets",
    ]:
        els.append(Paragraph(f"(+) {r}", BODY))
    els.append(Spacer(1,6))
    for r in [
        "Moderately leveraged balance sheet with D/E of 1.55x",
        "Geographic concentration in Uttar Pradesh",
        "Exposure to input cost volatility (bitumen, steel, aggregates)",
        "Working capital intensive nature of EPC business",
    ]:
        els.append(Paragraph(f"(-) {r}", BODY))
    els.append(Paragraph("Rating Date: 15 November 2025  |  Valid until: 14 November 2026", NOTE))
    _pdf(fp, els)

def gen_probe42_credit_ratings(fp):
    _write_json(fp, {
        "source": "probe42",
        "tool": "get_credit_ratings_by_identifier",
        "entity_key": ENTITY_ID,
        "as_of_date": "2026-04-06T08:54:00",
        "payload": {
            "cin": CIN,
            "ratings": [
                {
                    "agency": "CARE Ratings",
                    "instrument": "Long-Term Bank Facilities",
                    "rating": "CARE AA-",
                    "outlook": "Stable",
                    "amount_cr": 6200,
                    "action": "Reaffirmed",
                    "date": "2025-11-15",
                },
                {
                    "agency": "CARE Ratings",
                    "instrument": "Short-Term Bank Facilities",
                    "rating": "CARE A1+",
                    "outlook": None,
                    "amount_cr": 1550,
                    "action": "Reaffirmed",
                    "date": "2025-11-15",
                },
            ],
            "rating_history": [
                {"date": "2024-11-10", "rating": "CARE AA-", "action": "Reaffirmed"},
                {"date": "2023-11-08", "rating": "CARE AA-", "action": "Upgraded from A+"},
                {"date": "2022-10-15", "rating": "CARE A+", "action": "Reaffirmed"},
            ]
        }
    })

# ══════════════════════════════════════════════════════════════════
#  REQUEST
# ══════════════════════════════════════════════════════════════════

def gen_request_note_pdf(fp):
    els = _hdr("Credit Facility Request Note", "Relationship Manager")
    els.append(_tbl([
        ["Parameter","Details"],
        ["Borrower", COMPANY],
        ["Entity ID", ENTITY_ID],
        ["CIN", CIN],
        ["Facility Type","Term Loan"],
        ["Amount Requested","INR 1,500 Crores"],
        ["Proposed Tenor","72 months"],
        ["Purpose","Execution of NHAI highway EPC projects — 4-laning of NH-44 and Bundelkhand Expressway Phase-II"],
        ["Security Offered","Assignment of BOT rights + equipment charge + promoter guarantee"],
    ]))
    els.append(Paragraph("Key Highlights:", HEADING))
    for h in [
        "Order book: INR 27,680 Cr (3.2x FY2025 revenue)",
        "NHAI AAAA-rated EPC contractor",
        "CARE AA-/Stable rating — reaffirmed Nov 2025",
        "Promoter holding: 63.1% — stable, no pledge",
        "17+ years track record with NHAI bonuses for early completion",
        "EBITDA margin: 23.2% (FY2025) — above industry average",
        "Proposed D/E post-sanction: 1.85x (within policy ceiling of 2.0x)",
    ]:
        els.append(Paragraph(f"• {h}", BODY))
    _pdf(fp, els)

# ══════════════════════════════════════════════════════════════════
#  ROAD CONSTRUCTION PROJECTIONS (NEW)
# ══════════════════════════════════════════════════════════════════

def gen_road_construction_projections(fp):
    """Comprehensive road construction projection document with industry data."""
    els = _hdr("Road Construction Projections & Order Book Analysis",
               "Strategy & Business Development")

    els.append(Paragraph("1. India Road Construction Industry Outlook", HEADING))
    els.append(_tbl([
        ["Metric","FY2025","FY2026E","FY2027E","FY2028E","FY2030E"],
        ["NHAI Award (km)","12,350","14,000","16,500","18,000","22,000"],
        ["NHAI Construction (km)","10,050","11,500","13,200","15,000","18,000"],
        ["Bharatmala Phase-I (cum. km)","22,400","26,500","32,000","38,000","48,000"],
        ["Industry Revenue (INR Lakh Cr)","6.20","7.10","8.30","9.60","13.00"],
        ["Govt Capex Roads (INR Lakh Cr)","2.78","3.20","3.60","4.10","5.50"],
    ], [165,68,68,68,68,68]))

    els.append(Paragraph(
        "The National Infrastructure Pipeline targets total road investment of INR 20 lakh crore by FY2030. "
        "NHAI construction pace has accelerated from 28 km/day (FY2023) to an expected 40+ km/day by FY2028. "
        "Key programs: Bharatmala Pariyojana (83,677 km), National Highways expansion, and state expressways.", BODY))

    els.append(Paragraph("2. PNC Infratech — Order Book Composition", HEADING))
    tbl_data = [["Project","Type","State","Length (km)","Value (Cr)","Status","Target"]]
    total_value = 0
    for p in ORDER_BOOK:
        tbl_data.append([p["project"], p["employer"], p["state"],
                        str(p["length_km"]), _f(p["value_cr"]),
                        p["status"], p["completion"]])
        total_value += p["value_cr"]
    tbl_data.append(["TOTAL", "", "", str(sum(p["length_km"] for p in ORDER_BOOK)),
                     _f(total_value), "", ""])
    els.append(_tbl(tbl_data, [140, 35, 32, 35, 50, 65, 52]))

    els.append(PageBreak())
    els.append(Paragraph("3. Revenue & Execution Projections", HEADING))
    els.append(_tbl([
        ["Metric","FY2025 (A)","FY2026 (E)","FY2027 (P)","FY2028 (P)","FY2029 (P)"],
        ["Order Book (Cr)","27,680","30,500","28,200","32,000","35,000"],
        ["New Orders (Cr)","8,200","13,020","10,000","18,000","15,000"],
        ["Revenue:EPC (Cr)","6,050","7,140","8,570","10,280","12,340"],
        ["Revenue:HAM Annuity (Cr)","1,820","2,160","2,590","3,108","3,730"],
        ["Revenue:Other (Cr)","780","900","1,080","1,300","1,560"],
        ["Total Revenue (Cr)","8,650","10,200","12,240","14,688","17,630"],
        ["Revenue Growth","8.7%","17.9%","20.0%","20.0%","20.0%"],
        ["Order Book/Revenue","3.2x","3.0x","2.3x","2.2x","2.0x"],
    ], [140,75,75,75,75,75]))

    els.append(Paragraph("4. Profitability Projections", HEADING))
    els.append(_tbl([
        ["Metric","FY2025 (A)","FY2026 (E)","FY2027 (P)","FY2028 (P)","FY2029 (P)"],
        ["EBITDA (Cr)","2,004","2,448","3,060","3,672","4,407"],
        ["EBITDA Margin","23.2%","24.0%","25.0%","25.0%","25.0%"],
        ["Depreciation (Cr)","520","620","735","880","1,056"],
        ["Finance Cost (Cr)","610","680","720","700","650"],
        ["PBT (Cr)","1,059","1,296","1,755","2,242","2,851"],
        ["Tax (Cr)","150","196","456","583","741"],
        ["PAT (Cr)","909","1,100","1,300","1,660","2,110"],
        ["PAT Margin","10.5%","10.8%","10.6%","11.3%","12.0%"],
    ], [140,75,75,75,75,75]))

    els.append(Paragraph("5. Debt & Leverage Projections", HEADING))
    els.append(_tbl([
        ["Metric","FY2025 (A)","FY2026 (E)","FY2027 (P)","FY2028 (P)","FY2029 (P)"],
        ["Total Debt (Cr)","8,025","9,200","8,800","8,000","7,200"],
        ["Equity (Cr)","5,185","6,100","7,350","8,950","10,950"],
        ["Debt/Equity","1.55x","1.51x","1.20x","0.89x","0.66x"],
        ["Net Debt/EBITDA","3.67x","3.48x","2.65x","1.99x","1.48x"],
        ["DSCR","1.42x","1.55x","1.72x","1.90x","2.10x"],
        ["Interest Coverage","3.29x","3.60x","4.25x","5.25x","6.78x"],
    ], [140,75,75,75,75,75]))

    els.append(Paragraph("6. Key Assumptions", HEADING))
    for a in [
        "Revenue CAGR of ~20% FY25-29 driven by order book execution and new awards",
        "EBITDA margin stabilization at 25% from scale benefits and higher HAM share",
        "Debt reduction from FY2027 as HAM annuity cash flows begin and older TLs amortize",
        "New order win rate: INR 12,000-18,000 Cr p.a. based on NHAI tender pipeline",
        "No equity dilution assumed; growth funded through internal accruals + debt",
        "Bitumen price assumption: INR 40,000/MT (stable) based on OPEC+ production outlook",
        "Steel price assumption: INR 55,000/MT (stable) with import substitution benefits",
        "NHAI payment cycle: 45-60 days for EPC milestones (no material delays assumed)",
    ]:
        els.append(Paragraph(f"• {a}", BODY))

    els.append(Paragraph("7. Risk Factors", HEADING))
    for r in [
        "Government capex slowdown or election-year spending deferral",
        "Raw material cost spike (bitumen linked to crude oil)",
        "Land acquisition delays on HAM projects",
        "Labour availability challenges at remote project sites",
        "Working capital stretch if NHAI payment cycle extends beyond 90 days",
        "Interest rate changes impacting debt servicing cost",
    ]:
        els.append(Paragraph(f"• {r}", BODY))

    els.append(Paragraph("Prepared by: Strategy & BD Team  |  Date: March 2026", NOTE))
    _pdf(fp, els)

def gen_cma_projection_enhanced(fp):
    """Enhanced CMA projection with road construction-specific metrics."""
    els = _hdr("CMA Data & Financial Projections", "Finance Team / S.R. Batliboi & Co.")

    els.append(Paragraph("A. Profit & Loss Projections (INR Crores)", HEADING))
    els.append(_tbl([
        ["Particulars","FY2025 (A)","FY2026 (E)","FY2027 (P)","FY2028 (P)","FY2029 (P)"],
        ["Revenue — EPC","6,050","7,140","8,570","10,280","12,340"],
        ["Revenue — HAM/BOT Annuity","1,820","2,160","2,590","3,108","3,730"],
        ["Revenue — Other","780","900","1,080","1,300","1,560"],
        ["Total Revenue","8,650","10,200","12,240","14,688","17,630"],
        ["Construction/Material Cost","4,152","4,794","5,875","7,051","8,467"],
        ["Employee Cost","519","612","734","881","1,058"],
        ["Other Expenses","2,160","2,498","2,695","3,232","3,878"],
        ["Total Expenses","6,831","7,904","9,304","11,164","13,403"],
        ["EBITDA","2,004","2,448","3,060","3,672","4,407"],
        ["EBITDA Margin %","23.2%","24.0%","25.0%","25.0%","25.0%"],
        ["Depreciation","520","620","735","880","1,056"],
        ["Interest/Finance Cost","610","680","720","700","650"],
        ["PBT","1,059","1,296","1,755","2,242","2,851"],
        ["Tax","150","196","456","583","741"],
        ["PAT","909","1,100","1,300","1,660","2,110"],
    ], [140,70,70,70,70,70]))

    els.append(PageBreak())
    els.append(Paragraph("B. Balance Sheet Projections (INR Crores)", HEADING))
    els.append(_tbl([
        ["Particulars","FY2025 (A)","FY2026 (E)","FY2027 (P)","FY2028 (P)","FY2029 (P)"],
        ["Equity","5,185","6,100","7,350","8,950","10,950"],
        ["Long-Term Debt","5,618","6,200","5,800","5,000","4,200"],
        ["Short-Term Debt","2,407","3,000","3,000","3,000","3,000"],
        ["Total Debt","8,025","9,200","8,800","8,000","7,200"],
        ["Current Liabilities","4,425","5,200","5,850","6,550","7,350"],
        ["Total Liabilities","10,425","12,100","12,350","12,250","12,250"],
        ["Total E&L","15,610","18,200","19,700","21,200","23,200"],
        ["","","","","",""],
        ["Fixed Assets","6,800","7,900","8,700","9,500","10,200"],
        ["Investments","2,960","3,400","3,800","4,200","4,700"],
        ["Current Assets","5,850","6,900","7,200","7,500","8,300"],
        ["Total Assets","15,610","18,200","19,700","21,200","23,200"],
    ], [140,70,70,70,70,70]))

    els.append(Paragraph("C. Cash Flow & DSCR (INR Crores)", HEADING))
    els.append(_tbl([
        ["","FY2025 (A)","FY2026 (E)","FY2027 (P)","FY2028 (P)","FY2029 (P)"],
        ["Operating Cash Flow","1,850","2,200","2,750","3,300","3,960"],
        ["Capex","(780)","(900)","(850)","(800)","(750)"],
        ["Free Cash Flow","1,070","1,300","1,900","2,500","3,210"],
        ["Debt Service (P+I)","1,446","1,610","1,556","1,536","1,486"],
        ["DSCR","1.42x","1.55x","1.72x","1.90x","2.10x"],
        ["","","","","",""],
        ["Debt/Equity","1.55x","1.51x","1.20x","0.89x","0.66x"],
        ["Current Ratio","1.32x","1.33x","1.23x","1.15x","1.13x"],
        ["TOL/TNW","2.01x","1.98x","1.68x","1.37x","1.12x"],
    ], [140,70,70,70,70,70]))

    els.append(Paragraph("D. Project-wise Revenue Build-up (INR Crores)", HEADING))
    els.append(_tbl([
        ["Project","FY2026","FY2027","FY2028","FY2029"],
        ["Chakeri-Allahabad NH-2","650","850","350","—"],
        ["Challakere-Hariyur NH-150A","380","520","480","—"],
        ["Delhi-Vadodara Pkg 29","1,200","1,500","500","—"],
        ["Kanpur-Lucknow Pkg 1&2","2,400","1,800","—","—"],
        ["Sonauli-Gorakhpur NH-29E","420","680","750","—"],
        ["MH/KN Border NH-150C","—","1,200","1,800","520"],
        ["New Orders (FY26+)","—","1,500","5,000","8,500"],
        ["HAM Annuity Income","2,160","2,590","3,108","3,730"],
        ["Other","990","1,600","2,700","4,880"],
        ["TOTAL","10,200","12,240","14,688","17,630"],
    ], [150,70,70,70,70]))

    els.append(Paragraph("Certified by: CFO, PNC Infratech Limited", NOTE))
    els.append(Paragraph("Date: March 2026", NOTE))
    _pdf(fp, els)

# ══════════════════════════════════════════════════════════════════
#  MAIN ORCHESTRATION
# ══════════════════════════════════════════════════════════════════

def main():
    print(f"Generating comprehensive PNCR001 document set → {TEST_DOCS}")
    counters = {"created": 0, "copied": 0, "skipped": 0}

    def _gen(rel_path, gen_func, desc=None, is_json=False):
        fp = PACK / rel_path
        gen_func(fp)
        counters["created"] += 1
        print(f"  + {rel_path}  {'(JSON)' if is_json else '(PDF)'}")

    # ── Ensure directory structure ────────────────────────────────
    for cat in ["banking", "bureau", "collateral", "exchange", "financials",
                "gst", "kyc", "legal", "mca", "misc", "ratings", "request"]:
        (PACK / cat).mkdir(parents=True, exist_ok=True)

    # ── Copy real annual reports from website downloads ───────────
    print("\n── Real Annual Reports (from website) ──")
    real_ar_map = {
        "PNC_Annual_Report_FY2023.pdf": "annual_report_fy2023.pdf",
        "PNC_Annual_Report_FY2024.pdf": "annual_report_fy2024.pdf",
        "PNC_Annual_Report_FY2025.pdf": "annual_report_fy2025.pdf",
    }
    for src_name, dst_name in real_ar_map.items():
        src = REAL_AR / src_name
        if src.exists():
            dst = PACK / "financials" / dst_name
            shutil.copy2(src, dst)
            sz_mb = src.stat().st_size / (1024*1024)
            counters["copied"] += 1
            print(f"  ✓ financials/{dst_name}  ({sz_mb:.1f} MB — REAL from website)")
        else:
            print(f"  ⚠ {src_name} not found in {REAL_AR}")

    # ── Copy to CAM bootstrap directory ──────────────────────────
    CAM_DIR.mkdir(parents=True, exist_ok=True)
    for src_name in real_ar_map:
        src = REAL_AR / src_name
        if src.exists():
            shutil.copy2(src, CAM_DIR / src_name)
    print(f"  ✓ Copied real ARs to downloaded document/CAM/")

    # ── BANKING ──────────────────────────────────────────────────
    print("\n── Banking ──")
    _gen("banking/bank_statement_6m.pdf", gen_bank_statement_6m)
    _gen("banking/bank_statement_fy2025.pdf", gen_bank_statement_fy)
    _gen("banking/existing_facility_details.pdf", gen_existing_facility)
    _gen("banking/sanction_letter.pdf", gen_sanction_letter)

    # ── BUREAU ───────────────────────────────────────────────────
    print("\n── Bureau ──")
    _gen("bureau/commercial_bureau_report.pdf", gen_commercial_bureau_report)
    _gen("bureau/crilc_auto_fetch.json", gen_crilc_json, is_json=True)
    _gen("bureau/crilc_report.pdf", gen_crilc_report)

    # ── COLLATERAL ───────────────────────────────────────────────
    print("\n── Collateral ──")
    _gen("collateral/valuation_report.pdf", gen_valuation_report)

    # ── EXCHANGE ─────────────────────────────────────────────────
    print("\n── Exchange ──")
    _gen("exchange/corporate_governance_report.pdf", gen_corp_governance_report)
    _gen("exchange/quarterly_results_q3fy2025.pdf", gen_quarterly_results)

    # ── FINANCIALS ───────────────────────────────────────────────
    print("\n── Financials ──")
    _gen("financials/audited_financial_statements.pdf", gen_audited_financial_statements)
    _gen("financials/debt_schedule.json", gen_debt_schedule_xlsx, is_json=True)
    _gen("financials/itr_auto_fetch.json", gen_itr_auto_fetch, is_json=True)
    _gen("financials/provisional_financials_fy2026.pdf", gen_provisional_financials)
    _gen("financials/unaudited_results_fy2026.pdf", gen_unaudited_results)

    # ── GST ──────────────────────────────────────────────────────
    print("\n── GST ──")
    _gen("gst/gst_registration_certificate.pdf", gen_gst_registration)
    _gen("gst/gstr1_summary.pdf", gen_gstr1_summary)
    _gen("gst/gstr3b_summary.pdf", gen_gstr3b_summary)
    _gen("gst/probe42_gst_details.json", gen_probe42_gst_details, is_json=True)

    # ── KYC ──────────────────────────────────────────────────────
    print("\n── KYC ──")
    _gen("kyc/certificate_of_incorporation.pdf", gen_certificate_of_incorporation)
    _gen("kyc/pan_card.pdf", gen_pan_card)
    _gen("kyc/board_resolution_borrowing.pdf", gen_board_resolution_borrowing)
    _gen("kyc/probe42_kyc_details.json", gen_probe42_kyc_details, is_json=True)

    # ── LEGAL ────────────────────────────────────────────────────
    print("\n── Legal ──")
    _gen("legal/epfo_auto_fetch.json", gen_epfo_auto_fetch, is_json=True)
    _gen("legal/probe42_epfo_details.json", gen_probe42_epfo_details, is_json=True)
    _gen("legal/probe42_suit_filed_cases.json", gen_probe42_suit_filed, is_json=True)
    _gen("legal/probe42_legal_history.json", gen_probe42_legal_history, is_json=True)

    # ── MCA ──────────────────────────────────────────────────────
    print("\n── MCA ──")
    _gen("mca/mca_master_data.json", gen_mca_master_data, is_json=True)
    _gen("mca/probe42_base_details.json", gen_probe42_base_details, is_json=True)
    _gen("mca/probe42_director_network.json", gen_probe42_director_network, is_json=True)
    _gen("mca/probe42_open_charges.json", gen_probe42_open_charges, is_json=True)

    # ── MISC ─────────────────────────────────────────────────────
    print("\n── Misc ──")
    _gen("misc/company_profile_web.json", gen_company_profile_web, is_json=True)
    _gen("misc/market_auto_fetch.json", gen_market_auto_fetch, is_json=True)
    _gen("misc/probe42_bundle.json", gen_probe42_bundle, is_json=True)
    _gen("misc/probe42_data_status.json", gen_probe42_data_status, is_json=True)

    # ── RATINGS ──────────────────────────────────────────────────
    print("\n── Ratings ──")
    _gen("ratings/credit_rating_report.pdf", gen_credit_rating_report)
    _gen("ratings/probe42_credit_ratings.json", gen_probe42_credit_ratings, is_json=True)

    # ── REQUEST ──────────────────────────────────────────────────
    print("\n── Request ──")
    _gen("request/request_note.pdf", gen_request_note_pdf)

    # ── ROAD CONSTRUCTION PROJECTIONS (optional-inputs) ───────────
    print("\n── Road Construction Projections & CMA ──")
    proj_fp = TEST_DOCS / "optional-inputs" / "road_construction_projections.pdf"
    gen_road_construction_projections(proj_fp)
    counters["created"] += 1
    print(f"  + optional-inputs/road_construction_projections.pdf")

    cma_fp = TEST_DOCS / "optional-inputs" / "cma_projection_enhanced.pdf"
    gen_cma_projection_enhanced(cma_fp)
    counters["created"] += 1
    print(f"  + optional-inputs/cma_projection_enhanced.pdf")

    # ── Update metadata ──────────────────────────────────────────
    total_files = sum(1 for _ in PACK.rglob("*") if _.is_file())
    meta = {
        "entity_id": ENTITY_ID,
        "company_name": COMPANY,
        "cin": CIN,
        "pan": PAN,
        "generated": date.today().isoformat(),
        "total_documents": total_files,
        "source": "website_download + synthetic_generation",
        "real_documents": list(real_ar_map.values()),
        "categories": sorted(set(p.parent.name for p in PACK.rglob("*") if p.is_file() and p.parent != PACK)),
    }
    (PACK / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"\n── Metadata ──")
    print(f"  ✓ metadata.json updated ({total_files} documents)")

    # ── Also copy pack to storage/documents ──────────────────────
    if STORAGE.exists():
        # Merge into existing storage (don't overwrite what auto-fetch created)
        for src_file in PACK.rglob("*"):
            if src_file.is_file():
                rel = src_file.relative_to(PACK)
                dst = STORAGE / rel
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst)
                    counters["copied"] += 1
        print(f"\n  ✓ Merged {counters['copied']-len(real_ar_map)} new files into storage/documents/{ENTITY_ID}/")
    else:
        shutil.copytree(PACK, STORAGE)
        print(f"\n  ✓ Copied full pack to storage/documents/{ENTITY_ID}/")

    # ── Summary ──────────────────────────────────────────────────
    all_files = sum(1 for _ in TEST_DOCS.rglob("*") if _.is_file())
    print(f"\n{'='*60}")
    print(f"  PNCR001 Document Generation Complete")
    print(f"  Created:  {counters['created']} files")
    print(f"  Copied:   {counters['copied']} files")
    print(f"  Total:    {all_files} files in test-documents/PNCR001_PNC_Roads/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
