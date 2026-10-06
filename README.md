# CAM Intelligence Platform

> AI-powered Credit Approval Memorandum (CAM) automation for corporate lending.

## Overview

The CAM Intelligence Platform automates the end-to-end credit appraisal process for corporate lending. It ingests company data from multiple sources, runs deterministic analytical engines, performs AI-powered narrative generation, and produces a complete Credit Approval Memorandum — reducing analyst effort from days to minutes.

### Key Capabilities

- **Multi-source data ingestion** — Financial statements, KYC, bureau reports, MCA filings, GST data, market signals, NSE disclosures
- **14 analytical engines** — Ratio analysis, benchmarking, policy checks, fraud detection, ETB analytics, PEP/sanctions screening, social media intelligence
- **7-agent orchestration pipeline** — Deterministic super-agent coordinates sub-agents for data gathering, extraction, analysis, and CAM generation
- **AI-powered CAM generation** — 21-section CAM with LLM narrative commentary (14 AI sections + 7 template sections)
- **Financial Advisor chat** — Context-aware analyst copilot powered by LLM
- **Real-time progress tracking** — SSE-based pipeline progress with section-by-section completion
- **PDF & one-pager export** — Downloadable CAM report and executive summary memo

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | Alpine.js 3.14, Chart.js 4.4, Tailwind-style dark theme |
| LLM | Pluggable — Google Gemini (Vertex AI), Ollama (local), OpenAI, Anthropic, Azure |
| Database | SQLite (runtime persistence) |
| PDF | ReportLab (generation), pdfplumber (extraction) |
| OCR | PyMuPDF + Gemini Vision fallback |
| Deployment | Docker, Google Cloud Run, GCS Cloud Storage FUSE |

## Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) with `qwen3:8b` (the configured LLM) — or switch to another
  provider in `config/llm_providers.yaml`
- (Optional) Docker for containerized deployment

### Local LLM (Ollama + qwen3:8b)

```bash
ollama pull qwen3:8b        # ~5.2 GB, one-time
ollama serve                # if Ollama is not already running as a service
```

`config/llm_providers.yaml` sets `active_provider: ollama` with `model: qwen3:8b` and
`think: false`. qwen3 normally writes a long hidden reasoning pass before answering; turning
it off makes CAM generation several times faster on CPU and keeps the token budget for the
memo itself.

On a CPU-only laptop (16 GB RAM) expect roughly 3–5 tokens/second, i.e. **35–50 minutes for
a full CAM** (14 LLM-written sections). Each section is saved as soon as it is written, so if
a run fails part-way, running it again resumes from the last finished section. Timeouts are
set per section (`timeout_seconds`) and per chat reply (`chat_timeout_seconds`).

For quick functional checks without waiting for the LLM, set `narrative.mode: template` in
the same file (or `active_provider: mock`); the CAM is then rendered from templates.

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1 # Windows

# Install dependencies
pip install -r requirements.txt

# Local settings (API keys, Ollama host) — never committed
cp .env.example .env.local

