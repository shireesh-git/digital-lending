#!/usr/bin/env python3
import json, sys, re
sys.path.insert(0, '/app')
with open('/app/output/INFY001_fact_pack.json') as f:
    fp = json.load(f)
with open('/app/output/INFY001_pipeline_result.json') as f:
    cr = json.load(f)

from src.engines.cam_one_pager import generate_one_pager_html
html = generate_one_pager_html(fp, cr)

# Find ratio chips
chips = re.findall(r'chip-(\w+)"[^>]*>(\w+)<', html)
print('Chips:', chips[:12])

# Check collateral coverage
cov = re.findall(r'Coverage.*?(\d+\.\d+)', html)
print('Coverage values:', cov[:4])

# Collateral section raw
coll_match = re.search(r'Collateral.*?(?=<div class="section)', html, re.DOTALL)
if coll_match:
    text = re.sub(r'<[^>]+>', ' ', coll_match.group()[:500])
    text = re.sub(r'\s+', ' ', text).strip()
    print('Collateral section:', text[:300])

# Conditions section
cond_match = re.search(r'(Conditions:|Proposed Covenants:|No conditions).*?(?=<div class="section)', html, re.DOTALL)
if cond_match:
    text = re.sub(r'<[^>]+>', ' ', cond_match.group()[:400])
    text = re.sub(r'\s+', ' ', text).strip()
    print('Conditions section:', text[:200])

# N/A occurrences 
na_contexts = [html[max(0, m.start()-40):m.end()+40] for m in re.finditer('N/A', html)]
print(f'N/A count: {len(na_contexts)}')
for ctx in na_contexts[:3]:
    print(' -', re.sub(r'<[^>]+>', '', ctx).strip())
