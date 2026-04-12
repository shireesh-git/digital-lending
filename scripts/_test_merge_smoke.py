"""Quick smoke test: merge doesn't break non-PNCR companies."""
import sys
sys.path.insert(0, ".")

from src.data.company_catalog import seed_company_store
from src.api.main import _merge_overlay_company_data
from src.models.canonical_model import FinancialStatement, GroupEntity
from datetime import date

store = seed_company_store()
test_ids = ["TSTL001", "INFY001", "ADPT001", "BJFN001", "REIL001"]

for eid in test_ids:
    cd = store.get(eid)
    if not cd:
        continue
    # Simulate empty enrichment
    fake = {
        "borrower": cd["borrower"],
        "group": GroupEntity(group_id=f"GRP_{eid}", group_name="Test", parent_entity_id=eid, entities=[eid]),
        "directors": [],
        "financials": {},
        "facility": cd["facility"],
    }
    merged = _merge_overlay_company_data(cd, fake)
    fin = merged.get("financials", {})
    grp = merged.get("group")
    assert fin, f"{eid}: financials lost"
    assert grp.promoter_holding_pct > 0, f"{eid}: group promoter lost ({grp.promoter_holding_pct})"
    latest = sorted(fin.keys())[-1]
    fs = fin[latest]
    rev = fs.line_items.get("revenue_operating", 0) if hasattr(fs, "line_items") else 0
    print(f"{eid}: OK — {latest} rev={rev} Cr, promoter={grp.promoter_holding_pct}%")

print("\nAll companies passed smoke test!")
