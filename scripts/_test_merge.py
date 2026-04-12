"""Test that _merge_overlay_company_data preserves seed data."""
import sys; sys.path.insert(0, ".")
from src.data.company_catalog import seed_company_store
from src.api.main import _merge_overlay_company_data

store = seed_company_store()
seed = store["PNCR001"]

# Simulate probe enrichment with minimal financials (like probe result)
probe_data = {"borrower": seed["borrower"], "financials": {}, "group": None}
merged = _merge_overlay_company_data(seed, probe_data)

fins = merged.get("financials", {})
fy25 = fins.get("FY2025")
rev = fy25.line_items.get("revenue_operating") if fy25 else 0
grp = merged.get("group")
prom = grp.promoter_holding_pct if grp else 0
im = merged.get("infra_metrics", {})
sk = merged.get("sector_kpis", {})

print(f"Revenue: {rev} Cr")
print(f"Promoter: {prom}%")
print(f"infra_metrics: {bool(im)}")
print(f"sector_kpis: {bool(sk)}")
print(f"sector_type: {sk.get('sector_type', 'N/A')}")
