from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.core.runtime_paths import SYNTHETIC_ROOT
from src.services.document_store import doc_store


OPTIONAL_INPUT_ROOT = SYNTHETIC_ROOT / "optional_inputs"

OPTIONAL_INPUT_SPECS: list[dict[str, str]] = [
    {
        "key": "site_visit_report",
        "title": "Site Visit Report",
        "category": "request",
        "filename": "synthetic_site_visit_report.pdf",
        "source_hint": "RM, branch team, or field visit partner",
        "description": "Branch visit notes, promoter meetings, and operating observations.",
    },
    {
        "key": "valuation_report",
        "title": "Valuation Report",
        "category": "collateral",
        "filename": "synthetic_valuation_report.pdf",
        "source_hint": "Empanelled valuer or collateral team",
        "description": "Security valuation, FSV assumptions, and collateral comfort.",
    },
    {
        "key": "bank_statements",
        "title": "Bank Statements",
        "category": "banking",
        "filename": "synthetic_bank_statements.pdf",
        "source_hint": "Borrower bank statements or internal CBS for ETB cases",
        "description": "Latest operating account conduct and cash flow validation.",
    },
    {
        "key": "financial_projections",
        "title": "Financial Projections",
        "category": "request",
        "filename": "synthetic_cma_projection.pdf",
        "source_hint": "Borrower CFO pack, CMA data, or RM projections sheet",
        "description": "CMA, projected cash flows, and repayment assumptions.",
    },
    {
        "key": "credit_facility_details",
        "title": "Credit Facility Details",
        "category": "banking",
        "filename": "synthetic_credit_facility_details.pdf",
        "source_hint": "Internal LMS, sanction tracker, or lender-wise exposure note",
        "description": "Existing sanctions, limits, and lender-wise exposure.",
    },
    {
        "key": "internal_credit_notes",
        "title": "Internal Credit Notes",
        "category": "misc",
        "filename": "synthetic_internal_credit_notes.pdf",
        "source_hint": "RM, analyst, branch credit desk, or sanction memo",
        "description": "RM or analyst notes that strengthen the approval narrative.",
    },
    {
        "key": "property_documents",
        "title": "Property Documents",
        "category": "collateral",
        "filename": "synthetic_property_documents.pdf",
        "source_hint": "Collateral team / empanelled valuer / legal department",
        "description": "Title deed, search report, and encumbrance certificate for collateral properties.",
    },
    {
        "key": "cersai_search",
        "title": "CERSAI Search Report",
        "category": "legal",
        "filename": "synthetic_cersai_search.pdf",
        "source_hint": "Central Registry (CERSAI) / legal & compliance team",
        "description": "Central registry search for existing securitisation and security interests.",
    },
    {
        "key": "insurance_policies",
        "title": "Insurance Policies",
        "category": "collateral",
        "filename": "synthetic_insurance_policies.pdf",
        "source_hint": "Borrower / insurance broker / risk management team",
        "description": "Property, stock, and key man insurance coverage details.",
    },
    {
        "key": "undertakings",
        "title": "Undertakings & Declarations",
        "category": "legal",
        "filename": "synthetic_undertakings.pdf",
        "source_hint": "Borrower / Company Secretary / legal team",
        "description": "Non-default declaration, information consent, and end-use undertaking.",
    },
    {
        "key": "board_resolution_borrowing",
        "title": "Board Resolution — Borrowing",
        "category": "kyc",
        "filename": "synthetic_board_resolution_borrowing.pdf",
        "source_hint": "Company Secretary / legal team",
        "description": "Board resolution authorising borrowing powers and signatory details.",
    },
]


def _borrower_name(company_data: dict[str, Any], entity_id: str) -> str:
    borrower = company_data.get("borrower")
    return (
        getattr(borrower, "company_name", None)
        or company_data.get("company_name")
        or entity_id
    )


def _facility_amount(company_data: dict[str, Any]) -> float:
    facility = company_data.get("facility")
    amount = getattr(facility, "amount_requested_cr", None)
    if amount is None:
        amount = company_data.get("default_amount_cr") or 0.0
    try:
        return float(amount or 0.0)
    except Exception:
        return 0.0


