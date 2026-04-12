"""End-to-end test for CAM Intelligence Platform — All APIs & Pipeline"""
import requests
import json
import os
import sys
import time

if "pytest" in sys.modules:
    import pytest

    pytest.skip(
        "Legacy standalone smoke script; run directly with python instead of pytest.",
        allow_module_level=True,
    )

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE = os.environ.get("CAM_E2E_BASE", "http://localhost:8001")
PASS = 0
FAIL = 0
ERRORS = []

# Test data constants
CIN = "L29100MH2008PLC185432"
PAN = "AABCB1234F"
GSTIN = "27AABCB1234F1Z5"
ENTITY_ID = "BMFG001"


def assert_key(d, key):
    if key not in d:
        raise AssertionError(f"Missing key: {key}")

def check_cam_length(d, eid):
    text = d.get("cam_text", "")
    length = len(text)
    if length < 5000:
        raise AssertionError(f"CAM text too short for {eid}: {length} chars (expected 5000+)")
    print(f"         CAM length for {eid}: {length:,} chars")


def test(name, method, url, expected_status=200, json_body=None, check_fn=None, timeout=60):
    global PASS, FAIL
    try:
        if method == "GET":
            r = requests.get(url, timeout=timeout)
        elif method == "POST":
            r = requests.post(url, json=json_body, timeout=timeout)
        elif method == "PUT":
            r = requests.put(url, json=json_body, timeout=timeout)
        else:
            r = requests.request(method, url, json=json_body, timeout=timeout)

        if r.status_code == expected_status:
            if check_fn:
                try:
                    data = r.json()
                    check_fn(data)
                    PASS += 1
                    print(f"  PASS  {name}")
                except Exception as e:
                    FAIL += 1
                    ERRORS.append(f"{name}: check failed — {e}")
                    print(f"  FAIL  {name} — {e}")
            else:
                PASS += 1
                print(f"  PASS  {name}")
        else:
            FAIL += 1
            detail = ""
            try:
                detail = r.json().get("detail", "")[:100]
            except Exception:
                detail = r.text[:100]
            ERRORS.append(f"{name}: status={r.status_code}, detail={detail}")
            print(f"  FAIL  {name} — status={r.status_code} {detail}")
    except Exception as e:
        FAIL += 1
        ERRORS.append(f"{name}: EXCEPTION — {e}")
        print(f"  FAIL  {name} — EXCEPTION: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# 0. SET NARRATIVE MODE TO TEMPLATE (avoid LLM timeout)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 0. Config Setup ═══")
test("Set Narrative=template", "PUT", f"{BASE}/api/llm/active",
     json_body={"narrative_mode": "template"},
     check_fn=lambda d: assert_key(d, "narrative_mode"))

# ═══════════════════════════════════════════════════════════════════════════════
# 1. COMPANY ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 1. Company Endpoints ═══")
test("GET /api/companies", "GET", f"{BASE}/api/companies",
     check_fn=lambda d: assert_key(d, "companies"))

# ═══════════════════════════════════════════════════════════════════════════════
# 2. EXTERNAL DATA APIS (16 endpoints)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 2. External Data APIs ═══")
test("MCA Master (CIN)", "GET", f"{BASE}/api/external/mca/company/{CIN}",
     check_fn=lambda d: assert_key(d, "payload"))
test("MCA Directors (CIN)", "GET", f"{BASE}/api/external/mca/directors/{CIN}",
     check_fn=lambda d: assert_key(d, "payload"))
test("MCA Charges (CIN)", "GET", f"{BASE}/api/external/mca/charges/{CIN}",
     check_fn=lambda d: assert_key(d, "payload"))
test("GSTIN Details", "GET", f"{BASE}/api/external/gstin/{GSTIN}",
     check_fn=lambda d: assert_key(d, "payload"))
test("GST Turnover (PAN)", "GET", f"{BASE}/api/external/gst-turnover/{PAN}",
     check_fn=lambda d: assert_key(d, "payload"))
test("Bureau (PAN)", "GET", f"{BASE}/api/external/bureau/{PAN}",
     check_fn=lambda d: assert_key(d, "payload"))
test("Rating Action", "GET", f"{BASE}/api/external/rating/{ENTITY_ID}",
     check_fn=lambda d: assert_key(d, "payload"))
test("Market Intel", "GET", f"{BASE}/api/external/market/{ENTITY_ID}",
     check_fn=lambda d: assert_key(d, "payload"))
test("CRILC (PAN)", "GET", f"{BASE}/api/external/crilc/{PAN}",
     check_fn=lambda d: assert_key(d, "payload"))
