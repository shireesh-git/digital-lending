# Test Documents – Consolidated Structure

All test documents (real annual reports, synthetic optional inputs, platform-generated packs, reference CAMs) organized by entity.

## Folder Layout

```
test-documents/
├── APOL001_Apollo_Hospitals/
│   ├── annual-reports/          # Real annual reports (FY22-23 to FY24-25) + unaudited (FY25-26)
│   ├── optional-inputs/         # 6 synthetic PDFs (bank statements, CMA, site visit, valuation, etc.)
│   └── platform-document-pack/  # Full 12-category document pack from storage/documents/
├── IHCL001_IHCL/
│   ├── annual-reports/
│   ├── optional-inputs/
│   └── platform-document-pack/
├── INFY001_Infosys/
│   ├── annual-reports/
│   ├── optional-inputs/
│   └── platform-document-pack/
├── MFL001_Madras_Fertilisers/
│   ├── annual-reports/
│   ├── optional-inputs/
│   └── platform-document-pack/
├── MRF001_MRF/
│   ├── annual-reports/
│   ├── optional-inputs/
│   └── platform-document-pack/
├── TVS_Motors/
│   └── annual-reports/          # No entity ID yet – real reports only
├── reference-cams/              # Reference CAM documents (Infosys SBI/IndianBank, generic)
└── etb-overlays/                # ETB existing-to-bank overlay JSON files
```

## Document Sources

| Source Folder | Description |
|---|---|
| `downloaded document/CAM/` | Real annual reports and unaudited results (23 PDFs, 6 companies) |
| `synthetic-assets/optional_inputs/{entity}/` | Synthetic optional input PDFs (6 per entity, 5 entities) |
| `storage/documents/{entity}/` | Platform-generated document packs (12 category subdirectories) |
| `refer/` | Reference CAM documents for comparison |
| `synthetic-assets/etb_overlays/` | ETB overlay JSON files |

## Optional Input Types

Each entity's `optional-inputs/` folder contains:

| File | CAM Section(s) |
|---|---|
| `synthetic_site_visit_report.pdf` | 2. Borrower Profile / 7. Risk Assessment |
| `synthetic_valuation_report.pdf` | 6. Security & Collateral |
| `synthetic_bank_statements.pdf` | 10. Account Conduct |
| `synthetic_cma_projection.pdf` | 4. Financial Analysis / 5. Facility Details |
| `synthetic_credit_facility_details.pdf` | 5. Credit Facility Details |
| `synthetic_internal_credit_notes.pdf` | 1. Executive Summary / 12. Recommendation |

## Re-generating

These packs are static test inputs for upload demos; edit them directly when needed.
