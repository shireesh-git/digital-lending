# Architecture Process Document

> CAM Intelligence Platform — System Architecture, Data Flow & Process Design

## 1. System Architecture Overview

The CAM Intelligence Platform follows a **layered architecture** with clear separation between data ingestion, analytical processing, AI orchestration, and presentation.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND LAYER                           │
│              Alpine.js SPA + Chart.js Visualizations            │
│         (Dark theme, SSE real-time updates, 12+ pages)          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API + SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                        API LAYER (FastAPI)                       │
│    50+ endpoints: Companies, Cases, Pipeline, Documents,         │
│    Extraction, ETB, Chat, Fraud, 360°, Config, LLM              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   ORCHESTRATION LAYER                            │
│    SuperAgent → 7 Sub-Agents (sequential pipeline)              │
│    DataGatherAgent → ExtractionAgent → AnalysisAgent →          │
│    ValidationAgent → PolicyAgent → NarrativeAgent → FinalAgent  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      ENGINE LAYER (14 Engines)                   │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌───────────────┐   │
│  │  Ratio   │ │ Benchmark │ │ Validation │ │    Policy      │   │
│  │  Engine  │ │  Engine   │ │   Engine   │ │    Engine      │   │
│  └──────────┘ └───────────┘ └────────────┘ └───────────────┘   │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌───────────────┐   │
│  │  Fraud   │ │    ETB    │ │    CAM     │ │  CAM LLM      │   │
│  │ Detection│ │ Analytics │ │ Fact Build │ │  Renderer      │   │
│  └──────────┘ └───────────┘ └────────────┘ └───────────────┘   │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌───────────────┐   │
│  │  Core    │ │  Social   │ │  Document  │ │   CRILC       │   │
│  │ Banking  │ │   Media   │ │  Downloader│ │  Report Gen   │   │
│  └──────────┘ └───────────┘ └────────────┘ └───────────────┘   │
│  ┌──────────┐ ┌───────────┐                                     │
│  │ Document │ │ CAM One   │                                     │
│  │   OCR    │ │  Pager    │                                     │
│  └──────────┘ └───────────┘                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌───────────────┐   │
│  │  SQLite  │ │ In-Memory │ │   File     │ │  External     │   │
│  │   DB     │ │  Stores   │ │  Storage   │ │    APIs       │   │
│  └──────────┘ └───────────┘ └────────────┘ └───────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 2. Core Design Principles

### 2.1 Deterministic-First Architecture

The platform prioritizes **deterministic processing** over AI inference:

- All financial ratios, benchmarks, policy checks, and risk scores are computed by rule-based engines
- LLM is used **only** for narrative commentary — never for number crunching
- Same input always produces the same analytical output
- LLM sections are clearly marked and separated from computed sections

### 2.2 Canonical Data Model

All company data flows through a **single canonical model** (`src/models/canonical_model.py`):

```
Borrower           — Company identity (CIN, PAN, sector, listing status)
GroupEntity         — Corporate group structure
DirectorPromoter   — Board members and promoters
FinancialStatement — Standardized P&L, Balance Sheet, Cash Flow
FacilityRequest    — Credit facility being requested
ExistingExposure   — Current banking relationships
Collateral         — Security offered
MarketSignal       — Market intelligence and news
ConductRecord      — ETB account behavior (DPD, utilization)
CovenantRecord     — ETB covenant compliance
```

### 2.3 Pluggable LLM Architecture

The platform supports multiple LLM providers through a provider abstraction:

| Provider | Model | Use Case |
|----------|-------|----------|
| Google Vertex AI | Gemini 2.0 Flash | Production (Cloud Run) |
| Ollama | Qwen 2.5 32B | Local development |
| OpenAI | GPT-4 | Alternative cloud |
| Anthropic | Claude | Alternative cloud |
| Azure OpenAI | GPT-4 | Enterprise |
| Mock | Template-based | Testing (no LLM needed) |

## 3. Data Flow Process

### 3.1 Company Onboarding Flow

```
User enters CIN/PAN
        │
        ▼
POST /api/onboard
        │
        ▼
┌─────────────────────────┐
│  Company Onboarding     │
│  Service                │
│  ┌───────────────────┐  │
│  │ 1. MCA Lookup     │──── Fetch company master from MCA
│  │ 2. GSTIN Fetch    │──── Fetch GST profile
│  │ 3. Bureau Pull    │──── Fetch credit bureau data
│  │ 4. Rating Fetch   │──── Fetch credit ratings
│  │ 5. Market Intel   │──── Fetch news & market data
│  │ 6. NSE/BSE Data   │──── Fetch exchange filings
│  │ 7. CRILC Pull     │──── Fetch RBI CRILC data
│  └───────────────────┘  │
└────────────┬────────────┘
             │
             ▼
    Canonical Model Created
    Documents Stored in storage/documents/{entity_id}/
    Company registered in SQLite DB
```

