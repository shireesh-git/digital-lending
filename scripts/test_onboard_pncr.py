"""Quick test: onboard PNCR001 locally, verify docs + cache."""
import sys, os
sys.path.insert(0, ".")
os.environ.setdefault("CAM_ENV", "development")

from src.services.company_onboarding import onboard_company
from src.services.document_store import doc_store
from pathlib import Path

result = onboard_company("PNCR001")
print("=== ONBOARD RESULT ===")
print(f"Status: {result.get('status')}")
print(f"Entity: {result.get('entity_id')} - {result.get('company_name')}")
print(f"CIN: {result.get('cin')}")

eid = result.get("entity_id", "PNCR001")
docs = doc_store.list_company_documents(eid)
print(f"\n=== DOCUMENT STORE: {eid} ===")
cats = docs.get("categories", {})
total = 0
for cat, info in sorted(cats.items()):
    files = info.get("files", []) if isinstance(info, dict) else []
    if files:
        print(f"  {cat}/: {len(files)} files")
        for f in files[:5]:
            fn = f.get("name", f) if isinstance(f, dict) else f
            print(f"    - {fn}")
        total += len(files)
print(f"\nTotal: {total} documents across {len([c for c, i in cats.items() if (i.get('files') if isinstance(i, dict) else [])])} categories")

cache_dir = Path("storage/cache/probe42")
if cache_dir.exists():
    cache_files = list(cache_dir.glob("*.json"))
    print(f"\n=== PROBE CACHE ===")
    print(f"{len(cache_files)} cached bundles:")
    for f in cache_files[:10]:
        print(f"  - {f.name}")
else:
    print("\nNo probe cache directory found")
