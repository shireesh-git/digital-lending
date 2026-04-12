"""End-to-end test script for CAM Intelligence Platform."""
import requests
import json
import sys

BASE = "http://localhost:8001"

def test_companies():
    print("=" * 60)
    print("TEST: /api/companies")
    r = requests.get(f"{BASE}/api/companies")
    assert r.status_code == 200
    data = r.json()
    companies = data["companies"]
    print(f"  Total companies: {len(companies)}")
    assert len(companies) == 16, f"Expected 16, got {len(companies)}"
    print("  PASS")

def test_executed_only_before():
    print("\nTEST: /api/companies?executed_only=true (before pipeline)")
    r = requests.get(f"{BASE}/api/companies", params={"executed_only": "true"})
    data = r.json()
    companies = data["companies"]
    # Filter only those with has_result=True
    executed = [c for c in companies if c.get("has_result")]
    print(f"  Executed companies: {len(executed)}")
    print("  PASS")

def test_pipeline(entity_id):
    print(f"\nTEST: Pipeline run for {entity_id}")
    r = requests.post(f"{BASE}/api/cases/{entity_id}/run")
    assert r.status_code == 200, f"Pipeline failed: {r.status_code} - {r.text[:200]}"
    data = r.json()
    risk_grade = data.get("risk_grade", "N/A")
    decision = data.get("recommendation", "N/A")
    composite = data.get("composite_score", 0)
    
    print(f"  Risk Grade: {risk_grade}")
    print(f"  Decision: {decision}")
    print(f"  Composite Score: {composite}")
    
    # Check agent timings from pipeline_log
    pipeline_log = data.get("pipeline_log", [])
    for entry in pipeline_log:
        print(f"  {entry.get('agent', '?')}: {entry.get('duration_sec', 0):.2f}s - {entry.get('status', '?')}")
    
    assert decision != "error", f"Pipeline produced error recommendation"
    print("  PASS")
    return data

def test_cam_text(entity_id):
    print(f"\nTEST: CAM text for {entity_id}")
    r = requests.get(f"{BASE}/api/cases/{entity_id}/cam")
    assert r.status_code == 200, f"CAM endpoint failed: {r.status_code}"
    data = r.json()
    cam_text = data.get("cam_text", "")
    print(f"  CAM length: {len(cam_text)} chars")
    assert len(cam_text) > 500, f"CAM too short: {len(cam_text)} chars"
    print("  PASS")

def test_executed_only_after():
    print("\nTEST: /api/companies?executed_only=true (after pipeline)")
    r = requests.get(f"{BASE}/api/companies", params={"executed_only": "true"})
    data = r.json()
    companies = data["companies"]
    executed = [c for c in companies if c.get("has_result")]
    print(f"  Executed companies: {len(executed)}")
    for c in executed:
        print(f"    {c['entity_id']}: {c['company_name']}")
    assert len(executed) >= 1, "Expected at least 1 executed company"
    print("  PASS")

def test_360_view(entity_id):
    print(f"\nTEST: /api/companies/{entity_id}/360")
    r = requests.get(f"{BASE}/api/companies/{entity_id}/360")
    assert r.status_code == 200, f"360 failed: {r.status_code} - {r.text[:200]}"
    data = r.json()
    
    keys = sorted(data.keys())
    print(f"  360 keys: {keys}")
    
    # Check for new fields added this session
    for field in ["banking_exposure", "etb_conduct", "collateral"]:
        present = field in data
        print(f"  {field}: {'Present' if present else 'MISSING'}")
    print("  PASS")

def test_new_external_endpoints(entity_id):
    print(f"\nTEST: New external endpoints for {entity_id}")
    
    endpoints = [
        f"/api/external/exchange/financial-results/{entity_id}",
        f"/api/external/exchange/governance/{entity_id}",
        f"/api/external/social/reputation/{entity_id}",
    ]
    
    for ep in endpoints:
        r = requests.get(f"{BASE}{ep}")
        print(f"  {ep}: {r.status_code}")
        assert r.status_code == 200, f"Failed: {ep}"
    print("  PASS")

def test_existing_external_endpoints(entity_id):
    print(f"\nTEST: Existing external endpoints for {entity_id}")
    cin = "U28920MH2019PLC123456"
    pan = "AABCB1234A"
    gstin = "27AABCB1234A1Z5"
    
    endpoints = [
        f"/api/external/mca/company/{cin}",
        f"/api/external/bureau/{pan}",
        f"/api/external/gstin/{gstin}",
        f"/api/external/market/{entity_id}",
    ]
    
    for ep in endpoints:
        r = requests.get(f"{BASE}{ep}")
        print(f"  {ep}: {r.status_code}")
    print("  PASS")

def test_cam_one_pager(entity_id):
    print(f"\nTEST: /api/cases/{entity_id}/one-pager")
    r = requests.get(f"{BASE}/api/cases/{entity_id}/one-pager")
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        content = r.text
        print(f"  HTML length: {len(content)} chars")
        assert len(content) > 100, "One-pager HTML too short"
    print("  PASS" if r.status_code == 200 else "  SKIP (no pipeline run)")

def run_all():
    passed = 0
    failed = 0
    
    try:
        test_companies()
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    try:
        test_executed_only_before()
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    # Run pipeline for NTB company
    try:
        test_pipeline("BMFG001")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    # Run pipeline for ETB company
    try:
        test_pipeline("OLOG001")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    try:
        test_executed_only_after()
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    # Test CAM text retrieval
    try:
        test_cam_text("BMFG001")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    try:
        test_360_view("BMFG001")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    try:
        test_new_external_endpoints("BMFG001")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    try:
        test_existing_external_endpoints("BMFG001")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    try:
        test_cam_one_pager("BMFG001")
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    run_all()
