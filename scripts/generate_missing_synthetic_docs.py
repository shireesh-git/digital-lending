"""
Generate missing synthetic documents for the test document set.
Creates: property_documents, cersai_search, insurance_policies, undertakings
for all 5 entities — consistent with existing synthetic PDF format.
"""

from __future__ import annotations
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT

ENTITIES = {
    "APOL001": {"name": "APOLLO HOSPITALS ENTERPRISE LIMITED", "sector": "Healthcare"},
    "INFY001": {"name": "INFOSYS LIMITED", "sector": "IT Services"},
    "IHCL001": {"name": "THE INDIAN HOTELS COMPANY LIMITED", "sector": "Hospitality"},
    "MFL001":  {"name": "MADRAS FERTILIZERS LIMITED", "sector": "Fertilizers & Chemicals"},
    "MRF001":  {"name": "MRF LIMITED", "sector": "Tyres & Rubber"},
}

TODAY = date.today().isoformat()
STYLES = getSampleStyleSheet()
TITLE_STYLE = ParagraphStyle("DocTitle", parent=STYLES["Heading1"], fontSize=16, spaceAfter=12)
SUB_STYLE = ParagraphStyle("DocSub", parent=STYLES["Normal"], fontSize=10, textColor=colors.grey, spaceAfter=8)
BODY = ParagraphStyle("Body", parent=STYLES["Normal"], fontSize=10, leading=14, spaceAfter=6)
BOLD = ParagraphStyle("Bold", parent=BODY, fontName="Helvetica-Bold")
NOTE_STYLE = ParagraphStyle("Note", parent=BODY, fontSize=9, textColor=colors.HexColor("#888888"), spaceAfter=4)


def _build_pdf(filepath: Path, elements: list):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    doc.build(elements)


def _header(title, entity_id, company, source):
    return [
        Paragraph(title, TITLE_STYLE),
        Paragraph(f"Company: {company}", BOLD),
        Paragraph(f"Entity ID: {entity_id}", BODY),
        Paragraph(f"Typical Source: {source}", SUB_STYLE),
        Paragraph("Synthetic PDF generated for workflow continuity when the real source file is not yet available.", NOTE_STYLE),
        Spacer(1, 12),
    ]


def _table(data, col_widths=None):
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(style)
    return t


# ─── Property Documents ─────────────────────────────────────────────────────

def gen_property_documents(entity_id: str, info: dict, dest: Path):
    els = _header("Property Documents", entity_id, info["name"],
                  "Collateral team / Empanelled valuer / Legal department")

    els.append(Paragraph("Title Deed Summary", BOLD))
    els.append(_table([
        ["Property", "Type", "Area (sq.ft)", "Location", "Title Status"],
        ["Corporate Office Premises", "Commercial", "45,000", "Registered Address", "Clear — verified"],
        ["Industrial / Warehouse Unit", "Industrial", "1,20,000", "Operational site", "Clear — verified"],
    ], col_widths=[120, 80, 80, 110, 100]))
    els.append(Spacer(1, 14))

    els.append(Paragraph("Search Report Highlights", BOLD))
    els.append(Paragraph("• Title search conducted for the last 30 years — no adverse claims or disputes found.", BODY))
    els.append(Paragraph("• No encumbrance certificate obtained from Sub-Registrar's office — property is free of encumbrances.", BODY))
    els.append(Paragraph("• Revenue records verification confirms owner details match company registration.", BODY))
    els.append(Spacer(1, 10))

    els.append(Paragraph("Pending Real Inputs", BOLD))
    els.append(Paragraph("• Original title deed copy with registration details", NOTE_STYLE))
    els.append(Paragraph("• Encumbrance certificate from Sub-Registrar", NOTE_STYLE))
    els.append(Paragraph("• Latest municipal tax receipts", NOTE_STYLE))

    _build_pdf(dest / "synthetic_property_documents.pdf", els)


# ─── CERSAI Search ───────────────────────────────────────────────────────────