# Run the server
python run.py
```

The application starts at **http://localhost:8001**

### Docker

```bash
docker-compose up --build
```

### Google Cloud Run

```powershell
.\scripts\deploy_gcp_camdemo.ps1
```

## Project Structure

```
├── src/
│   ├── api/
│   │   ├── main.py         # ASGI entry point (src.api.main:app)
│   │   ├── app.py          # create_app(): middleware, static files, routers, error mapping
│   │   ├── dependencies.py # FastAPI dependency providers
│   │   └── routers/        # One router per area: cases, cam, approvals, companies,
│   │                       #   onboarding, documents, analytics, external, chat, admin, system
│   ├── application/        # Use-case services between the API and the engines
│   │   ├── container.py    # Composition root: builds state and wires services
│   │   ├── state.py        # In-process caches (companies, cases, extractions, ...)
│   │   ├── company_service.py, case_service.py, cam_service.py,
│   │   ├── approval_service.py, document_workspace.py
│   │   └── errors.py       # Application errors → HTTP status codes
│   ├── agents/             # Pipeline orchestrator (pipeline.py) and one module per agent
│   ├── engines/            # Deterministic engines; credit_assessment.py is the single
│   │                       #   definition of validation → benchmarks → policy decision
│   ├── rendering/          # CAM markdown/HTML, CAM PDF, CRILC PDF
│   ├── models/             # Canonical data model (dataclasses)
│   ├── services/           # Integrations and persistence (SQLite, DMS, OCR, Probe42, chat)
│   ├── data/               # Company data (synthetic + real Indian corporates)
│   ├── core/               # Configuration, LLM providers, runtime paths
│   └── ui/                 # Alpine.js SPA frontend
├── config/                 # YAML configuration (benchmarks, rules, LLM providers, approval matrix)
├── scripts/                # Deployment, testing, and data generation scripts
├── tests/                  # Unit tests, plus characterization tests (tests/characterization)
├── postman/                # Postman collections for API testing
├── docs/                   # Architecture and technical documentation
├── documents/              # User documentation
├── storage/                # Document storage (runtime)
└── runtime-db/             # SQLite database (runtime)
```

### Layering rules

- `api/routers` only translate HTTP to service calls; no business logic.
- `application` services own state and orchestration; they raise `ApplicationError`
  subclasses, which `create_app` maps to HTTP status codes.
- `engines` are deterministic and stateless; `agents` call engines and pass results
  forward through the pipeline context.

### Pipeline reliability

- Every run is recorded in `pipeline_runs` (`GET /api/cases/{id}/runs`), including failures.
- Each LLM-written CAM section is checkpointed as soon as it is written. Re-running after a
  failure reuses finished sections whose inputs (data, prompt, model, settings) are unchanged.
- Bump `PROMPT_VERSION` in `src/engines/cam_llm_renderer.py` when section prompts change.

### Tests

```bash
python -m pytest tests                                   # everything (~3 min, offline)
python -m tests.characterization.snapshot --write        # accept intended pipeline changes
python -m tests.characterization.api_contract --write    # accept intended API changes
```

Tests run against a temporary copy of `config/` and `storage/` with the mock LLM and Probe42
disabled (`tests/conftest.py`); they never touch your database or call external services.

## API Endpoints (Summary)

| Category | Endpoints | Description |
|----------|-----------|-------------|
| Dashboard | `GET /api/dashboard` | Platform overview metrics |
| Companies | `GET/POST/DELETE /api/companies` | Company CRUD & catalog |
| Cases | `GET/POST /api/cases/{id}` | CAM case management |
| Pipeline | `POST /api/cases/{id}/run`, `GET /api/cases/{id}/run-stream` | Run full CAM pipeline (blocking / SSE) |
| Run history | `GET /api/cases/{id}/runs` | Pipeline attempts with status and errors |
| Approvals | `GET /api/cases/{id}/workflow`, `POST /api/cases/{id}/workflow/{action}` | Maker-checker workflow (submit, recall, approve, reject, return) |
| Approval queue | `GET /api/approvals/queue?authority=…`, `GET /api/approvals/authority-matrix` | Cases awaiting an authority; delegation matrix |
| Documents | `GET/POST /api/companies/{id}/documents` | Document upload & management |
| Extraction | `POST /api/companies/{id}/extract` | Document data extraction |
| ETB Analytics | `POST/GET /api/companies/{id}/etb-analytics` | Existing-to-bank analysis |
| Chat | `POST /api/chat/{id}` | Financial advisor chat |
| Fraud | `POST/GET /api/companies/{id}/fraud-analysis` | Fraud detection analysis |
| 360° View | `GET /api/companies/{id}/360` | Comprehensive entity view |
| Onboarding | `POST /api/onboard` | CIN/PAN-based company onboarding |
| Config | `GET/PUT /api/config/{section}` | Runtime configuration |
| LLM | `GET /api/llm/providers` | LLM provider management |

## Configuration

Configuration is managed via YAML files in `config/`:

- **settings.yaml** — Global platform settings
- **llm_providers.yaml** — LLM provider configuration (Gemini, Ollama, OpenAI, etc.)
- **benchmarks.yaml** — Industry benchmark thresholds
- **rules.yaml** — Policy and validation rules
- **external_apis.yaml** — External data source configuration
- **approval.yaml** — Delegation of powers (approval authority levels). The shipped values are
  placeholders; replace them with your bank's approved matrix.

Secrets and machine-specific settings go in `.env.local` (see `.env.example`).

## Test Companies

The catalog seeds 6 companies with full data and document packs: APOL001 (Apollo Hospitals), INFY001 (Infosys), IHCL001 (IHCL), MFL001 (Madras Fertilisers), MRF001 (MRF) and PNCR001 (PNC Infratech). They cover different sectors and outcomes from approve to decline. More companies can be added through onboarding (`POST /api/onboard`) or manual entry.

## Documentation

- [Architecture Reference](docs/ARCHITECTURE_REFERENCE.md) — Detailed technical architecture
- [Architecture Process Document](docs/ARCHITECTURE_PROCESS.md) — System design and data flow
- [Technical Documentation](docs/TECHNICAL_DOCUMENTATION.md) — Implementation details
- [Deployment & Storage Model](docs/DEPLOYMENT_STORAGE_MODEL.md) — Docker and cloud deployment
- [CAM Data-Point Source Matrix](docs/CAM_DATAPOINT_SOURCE_MATRIX.md) — Where each CAM field comes from
- [GCP Deployment Guide](documents/GCP_DEPLOYMENT.md) — Google Cloud Run setup
- [User Manual](documents/USER_MANUAL.md) — End-user guide

## License

Proprietary — All rights reserved.
