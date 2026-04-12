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
- (Optional) Ollama for local LLM inference
- (Optional) Docker for containerized deployment

### Local Development

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1 # Windows

# Install dependencies
pip install -r requirements.txt

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
│   ├── api/            # FastAPI endpoints (50+ routes)
│   ├── agents/         # Super-agent pipeline orchestration
│   ├── engines/        # 14 analytical engines
│   ├── models/         # Canonical data model (dataclasses)
│   ├── services/       # Business services (onboarding, extraction, chat, etc.)
│   ├── data/           # Company data (synthetic + real Indian corporates)
│   ├── core/           # Core utilities and configuration
│   └── ui/             # Alpine.js SPA frontend
├── config/             # YAML configuration (benchmarks, rules, LLM providers)
├── prompts/            # LLM system prompts per CAM section
├── scripts/            # Deployment, testing, and data generation scripts
├── tests/              # Unit and integration tests
├── postman/            # Postman collections for API testing
├── storage/            # Document storage (runtime)
├── runtime-db/         # SQLite database (runtime)
└── documents/          # User documentation
```

## API Endpoints (Summary)

| Category | Endpoints | Description |
|----------|-----------|-------------|
| Dashboard | `GET /api/dashboard` | Platform overview metrics |
| Companies | `GET/POST/DELETE /api/companies` | Company CRUD & catalog |
| Cases | `GET/POST /api/cases/{id}` | CAM case management |
| Pipeline | `POST /api/cases/{id}/run` | Run full CAM pipeline (SSE) |
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

## Test Companies

The platform includes 22 pre-configured companies (18 inspired by real Indian corporates + 4 synthetic) covering diverse sectors, risk profiles, and case types (NTB/ETB).

## Documentation

- [Architecture Reference](ARCHITECTURE_REFERENCE.md) — Detailed technical architecture
- [Architecture Process Document](docs/ARCHITECTURE_PROCESS.md) — System design and data flow
- [Technical Documentation](docs/TECHNICAL_DOCUMENTATION.md) — Implementation details
- [Deployment & Storage Model](DEPLOYMENT_STORAGE_MODEL.md) — Docker and cloud deployment
- [GCP Deployment Guide](documents/GCP_DEPLOYMENT.md) — Google Cloud Run setup
- [User Manual](documents/USER_MANUAL.md) — End-user guide

## License

Proprietary — All rights reserved.
