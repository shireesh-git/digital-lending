"""Quick check of pipeline results for all 4 companies."""
import requests

BASE = "http://localhost:8001"

# Set template mode first
requests.put(f"{BASE}/api/llm/active", json={"narrative_mode": "template"})

# Run pipeline for all 4 companies
print("Running pipelines...")
for eid in ["BMFG001", "PINF001", "SPHR001", "OLOG001"]:
    r = requests.post(f"{BASE}/api/cases/{eid}/run", timeout=300)
    print(f"  {eid}: {r.status_code}")

print("\nResults:")
for eid in ["BMFG001", "PINF001", "SPHR001", "OLOG001"]:
    r = requests.get(f"{BASE}/api/cases/{eid}")
    d = r.json()
    rec = d.get("recommendation", "N/A")
    rg = d.get("risk_grade", "N/A")
    score = d.get("composite_score", 0)
    cam_len = len(d.get("cam_text", ""))
    mode = d.get("narrative_mode", "N/A")
    fp_keys = len(d.get("fact_pack", {}).keys())
    print(f"  {eid}: rec={rec}, grade={rg}, score={score:.1f}, cam={cam_len:,} chars, mode={mode}, fp_keys={fp_keys}")

# Also check 360 view data richness
print("\n360 View check:")
for eid in ["BMFG001", "PINF001"]:
    r = requests.get(f"{BASE}/api/companies/{eid}/360")
    d = r.json()
    sections = list(d.keys())
    print(f"  {eid}: {len(sections)} sections — {', '.join(sections[:10])}")

# Check one pager
print("\nOne pager check:")
r = requests.get(f"{BASE}/api/cases/BMFG001/one-pager")
print(f"  BMFG001 one-pager: {r.status_code}, {len(r.text):,} chars")
