"""Test that all CAM sections with Source columns render without errors."""
import sqlite3, json, traceback, sys

from src.engines.cam_renderer_v2 import render_complete_cam

db = sqlite3.connect("runtime-db/cam_platform.sqlite3")
db.row_factory = sqlite3.Row

rows = db.execute("SELECT entity_id, payload_json FROM case_runs WHERE payload_json IS NOT NULL ORDER BY created_at DESC").fetchall()
print(f"Found {len(rows)} cases in DB")

failed = []
for row in rows:
    eid = row["entity_id"]
    try:
        payload = json.loads(row["payload_json"])
        # The fact pack may be the payload itself or nested
        fp = payload.get("fact_pack", payload) if isinstance(payload, dict) else payload
        result = render_complete_cam(fp)
        lines = result.count("\n")
        src_cols = result.count("| Source")
        print(f"  {eid}: {lines} lines, {src_cols} Source cols - OK")
    except Exception as e:
        print(f"  {eid}: FAILED - {e}")
        traceback.print_exc()
        failed.append(eid)

print(f"\nResult: {len(rows) - len(failed)}/{len(rows)} passed")
if failed:
    print(f"Failed: {failed}")
db.close()
