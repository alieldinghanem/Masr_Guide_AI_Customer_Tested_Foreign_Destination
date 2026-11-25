# Masr Guide AI

<p align="center">
  <img src="frontend/public/assets/brand/social-preview.png" alt="Masr Guide AI — discover Egypt and build smarter itineraries" width="900">
</p>

<p align="center">
  <a href="https://github.com/alieldinghanem/Masr_Guide_AI_Customer_Tested_Foreign_Destination/actions/workflows/ci.yml"><img src="https://github.com/alieldinghanem/Masr_Guide_AI_Customer_Tested_Foreign_Destination/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=111827" alt="React 18">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker ready">
</p>

<p align="center">
  A multilingual, full-stack Egypt travel discovery and itinerary-planning portfolio project.
</p>

<p align="center">
  <a href="https://masr-guide-ai-customer-tested-foreign-8aro.onrender.com/"><strong>Live demo</strong></a>
  ·
  <a href="START_LOCAL_FIRST_AR.md"><strong>دليل التشغيل بالعربية</strong></a>
  ·
  <a href="#quick-start"><strong>Quick start</strong></a>
</p>

## Overview

Masr Guide AI helps visitors discover Egyptian destinations, ask a multilingual travel guide for grounded suggestions, and create editable multi-day itineraries.

The application combines a React interface with a FastAPI backend. Gemini or OpenAI can provide optional AI responses, while the application's validated itinerary engine remains the authoritative source of trip state. A local catalogue-based fallback keeps the core experience usable when an AI provider is unavailable.

> **Portfolio scope:** This project is a travel-planning and product-engineering demonstration. It does not process real bookings, payments, hotel inventory, live prices, or confirmed partner reservations.

## Highlights

- **Egypt discovery:** Curated destinations, attractions, coastal locations, maps, search, editorial content, and practical travel information.
- **Validated trip planning:** Build and revise 1–30 day itineraries while preserving explicit cities, day allocations, and unrelated trip choices.
- **Multilingual guide:** Arabic, English, and French conversation flows with contextual follow-ups and catalogue-backed recommendations.
- **Traveler accounts:** Saved trips, ratings, comments, export, and deletion flows with server-side data isolation.
- **Operational tooling:** Protected content management and partner-offer demonstrations, disabled or restricted by default.
- **Resilient AI integration:** Optional Gemini/OpenAI providers, honest fallback behavior, server-side keys, rate limits, and release checks.
- **Responsive product experience:** Mobile and desktop layouts, RTL support, accessible components, and production-build browser testing.

## Live demo

Open the [hosted portfolio preview](https://masr-guide-ai-customer-tested-foreign-8aro.onrender.com/).

The free Render service may need time to wake up. Its default storage is not a durable customer-data service, so accounts or saved data can be reset after redeployment. New public registration may be disabled unless persistent storage is configured.

## Architecture

```text
Browser
  └─ React + Vite
       ├─ discovery and search
       ├─ multilingual guide
       ├─ itinerary planner
       └─ traveler account experience
             │
             ▼
FastAPI
  ├─ catalogue and editorial APIs
  ├─ deterministic itinerary validation
  ├─ optional Gemini / OpenAI integration
  ├─ accounts, trips, ratings, and comments
  └─ protected staff operations
             │
             ▼
SQLite for local development
PostgreSQL-compatible configuration for durable deployments
```

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Vite, Vitest, Testing Library, ESLint |
| Backend | Python 3.12, FastAPI, Pydantic, Uvicorn |
| Data | SQLite for local development, PostgreSQL support for deployment |
| AI | Optional Gemini or OpenAI, plus catalogue-based fallback |
| Quality | Pytest, contract tests, planner stress tests, Chromium desktop/mobile E2E |
| Delivery | Docker, Docker Compose, GitHub Actions, Render blueprint |

## Quick start

### Requirements

- Python 3.11 or 3.12
- Node.js 20+ (Node.js 22 recommended)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/alieldinghanem/Masr_Guide_AI_Customer_Tested_Foreign_Destination.git
cd Masr_Guide_AI_Customer_Tested_Foreign_Destination
```

### 2. Set up the backend

```bash
python -m venv backend/.venv
```

Activate the environment:

```powershell
# Windows PowerShell
backend\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source backend/.venv/bin/activate
```

Install dependencies and run the API:

```bash
pip install -r backend/requirements-dev.txt
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Set up the frontend

In a second terminal from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

Open:

- Website: http://localhost:5173
- API documentation: http://localhost:8000/docs
- Readiness check: http://localhost:8000/api/ready

Windows users can follow [START_LOCAL_FIRST_AR.md](START_LOCAL_FIRST_AR.md) and use the included setup and launcher scripts.

### Optional AI provider

The catalogue and deterministic planner work without a live AI key. To enable an AI provider, copy `backend/.env.example` to `backend/.env`, configure the provider and model, and add a private server-side API key.

Never place an API key in frontend code or commit `.env` files.

## Tests and quality gates

Run the main local checks:

```bash
cd backend
python -m pytest -q

cd ../frontend
npm ci
npm test
npm run lint
npm run build
```

The [GitHub Actions workflow](https://github.com/alieldinghanem/Masr_Guide_AI_Customer_Tested_Foreign_Destination/actions/workflows/ci.yml) also runs:

- backend tests and source-secret checks;
- frontend unit tests, lint, and production build;
- conversation and API contract checks;
- a 1,500-scenario planner stress suite;
- compiled React + FastAPI desktop/mobile Chromium E2E.

Automated checks use isolated or mocked provider behavior unless a live-provider test is explicitly started. A green CI run does not prove live AI availability, production security, storage durability, or real-world travel accuracy.

## Repository structure

```text
backend/        FastAPI application, data access, AI adapters, and tests
frontend/       React application, public assets, and frontend tests
scripts/        release, security, backup, browser, and QA tooling
qa_chatbot/     conversational acceptance and regression checks
docs/           engineering, deployment, product, and audit documentation
Dockerfile      production-style single-service build
render.yaml     Render portfolio-preview blueprint
```

## Docker

Build and run the integrated app:

```bash
docker compose -f docker-compose.prod.yml up --build
```

Then open http://localhost:8000.

For any real deployment, configure a durable database, backups, TLS, protected administration, monitoring, and reviewed secrets before enabling public accounts.

## Important limitations

- No real bookings, payment processing, hotel inventory, live pricing, or guaranteed partner offers.
- AI answers and changing travel details such as opening hours, visas, transport, and prices require independent verification.
- The free hosted preview may use temporary storage.
- Production use requires a security review, durable database, tested backup and recovery, moderation, and operational monitoring.
- Confirm licensing and attribution for all media before commercial use.

## Documentation

- [Arabic local setup](START_LOCAL_FIRST_AR.md)
- [Deployment guidance](docs/DEPLOY_GITHUB_RENDER_AR.md)
- [Production gaps](docs/PRODUCTION_GAPS_AR.md)
- [Photography credits](docs/EDITORIAL_IMAGE_CREDITS.md)
- [Recruiter demo script](docs/HR_DEMO_SCRIPT_AR.md)

---

Built as a full-stack AI travel-product portfolio project focused on transparent behavior, validated state changes, and practical release engineering.
