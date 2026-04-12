"""
Generate document folder + synthetic data files for PNCR001 (PNC Roads & Infra Ltd).
Creates the same folder structure as other seeded companies.
"""
import json
import sys
from pathlib import Path
from datetime import date, datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.services.document_store import doc_store

ENTITY_ID = "PNCR001"
COMPANY = "PNC Roads & Infra Ltd"
CIN = "L45201DL1999PLC195937"
PAN = "AABCP1234R"
GSTIN = "09AABCP1234R1Z6"
NOW = datetime.utcnow().isoformat(timespec="seconds")

def _json(data: dict) -> bytes:
    return json.dumps(data, indent=2, default=str).encode("utf-8")

def _text(content: str) -> bytes:
    return content.encode("utf-8")

def main():
    doc_store.init_company_folder(ENTITY_ID)

    # ── MCA ──
    doc_store.store_document(ENTITY_ID, "mca", "mca_master_auto_fetch.json", _json({
        "source": "mca_v3",
        "entity_key": CIN,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "cin": CIN,
            "company_name": "PNC ROADS & INFRA LIMITED",
            "status": "Active",
            "date_of_incorporation": "2007-06-09",
            "registered_state": "Uttar Pradesh",
            "registered_office": "14th Floor, Vikas Deep Building, Lalbagh, Lucknow, Uttar Pradesh - 226001",
            "authorized_capital_inr": 1500000000,
            "paid_up_capital_inr": 513000000,
            "nic_code": "42101",
            "industrial_class": "Construction of roads and highways",
            "listed_exchange": "BSE/NSE",
            "company_category": "Company limited by Shares",
            "company_sub_category": "Non-govt company",
            "email": "info@pncroadsinfra.com",
        }
    }), source="synthetic_seed")

    doc_store.store_document(ENTITY_ID, "mca", "mca_directors_auto_fetch.json", _json({
        "source": "mca_v3",
        "entity_key": CIN,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "directors": [
                {"din": "00056994", "name": "YOGESH KUMAR JAIN", "designation": "Chairman & Managing Director", "date_of_appointment": "2007-06-09", "shareholding_pct": 45.2},
                {"din": "00057760", "name": "NAVEEN KUMAR JAIN", "designation": "Whole-time Director", "date_of_appointment": "2007-06-09", "shareholding_pct": 12.8},
                {"din": "07889421", "name": "CHANDRA PRAKASH JAIN", "designation": "Executive Director — Projects", "date_of_appointment": "2018-04-01", "shareholding_pct": 5.1},
                {"din": "08123456", "name": "RUCHI BISHT", "designation": "Independent Director", "date_of_appointment": "2020-09-15", "shareholding_pct": 0.0},
            ]
        }
    }), source="synthetic_seed")

    doc_store.store_document(ENTITY_ID, "mca", "mca_charges_auto_fetch.json", _json({
        "source": "mca_v3",
        "entity_key": CIN,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "charges": [
                {"charge_id": "CHG-001", "holder": "State Bank of India", "amount_cr": 2500.0, "date_created": "2022-03-15", "status": "Open", "assets": "Toll collection rights — Agra-Lucknow section"},
                {"charge_id": "CHG-002", "holder": "HDFC Bank", "amount_cr": 800.0, "date_created": "2023-07-20", "status": "Open", "assets": "Construction equipment fleet"},
            ]
        }
    }), source="synthetic_seed")

    # ── KYC ──
    doc_store.store_document(ENTITY_ID, "kyc", "probe42_kyc_details.json", _json({
        "source": "probe42",
        "entity_key": CIN,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "vitals": {
                "company_name": COMPANY,
                "cin": CIN,
                "pan_of_entity": PAN,
                "date_of_incorporation": "2007-06-09",
                "listing_status": "Listed",
                "paid_up_capital": 513000000,
                "authorized_capital": 1500000000,
                "website": "www.pncroadsinfra.com",
                "registered_address": {
                    "line1": "14th Floor, Vikas Deep Building",
                    "city": "Lucknow",
                    "state": "Uttar Pradesh",
                    "pin": "226001"
                }
            },
            "industry_segment": {
                "industry": "Road & Highway Construction — EPC",
                "segments": ["Infrastructure", "Construction", "EPC"]
            },
            "key_indicators": {
                "employee_count_range": "10001-15000"
            }
        }
    }), source="synthetic_seed")

    # ── Bureau ──
    doc_store.store_document(ENTITY_ID, "bureau", "bureau_auto_fetch.json", _json({
        "source": "bureau",
        "entity_key": PAN,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "credit_score": 742,
            "dpd_status": "Standard",
            "total_exposure_cr": 6282.0,
            "lender_count": 8,
            "suit_filed_amount_cr": 0.0,
            "wilful_defaulter_flag": False,
            "sma_status": "SMA-0"
        }
    }), source="synthetic_seed")

    # ── GST ──
    doc_store.store_document(ENTITY_ID, "gst", "gstin_auto_fetch.json", _json({
        "source": "gstin",
        "entity_key": GSTIN,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "gstin": GSTIN,
            "legal_name": "PNC ROADS & INFRA LIMITED",
            "trade_name": "PNC ROADS",
            "registration_date": "2017-07-01",
            "status": "Active",
            "type": "Regular",
            "state": "Uttar Pradesh",
            "constitution": "Public Limited Company",
            "nature_of_business": ["Construction", "Works Contract"]
        }
    }), source="synthetic_seed")

    doc_store.store_document(ENTITY_ID, "gst", "gst_turnover_auto_fetch.json", _json({
        "source": "gstin",
        "entity_key": PAN,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "fy2025_turnover_cr": 8650.0,
            "fy2024_turnover_cr": 7956.0,
            "fy2023_turnover_cr": 7208.0,
            "filing_status": "Filed on Time",
            "annual_returns_filed": True
        }
    }), source="synthetic_seed")

    # ── Ratings ──
    doc_store.store_document(ENTITY_ID, "ratings", "rating_auto_fetch.json", _json({
        "source": "rating_agency",
        "entity_key": ENTITY_ID,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "rating_agency": "CARE",
            "long_term_rating": "AA-",
            "short_term_rating": "A1+",
            "outlook": "Stable",
            "last_action": "Reaffirmed",
            "action_date": "2025-11-15",
            "rationale": "Strong order book at 3.2x revenue, healthy EBITDA margins, experienced promoter group with 17+ years track record in road EPC."
        }
    }), source="synthetic_seed")

    # ── Legal ──
    doc_store.store_document(ENTITY_ID, "legal", "probe42_legal_history.json", _json({
        "source": "probe42",
        "entity_key": CIN,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "total_cases": 3,
            "pending_cases": 1,
            "resolved_cases": 2,
            "cases": [
                {"case_type": "Civil", "court": "Lucknow High Court", "status": "Pending", "amount_cr": 12.5, "description": "Land acquisition dispute — NH-44 alignment"},
                {"case_type": "Arbitration", "court": "NHAI Arbitration Tribunal", "status": "Resolved", "amount_cr": 45.0, "description": "Cost escalation claim — Bundelkhand Expressway Phase-I"},
                {"case_type": "Civil", "court": "District Court Agra", "status": "Resolved", "amount_cr": 3.2, "description": "Subcontractor payment dispute"}
            ]
        }
    }), source="synthetic_seed")

    # ── Exchange ──
    doc_store.store_document(ENTITY_ID, "exchange", "nse_live_quote.json", _json({
        "source": "nse",
        "entity_key": ENTITY_ID,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "symbol": "PNCINFRA",
            "last_price": 485.60,
            "prev_close": 478.25,
            "change_pct": 1.54,
            "market_cap_cr": 12450.0,
            "pe_ratio": 13.7,
            "book_value": 118.5,
            "face_value": 2.0,
            "52w_high": 565.0,
            "52w_low": 310.0,
            "volume": 485620
        }
    }), source="synthetic_seed")

    # ── Financials (web-scraped summary) ──
    doc_store.store_document(ENTITY_ID, "financials", "web_scraped_financials.json", _json({
        "source": "screener_in",
        "entity_key": ENTITY_ID,
        "as_of_date": NOW,
        "source_status": "success",
        "payload": {
            "FY2025": {"revenue_cr": 8650.0, "ebitda_cr": 2004.0, "pat_cr": 909.0, "total_debt_cr": 8025.0, "equity_cr": 5180.0},
            "FY2024": {"revenue_cr": 7956.0, "ebitda_cr": 1585.0, "pat_cr": 658.0, "total_debt_cr": 6282.0, "equity_cr": 4350.0},
            "FY2023": {"revenue_cr": 7208.0, "ebitda_cr": 1489.0, "pat_cr": 580.0, "total_debt_cr": 4793.0, "equity_cr": 3820.0},
            "FY2022": {"revenue_cr": 5620.0, "ebitda_cr": 1166.0, "pat_cr": 442.0, "total_debt_cr": 3670.0, "equity_cr": 3280.0},
        }
    }), source="synthetic_seed")

    # ── Request ──
    doc_store.store_document(ENTITY_ID, "request", "request_note.txt", _text(f"""
═══════════════════════════════════════════════════════════════
  CREDIT FACILITY REQUEST — {COMPANY}
  Entity ID: {ENTITY_ID}
═══════════════════════════════════════════════════════════════

Date: {date.today().isoformat()}

Facility Type:    Term Loan
Amount Requested: ₹1,500 Crore
Tenor:            72 months
Purpose:          Execution of NHAI highway EPC projects —
                  4-laning of NH-44 (Agra-Lucknow section, 220 km) and
                  Bundelkhand Expressway Phase-II (145 km).
                  Funds for mobilization advance, equipment procurement
                  (pavers, batching plants, excavators), and
                  bridge/flyover sub-contracting.

Key Highlights:
  - Order book: ₹27,680 Cr (3.2x FY2025 revenue)
  - NHAI AAAA-rated company
  - AA-/Stable rated by CARE
  - Promoter holding: 63.1%
  - 17+ years track record in road EPC
═══════════════════════════════════════════════════════════════
"""), source="synthetic_seed")

    # ── Metadata ──
    categories = ["kyc", "financials", "bureau", "legal", "collateral", "ratings", "gst", "mca", "exchange", "request"]
    total = sum(1 for cat in categories for _ in (doc_store.root / ENTITY_ID / cat).glob("*") if _.is_file())
    metadata = {
        "entity_id": ENTITY_ID,
        "source": "synthetic_seed",
        "last_fetched": NOW,
        "total_documents": total,
        "categories": categories,
    }
    (doc_store.root / ENTITY_ID / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    print(f"Created document folder for {ENTITY_ID} with {total} documents")
    for cat in categories:
        cat_path = doc_store.root / ENTITY_ID / cat
        if cat_path.exists():
            files = list(cat_path.glob("*"))
            print(f"  {cat}/: {len(files)} files")
            for f in files:
                print(f"    - {f.name}")


if __name__ == "__main__":
    main()
