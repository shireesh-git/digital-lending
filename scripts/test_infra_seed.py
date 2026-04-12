"""Quick local test to verify infra_metrics flows through company_catalog seed"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.company_catalog import seed_company_store

store = seed_company_store()

pncr = store.get("PNCR001", {})
im = pncr.get("infra_metrics")

if im:
    print(f"PASS: PNCR001 infra_metrics present with {len(im)} keys")
    print(f"  Keys: {list(im.keys())}")
    print(f"  book_to_bill_ratio: {im.get('book_to_bill_ratio')}")
    print(f"  toll_revenue_cr: {im.get('toll_revenue_cr')}")
else:
    print("FAIL: PNCR001 infra_metrics NOT found in seeded store")
    sys.exit(1)