test("CRILC PDF (PAN)", "GET", f"{BASE}/api/external/crilc/{PAN}/pdf")
test("EPFO (PAN)", "GET", f"{BASE}/api/external/epfo/{PAN}",
     check_fn=lambda d: assert_key(d, "payload"))
test("ITR (PAN)", "GET", f"{BASE}/api/external/itr/{PAN}",
     check_fn=lambda d: assert_key(d, "payload"))
test("Exchange Financials", "GET", f"{BASE}/api/external/exchange/financial-results/{ENTITY_ID}",
     check_fn=lambda d: assert_key(d, "payload"))
test("Exchange Governance", "GET", f"{BASE}/api/external/exchange/governance/{ENTITY_ID}",
     check_fn=lambda d: assert_key(d, "payload"))
test("Social Reputation", "GET", f"{BASE}/api/external/social/reputation/{ENTITY_ID}",
     check_fn=lambda d: assert_key(d, "payload"))
test("Web Crawl", "GET", f"{BASE}/api/external/web-crawl/{ENTITY_ID}",
     check_fn=lambda d: assert_key(d, "articles"))

# ═══════════════════════════════════════════════════════════════════════════════
# 3. ONBOARDING (ETB + NTB)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 3. Onboarding ═══")
# CIN Lookup is a POST
test("CIN Lookup", "POST", f"{BASE}/api/onboard/cin-lookup",
     json_body={"cin": CIN},
     check_fn=lambda d: assert_key(d, "company_name"))

# Onboard uses 'identifier' field, not 'cin'
test("Onboard NTB (new company)", "POST", f"{BASE}/api/onboard",
     json_body={
         "identifier": PAN,
         "case_type": "NTB",
         "facility_type": "WORKING_CAPITAL",
         "amount_requested_cr": 100.0,
         "purpose": "Working capital augmentation",
         "tenor_months": 12
     },
     check_fn=lambda d: assert_key(d, "entity_id"))

# ═══════════════════════════════════════════════════════════════════════════════
# 4. PIPELINE RUN (4 main companies)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 4. Pipeline Run ═══")
test_companies = ["BMFG001", "INFY001", "APOL001", "MRF001"]
for eid in test_companies:
    test(f"Pipeline {eid}", "POST", f"{BASE}/api/cases/{eid}/run",
         check_fn=lambda d: assert_key(d, "recommendation"),
         timeout=300)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. CASE RESULTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 5. Case Results ═══")
for eid in test_companies:
    test(f"Case Result {eid}", "GET", f"{BASE}/api/cases/{eid}",
         check_fn=lambda d: assert_key(d, "cam_text"))
    test(f"CAM Text {eid}", "GET", f"{BASE}/api/cases/{eid}/cam",
         check_fn=lambda d: check_cam_length(d, eid))

# ═══════════════════════════════════════════════════════════════════════════════
# 6. CAM PDF
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 6. CAM PDF ═══")
for eid in test_companies:
    test(f"CAM PDF {eid}", "GET", f"{BASE}/api/cases/{eid}/cam-pdf")

# ═══════════════════════════════════════════════════════════════════════════════
# 7. CUSTOMER 360
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 7. Customer 360 ═══")
for eid in test_companies:
    test(f"360 View {eid}", "GET", f"{BASE}/api/companies/{eid}/360",
         check_fn=lambda d: assert_key(d, "entity_id"))

# ═══════════════════════════════════════════════════════════════════════════════
# 8. ONE PAGER
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 8. One Pager ═══")
test("One Pager BMFG001", "GET", f"{BASE}/api/cases/BMFG001/one-pager")

# ═══════════════════════════════════════════════════════════════════════════════
# 9. HIERARCHY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 9. Corporate Hierarchy ═══")
test("Hierarchy BMFG001", "GET", f"{BASE}/api/companies/BMFG001/hierarchy",
     check_fn=lambda d: assert_key(d, "entity_id"))

# ═══════════════════════════════════════════════════════════════════════════════
# 10. FRAUD DETECTION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 10. Fraud Detection ═══")
test("Fraud Scan BMFG001", "POST", f"{BASE}/api/companies/BMFG001/fraud-analysis")

# ═══════════════════════════════════════════════════════════════════════════════
# 11. CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
print("\n═══ 11. Config ═══")
test("GET Config", "GET", f"{BASE}/api/config")
test("GET Engines", "GET", f"{BASE}/api/engines")
test("GET Agents", "GET", f"{BASE}/api/agents")

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS+FAIL} tests")
if ERRORS:
    print(f"\nFailed tests:")
    for e in ERRORS:
        print(f"  - {e}")
print(f"{'='*60}")
sys.exit(0 if FAIL == 0 else 1)
