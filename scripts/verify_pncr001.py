"""Verify PNCR001 data completeness."""
from src.data.real_companies import REAL_COMPANIES
from src.services.document_store import doc_store
import os

r = REAL_COMPANIES["PNCR001"]

print("=" * 60)
print("PNCR001 DATA COMPLETENESS CHECK")
print("=" * 60)

# 1. Financials
print("\n--- FINANCIALS ---")
for k, fin in r["financials"].items():
    items = fin.line_items
    rev = items.get("revenue_operating", "MISSING")
    ebitda = items.get("ebitda", "MISSING")
    pat = items.get("pat", "MISSING")
    debt = items.get("total_debt", "MISSING")
    nw = items.get("net_worth", "MISSING")
    print(f"  {k}: revenue={rev}, ebitda={ebitda}, pat={pat}, debt={debt}, nw={nw}")

# 2. Provisional
p = r["provisional"]
pitems = p.line_items
print(f"\n  Provisional {p.period}:")
for label, val in pitems.items():
    print(f"    {label}: {val}")

# 3. Directors
print("\n--- DIRECTORS ---")
for d in r["directors"]:
    print(f"  {d.name} | DIN={d.din} | {d.designation} | promoter={d.is_promoter}")

# 4. Collateral
print("\n--- COLLATERAL ---")
for c in r["collateral"]:
    print(f"  {c.collateral_type}: {c.description}")
    print(f"    MV={c.market_value_cr} Cr | FSV={c.forced_sale_value_cr} Cr")

# 5. Market signals
print("\n--- MARKET SIGNALS ---")
for m in r["market_signals"]:
    print(f"  [{m.signal_type}] {m.headline} | sentiment={m.sentiment}")

# 6. Exchange filing
print("\n--- EXCHANGE FILING ---")
ef = r.get("exchange_filing")
if ef:
    print(f"  period={ef.period}, revenue={ef.revenue_cr} Cr")
else:
    print("  None")

# 7. Existing exposure
print("\n--- EXISTING EXPOSURE ---")
for e in r.get("existing_exposure", []):
    print(f"  {e.facility_type}: sanctioned={e.sanctioned_limit_cr}, outstanding={e.outstanding_cr}")

# 8. Group
g = r.get("group")
if g:
    print(f"\n--- GROUP ---")
    print(f"  {g.group_name} | entities: {g.entities}")

# 9. Documents in storage
print("\n--- DOCUMENT STORE ---")
doc_path = doc_store.root / "PNCR001"
if doc_path.exists():
    for root, dirs, files in os.walk(doc_path):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), doc_path)
            print(f"  {rel}")
else:
    print("  NO document folder exists for PNCR001")

# 10. Test documents
print("\n--- TEST DOCUMENTS ---")
test_path = os.path.join("test-documents")
pncr_dirs = [d for d in os.listdir(test_path) if "PNCR" in d or "PNC" in d] if os.path.exists(test_path) else []
if pncr_dirs:
    for d in pncr_dirs:
        print(f"  {d}/")
else:
    print("  NO test documents folder for PNCR001")

# 11. Check data_provider in catalog
print("\n--- CATALOG CONFIG ---")
from src.data.company_catalog import CATALOG_COMPANIES
for c in CATALOG_COMPANIES:
    if c["entity_id"] == "PNCR001":
        print(f"  sector: {c['sector']}")
        print(f"  case_type: {c['case_type']}")
        print(f"  facility_type: {c['facility_type']}")
        print(f"  default_amount_cr: {c['default_amount_cr']}")
        break

# 12. Check what the seeded store looks like
print("\n--- SEEDED STORE CHECK ---")
from src.data.company_catalog import seed_company_store
store = seed_company_store()
pncr = store.get("PNCR001", {})
print(f"  data_provider: {pncr.get('data_provider')}")
print(f"  catalog_source: {pncr.get('catalog_source')}")
print(f"  financials keys: {list(pncr.get('financials', {}).keys())}")
print(f"  directors count: {len(pncr.get('directors', []))}")
print(f"  collateral count: {len(pncr.get('collateral', []))}")
print(f"  market signals: {len(pncr.get('market_signals', []))}")

# 13. Verify borrower in seeded store
b = pncr.get("borrower")
if b:
    print(f"  borrower.cin: {b.cin}")
    print(f"  borrower.subsector: {b.subsector}")
    print(f"  borrower.credit_rating: {b.credit_rating}")
else:
    print("  BORROWER NOT FOUND in seeded store!")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
