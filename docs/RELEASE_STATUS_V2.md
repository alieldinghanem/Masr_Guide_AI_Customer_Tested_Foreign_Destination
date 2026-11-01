# Masr Guide AI v2.0 — Release verification snapshot

**Type:** Source-code release candidate / private GitHub upload bundle. Not a certified production deployment.

## Verified in this delivery environment

- Archive extracted successfully; project layout and source files inspected.
- Backend unit/integration suite: **72 passed** via `python -m pytest -q` in `backend/` on 2026-10-15.
- `.env` and credential files are excluded from the delivered ZIP. Environment examples contain empty placeholder variables.
- The ZIP was CRC checked after packaging.

## Not verified here

- `npm ci`, React build, JS unit tests, and real browser E2E: `npm ci` failed in the delivery environment with npm CLI `Exit handler never called`, so these checks are **BLOCKED**, not passed.
- Live Gemini API response using user's actual credential: **NOT RUN**. Key must remain local.
- Docker deployment / cloud hosting: **NOT RUN**.
- Attraction source verification, asset-image rights and legal/commercial release approval: **NOT COMPLETED**.

## Functional scope and constraints

- Frontend: React + Vite, trip exploration, maps and conversational planner.
- Backend: FastAPI, deterministic itinerary planner, BM25 tourism retrieval, optional Gemini API calls.
- Free/demo mode works using supported local planner phrasing without API credentials; it does **not** provide general-purpose LLM understanding.
- Chat can create and edit the supported 1–30 day trip state. More complex unconstrained travel requests depend on LLM availability and input validation.
- No real-time tickets, hotels, route or price API; use as an illustrative planner.

## Publication gate

Run all CI checks, manual multilingual trip tests and live Gemini checks before presenting the public site as fully verified. Keep the repository private initially.