### 3.2 CAM Pipeline Flow (SuperAgent Orchestration)

```
POST /api/cases/{id}/run
        │
        ▼
┌──────────────────────────────────────────────┐
│              SUPER AGENT PIPELINE            │
│                                              │
│  Stage 1: DataGatherAgent                    │
│  ├── Load company data from store            │
│  ├── Fetch external data (bureau, MCA, GST)  │
│  └── Assemble raw data package               │
│                                              │
│  Stage 2: ExtractionAgent                    │
│  ├── Parse uploaded documents (PDF/XLSX)     │
│  ├── OCR processing (PyMuPDF + Gemini)       │
│  └── Extract financial data & metadata       │
│                                              │
│  Stage 3: AnalysisAgent                      │
│  ├── Ratio Engine (20+ financial ratios)     │
│  ├── Benchmark Engine (sector comparison)    │
│  ├── ETB Analytics (if existing customer)    │
│  ├── Fraud Detection Engine                  │
│  └── PEP/Sanctions Screening                 │
│                                              │
│  Stage 4: ValidationAgent                    │
│  ├── Cross-document validation               │
│  ├── Regulatory compliance checks            │
│  └── Data quality scoring                    │
│                                              │
│  Stage 5: PolicyAgent                        │
│  ├── Credit policy rule evaluation           │
│  ├── Exposure limit checks                   │
│  └── Risk grade computation                  │
│                                              │
│  Stage 6: NarrativeAgent                     │
│  ├── Build CAM fact pack (38 keys)           │
│  ├── Render template sections                │
│  └── Generate LLM narrative (14 sections)    │
│                                              │
│  Stage 7: FinalAgent                         │
│  ├── Assemble complete CAM                   │
│  ├── Generate one-pager                      │
│  └── Persist to database                     │
└──────────────────────────────────────────────┘
        │
        ▼
    SSE events → Frontend (real-time progress)
    CAM stored in case_runs table
    PDF/Markdown available for download
```

### 3.3 CAM Fact Pack Assembly

The CAM fact pack is the central data structure assembled by `cam_fact_builder.py`:

```
Fact Pack (38 keys)
├── cover_data          — Company name, CIN, date, analyst
├── borrower_profile    — Sector, incorporation, promoters, group
├── industry_analysis   — Revenue segments, geo mix, SWOT
├── facility_details    — Requested amount, type, tenor, purpose
├── financial_summary   — 3-year P&L, BS, CF with YoY trends
├── ratio_analysis      — 20+ computed ratios with RAG status
├── benchmark_results   — Sector peer comparison
├── collateral_details  — Security valuation, coverage ratio
├── conduct_summary     — ETB behavior (DPD, utilization, SMA)
├── compliance_checks   — 6-7 regulatory compliance items
├── quarterly_performance — Q1-Q4 with seasonal weighting
├── validation_results  — Cross-document validation findings
├── policy_decisions    — Rule evaluation results
├── risk_assessment     — Composite score, grade, recommendation
├── fraud_indicators    — Fraud detection signals
├── pep_screening       — PEP/sanctions/adverse media results
├── market_intelligence — News sentiment, stock signals
├── external_ratings    — Agency ratings with outlook
├── site_visit_data     — (Optional) site visit findings
├── valuation_data      — (Optional) valuation assessment
├── bank_statement_data — (Optional) bank statement analysis
└── audit_trail         — Data lineage & processing log
```

### 3.4 CAM Rendering Process

```
Fact Pack JSON
      │
      ├──► Template Renderer (cam_renderer_v2.py)
      │    └── 7 template sections (cover, TOC, financials, tables)
      │
      ├──► LLM Renderer (cam_llm_renderer.py)
      │    └── 14 AI narrative sections
      │    └── Per-section system prompts from prompts/
      │    └── Context injection from fact pack
      │
      └──► Combined Markdown CAM (21 sections total)
           ├── Section 1:  Cover Page
           ├── Section 2:  Table of Contents
           ├── Section 3:  Executive Summary (LLM)
           ├── Section 4:  Borrower Profile (LLM)
           ├── Section 5:  Industry Analysis (LLM)
           ├── Section 6:  Facility Details
           ├── Section 7:  Financial Analysis (LLM + Tables)
           ├── Section 8:  Benchmark Comparison (LLM)
           ├── Section 9:  Collateral Assessment (LLM)
           ├── Section 10: Account Conduct (LLM — ETB only)
           ├── Section 11: Compliance & Regulatory
           ├── Section 12: Infrastructure Assessment (LLM)
           ├── Section 13: External Intelligence (LLM)
           ├── Section 14: Fraud & PEP Screening (LLM)
           ├── Section 15: Key Risks & Mitigants (LLM)
           ├── Section 16: Validation Summary
           ├── Section 17: Policy Assessment
           ├── Section 18: Risk Assessment & Scoring
           ├── Section 19: Recommendation (LLM)
           ├── Section 20: Annexures (Tables)
           └── Section 21: Audit Trail
```

