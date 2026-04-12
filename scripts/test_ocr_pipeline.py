"""Quick pipeline test script — runs inside Docker container."""
import httpx
import json
import time
import sys

entity = sys.argv[1] if len(sys.argv) > 1 else "INFY001"
print(f"Running pipeline for {entity}...")
start = time.time()
try:
    r = httpx.post(
        f"http://localhost:8000/api/cases/{entity}/run",
        timeout=httpx.Timeout(connect=10.0, read=900.0, write=10.0, pool=10.0),
    )
    d = r.json()
    dur = time.time() - start
    print(f"Completed in {dur:.1f}s")
    print(f"status={d.get('status')} risk_grade={d.get('risk_grade')} mode={d.get('narrative_mode')}")
    for step in d.get("pipeline_log", []):
        nm = step.get("agent_name", "?")
        st = step.get("status", "?")
        ms = step.get("duration_ms", 0)
        err = (step.get("error") or "")[:150]
        print(f"  {nm}: {st} {ms:.0f}ms {err}")
    with open(f"/app/output/{entity}_ocr_test.json", "w") as f:
        json.dump(d, f, indent=2, default=str)
    print(f"Result saved to /app/output/{entity}_ocr_test.json")
except Exception as e:
    dur = time.time() - start
    import traceback
    traceback.print_exc()
    print(f"ERROR after {dur:.1f}s: {e}")
