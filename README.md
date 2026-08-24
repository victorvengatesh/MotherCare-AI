# MotherCare AI — Bilingual Maternal Health Decision Support

[![CI](https://github.com/victorvengatesh/MotherCare-AI/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/victorvengatesh/MotherCare-AI/actions/workflows/ci-cd.yml)

> A Tamil-and-English maternal-health decision-support prototype that combines symptom analysis, multi-agent routing, retrieval-augmented generation and pregnancy risk tracking.

> **Safety notice:** MotherCare AI is an educational and research prototype. It does not diagnose, prescribe or replace licensed medical care. Urgent or severe symptoms should be handled by qualified clinicians or local emergency services.

---

## Why this project exists

Pregnancy-related questions often arrive as unstructured descriptions rather than clean clinical data. MotherCare AI explores how an AI-assisted system can organize those inputs, route them to specialized reasoning paths, preserve context and surface risk signals while keeping a human-in-the-loop safety boundary.

The goal is not autonomous medicine. The goal is to study how a dependable software system can support preliminary triage, structured tracking and safer escalation.

---

## Core capabilities

- **Bilingual interaction** — Tamil and English user flows
- **Multi-agent routing** — routes requests to specialized maternal-health, nutrition, mental-health or emergency-oriented logic
- **RAG knowledge retrieval** — retrieves relevant medical knowledge for grounded responses
- **Pregnancy digital twin** — tracks selected maternal biomarkers and longitudinal state
- **Risk analytics** — supports rule/model-based signals for conditions such as anemia, gestational diabetes and pre-eclampsia risk
- **Health records** — persists user history and structured records
- **Document analysis** — accepts supported health-report uploads for extraction/analysis workflows
- **Image-analysis research path** — experimental classification workflow for selected image categories
- **Resilience controls** — validation, error handling, rate limiting and circuit-breaker patterns

---

## Architecture

```text
React frontend
      │
      ▼
FastAPI API
      │
      ├── Authentication / validation
      ├── Symptom + risk analysis
      ├── Multi-agent orchestration
      ├── Digital-twin state
      ├── Health-record workflows
      │
      ├── Gemini / model adapters
      ├── RAG / vector retrieval
      └── SQLAlchemy persistence
```

### Main stack

**Backend:** Python · FastAPI · Pydantic · SQLAlchemy  
**Frontend:** React · Vite  
**AI:** Gemini integration · RAG · NLP/rule-based fallback paths  
**Data:** SQLite for local development · vector-store integration for retrieval  
**Engineering:** Docker · GitHub Actions · pytest · validation and resilience utilities

---

## Repository layout

```text
MotherCare-AI/
├── backend/              FastAPI service, models, routes, services and tests
├── frontend/             React application
├── model/                Model-training / experimentation code
├── .github/              Automation and CI configuration
├── docker-compose.yml    Local multi-service startup
├── ARCHITECTURE.md       Architecture notes
├── DEPLOYMENT_GUIDE.md   Deployment guidance
└── README.md
```

The repository also contains historical implementation reports produced during development. They document project evolution, but this README is the primary source for the current project overview.

---

## Quick start

### Docker

```bash
git clone https://github.com/victorvengatesh/MotherCare-AI.git
cd MotherCare-AI

cp production.env.example .env
# Replace every CHANGE_ME / replace_this value before continuing.

# Linux/macOS: generate local development TLS files
./scripts/generate_certs.sh

# Windows PowerShell alternative
# .\scripts\generate_certs.ps1

docker compose up --build
```

Typical local services:

- Frontend: `http://localhost:3000` or the port configured by the frontend runtime
- Backend API: `http://localhost:8000` / `8001` depending on the selected run command
- FastAPI docs: `/docs`

### Manual development

```bash
# Backend
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Replace the required secret placeholders in .env.
python -m uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

---

## Testing

Backend tests live under `backend/tests/`.

```bash
cd backend
pytest -v
```

Where coverage tooling is installed:

```bash
pytest --cov=app
```

Performance, security and coverage numbers should be treated as measured results only when they are backed by a reproducible test run or CI artifact. This repository intentionally avoids presenting estimated values as guarantees.

---

## Safety design

MotherCare AI treats medical AI as **decision support**, not autonomous clinical authority.

Key design principles:

- explicit emergency escalation paths
- input validation before analysis
- fallbacks when external model services are unavailable
- human-readable outputs instead of hidden autonomous actions
- separation between informational guidance and medical diagnosis
- persistence of structured context for longitudinal review

The system should not be deployed for real clinical use without appropriate medical validation, privacy review, security assessment, regulatory analysis and supervised evaluation on representative data.

---

## Security notes

The project includes authentication, validation, rate-limiting and security-oriented middleware patterns. Those controls reduce common application risks but **do not by themselves establish formal OWASP compliance or clinical-grade security certification**.

Before any real-world deployment, perform at minimum:

- dependency and secret scanning
- authentication/authorization review
- threat modeling
- database and privacy review
- penetration testing
- production logging/monitoring design
- clinical data-governance review

Never commit API keys, tokens or patient-identifying data.

---

## Current engineering priorities

- strengthen real-world dataset quality and model evaluation
- improve automated test coverage and CI evidence
- consolidate historical development documentation
- add clearer experiment and benchmark reporting
- strengthen privacy/security review for health-data workflows
- improve deployment observability and failure monitoring

---

## Project status

**Status:** active research / portfolio prototype  
**Primary use:** learning, experimentation, demonstration and engineering research  
**Not intended for:** unsupervised medical diagnosis or emergency decision-making

---

## License

See the repository license file if present. Third-party models, APIs, datasets and medical references remain subject to their own terms and licenses.

---

Built by **M. Victor Vengatesh**.
