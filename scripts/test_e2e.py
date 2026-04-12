"""End-to-end test of all new API endpoints."""
import requests
import sys

base = "http://localhost:8001/api"

def check(label, response, expected_status=200):
    ok = response.status_code == expected_status
    sym = "PASS" if ok else "FAIL"
    print(f"  [{sym}] {label} -> {response.status_code}")
    if not ok:
        print(f"        Body: {response.text[:300]}")
    return ok

passed = 0
failed = 0

def tally(ok):
    global passed, failed
    if ok:
        passed += 1
    else:
        failed += 1

print("=" * 60)
print("CAM Platform — E2E Test Suite")
print("=" * 60)

# 1. Health
print("\n--- Health ---")
r = requests.get(f"{base}/health")
tally(check("GET /health", r))
h = r.json()
print(f"  Companies: {h.get('companies')}, Cases: {h.get('cases_analysed')}")

# 2. Companies
print("\n--- Companies ---")
r = requests.get(f"{base}/companies")
tally(check("GET /companies", r))
cos = [c["entity_id"] for c in r.json().get("companies", [])]
print(f"  Entities: {cos}")

# 3. Extraction
print("\n--- Document Extraction (all 16) ---")
ALL_EIDS = ["BMFG001", "PINF001", "SPHR001", "OLOG001",
            "TSTL001", "REIL001", "INFY001", "ADPT001",
            "BJFN001", "CIPL001", "DLFR001", "JSWL001",
            "MRUT001", "TITN001", "NTPC001", "YESB001"]
for eid in ALL_EIDS:
    r = requests.post(f"{base}/companies/{eid}/extract")
    tally(check(f"POST /extract {eid}", r))
    if r.status_code == 200:
        print(f"    Documents: {r.json().get('document_count', 0)}")

# 4. Get extraction
print("\n--- Get Extraction ---")
r = requests.get(f"{base}/companies/BMFG001/extraction")
tally(check("GET /extraction BMFG001", r))
ext = r.json()
print(f"  Fin sources: {list(ext.get('financials', {}).keys())}")
print(f"  Rating: {ext.get('rating', {})}")
print(f"  GST: {ext.get('gst', {})}")

# PINF001 - should have mismatch data
r = requests.get(f"{base}/companies/PINF001/extraction")
tally(check("GET /extraction PINF001", r))
pext = r.json()
prov = pext.get("provisional", {})
print(f"  PINF001 provisional: {prov}")

# 5. ETB Analytics
print("\n--- ETB Analytics ---")
ETB_EIDS = ["OLOG001", "DLFR001", "NTPC001", "YESB001"]
for eid in ETB_EIDS:
    r = requests.post(f"{base}/companies/{eid}/etb-analytics")
    tally(check(f"POST /etb-analytics {eid}", r))
    if r.status_code == 200:
        d = r.json()
        print(f"    {eid}: composite={d.get('composite_score')}, grade={d.get('risk_grade')}")

for eid in ETB_EIDS:
    r = requests.get(f"{base}/companies/{eid}/etb-analytics")
    tally(check(f"GET /etb-analytics {eid}", r))
    etb = r.json()
    print(f"    {eid}: conduct={etb.get('conduct', {}).get('score')}, repayment={etb.get('repayment', {}).get('score')}, flags={len(etb.get('flags', []))}")

# ETB for non-ETB company should fail
r = requests.post(f"{base}/companies/BMFG001/etb-analytics")
tally(check("POST /etb-analytics BMFG001 (should 400)", r, 400))

# 6. Analyst Chat
print("\n--- Analyst Chat ---")
r = requests.post(f"{base}/chat/BMFG001", json={"message": "What is the revenue trend?"})
tally(check("POST /chat BMFG001", r))
resp_text = r.json().get("response", "N/A")
print(f"  Response type: {type(resp_text)}")
if isinstance(resp_text, str):
    print(f"  Response: {resp_text[:150]}")
else:
    print(f"  Response: {resp_text}")

r = requests.get(f"{base}/chat/BMFG001/history")
tally(check("GET /chat/history BMFG001", r))
print(f"  Messages: {len(r.json().get('messages', []))}")

