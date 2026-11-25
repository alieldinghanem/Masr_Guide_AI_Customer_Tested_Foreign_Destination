# Masr Guide AI 🇪🇬

### Discover Egypt. Plan your trip. Keep the conversation going.

Masr Guide AI is a full-stack travel discovery and conversational trip-planning platform focused on Egypt. It helps travelers explore attractions, discover coastal destinations, and create personalized itineraries through a multilingual travel assistant.

[Open the hosted preview](https://masr-guide-ai-customer-tested-foreign-8aro.onrender.com/) · [Quick start](#quick-start) · [دليل التشغيل بالعربية](START_LOCAL_FIRST_AR.md)

The platform combines a curated, source-linked tourism catalog with a structured itinerary engine and optional Gemini or OpenAI integration. The app validates trip edits and preserves unrelated trip details.

## Key Features

- **Multilingual travel assistant:** Arabic, English, and French, with conversation context and follow-up recommendations.
- **Conversational itinerary planning:** Create and revise trips of 1–30 days, including city allocations and day-specific changes.
- **Family-aware planning:** Activity limits, rest allowances, and approximate intercity transfer estimates.
- **Destination discovery:** Searchable attractions, museums, heritage sites, and coastal destinations with reference sources.
- **Traveler accounts:** Email and password sign-in, optional Google sign-in, saved trips, and account data controls.
- **Traveler community:** Posts, replies, likes, ratings, comments, and reporting tools, subject to moderation configuration.
- **Transparent AI behavior:** The app distinguishes model-generated answers, local planning, and fallback responses.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI, Pydantic |
| Storage | SQLite for local development, PostgreSQL support |
| AI | Optional Gemini and OpenAI integrations |
| Delivery | Docker, GitHub Actions, Render |
| Testing | pytest, Vitest, React Testing Library, Chromium E2E |

## Project Status

Masr Guide AI is an actively developed TravelTech MVP with a hosted preview. Feature availability depends on the deployed version and service configuration. Google sign-in, transactional email, AI providers, and community publishing each require setup.

The app supports trip discovery and planning. Bookings and payments are outside its scope. Travel times are estimates. Verify prices, opening hours, transport schedules, and availability with official providers.

## Live Preview

[Open Masr Guide AI](https://masr-guide-ai-customer-tested-foreign-8aro.onrender.com/). The Render service may take a moment to start.

**Try this example.** Ask, “What should I visit in Luxor if I like ancient Egyptian history?” Then build a five-day trip across Cairo and Luxor and revise one day in the planner.

<p align="center">
  <img src="frontend/public/assets/brand/social-preview.png" alt="Masr Guide AI project preview" width="780">
</p>

## Engineering Approach

- Validated, structured trip state
- Regression tests for multilingual planning and trip edits
- Account authorization and data-isolation checks
- Automated frontend, backend, and browser testing
- Explicit handling of unavailable external services

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
.\backend\.venv\Scripts\Activate.ps1
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