def _facility_type(company_data: dict[str, Any]) -> str:
    facility = company_data.get("facility")
    raw = getattr(facility, "facility_type", None)
    return getattr(raw, "value", None) or str(raw or "working_capital")


def _sector_value(company_data: dict[str, Any]) -> str:
    borrower = company_data.get("borrower")
    raw = getattr(borrower, "sector", None)
    return getattr(raw, "value", None) or str(raw or "general")


def _currency(value: float) -> str:
    return f"{value:,.2f}"


def _pdf_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SyntheticTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f3d73"),
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "SyntheticSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#5f6f84"),
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "SyntheticSection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0f3d73"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "SyntheticBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceAfter=4,
        ),
        "note": ParagraphStyle(
            "SyntheticNote",
            parent=styles["BodyText"],
            fontName="Helvetica-Oblique",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#6b7280"),
            spaceAfter=8,
        ),
    }


def _table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fa")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f3d73")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d6e0ec")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#334155")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])


def _make_pdf(title: str, company_name: str, entity_id: str, source_hint: str, sections: list[dict[str, Any]]) -> bytes:
    styles = _pdf_styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=16 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        bottomMargin=16 * mm,
    )
    story: list[Any] = [
        Paragraph(title, styles["title"]),
        Paragraph(
            f"Company: {company_name}<br/>Entity ID: {entity_id}<br/>Typical Source: {source_hint}",
            styles["subtitle"],
        ),
        Paragraph("Synthetic PDF generated for workflow continuity when the real source file is not yet available.", styles["note"]),
        Spacer(1, 2 * mm),
    ]

    for section in sections:
        story.append(Paragraph(section["heading"], styles["section"]))
        for text in section.get("paragraphs", []):
            story.append(Paragraph(text, styles["body"]))
        if section.get("bullets"):
            for bullet in section["bullets"]:
                story.append(Paragraph(f"- {bullet}", styles["body"]))
        table_rows = section.get("table_rows")
        if table_rows:
            story.append(Table(table_rows, repeatRows=1, style=_table_style()))
        story.append(Spacer(1, 2 * mm))

    doc.build(story)
    return buffer.getvalue()