r = requests.get(f"{base}/chat/sessions")
tally(check("GET /chat/sessions", r))
print(f"  Sessions: {r.json()}")

r = requests.delete(f"{base}/chat/BMFG001")
tally(check("DELETE /chat BMFG001", r))

# 7. Run Pipeline (all 16 companies)
print("\n--- Pipeline (all 16 companies) ---")
for eid in ALL_EIDS:
    r = requests.post(f"{base}/cases/{eid}/run")
    tally(check(f"POST /run {eid}", r))
    if r.status_code == 200:
        d = r.json()
        print(f"    {eid}: {d.get('recommendation')} / {d.get('risk_grade')} / {d.get('composite_score')}")

# 8. Verify fact pack has new sections
print("\n--- Fact Pack Verification ---")
r = requests.get(f"{base}/cases/BMFG001")
tally(check("GET /cases/BMFG001", r))
fp = r.json().get("fact_pack", {})
has_doc_ext = "document_extraction" in fp
has_etb = "etb_behavioral_analytics" in fp
print(f"  document_extraction in fact_pack: {has_doc_ext}")
print(f"  etb_behavioral_analytics in fact_pack: {has_etb}")

# Check OLOG001 has ETB data
r = requests.get(f"{base}/cases/OLOG001")
fp2 = r.json().get("fact_pack", {})
etb_fp = fp2.get("etb_behavioral_analytics", {})
print(f"  OLOG001 ETB in fact_pack: {bool(etb_fp)}")

# 9. Dashboard
print("\n--- Dashboard ---")
r = requests.get(f"{base}/dashboard")
tally(check("GET /dashboard", r))
d = r.json()
print(f"  Total cases: {d['metrics']['total_cases']}, Approved: {d['metrics']['approved']}")

# 10. Documents list
print("\n--- Document Management ---")
for eid in ALL_EIDS:
    r = requests.get(f"{base}/companies/{eid}/documents")
    tally(check(f"GET /documents {eid}", r))
    cats = r.json().get("categories", {})
    total_docs = sum(len(v.get("files", [])) for v in cats.values())
    print(f"    {eid}: {total_docs} files")

# 11. Fraud Detection (all 16)
print("\n--- Fraud Detection (all 16) ---")
for eid in ALL_EIDS:
    r = requests.post(f"{base}/companies/{eid}/fraud-analysis")
    tally(check(f"POST /fraud-analysis {eid}", r))
    if r.status_code == 200:
        d = r.json()
        print(f"    {eid}: score={d.get('composite_score')}, grade={d.get('risk_grade')}, flags={len(d.get('flags', []))}")

# Verify cached fraud results
for eid in ["BMFG001", "YESB001", "DLFR001"]:
    r = requests.get(f"{base}/companies/{eid}/fraud-analysis")
    tally(check(f"GET /fraud-analysis {eid}", r))

# 12. OCR
print("\n--- OCR & Document Intelligence ---")
r = requests.get(f"{base}/companies/BMFG001/documents")
if r.status_code == 200:
    cats = r.json().get("categories", {})
    # Find a PDF to test OCR on
    for cat, info in cats.items():
        files = info.get("files", [])
        pdfs = [f for f in files if f.endswith(".pdf")]
        if pdfs:
            fname = pdfs[0]
            r2 = requests.post(f"{base}/companies/BMFG001/ocr/{cat}/{fname}")
            tally(check(f"POST /ocr BMFG001/{cat}/{fname}", r2))
            if r2.status_code == 200:
                print(f"    Strategy: {r2.json().get('extraction_strategy')}, Chars: {r2.json().get('total_chars')}")
            r3 = requests.post(f"{base}/companies/BMFG001/ocr-metadata/{cat}/{fname}")
            tally(check(f"POST /ocr-metadata BMFG001/{cat}/{fname}", r3))
            if r3.status_code == 200:
                print(f"    Risk: {r3.json().get('risk_score')}, Anomalies: {r3.json().get('anomalies')}")
            break

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed out of {passed+failed}")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