def gen_cersai_search(entity_id: str, info: dict, dest: Path):
    els = _header("CERSAI Search Report", entity_id, info["name"],
                  "Central Registry (CERSAI) / Legal & compliance team")

    els.append(Paragraph("Central Registry of Securitisation Asset Reconstruction and Security Interest", BOLD))
    els.append(Paragraph(f"Search Date: {TODAY}", BODY))
    els.append(Spacer(1, 10))

    els.append(_table([
        ["Parameter", "Details"],
        ["Entity Name", info["name"]],
        ["Search Type", "Company-wide asset search"],
        ["Registry Status", "Search completed"],
        ["Existing Charges Found", "Nil — No prior securitisation interest registered"],
        ["Mortgage Entries", "Nil"],
        ["Pledge Entries", "Nil"],
        ["Hypothecation Entries", "Nil"],
        ["Assignment Entries", "Nil"],
    ], col_widths=[180, 320]))
    els.append(Spacer(1, 14))

    els.append(Paragraph("Observations", BOLD))
    els.append(Paragraph("• No existing security interest registered with CERSAI against the borrower entity.", BODY))
    els.append(Paragraph("• The proposed security can be registered as a fresh charge without conflict.", BODY))
    els.append(Paragraph("• Recommend registering the new charge within 30 days of disbursement per SARFAESI Act.", BODY))
    els.append(Spacer(1, 10))

    els.append(Paragraph("Pending Real Inputs", BOLD))
    els.append(Paragraph("• Actual CERSAI portal search printout with transaction ID", NOTE_STYLE))
    els.append(Paragraph("• Cross-reference with ROC charge register", NOTE_STYLE))

    _build_pdf(dest / "synthetic_cersai_search.pdf", els)


# ─── Insurance Policies ─────────────────────────────────────────────────────

def gen_insurance_policies(entity_id: str, info: dict, dest: Path):
    els = _header("Insurance Policies Summary", entity_id, info["name"],
                  "Borrower / Insurance broker / Risk management team")

    els.append(Paragraph("Current Insurance Coverage", BOLD))
    els.append(_table([
        ["Policy Type", "Insurer", "Sum Insured (₹ Cr)", "Validity", "Status"],
        ["Property All Risk", "New India Assurance", "150.00", f"01-Apr-2025 to 31-Mar-2026", "Active"],
        ["Stock / Inventory", "ICICI Lombard", "75.00", f"01-Apr-2025 to 31-Mar-2026", "Active"],
        ["Key Man Insurance", "HDFC Life", "25.00", f"01-Apr-2025 to 31-Mar-2026", "Active"],
        ["Fire & Allied Perils", "United India Insurance", "200.00", f"01-Apr-2025 to 31-Mar-2026", "Active"],
        ["Public Liability", "Bajaj Allianz", "10.00", f"01-Apr-2025 to 31-Mar-2026", "Active"],
    ], col_widths=[100, 100, 80, 120, 60]))
    els.append(Spacer(1, 14))

    els.append(Paragraph("Adequacy Assessment", BOLD))
    els.append(Paragraph("• Total property coverage of ₹150 Cr appears adequate against proposed collateral value.", BODY))
    els.append(Paragraph("• Stock coverage of ₹75 Cr aligns with average inventory levels reported.", BODY))
    els.append(Paragraph("• Key Man Insurance covers the Managing Director / CEO — standard practice.", BODY))
    els.append(Paragraph("• Bank clause / lender's interest noted in property and stock policies.", BODY))
    els.append(Spacer(1, 10))

    els.append(Paragraph("Pending Real Inputs", BOLD))
    els.append(Paragraph("• Certified copies of all active insurance policies", NOTE_STYLE))
    els.append(Paragraph("• Confirmation of bank clause / lender interest endorsement", NOTE_STYLE))
    els.append(Paragraph("• Premium payment receipts for current year", NOTE_STYLE))

    _build_pdf(dest / "synthetic_insurance_policies.pdf", els)


# ─── Undertakings ────────────────────────────────────────────────────────────

def gen_undertakings(entity_id: str, info: dict, dest: Path):
    els = _header("Undertakings & Declarations", entity_id, info["name"],
                  "Borrower / Company Secretary / Legal team")

    els.append(Paragraph("Non-Default Declaration", BOLD))
    els.append(Paragraph(
        f"We, {info['name']}, hereby declare and confirm that as on {TODAY}:", BODY))
    els.append(Paragraph("• The company is not in default in repayment of any loan / credit facility availed from any bank / financial institution / NBFC.", BODY))
    els.append(Paragraph("• No proceedings under IBC / NCLT have been initiated against the company or its promoters.", BODY))
    els.append(Paragraph("• The company has not been classified as a wilful defaulter by any lender.", BODY))
    els.append(Paragraph("• All statutory dues including GST, TDS, PF, ESI are paid up to date.", BODY))
    els.append(Spacer(1, 14))

    els.append(Paragraph("Information Consent", BOLD))
    els.append(Paragraph(
        "The company hereby provides consent to the lender to:", BODY))
    els.append(Paragraph("• Obtain credit information from CIBIL, Equifax, Experian, CRIF High Mark, or any other credit bureau.", BODY))
    els.append(Paragraph("• Verify information provided in the loan application with any third party including RBI, SEBI, stock exchanges, ROC, income tax authorities.", BODY))
    els.append(Paragraph("• Share information with RBI or any other regulatory authority as required under applicable laws.", BODY))
    els.append(Spacer(1, 14))

    els.append(Paragraph("KYC End-Use Declaration", BOLD))
    els.append(Paragraph("• The credit facility, if sanctioned, shall be used exclusively for the stated purpose.", BODY))
    els.append(Paragraph("• No part of the facility shall be used for speculative purposes, capital market investment, or purposes prohibited under RBI guidelines.", BODY))
    els.append(Spacer(1, 10))

    els.append(Paragraph("Pending Real Inputs", BOLD))
    els.append(Paragraph("• Board-authorised signed undertaking on company letterhead", NOTE_STYLE))
    els.append(Paragraph("• Notarised information consent form", NOTE_STYLE))
    els.append(Paragraph("• Company Secretary certificate on non-default status", NOTE_STYLE))

    _build_pdf(dest / "synthetic_undertakings.pdf", els)


