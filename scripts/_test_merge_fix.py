"""Test that _merge_overlay_company_data preserves seed data correctly."""
import sys
sys.path.insert(0, ".")

from src.data.company_catalog import seed_company_store
store = seed_company_store()
cd = store["PNCR001"]
fin = cd["financials"]
group = cd["group"]
im = cd.get("infra_metrics", {})

fy25 = fin.get("FY2025")
print(f"FY2025 revenue: {fy25.line_items['revenue_operating']} Cr")
print(f"FY2025 EBITDA: {fy25.line_items['ebitda']} Cr")
print(f"Periods: {sorted(fin.keys())}")
print(f"Group promoter_holding_pct: {group.promoter_holding_pct}")
print(f"infra_metrics keys: {list(im.keys()) if im else 'EMPTY'}")
print(f"order_book: {im.get('order_book', {}).get('total_order_book_cr', 'missing')}")
print()

# Simulate the merge
from src.api.main import _merge_overlay_company_data
from src.models.canonical_model import FinancialStatement, GroupEntity
from datetime import date

fake_enriched = {
    "borrower": cd["borrower"],
    "group": GroupEntity(group_id="GRP_PNCR", group_name="PNC Group",
                         parent_entity_id="PNCR001", entities=["PNCR001"],
                         promoter_holding_pct=0.0),
    "directors": [],
    "financials": {
        "FY2024": FinancialStatement(
            entity_id="PNCR001", period="FY2024",
            statement_type="standalone", source="auto_estimated",
            as_of_date=date(2024, 3, 31),
            line_items={"revenue_operating": 1000.0, "ebitda": 150.0}),
    },
    "facility": cd["facility"],
    "collateral": [],
    "market_signals": [],
    "existing_exposure": [],
    "conduct": [],
    "covenants": [],
}

merged = _merge_overlay_company_data(cd, fake_enriched)
m_fin = merged["financials"]
m_group = merged["group"]
m_im = merged.get("infra_metrics", {})

print("--- After merge ---")
latest = sorted(m_fin.keys())[-1]
fs = m_fin[latest]
if hasattr(fs, "line_items"):
    print(f"Latest period: {latest}")
    print(f"Revenue: {fs.line_items.get('revenue_operating')} Cr")
    print(f"EBITDA: {fs.line_items.get('ebitda')} Cr")
else:
    print(f"Financial type: {type(fs)}")
print(f"Group promoter: {m_group.promoter_holding_pct}%")
print(f"infra_metrics keys: {list(m_im.keys()) if m_im else 'EMPTY'}")
print(f"collateral count: {len(merged.get('collateral', []))}")
print(f"market_signals count: {len(merged.get('market_signals', []))}")
print(f"directors count: {len(merged.get('directors', []))}")

# Assertions
assert m_group.promoter_holding_pct == 56.07, f"Expected 56.07, got {m_group.promoter_holding_pct}"
assert fs.line_items.get("revenue_operating") == 8650.0, f"Expected 8650, got {fs.line_items.get('revenue_operating')}"
assert "order_book" in m_im, f"Expected order_book in infra_metrics, got {list(m_im.keys())}"
assert len(merged.get("collateral", [])) == 3, f"Expected 3 collateral, got {len(merged.get('collateral', []))}"
print("\nAll assertions passed!")
