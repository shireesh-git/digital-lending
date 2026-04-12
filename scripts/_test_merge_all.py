"""Smoke test: merge preserves all seed companies' data correctly."""
import sys
sys.path.insert(0, ".")

from src.data.company_catalog import seed_company_store
from src.api.main import _merge_overlay_company_data
from src.models.canonical_model import FinancialStatement, GroupEntity
from datetime import date

store = seed_company_store()

for eid, cd in store.items():
    fake = {
        "borrower": cd["borrower"],
        "group": GroupEntity(group_id=f"GRP_{eid}", group_name="Test",
                             parent_entity_id=eid, entities=[eid]),
        "directors": [],
        "financials": {},
        "facility": cd["facility"],
    }
    merged = _merge_overlay_company_data(cd, fake)
    fin = merged.get("financials", {})
    grp = merged.get("group")
    assert fin, f"{eid}: financials lost"
    # Group should always come from seed (not the stub 0.0 from fake enrichment)
    seed_grp = cd.get("group")
    if seed_grp:
        assert grp.promoter_holding_pct == seed_grp.promoter_holding_pct, (
            f"{eid}: promoter changed from {seed_grp.promoter_holding_pct} to {grp.promoter_holding_pct}"
        )
    latest = sorted(fin.keys())[-1]
    fs = fin[latest]
    rev = fs.line_items.get("revenue_operating", 0) if hasattr(fs, "line_items") else 0
    im = merged.get("infra_metrics", {})
    print(f"{eid}: rev={rev:,.0f} Cr, promoter={grp.promoter_holding_pct}%, infra={bool(im)}")

print(f"\nAll {len(store)} companies passed!")
