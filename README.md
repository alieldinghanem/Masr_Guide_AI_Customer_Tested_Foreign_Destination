# Masr Guide AI

**Explore Egypt and build an editable, day-by-day trip plan.** Search for places such as the Pyramids of Giza or Karnak Temple, ask the travel guide for suggestions in Arabic, English, or French, and organize your chosen places into a multi-day itinerary.

[Hosted preview](https://masr-guide-ai-customer-tested-foreign-8aro.onrender.com/) · [دليل التشغيل بالعربية](START_LOCAL_FIRST_AR.md) · [Quick start](#quick-start)

## What you can do

- **Explore destinations.** Browse Egyptian cities, historical sites, and beaches. Search the catalogue and use maps and travel information to decide where to go.
- **Plan a trip.** Pick your destinations and trip length to build a day-by-day itinerary. Adjust it as your plans change.
- **Ask the guide.** Request places to visit or ask a follow-up in Arabic, English, or French. The guide can use the local catalogue when its optional AI provider is unavailable.

### Try this example

Explore Cairo and Luxor, then ask the guide: **“What should I visit in Luxor if I like ancient Egyptian history?”** Build a five-day trip across the two cities. Open the itinerary to see which places are scheduled each day, then use the planner to adjust it.

> **بالعربي:** اكتشف أماكن ومعالم في مصر، واسأل المساعد عن اقتراحات، واعمل برنامج رحلة يوم بيوم تقدر تعدّله.

<p align="center">
  <img src="frontend/public/assets/brand/social-preview.png" alt="Masr Guide AI project preview" width="780">
</p>

## How it works

React provides the traveller interface and FastAPI serves the catalogue and trip planner. An optional Gemini or OpenAI integration helps answer guide questions. The itinerary validator checks trip edits and keeps the saved plan consistent.

This portfolio preview is for discovery and itinerary planning. Bookings and payments are outside its scope. The hosted preview can take time to start, and account features depend on its storage configuration.

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
