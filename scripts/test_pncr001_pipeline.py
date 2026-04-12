"""Quick pipeline test for PNCR001."""
import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.company_catalog import seed_company_store
company_store = seed_company_store()

# Check company store
cd = company_store.get("PNCR001")
if not cd:
    print("PNCR001 NOT in company_store!")
    sys.exit(1)

print("== Company Data Keys ==")
print(list(cd.keys()))

borrower = cd.get("borrower")
print(f"\n== Borrower ==")
print(f"  entity_id: {getattr(borrower, 'entity_id', 'N/A')}")
print(f"  company_name: {getattr(borrower, 'company_name', 'N/A')}")
print(f"  cin: {getattr(borrower, 'cin', 'N/A')}")
print(f"  pan: {getattr(borrower, 'pan', 'N/A')}")
print(f"  sector: {getattr(borrower, 'sector', 'N/A')}")
print(f"  subsector: {getattr(borrower, 'subsector', 'N/A')}")
print(f"  credit_rating: {getattr(borrower, 'credit_rating', 'N/A')}")

print(f"\n== data_provider: {cd.get('data_provider')}")
print(f"== seeded: {cd.get('seeded')}")

facility = cd.get("facility")
print(f"\n== Facility ==")
print(f"  case_type: {getattr(facility, 'case_type', 'N/A')}")
print(f"  facility_type: {getattr(facility, 'facility_type', 'N/A')}")
print(f"  amount_requested_cr: {getattr(facility, 'amount_requested_cr', 'N/A')}")
print(f"  purpose: {getattr(facility, 'purpose', 'N/A')}")
print(f"  tenor_months: {getattr(facility, 'tenor_months', 'N/A')}")

# Try the fact builder
print("\n\n== Testing Fact Builder ==")
try:
    from src.engines.cam_fact_builder import build_cam_fact_pack
    facts = build_cam_fact_pack(cd)
    print(f"  Fact pack keys: {list(facts.keys())}")
    print(f"  borrower_name: {facts.get('borrower_name')}")
    print(f"  sector: {facts.get('sector')}")
    print(f"  subsector: {facts.get('subsector')}")
    print(f"  fin_years: {list(facts.get('financials', {}).keys())}")
    print(f"  benchmarks: {list(facts.get('benchmarks', {}).keys())[:5]}")
except Exception as e:
    print(f"  FACT BUILDER ERROR: {e}")
    traceback.print_exc()

# Try the CAM renderer
print("\n\n== Testing CAM Renderer ==")
try:
    from src.engines.cam_renderer_v2 import render_cam_markdown
    facts = build_cam_fact_pack(cd)
    md = render_cam_markdown(facts)
    print(f"  Rendered {len(md)} characters of markdown")
    # Show first 500 chars
    print(f"  Preview: {md[:500]}...")
except Exception as e:
    print(f"  CAM RENDERER ERROR: {e}")
    traceback.print_exc()

print("\n\n== DONE ==")
