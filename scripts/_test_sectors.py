"""Quick test: render CAMs for companies from different sectors."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.synthetic_companies import ALL_COMPANIES
from src.engines.cam_fact_builder import build_cam_fact_pack
from src.engines.cam_renderer_v2 import render_complete_cam
import traceback

test_cases = ['PNCR001', 'INFY001', 'BJFN001', 'IHCL001', 'TITN001', 'OLOG001', 'DLFR001', 'REIL001']
for eid in test_cases:
    try:
        cd = ALL_COMPANIES[eid]
        fp = build_cam_fact_pack(cd)
        md = render_complete_cam(fp)
        has_s12 = '12. DETAILED OPERATIONAL' in md
        has_s13 = '13. FINANCIAL PROJECTIONS' in md
        has_s135 = '13.5 Sector-Specific' in md
        sk = fp.get('sector_kpis', {})
        st = sk.get('sector_type', 'none')
        s12_start = md.find('12. DETAILED')
        s13_start = md.find('13. FINANCIAL')
        s12_len = s13_start - s12_start if s12_start >= 0 and s13_start > s12_start else 0
        has_dev = bool(sk.get('development_projections'))
        s135_ok = "OK" if has_s135 else ("SKIP(no dev_proj)" if not has_dev else "MISSING")
        print(f"{eid} [{st:25s}]: S12={has_s12}({s12_len:5d}ch) S13={has_s13} S13.5={s135_ok}")
    except Exception as e:
        print(f"{eid}: FAIL - {e}")
        traceback.print_exc()
