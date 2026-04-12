import requests, json

r = requests.get('https://camdemo-228620181301.asia-south1.run.app/api/cases/PNCR001', timeout=30)
d = r.json()

print("=== Key Scores ===")
print(f"Sector: {d['sector']}")
print(f"Financial Score: {d['financial_score']}")
print(f"Composite Score: {d['composite_score']}")
print(f"Risk Grade: {d['risk_grade']}")
print(f"Recommendation: {d['recommendation']}")
print(f"Covenants: {len(d['covenants_proposed'])}")
for c in d['covenants_proposed']:
    print(f"  - {c}")

print("\n=== Infra Metrics ===")
im = d['fact_pack'].get('infra_metrics', {})
print(json.dumps(im, indent=2, default=str)[:3000])

print("\n=== Conditions ===")
for c in d.get('conditions', []):
    print(f"  - {c}")
