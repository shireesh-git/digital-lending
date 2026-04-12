# CAM Intel User Manual

## 1. Purpose

This application is used to generate a Credit Appraisal Memorandum (CAM) from:

- verified public-record data retained locally until deleted
- borrower / RM uploaded documents
- local OCR and document extraction
- one ETB overlay for an existing-bank relationship case

The application is intentionally limited to five real companies with document-backed folders.

## 2. Access

### Start the application

```powershell
docker compose up -d --build
```

### Open the application

```text
http://127.0.0.1:8000
```

### Health check

```text
GET /api/health
```

Expected:

- app status is `healthy`
- `probe42.configured = true`
- `cache_enabled = true`
- `cache_ttl_hours = 0`
- retained public-record snapshots stay attached until explicitly deleted

## 3. Active Companies

Use only these company IDs in the current runtime:

- `APOL001` - Apollo Hospitals Enterprise Limited - NTB
- `INFY001` - Infosys Limited - NTB
- `IHCL001` - The Indian Hotels Company Limited - ETB
- `MFL001` - Madras Fertilizers Limited - NTB
- `MRF001` - MRF Limited - NTB

Recommended first runs:

- `INFY001` for a clean NTB flow
- `IHCL001` for the ETB flow with internal banking overlay

## 4. Main Navigation

### Dashboard

Use this page to see whether any real cases have already been executed.

If no cases exist:

- the page shows `Borrowers Ready`
- it does not show fake in-progress cases
- it gives a clear prompt to start the first CAM journey

### CAM Journey

Use this page to begin a new case from verified public data and then move into uploads, extraction, and CAM generation.

### Documents

Use this page to:

- review borrower file coverage
- see verified public-data coverage
- upload newer borrower files
- run extraction

### Pipeline

Use this page to execute the selected borrower through the scoring and CAM pipeline.

### Final CAM

Use this page to:

- load the final CAM
- review section-wise content
- add reviewer comments
- download the CAM PDF

### Settings

Use this page to edit:

- benchmarks
- rules
- engine toggles
- LLM / narrative settings

## 5. Step-By-Step NTB Flow

Use this flow for `INFY001`, `APOL001`, `MFL001`, or `MRF001`.

### Step 1: Open Dashboard

Confirm:

- the app is up
- no old cases are present if you want a clean run
- the verified-public-record banner is visible at the top

### Step 2: Start CAM Journey

Click:

- `+ Create New CAM`

Or open:

- `CAM Journey`

### Step 3: Select the Borrower

Enter one of the supported borrowers, for example:

- `Infosys Limited`
- `INFY001`

Set:

- case type: `NTB`
- facility type: `working_capital`
- requested amount
- purpose

### Step 4: Review Verified Data

After onboarding, confirm the public baseline is available:

- company master
- KYC / directors
- ratings
- GST
- legal history
- open charges
- EPFO / suit-filed / freshness when available

Important:

- this public baseline is retained locally
- repeated runs should reuse the retained public snapshot instead of pulling again

### Step 5: Review the Documents Page

Go to `Documents`.

Check two things separately:

- borrower file workspace
- verified public-data panel

The borrower file workspace is where RM uploads should go.

### Step 6: Upload Newer Borrower Files

Upload any file that is newer than the retained public baseline, for example:

- latest annual report
- latest audited financials
- provisional / unaudited results
- debt schedule
- CMA / projections / repayment assumptions
- sanction / banking / collateral files where applicable

Use the category dropdown before uploading.

If a real optional input is not available yet, the CAM Journey `Inputs` step can import a synthetic PDF from:

- `synthetic-assets/optional_inputs/<ENTITY_ID>`

These synthetic PDFs are clearly synthetic and are meant only for demo or workflow-completion use until the RM or internal team provides the real document.

Typical optional-input sources:

- site visit report: RM / branch visit / field partner
- valuation report: empanelled valuer / collateral team
- bank statements: borrower upload or internal CBS for ETB
- financial projections / CMA: borrower CFO pack or RM model
- credit facility details: internal LMS / sanction tracker / lender-wise exposure note
- internal credit notes: RM / analyst / branch credit desk

### Step 7: Run Extraction

On the `Documents` page, click:

- `Run Extraction`

This uses local extraction only:

- PyMuPDF
- Tesseract
- local parsing

No external OCR API is required.

### Step 8: Execute the Pipeline

Go to `Pipeline`.

Select the borrower and click:

- `Execute Pipeline`

This creates the first case run and applies:

- validation
- policy hard rules
- scoring
- recommendation logic
- CAM generation

### Step 9: Review the Case

After execution, review:

- recommendation
- risk grade
- composite score
- validation exceptions
- policy decisions
- supporting facts

### Step 10: Open Final CAM

Go to `Final CAM`.

Use:

- `Load Report`
- `Download PDF`
- reviewer comments per section

Important:

