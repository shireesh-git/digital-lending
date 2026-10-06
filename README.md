# CAM Intelligence Platform

> AI-powered Credit Approval Memorandum (CAM) automation for corporate lending.

## Overview

The CAM Intelligence Platform automates the end-to-end credit appraisal process for corporate lending. It ingests company data from multiple sources, runs deterministic analytical engines, performs AI-powered narrative generation, and produces a complete Credit Approval Memorandum — reducing analyst effort from days to minutes.

### Key Capabilities

- **Multi-source data ingestion** — Financial statements, KYC, bureau reports, MCA filings, GST data, market signals, NSE disclosures
- **14 analytical engines** — Ratio analysis, benchmarking, policy checks, fraud detection, ETB analytics, PEP/sanctions screening, social media intelligence
- **7-agent orchestration pipeline** — Deterministic super-agent coordinates sub-agents for data gathering, extraction, analysis, and CAM generation; agents that do not depend on each other run in parallel
- **AI-powered CAM generation** — 21-section CAM with LLM narrative commentary (14 AI sections + 7 template sections); on hosted LLMs several sections are written at once
- **Pluggable LLM** — switch between a local model (Ollama) and hosted models (Gemini, OpenAI, Anthropic, Azure) with one setting; each provider gets its own execution path (see [Pipeline execution & performance](#pipeline-execution--performance))
- **Maker-checker approvals** — Submit, approve, reject, return and recall against a delegation-of-powers matrix, with a decision history
- **Risk checks** — Fraud signals (Beneish, Altman, Benford) and PEP/sanctions screening per case
- **Financial Advisor chat** — Context-aware analyst copilot powered by LLM
- **Real-time progress tracking** — SSE-based pipeline progress with section-by-section completion
- **PDF & one-pager export** — Downloadable CAM report and executive summary memo

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | Alpine.js 3.14, Chart.js 4.4; one component split into page modules (`src/ui/static/js/modules/`) |
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

On a CPU-only laptop (16 GB RAM) expect roughly 3–5 tokens/second; a full CAM (14 LLM-written
sections) was measured at **35–50 minutes** before the Ollama optimizations below (one context
size per run, compact prompts, shorter output limits for table-led sections, keep-alive), so
expect less — re-measure on your machine. Sections are written one at a time on Ollama. Each
section is saved as soon as it is written, so if a run fails part-way, running it again resumes
from the finished sections. Timeouts are set per section (`timeout_seconds`) and per chat reply
(`chat_timeout_seconds`).

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
│   │                       #   definition of validation → benchmarks → policy decision;
│   │                       #   cam_sections.py holds the CAM prompts, cam_llm_renderer.py
│   │                       #   writes them; cam_renderer.py is legacy (tests only)
│   ├── rendering/          # CAM markdown/HTML, CAM PDF, CRILC PDF
│   ├── models/             # Canonical data model (dataclasses)
│   ├── services/           # Integrations and persistence (SQLite, DMS, OCR, Probe42, chat)
│   ├── data/               # Company data (synthetic + real Indian corporates)
│   ├── core/               # Configuration, LLM providers, runtime paths
│   └── ui/                 # Alpine.js SPA: templates/index.html, static/js/app.js (core
│                           #   state + navigation) and static/js/modules/ (one file per page)
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
- An agent declares `requires` (agents that must succeed first) and `waits_for` (agents
  whose result it uses if present). Agents running at the same time must not write to
  `company_data` keys another independent agent reads.
- All LLM calls — CAM sections and chat — go through `src/core/llm_provider.py`; nothing
  else talks to an LLM API directly.

### Pipeline reliability

- Every run is recorded in `pipeline_runs` (`GET /api/cases/{id}/runs`), including failures.
- Each LLM-written CAM section is checkpointed as soon as it is written. Re-running after a
  failure reuses finished sections whose inputs (data, prompt, model, settings) are unchanged.
- Prompts live in `src/engines/cam_sections.py`; bump `PROMPT_VERSION` there when they change.

### Pipeline execution & performance

Agents start as soon as their dependencies finish:

```
data_ingestion ─┬─ financial_analysis ── benchmark ─┐
                └─ validation ──────────────────────┴─ policy ─┐
pep_screening ─────────────────────────────────────────────────┴─ narrative
```

The LLM execution path follows `active_provider` in `config/llm_providers.yaml` (also
**Settings → LLM Provider**):

| | Ollama (local) | Hosted (Gemini, OpenAI, Anthropic, Azure) |
|---|---|---|
| CAM sections at once | 1 (`providers.ollama.max_parallel_sections`) | `narrative.max_parallel_sections` (4) |
| Context size | One `num_ctx` for the whole run, so the model loads once; chat reuses it | Not applicable |
| Model residency | `keep_alive` (15m) keeps it loaded between runs and chat | Not applicable |
| Timeout | Streamed: `timeout_seconds` is the longest silence allowed, so a slow but working section finishes | SDK timeouts |
| Model routing (optional) | Table-led sections on a smaller model (e.g. `qwen2.5:3b`), run first as one group, then unloaded | Same mechanism, e.g. a cheaper model |
| Rate limits / server errors | — | Retried with backoff (`max_retries`, default 4) |
| Connections | — | One client per provider, shared by parallel sections |

For every provider: section data is sent as compact JSON; `narrative.section_max_tokens`
caps output for short, table-led sections; and a section cut off at its limit is logged as
`<provider> output hit the N-token limit`. Raise that section's limit if this repeats.

| Setting | Where | Effect |
|---|---|---|
| `pipeline.parallel_agents` | `settings.yaml` | `false` runs agents one at a time |
| `narrative.max_parallel_sections` | `llm_providers.yaml` | Sections written at once (a provider may lower it) |
| `narrative.section_max_tokens` | `llm_providers.yaml` | Per-section output limits |
| `providers.ollama.keep_alive` | `llm_providers.yaml` | How long Ollama keeps the model loaded (`0` = unload) |
| `providers.<id>.max_retries` | `llm_providers.yaml` | Retries for hosted providers |
| `providers.<id>.model_routing` | `llm_providers.yaml` | `enabled`, `routes: {model: [section ids]}`, `verify_figures` |

**Model routing** (off by default). Sections listed under a route are written by that model;
the rest by the provider's `model`. Routed sections run first as one group, then that model is
unloaded, so a run switches model once and the two are never in memory together. With
`verify_figures`, every figure in a routed section must appear in the data it was given
(after rounding, or as a fraction shown in percent); otherwise the section is rewritten by
the main model, in its group. Each section's model is recorded in the progress events and the
CAM's generation metadata. Compare a few CAMs with routing on before relying on it.

Document extraction results are cached per file in `storage/cache/extractions/`, keyed by
the file's content hash, so unchanged documents are not read again after an upload or a
restart. Deleting that folder only costs one re-read.

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
| Fraud | `POST/GET /api/companies/{id}/fraud-analysis` | Fraud detection analysis (UI: case detail → Risk Checks) |
| PEP screening | `GET /api/companies/{id}/pep-screening` | Directors against PEP/sanctions lists (UI: Risk Checks) |
| Document packs | `POST /api/companies/{id}/fetch-documents`, `GET /api/companies/supported-downloads` | Generate a company's document pack where supported |
| Verified data | `DELETE /api/companies/{id}/verified-public-data` | Remove the retained public-record snapshot |
| 360° View | `GET /api/companies/{id}/360` | Comprehensive entity view |
| Onboarding | `POST /api/onboard` | CIN/PAN-based company onboarding |
| Config | `GET/PUT /api/config/{section}` | Runtime configuration |
| LLM | `GET /api/llm/providers` | LLM provider management |

## Configuration

Configuration is managed via YAML files in `config/`:

- **settings.yaml** — Global platform settings, including `pipeline.parallel_agents`
- **llm_providers.yaml** — LLM provider configuration (Gemini, Ollama, OpenAI, etc.) and
  narrative settings: parallel sections, per-section output limits, Ollama keep-alive,
  retries (see [Pipeline execution & performance](#pipeline-execution--performance))
- **benchmarks.yaml** — Industry benchmark thresholds
- **rules.yaml** — Policy and validation rules
- **external_apis.yaml** — External data source configuration
- **approval.yaml** — Delegation of powers (approval authority levels). The shipped values are
  placeholders; replace them with your bank's approved matrix.

Secrets and machine-specific settings go in `.env.local` (see `.env.example`).

## Test Companies

The catalog seeds 6 companies with full data and document packs: APOL001 (Apollo Hospitals), INFY001 (Infosys), IHCL001 (IHCL), MFL001 (Madras Fertilisers), MRF001 (MRF) and PNCR001 (PNC Infratech). They cover different sectors and outcomes from approve to decline. More companies can be added through onboarding (`POST /api/onboard`) or manual entry.

## Documentation

- [Frontend ↔ Backend Integration](docs/FRONTEND_BACKEND_INTEGRATION.md) — Purpose of each screen, which control calls which endpoint, end-to-end flows
- [Architecture Reference](docs/ARCHITECTURE_REFERENCE.md) — Detailed technical architecture
- [Architecture Process Document](docs/ARCHITECTURE_PROCESS.md) — System design and data flow
- [Technical Documentation](docs/TECHNICAL_DOCUMENTATION.md) — Implementation details
- [Deployment & Storage Model](docs/DEPLOYMENT_STORAGE_MODEL.md) — Docker and cloud deployment
- [CAM Data-Point Source Matrix](docs/CAM_DATAPOINT_SOURCE_MATRIX.md) — Where each CAM field comes from
- [GCP Deployment Guide](documents/GCP_DEPLOYMENT.md) — Google Cloud Run setup
- [User Manual](documents/USER_MANUAL.md) — End-user guide

## License

Proprietary — All rights reserved.
