"""Verify key CAM sections for PNCR001 on deployed server."""
import requests, re, sys

BASE = "https://camdemo-228620181301.asia-south1.run.app"
r = requests.get(f"{BASE}/api/cases/PNCR001/cam")
cam = r.json()["cam_text"]

print("=== SECTION CHECKS ===\n")

# 1. Revenue check
if "8,650" in cam or "8650" in cam:
    print("[OK] Revenue 8,650 Cr found")
else:
    print("[FAIL] Revenue 8,650 Cr NOT found")
    # Find actual revenue
    m = re.search(r"Revenue.*?(\d[\d,.]+)\s*Cr", cam[:5000])
    if m: print(f"       Found: {m.group(1)}")

# 2. EBITDA check
if "2,004" in cam or "2004" in cam:
    print("[OK] EBITDA 2,004 Cr found")
else:
    print("[FAIL] EBITDA 2,004 Cr NOT found")

# 3. Shareholding
if "56.07" in cam:
    print("[OK] Promoter holding 56.07% found")
else:
    print("[FAIL] Promoter holding 56.07% NOT found")

if "33.10" in cam or "33.1" in cam:
    print("[OK] Institutional holding 33.10% found")
else:
    print("[FAIL] Institutional holding NOT found")

# 4. Infra metrics - Order Book
if "27,680" in cam or "27680" in cam:
    print("[OK] Order book 27,680 Cr found")
else:
    print("[FAIL] Order book 27,680 Cr NOT found")

# 5. Project Pipeline
if "Project Pipeline" in cam:
    print("[OK] Project Pipeline section found")
else:
    print("[FAIL] Project Pipeline section NOT found")

if "Ganga Expressway" in cam or "Bundelkhand" in cam:
    print("[OK] Specific project names found")
else:
    print("[FAIL] Specific project names NOT found")

# 6. BOT/HAM
if "BOT" in cam or "HAM" in cam:
    print("[OK] BOT/HAM mentioned")
else:
    print("[FAIL] BOT/HAM NOT mentioned")

# 7. Social media
if "3,800" in cam or "3800" in cam:
    print("[OK] Social media 3,800 mentions found")
else:
    print("[FAIL] Social media 3,800 mentions NOT found")

if "185,000" in cam or "185000" in cam or "185K" in cam:
    print("[OK] LinkedIn 185,000 followers found") 
else:
    print("[FAIL] LinkedIn 185K followers NOT found")

# 8. Sector KPIs
if "road_construction" in cam or "Road Construction" in cam or "Highway" in cam:
    print("[OK] Road construction KPIs referenced")
else:
    print("[FAIL] Road construction KPIs NOT referenced")

# 9. Check EBITDA margin in peer comparison
m = re.search(r"EBITDA Margin.*?(\d+\.\d+)", cam)
if m:
    margin = float(m.group(1))
    if margin > 0.20:
        print(f"[OK] EBITDA Margin in peer comparison: {margin} (>0.20)")
    else:
        print(f"[WARN] EBITDA Margin in peer comparison: {margin}")
else:
    print("[WARN] Could not find EBITDA Margin in peer comparison")

# 10. Debt/EBITDA check (should be much lower than 41.75 now)
m = re.search(r"Debt.*?EBITDA.*?(\d+\.\d+)", cam)
if m:
    de = float(m.group(1))
    if de < 10:
        print(f"[OK] Debt/EBITDA: {de} (<10)")
    else:
        print(f"[WARN] Debt/EBITDA: {de} (still high)")

# 11. Data sources section  
if "Data Source" in cam or "AUDIT TRAIL" in cam:
    print("[OK] Data sources / audit trail section found")
else:
    print("[FAIL] Data sources / audit trail NOT found")

# Section 3 subsections
s3_sections = re.findall(r"### 3\.(\d+)", cam)
print(f"\nSection 3 subsections found: 3.{', 3.'.join(s3_sections)}")

# Section 12 check
s12 = re.findall(r"### 12\.(\d+)", cam)
print(f"Section 12 subsections found: 12.{', 12.'.join(s12)}")

print("\n=== DONE ===")