# ─── Board Resolution (Borrowing) ───────────────────────────────────────────

def gen_board_resolution(entity_id: str, info: dict, dest: Path):
    els = _header("Board Resolution — Borrowing Powers", entity_id, info["name"],
                  "Company Secretary / Legal team")

    els.append(Paragraph("Certified Extract of Board Resolution", BOLD))
    els.append(Paragraph(f"Meeting Date: {TODAY}", BODY))
    els.append(Paragraph("Quorum: Present as required under Articles of Association", BODY))
    els.append(Spacer(1, 10))

    els.append(Paragraph("RESOLVED THAT:", BOLD))
    els.append(Paragraph(
        f"Pursuant to Article [XX] of the Articles of Association of {info['name']} and "
        "Section 179 read with Section 180(1)(c) of the Companies Act, 2013, the Board hereby resolves to:", BODY))
    els.append(Paragraph("(a) Borrow moneys from time to time from banks / financial institutions up to an aggregate amount not exceeding the limits approved by shareholders in the General Meeting.", BODY))
    els.append(Paragraph("(b) Authorise the following persons to execute all documents, agreements, and security creation instruments on behalf of the company:", BODY))
    els.append(Spacer(1, 6))
    els.append(_table([
        ["Authorised Signatory", "Designation", "Scope"],
        ["[Director Name 1]", "Managing Director", "All loan documents and security instruments"],
        ["[Director Name 2]", "Whole-time Director", "All loan documents and security instruments"],
        ["[CS Name]", "Company Secretary", "Filing and compliance documentation"],
    ], col_widths=[160, 140, 200]))
    els.append(Spacer(1, 14))

    els.append(Paragraph("FURTHER RESOLVED THAT:", BOLD))
    els.append(Paragraph("The company agrees to create such security / charge over the assets of the company as may be required by the lending institution.", BODY))
    els.append(Spacer(1, 10))

    els.append(Paragraph("Pending Real Inputs", BOLD))
    els.append(Paragraph("• Certified true copy of board resolution on company letterhead", NOTE_STYLE))
    els.append(Paragraph("• Shareholders' resolution under Section 180(1)(c) if borrowing exceeds aggregate limits", NOTE_STYLE))
    els.append(Paragraph("• Specimen signatures of authorised signatories", NOTE_STYLE))

    _build_pdf(dest / "synthetic_board_resolution_borrowing.pdf", els)


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    generators = [
        gen_property_documents,
        gen_cersai_search,
        gen_insurance_policies,
        gen_undertakings,
        gen_board_resolution,
    ]

    for entity_id, info in ENTITIES.items():
        dest = ROOT / "synthetic-assets" / "optional_inputs" / entity_id
        for gen_fn in generators:
            gen_fn(entity_id, info, dest)
            print(f"  {entity_id}: {gen_fn.__name__.replace('gen_', '')}")

    # Also copy to test-documents consolidated folder
    for entity_id in ENTITIES:
        src = ROOT / "synthetic-assets" / "optional_inputs" / entity_id
        # Find matching test-documents folder
        td = ROOT / "test-documents"
        if td.exists():
            for folder in td.iterdir():
                if folder.is_dir() and folder.name.startswith(entity_id):
                    opt_dir = folder / "optional-inputs"
                    opt_dir.mkdir(parents=True, exist_ok=True)
                    import shutil
                    for pdf in src.glob("*.pdf"):
                        shutil.copy2(pdf, opt_dir / pdf.name)
                    print(f"  Copied to test-documents/{folder.name}/optional-inputs/")

    print("\nDone — 5 new synthetic PDF types × 5 entities = 25 files generated")


if __name__ == "__main__":
    main()
