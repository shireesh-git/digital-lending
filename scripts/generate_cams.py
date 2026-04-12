"""
Generate Complete CAMs for all 4 test companies.
Outputs each CAM to output/ as Markdown files.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.data.synthetic_companies import ALL_COMPANIES
from src.engines.cam_fact_builder import build_cam_fact_pack
from src.engines.cam_renderer_v2 import render_complete_cam


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "output")
    os.makedirs(output_dir, exist_ok=True)

    for entity_id, company_data in ALL_COMPANIES.items():
        print(f"\n{'='*70}")
        print(f"  Generating CAM for: {company_data['borrower'].company_name} ({entity_id})")
        print(f"{'='*70}")

        # Step 1: Build deterministic fact-pack
        fact_pack = build_cam_fact_pack(company_data)

        # Save fact-pack JSON
        fp_path = os.path.join(output_dir, f"{entity_id}_fact_pack.json")
        with open(fp_path, "w", encoding="utf-8") as f:
            json.dump(fact_pack, f, indent=2, default=str)
        print(f"  ✅ Fact-pack → {fp_path}")

        # Step 2: Render full CAM
        cam_md = render_complete_cam(fact_pack)

        # Save CAM Markdown
        cam_path = os.path.join(output_dir, f"{entity_id}_CAM.md")
        with open(cam_path, "w", encoding="utf-8") as f:
            f.write(cam_md)
        print(f"  ✅ CAM ({len(cam_md):,} chars) → {cam_path}")

        # Stats
        page_estimate = len(cam_md) / 3000  # ~3000 chars per page
        print(f"  📄 Estimated pages: {page_estimate:.1f}")

    print(f"\n{'='*70}")
    print(f"  All CAMs generated successfully! Check output/ directory.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
