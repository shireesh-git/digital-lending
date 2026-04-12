"""Quick test: run pipeline and report narrative mode + timing."""
import httpx
import json
import sys
import time

BASE = "http://localhost:8000"
entity = sys.argv[1] if len(sys.argv) > 1 else "INFY001"

# Ensure onboarded
httpx.post(f"{BASE}/api/onboard", json={"identifier": entity}, timeout=30.0)

start = time.time()
print(f"Running pipeline for {entity} with LLM narrative... (may take several minutes)")
sys.stdout.flush()
r = httpx.post(f"{BASE}/api/cases/{entity}/run", timeout=1800.0)
elapsed = time.time() - start
data = r.json()

mode = data.get("narrative_mode", "unknown")
print(f"\nnarrative_mode: {mode}")
print(f"elapsed: {elapsed:.1f}s\n")

for a in data.get("pipeline_log", []):
    name = a.get("agent", "?")
    status = a.get("status", "?")
    dur = a.get("duration_ms", "?")
    err = a.get("error", "")
    line = f"  {name:20s}  {status:10s}  {dur}ms"
    if err:
        line += f"  ERROR: {err[:80]}"
    print(line)

# Save full result for inspection
out = f"/app/output/{entity}_llm_result.json"
with open(out, "w") as f:
    json.dump({"narrative_mode": mode, "elapsed": elapsed, "pipeline_log": data.get("pipeline_log", [])}, f, indent=2)

# Save CAM output
cam = data.get("cam_text", "")
if cam:
    path = f"/app/output/{entity}_CAM_LLM.md"
    with open(path, "w") as f:
        f.write(cam)
    print(f"\nCAM saved: {len(cam)} chars → {path}")