## 4. Engine Details

### 4.1 Ratio Engine

Computes 20+ financial ratios from canonical `FinancialStatement` line items:

| Category | Ratios |
|----------|--------|
| Profitability | EBITDA Margin, PAT Margin, ROE, ROCE, ROA |
| Leverage | Debt-to-Equity, Debt/EBITDA, Interest Coverage (ICR) |
| Liquidity | Current Ratio, Quick Ratio, Cash Ratio |
| Efficiency | Asset Turnover, Inventory Turnover, Receivable Days |
| Cash Flow | Operating CF/Revenue, Free Cash Flow, DSCR |
| Growth | Revenue Growth YoY, EBITDA Growth, PAT Growth |

### 4.2 Benchmark Engine

Compares computed ratios against sector-specific thresholds from `config/benchmarks.yaml`:

- **Sector benchmarks** — Industry-specific thresholds (manufacturing, IT, pharma, etc.)
- **Size band comparison** — Large cap vs mid cap vs small cap
- **Rating bucket comparison** — AAA vs AA vs A vs BBB
- **RAG classification** — Green/Amber/Red for each metric

### 4.3 Policy Engine

Evaluates credit policy rules from `config/rules.yaml`:

- Exposure limits (single borrower, group, sector)
- Minimum financial thresholds (ICR, DSCR, leverage)
- Rating-based eligibility
- NPA/SMA status checks
- Regulatory hold checks

### 4.4 Fraud Detection Engine

Analyzes multiple signals for fraud/governance concerns:

- Director disqualification checks
- Circular trading patterns
- Revenue-employee mismatch
- GST turnover vs declared revenue mismatch
- PEP/sanctions database screening
- Adverse media scanning
- Related party transaction analysis

### 4.5 ETB Analytics Engine

For existing bank customers, analyzes transactional behavior:

- Account utilization patterns
- DPD (Days Past Due) frequency
- SMA (Special Mention Account) status
- Covenant compliance tracking
- Conduct score computation

## 5. External Data Integration

### 5.1 Data Sources

| Source | Data Retrieved | Protocol |
|--------|---------------|----------|
| MCA (Ministry of Corporate Affairs) | Company master, directors, charges | REST API |
| GSTIN | GST profile, turnover, filing compliance | REST API |
| Credit Bureau | Credit score, DPD, facility list | REST API |
| CRILC (RBI) | Fund/non-fund facility aggregation | REST API |
| NSE/BSE | Filings, financial results, corporate actions | REST API |
| Credit Rating Agencies | Ratings, outlook, history | REST API |
| EPFO | Employee count, compliance | REST API |
| Market Intelligence | News, sentiment, legal proceedings | REST API |

### 5.2 Integration Pattern

All external data follows a standardized envelope:

```json
{
  "source": "bureau_commercial",
  "record_type": "COMMERCIAL_BUREAU_REPORT",
  "entity_key": "AABCB1234F",
  "as_of_date": "2026-03-13",
  "payload_version": "2.0",
  "source_status": "valid",
  "payload": { ... }
}
```

## 6. Deployment Architecture

### 6.1 Local Development

```
┌─────────────┐    ┌──────────────┐
│  Browser     │───▶│  FastAPI      │
│  :8001       │    │  (uvicorn)   │
└─────────────┘    │              │
                   │  SQLite DB   │
                   │  File Storage│
                   │  Ollama LLM  │
                   └──────────────┘
```

### 6.2 Google Cloud Run (Production)

```
┌─────────────┐    ┌──────────────────────────────┐
│  Browser     │───▶│  Cloud Run Service            │
│              │    │  (Docker container)            │
└─────────────┘    │                                │
                   │  ┌──────────────────────────┐  │
                   │  │ FastAPI + Alpine.js SPA   │  │
                   │  └──────────────────────────┘  │
                   │                                │
                   │  ┌──────────────────────────┐  │
                   │  │ GCS FUSE Volume           │  │
                   │  │ /app/runtime-db           │  │
                   │  │ (SQLite + persistent data)│  │
                   │  └──────────────────────────┘  │
                   │                                │
                   │  ┌──────────────────────────┐  │
                   │  │ Vertex AI (Gemini 2.0)    │  │
                   │  │ ADC authentication        │  │
                   │  └──────────────────────────┘  │
                   └──────────────────────────────┘
```

### 6.3 Docker Compose

```yaml
services:
  cam:        # Main application (port 8000)
  mock:       # External API mock server
```

## 7. Security Considerations

- **No hardcoded credentials** — All secrets via environment variables
- **Input validation** — FastAPI Pydantic models for all endpoints
- **CORS** — Configurable origin whitelist
- **Authentication** — SQLite RBAC framework (ready for production auth)
- **LLM safety** — System prompts prevent prompt injection in CAM generation
- **Data isolation** — Per-entity document storage with entity ID scoping
