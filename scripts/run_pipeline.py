"""Run pipeline inside Docker container and log results to file."""
import httpx
import json
import time
import sys
import traceback

entity_id = sys.argv[1] if len(sys.argv) > 1 else "INFY001"
log_file = f"/app/output/{entity_id}_pipeline_log.txt"
result_file = f"/app/output/{entity_id}_pipeline_result.json"

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(log_file, "a") as f:
        f.write(line + "\n")

log(f"Starting pipeline for {entity_id}")
start = time.time()

try:
    r = httpx.post(
        f"http://localhost:8000/api/cases/{entity_id}/run",
        timeout=httpx.Timeout(connect=30.0, read=3600.0, write=30.0, pool=30.0),
    )
    elapsed = time.time() - start
    log(f"Completed in {elapsed:.1f}s - HTTP {r.status_code}")

    data = r.json()
    log(f"Pipeline status: {data.get('status', '?')}")

    for agent, result in data.get("agents", {}).items():
        if isinstance(result, dict):
            status = result.get("status", "?")
            dur = result.get("duration_ms", 0)
            err = result.get("error", "")
            line = f"  {agent}: {status} ({dur/1000:.1f}s)"
            if err:
                line += f" - ERROR: {err[:200]}"
            log(line)
        else:
            log(f"  {agent}: {result}")

    with open(result_file, "w") as f:
        json.dump(data, f, indent=2, default=str)
    log(f"Result saved to {result_file}")

except Exception as e:
    elapsed = time.time() - start
    log(f"EXCEPTION after {elapsed:.1f}s: {e}")
    log(traceback.format_exc())