- reviewer comments are stored per `run_id`
- a fresh run starts with a clean comment set

## 6. Step-By-Step ETB Flow

Use this flow for:

- `IHCL001`

Key difference:

- this case has an ETB overlay
- it complements public data with internal banking context

The ETB overlay can contribute:

- existing facilities
- sanctioned and utilized limits
- conduct history
- covenant observations
- internal relationship metrics

Flow:

1. Open `CAM Journey`
2. Select or enter `IHCL001` / `The Indian Hotels Company Limited`
3. Keep case type as `ETB`
4. Review verified public data
5. Review ETB-specific internal context
6. Upload any newer borrower files if needed
7. Run extraction
8. Run pipeline
9. Review CAM

## 7. How Documents Work

The app distinguishes between three data layers.

### Borrower / RM uploads

These are the files the RM provides or refreshes.

Examples:

- latest annual report
- debt schedule
- CMA / projections
- sanction letter

These should be treated as the latest override layer.

### Verified public data

This is the retained public-record baseline for the borrower.

It is shown separately from borrower uploads.

### Hidden legacy / system artifacts

Some files exist on disk but are hidden from the active borrower workspace.

These are excluded from gap analysis when they are treated as legacy or system artifacts.

## 8. What “Missing Documents” Means

A missing item on the Documents page normally means one of these:

- the borrower has not uploaded the required file yet
- the file exists only as a hidden legacy/system artifact and is not counted as an active borrower document

Current common true gaps:

- `debt_schedule.xlsx`
- `CMA data / projections / repayment assumptions`

## 9. Rules And Settings

### Rules are live

The rules in `Settings > Rules` are not display-only.

Saved rule changes apply to subsequent pipeline runs.

The live rule file is:

- `config/rules.yaml`

### Rules currently wired into execution

These are actively used by the policy engine:

- hard-rule enable / applies-to / blocked-status / vintage parameters
- financial penalty thresholds and penalties
- conduct thresholds and penalties
- recommendation covenant lists
- recommendation monitoring lists

These are also used during scoring:

- scoring weights
- grade thresholds

### Important note

Rule changes affect future runs only.

They do not rewrite already-generated cases or CAMs.

## 10. Public Snapshot Retention

The verified public-data snapshot is stored separately from case output.

Location:

- `storage/cache/probe42`

Retention:

- retained until explicitly deleted
- `cache_ttl_hours = 0`

Effect:

- repeated borrower runs reuse the retained public data
- you should not need repeated public pulls for the same borrower until the retained snapshot is deleted

## 11. Storage Model

### Documents

- `storage/documents`

### Public snapshot store

- `storage/cache/probe42`

### Generated outputs

- `output`

### Database

- `runtime-db/cam_platform.sqlite3`

### Reference reports

- `downloaded document`

### Optional external mock / overlay assets

- `synthetic-assets`

### Synthetic optional-input PDFs

- `synthetic-assets/optional_inputs/<ENTITY_ID>`

## 12. Database Model

The runtime database uses SQLite.

Main tables:

- `app_users`
- `companies`
- `case_runs`
- `case_comments`

Notes:

- `app_users` is reserved for future login / RBAC work
- `case_runs` stores run history
- `case_comments` stores reviewer notes by `run_id`

## 13. Operational Tips

### Best first demo

Use `INFY001`.

Reason:

- strong document pack
- good public baseline
- clean NTB flow

### Best ETB demo

Use `IHCL001`.

Reason:

- ETB overlay is available
- existing-bank relationship context is included

### After changing rules

Do this:

1. Save rules in `Settings`
2. Re-run the borrower in `Pipeline`
3. Review the new case result and CAM

### If no case exists yet

Expected behavior now:

- Dashboard shows `Borrowers Ready`
- Pipeline says no run has been executed yet
- Final CAM waits for the first executed case

## 14. Troubleshooting

### Dashboard shows no real cases

This is expected after a case reset.

Action:

- open `CAM Journey`
- start the first borrower

### Documents show public data but CAM not generated

Action:

- run extraction if borrower files were uploaded
- then run pipeline

### Rules screen shows bad values

Expected after the latest fix:

- no `[object Object]`
- nested values such as `threshold`, `penalty`, and `bonus` render as real fields

### Changes do not appear in the app

Rebuild the Docker app:

```powershell
docker compose up -d --build
```

## 15. Quick Start Checklist

For the fastest complete run:

1. Start Docker
2. Open `http://127.0.0.1:8000`
3. Click `Create New CAM`
4. Use `INFY001`
5. Review verified data
6. Upload any fresher borrower files
7. Run extraction
8. Open `Pipeline`
9. Click `Execute Pipeline`
10. Open `Final CAM`

## 16. Current Scope

This manual reflects the current runtime behavior as of the present Docker build.

Out of scope for now:

- login
- RBAC
- user ownership workflows
- multi-user task routing
- enterprise DMS / LOS integration beyond the current local runtime
