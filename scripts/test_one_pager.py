#!/usr/bin/env python3
"""Quick test for one-pager fix using INFY001 stored fact_pack."""
import json, sys, re
sys.path.insert(0, '/app')

with open('/app/output/INFY001_fact_pack.json') as f:
    fp = json.load(f)
with open('/app/output/INFY001_pipeline_result.json') as f:
    cr = json.load(f)

from src.engines.cam_one_pager import generate_one_pager_html
html = generate_one_pager_html(fp, cr)

company = fp.get('borrower_profile', {}).get('company_name', '?')
print(f"HTML len: {len(html)}")
print(f"Company name '{company}' in html: {company in html}")
print(f"Current Ratio shown: {'Current Ratio' in html}")
print(f"Account Conduct shown: {'Account Conduct' in html}")
print(f"Operating CF shown: {'Operating CF' in html}")
print(f"N/A raw count: {html.count('N/A')}")
print(f"Conditions/covenants shown: {'Conditions:' in html or 'Proposed Covenants' in html or 'No conditions' in html}")

# Show ratio values
ratio_match = re.search(r'(Key Ratios.*?)(?=<div class="section-title)', html, re.DOTALL)
if ratio_match:
    # strip html tags for readability
    text = re.sub(r'<[^>]+>', ' ', ratio_match.group())
    text = re.sub(r'\s+', ' ', text).strip()
    print(f"\nRatios section: {text[:300]}")

# Sample conduct section
conduct_match = re.search(r'(Account Conduct.*?)(?=<strong|</div>)', html, re.DOTALL)
if conduct_match:
    text = re.sub(r'<[^>]+>', ' ', conduct_match.group())
    text = re.sub(r'\s+', ' ', text).strip()
    print(f"\nConduct section: {text[:200]}")

# Check score bars
scores = {
    'financial_score': cr.get('financial_score'),
    'conduct_score': cr.get('conduct_score'),
    'composite_score': cr.get('composite_score'),
}
print(f"\nScores from case_result: {scores}")
print("All scores in html:", all(str(int(v or 0)) in html for v in scores.values() if v))