def _site_visit_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    sector = _sector_value(company_data).replace("_", " ").title()
    visit_date = date.today() - timedelta(days=5)
    sections = [
        {
            "heading": "Visit Coverage",
            "paragraphs": [
                f"Visit date captured as {visit_date.isoformat()} for the operating unit review of {company_name}.",
                f"Sector orientation used for this synthetic note: {sector}.",
            ],
        },
        {
            "heading": "Site Observations",
            "bullets": [
                "Operating area appeared active during the walkthrough.",
                "Management was available for high-level business and cash-flow discussion.",
                "No obvious shutdown or idle-capacity issue was observed in the synthetic walkthrough.",
            ],
        },
        {
            "heading": "Pending Real Inputs",
            "bullets": [
                "Signed RM or field visit memorandum",
                "Photographs and location references",
                "Specific observations on promoter or management interaction",
            ],
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _valuation_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    amount = _facility_amount(company_data)
    market_value = max(amount * 1.65, 75.0)
    forced_sale_value = market_value * 0.68
    sections = [
        {
            "heading": "Indicative Security Summary",
            "table_rows": [
                ["Metric", "Value"],
                ["Requested facility (Cr)", _currency(amount)],
                ["Indicative market value (Cr)", _currency(market_value)],
                ["Indicative forced sale value (Cr)", _currency(forced_sale_value)],
                ["Cover to requested facility", f"{market_value / max(amount, 1):.2f}x"],
            ],
        },
        {
            "heading": "Valuation Notes",
            "bullets": [
                "Synthetic valuation summary created only for workflow continuity.",
                "Actual valuer certificate, charge ranking, and title comfort remain mandatory for final reliance.",
                "Security mix should be replaced with the empanelled valuer report before credit sign-off.",
            ],
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _bank_statements_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    amount = _facility_amount(company_data)
    base_balance = max(amount * 0.06, 18.0)
    rows = [["Month", "Avg Balance (Cr)", "Credits (Cr)", "Debits (Cr)", "Cheque Returns"]]
    for idx, month in enumerate(("Oct-25", "Nov-25", "Dec-25", "Jan-26", "Feb-26", "Mar-26")):
        avg_balance = base_balance + idx * 1.4
        credits = max(amount * 0.45, 60.0) + idx * 6
        debits = credits * 0.96
        rows.append([month, f"{avg_balance:.2f}", f"{credits:.2f}", f"{debits:.2f}", "0"])
    sections = [
        {
            "heading": "Synthetic Conduct Snapshot",
            "paragraphs": [
                "Use this PDF only until the real borrower bank statement set or ETB CBS extract is uploaded.",
            ],
            "table_rows": rows,
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _projection_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    amount = _facility_amount(company_data)
    annual_revenue = max(amount * 5.5, 350.0)
    rows = [
        ["Period", "Revenue (Cr)", "EBITDA (Cr)", "PAT (Cr)", "Operating Cash Flow (Cr)", "DSCR", "Current Ratio"],
        ["FY2026", f"{annual_revenue:.2f}", f"{annual_revenue * 0.21:.2f}", f"{annual_revenue * 0.14:.2f}", f"{annual_revenue * 0.17:.2f}", "1.48", "1.33"],
        ["FY2027", f"{annual_revenue * 1.09:.2f}", f"{annual_revenue * 0.23:.2f}", f"{annual_revenue * 0.15:.2f}", f"{annual_revenue * 0.18:.2f}", "1.56", "1.37"],
        ["FY2028", f"{annual_revenue * 1.18:.2f}", f"{annual_revenue * 0.25:.2f}", f"{annual_revenue * 0.17:.2f}", f"{annual_revenue * 0.20:.2f}", "1.64", "1.40"],
    ]
    sections = [
        {
            "heading": "Projection Table",
            "paragraphs": [
                "This synthetic projection should be replaced by the RM-approved CMA or borrower management forecast before final sign-off.",
            ],
            "table_rows": rows,
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _facility_details_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    amount = _facility_amount(company_data)
    facility_type = _facility_type(company_data).replace("_", " ").title()
    rows = [
        ["Lender", "Facility Type", "Sanctioned Limit (Cr)", "Outstanding (Cr)", "Security", "Remarks"],
        ["Lead Bank", facility_type, f"{max(amount * 0.70, 40.0):.2f}", f"{max(amount * 0.52, 28.0):.2f}", "Primary charge on current assets", "Synthetic line item"],
        ["Consortium Bank A", "Term Loan", f"{max(amount * 0.22, 18.0):.2f}", f"{max(amount * 0.16, 11.0):.2f}", "Pari passu charge", "Illustrative only"],
        ["Consortium Bank B", "Non-fund based", f"{max(amount * 0.18, 12.0):.2f}", f"{max(amount * 0.09, 6.0):.2f}", "Cash margin backed", "Illustrative only"],
    ]
    sections = [
        {
            "heading": "Existing Exposure Summary",
            "table_rows": rows,
        },
        {
            "heading": "Usage Note",
            "bullets": [
                "Replace this synthetic PDF with the real sanction tracker or lender-wise exposure memo before final review.",
            ],
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _internal_notes_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    amount = _facility_amount(company_data)
    facility_type = _facility_type(company_data).replace("_", " ").title()
    sections = [
        {
            "heading": "Analyst Summary",
            "paragraphs": [
                f"Requested facility: {facility_type}",
                f"Requested amount: INR {_currency(amount)} Cr",
                "Public-record baseline has been retrieved and latest borrower uploads should replace older public-period figures.",
            ],
        },
        {
            "heading": "Follow-up Before Final Approval",
            "bullets": [
                "Validate latest turnover trajectory against provisional or quarterly statements.",
                "Confirm lender-wise exposure and current sanction terms.",
                "Confirm security value and charge perfection before final recommendation wording.",
            ],
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _property_documents_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    amount = _facility_amount(company_data)
    market_value = max(amount * 1.65, 75.0)
    sections = [
        {
            "heading": "Title Deed Summary",
            "table_rows": [
                ["Property", "Type", "Area (sq.ft)", "Location", "Title Status"],
                ["Corporate Office Premises", "Commercial", "45,000", "Registered Address", "Clear — verified"],
                ["Industrial / Warehouse Unit", "Industrial", "1,20,000", "Operational site", "Clear — verified"],
            ],
        },
        {
            "heading": "Search Report Highlights",
            "bullets": [
                "Title search conducted for the last 30 years — no adverse claims or disputes found.",
                "No encumbrance certificate obtained from Sub-Registrar's office — property is free of encumbrances.",
                "Revenue records verification confirms owner details match company registration.",
            ],
        },
        {
            "heading": "Pending Real Inputs",
            "bullets": [
                "Original title deed copy with registration details",
                "Encumbrance certificate from Sub-Registrar",
                "Latest municipal tax receipts",
            ],
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _cersai_search_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    today = date.today().isoformat()
    sections = [
        {
            "heading": "Central Registry Search Result",
            "table_rows": [
                ["Parameter", "Details"],
                ["Entity Name", company_name],
                ["Search Type", "Company-wide asset search"],
                ["Search Date", today],
                ["Existing Charges Found", "Nil — No prior securitisation interest registered"],
                ["Mortgage Entries", "Nil"],
                ["Pledge Entries", "Nil"],
                ["Hypothecation Entries", "Nil"],
            ],
        },
        {
            "heading": "Observations",
            "bullets": [
                "No existing security interest registered with CERSAI against the borrower entity.",
                "The proposed security can be registered as a fresh charge without conflict.",
                "Recommend registering the new charge within 30 days of disbursement per SARFAESI Act.",
            ],
        },
        {
            "heading": "Pending Real Inputs",
            "bullets": [
                "Actual CERSAI portal search printout with transaction ID",
                "Cross-reference with ROC charge register",
            ],
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _insurance_policies_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    sections = [
        {
            "heading": "Current Insurance Coverage",
            "table_rows": [
                ["Policy Type", "Insurer", "Sum Insured (Cr)", "Validity", "Status"],
                ["Property All Risk", "New India Assurance", "150.00", "01-Apr-2025 to 31-Mar-2026", "Active"],
                ["Stock / Inventory", "ICICI Lombard", "75.00", "01-Apr-2025 to 31-Mar-2026", "Active"],
                ["Key Man Insurance", "HDFC Life", "25.00", "01-Apr-2025 to 31-Mar-2026", "Active"],
                ["Fire & Allied Perils", "United India Insurance", "200.00", "01-Apr-2025 to 31-Mar-2026", "Active"],
            ],
        },
        {
            "heading": "Adequacy Assessment",
            "bullets": [
                "Total property coverage appears adequate against proposed collateral value.",
                "Stock coverage aligns with average inventory levels reported.",
                "Key Man Insurance covers the Managing Director / CEO — standard practice.",
                "Bank clause / lender's interest noted in property and stock policies.",
            ],
        },
        {
            "heading": "Pending Real Inputs",
            "bullets": [
                "Certified copies of all active insurance policies",
                "Confirmation of bank clause / lender interest endorsement",
                "Premium payment receipts for current year",
            ],
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _undertakings_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    today = date.today().isoformat()
    sections = [
        {
            "heading": "Non-Default Declaration",
            "paragraphs": [
                f"We, {company_name}, hereby declare and confirm as on {today}:",
            ],
            "bullets": [
                "The company is not in default in repayment of any loan / credit facility.",
                "No proceedings under IBC / NCLT have been initiated against the company or its promoters.",
                "The company has not been classified as a wilful defaulter by any lender.",
                "All statutory dues including GST, TDS, PF, ESI are paid up to date.",
            ],
        },
        {
            "heading": "Information Consent",
            "bullets": [
                "Consent to obtain credit information from CIBIL, Equifax, Experian, CRIF High Mark.",
                "Consent to verify information with RBI, SEBI, stock exchanges, ROC, and income tax authorities.",
                "Consent to share information with regulators as required under applicable laws.",
            ],
        },
        {
            "heading": "Pending Real Inputs",
            "bullets": [
                "Board-authorised signed undertaking on company letterhead",
                "Notarised information consent form",
                "Company Secretary certificate on non-default status",
            ],
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _board_resolution_pdf(entity_id: str, company_data: dict[str, Any], spec: dict[str, str]) -> bytes:
    company_name = _borrower_name(company_data, entity_id)
    today = date.today().isoformat()
    facility_type = _facility_type(company_data).replace("_", " ").title()
    sections = [
        {
            "heading": "Certified Extract of Board Resolution",
            "paragraphs": [
                f"Meeting Date: {today}",
                "Quorum: Present as required under Articles of Association",
            ],
        },
        {
            "heading": "Resolution Content",
            "paragraphs": [
                f"RESOLVED THAT pursuant to Articles of Association of {company_name} and "
                "Section 179 read with Section 180(1)(c) of the Companies Act, 2013, the Board hereby resolves to:",
            ],
            "bullets": [
                f"Borrow moneys from banks / financial institutions for {facility_type} facility.",
                "Authorise designated signatories to execute all documents, agreements, and security creation instruments.",
                "Create such security / charge over assets as may be required by the lending institution.",
            ],
        },
        {
            "heading": "Pending Real Inputs",
            "bullets": [
                "Certified true copy of board resolution on company letterhead",
                "Shareholders' resolution under Section 180(1)(c) if borrowing exceeds aggregate limits",
                "Specimen signatures of authorised signatories",
            ],
        },
    ]
    return _make_pdf(spec["title"], company_name, entity_id, spec["source_hint"], sections)


def _content_for(spec: dict[str, str], entity_id: str, company_data: dict[str, Any]) -> bytes:
    builders = {
        "site_visit_report": _site_visit_pdf,
        "valuation_report": _valuation_pdf,
        "bank_statements": _bank_statements_pdf,
        "financial_projections": _projection_pdf,
        "credit_facility_details": _facility_details_pdf,
        "internal_credit_notes": _internal_notes_pdf,
        "property_documents": _property_documents_pdf,
        "cersai_search": _cersai_search_pdf,
        "insurance_policies": _insurance_policies_pdf,
        "undertakings": _undertakings_pdf,
        "board_resolution_borrowing": _board_resolution_pdf,
    }
    return builders[spec["key"]](entity_id, company_data, spec)


def _entry_for(entity_id: str, spec: dict[str, str], path: Path) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "key": spec["key"],
        "title": spec["title"],
        "category": spec["category"],
        "filename": spec["filename"],
        "description": spec["description"],
        "source_hint": spec["source_hint"],
        "available": path.exists(),
        "relative_path": str(path.relative_to(SYNTHETIC_ROOT)),
    }


def ensure_optional_input_pack(entity_id: str, company_data: dict[str, Any], replace_existing: bool = False) -> list[dict[str, Any]]:
    entity_dir = OPTIONAL_INPUT_ROOT / entity_id
    entity_dir.mkdir(parents=True, exist_ok=True)
    expected_names = {spec["filename"] for spec in OPTIONAL_INPUT_SPECS}
    for path in entity_dir.iterdir():
        if path.is_file() and path.name not in expected_names:
            path.unlink()

    entries: list[dict[str, Any]] = []
    for spec in OPTIONAL_INPUT_SPECS:
        target = entity_dir / spec["filename"]
        if replace_existing or not target.exists():
            target.write_bytes(_content_for(spec, entity_id, company_data))
        entries.append(_entry_for(entity_id, spec, target))
    return entries


def bootstrap_optional_input_packs(company_store: dict[str, dict[str, Any]], replace_existing: bool = False) -> dict[str, int]:
    summary: dict[str, int] = {}
    for entity_id, company_data in company_store.items():
        entries = ensure_optional_input_pack(entity_id, company_data, replace_existing=replace_existing)
        summary[entity_id] = len(entries)
    return summary


def list_optional_input_pack(entity_id: str, company_data: dict[str, Any]) -> list[dict[str, Any]]:
    return ensure_optional_input_pack(entity_id, company_data, replace_existing=False)


def import_optional_input(entity_id: str, company_data: dict[str, Any], input_key: str) -> dict[str, Any]:
    entries = ensure_optional_input_pack(entity_id, company_data, replace_existing=False)
    entry = next((item for item in entries if item["key"] == input_key), None)
    if not entry:
        raise KeyError(input_key)
    source_path = OPTIONAL_INPUT_ROOT / entity_id / entry["filename"]
    if not source_path.exists():
        raise FileNotFoundError(str(source_path))
    return doc_store.store_document(
        entity_id,
        entry["category"],
        entry["filename"],
        source_path.read_bytes(),
        source="synthetic_assets",
    )
