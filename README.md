> **Latest full-stack handoff (31 Oct 2026):** Start with [FINAL_FULLSTACK_QA_2026-10-31_AR.md](FINAL_FULLSTACK_QA_2026-10-31_AR.md). The AI chat is the homepage, with separate heritage/beach pages, mobile-first EN/AR navigation, and orange visual identity. Backend tests and offline customer QA passed, but the production React build/browser and live AI providers are still NOT VERIFIED in this build environment.

> **Company deployment note (30 Oct 2026):** This repository is a commercial-pilot candidate, not a verified live booking service. Start with [COMPANY_RELEASE_GATE_AR.md](COMPANY_RELEASE_GATE_AR.md) and run `python scripts/check_company_release.py` before any public launch. React browser and live Gemini checks remain required.

# Masr Guide AI — current repository entry (28 October 2026)

**Start here:** [START_HERE_VERIFIED_2026-10-28_AR.md](START_HERE_VERIFIED_2026-10-28_AR.md).
Run `OPEN_WEBSITE_WINDOWS.bat` for the actual local React + FastAPI site; wait for `[READY]` before opening `http://127.0.0.1:5173/` in a browser on the same PC. `VERIFY_LOCAL_WINDOWS.bat` reruns a local multi-suite QA report. `TEST_GEMINI_LIVE_WINDOWS.bat` is opt-in and requires a private local API key.

**Release truth:** Backend checks pass, but React production build/browser and a real Gemini call were not verified in the October 28 review environment due to missing npm access and no available API key. See the report; do not call this production-ready. Historical earlier-stage reports are preserved below for auditability.

---

# Masr Guide AI — ONE ENTRY POINT FOR LOCAL TESTING (17 October 2026)

**ابدأ من [START_HERE_2026-10-17_AR.md](START_HERE_2026-10-17_AR.md).**

- **Main React tourism website:** double-click `OPEN_WEBSITE_WINDOWS.bat`, wait for `[READY]`, then visit `http://127.0.0.1:5173/` on the same PC. Requires Python 3.11+, Node 20+ and npm internet access for first-time install.
- **Limited API-only demo when npm is unavailable:** double-click `RUN_FREE_DEMO_WINDOWS.bat`, wait for `[READY]`, then visit `http://127.0.0.1:8000/demo` on the same PC. **This is not React and is not a substitute for the main website.**
- Live Gemini requires configuring `backend/.env` locally; never publish secrets.
- Local/backend source checks passing **do not prove** a successful React build, Chromium UI or public production deployment. See `docs/LOCAL_RELEASE_VERIFICATION_2026-10-17_AR.md`.

---

# Masr Guide AI — current local-testing entry point (16 October 2026)

The current source is the **v7.8.1 baseline plus documented incremental fixes**. For the Windows local-first workflow use **`START_LOCAL_FIRST_AR.md`**, then `SETUP_AND_TEST_LOCAL_WINDOWS.bat` and `RUN_STARTUP_WINDOWS.bat`. See `LOCAL_TEST_STATUS_2026-10-16_AR.md` for freshly executed QA and environment-specific blocked checks. The main React tourism website runs on `http://localhost:5173`; `http://localhost:8000/demo` is only a mini demo, not a substitute for testing React.

**Release status:** source packaged for local acceptance; not yet a verified full-browser/real-Gemini or production deployment. Do not publish test accounts, private keys, or temporary SQLite data as a live customer service.

---

> **ابدأ التجربة المحلية من هنا:** [START_LOCAL_FIRST_AR.md](START_LOCAL_FIRST_AR.md). هذه حزمة المصدر كاملة؛ نجاح اختبارات Backend وحده لا يثبت React أو Gemini أو النشر.

> **Continuing the original Masr Guide AI project (16 Oct 2026):** Full repository handoff and up-to-date status: [CONTINUE_HERE_MASR_GUIDE_AI_AR.md](CONTINUE_HERE_MASR_GUIDE_AI_AR.md). **232/232 Python tests, 27/27 local HTTP checks, 52/52 corrected offline conversation checks** ran successfully. React compilation/Chromium and real Gemini integration remain **BLOCKED / NOT EXECUTED** here. Do not describe this source as a verified production launch. Existing earlier release history below is retained for auditability.

> **Part 2 actual-code audit (16 October 2026):** [Engineering patch and executed QA report](docs/PART2_ENGINEERING_AUDIT_2026-10-16_AR.md). Backend 228/228 and Node contract 4/4 passed; React build, compiled-browser E2E, live Gemini and deployment still BLOCKED/NOT EXECUTED. Earlier 219-test status below is historical.

> **Single-source handoff (16 October 2026):** Start with [START_HERE_DELIVERY_AR.md](START_HERE_DELIVERY_AR.md). Full copyable build/review prompt: [docs/MASTER_PROMPT_MASR_GUIDE_AI.md](docs/MASTER_PROMPT_MASR_GUIDE_AI.md). Earlier version notes below are historical; frontend build, real browser and live Gemini remain unverified here.

> **Latest audited source patch v7.8.1:** See [FINAL_RELEASE_STATUS_AR.md](FINAL_RELEASE_STATUS_AR.md) for executed tests and mandatory deployment gates.

> **v7.8 — Portfolio release candidate.** Full-stack Egypt tourism platform with destination discovery, planning, account-based trip storage, CMS and an AI companion. New: Gemini rolling-model compatibility fix, cloud save from the guide, tested SQLite account backup, unified fail-closed release verification. Run `VERIFY_FULL_RELEASE_WINDOWS.bat` before putting any live link on a CV. See `docs/PORTFOLIO_RELEASE_V7_8_AR.md` for exact validated and blocked tests. This is **not** a production booking platform.

> **Current candidate:** v7.7 verification release. See [START_HERE_V7_7_AR.md](START_HERE_V7_7_AR.md) for the browser CI gate, real Gemini opt-in smoke test, and unverified production requirements.

# v7.6 Hardening Update (15 October 2026)

Security and data-integrity fixes: actual streamed-request body limits, stricter
trip stop validation, production optimistic concurrency enforcement, account
and session erasure, closing SQLite connections, deployment safeguards and
database readiness. See [`docs/RELIABILITY_AUDIT_V7_6_AR.md`](docs/RELIABILITY_AUDIT_V7_6_AR.md).

**Status: Portfolio candidate, NOT verified production-ready.** React dependencies
could not be installed in the audit container (missing npm cache tarball); full
React build, browser E2E, live Gemini, dependency vulnerability scan, external
security audit, live hosting and backup/restore drills remain release blockers.

---

**v7.5 Reliability Hardening (latest):** Additional credential/partner abuse throttling, saved-trip validation, optimistic concurrency on saved conversations, safer partner redirects and expanded adversarial tests. Local backend 170/170 passed; corrected Chatbot QA 52/52, original 50/52; full React build, live Gemini and deployment remain unverified. See [Arabic release notes](START_HERE_V7_5_AR.md) and [risk register](docs/RELIABILITY_HARDENING_V7_5_AR.md).

**v7.4 transactional safety update:** See [Arabic quick start](START_HERE_V7_4_AR.md) and [transactional AI guard verification](docs/TRANSACTIONAL_AI_GUARDS_V7_4_AR.md). This update prevents unauthorized destination swaps, rejects invalid trip states, and preserves prior state on rejected edits. Backend 143/143 passed; corrected offline QA 52/52 passed; React build and live Gemini are not yet independently verified.

**v7.3 release review:** See [START_HERE_V7_3_AR.md](START_HERE_V7_3_AR.md) and [release QA report](docs/RELEASE_QA_V7_3_AR.md) for verified tests, legacy QA caveats and deployment limitations. This is a portfolio release candidate, **not a production-approved travel booking service**.

# Masr Guide AI — TravelTech Portfolio v7.2

**Current release:** improved multilingual tourist intent routing, explicit day-allocation parsing, safe AI outage fallback, and opt-in account-backed conversation save/restore/delete. The full app includes discovery, trips, content and partner demos, but **does not process real reservations/payments**. See [Arabic release notes](docs/AI_AND_STARTUP_RELEASE_V7_AR.md) and [Windows quick start](START_HERE_V7_AR.md).

**QA:** 99/99 backend tests passed; frontend syntax checked. React production build and live Gemini/hosting are not validated in the build environment. Use GitHub Actions and local `npm ci && npm test && npm run lint && npm run build` before a public demo.

---

# Masr Guide AI · TravelTech Global Tourism UI Portfolio v6.0

**Discover Egypt · Plan smarter · Travel better**

An Egypt-focused **full-stack travel-discovery and planning portfolio application** with an editorial tourism website, multilingual AI travel companion, curated attraction data, saved itineraries, a configurable cost calculator, and content/partner operations tooling. This is an **MVP/portfolio release, not a live travel booking agency**.

## What works

| Product area | Implemented |
|---|---|
| Destination and attraction discovery | Curated catalogue (12 cities / ~40 attractions), searchable places, maps and bilingual pages |
| Tourism experiences and practical travel info | Interest-based experiences, useful external institutional sources |
| Editorial travel journal | Seeded articles, published/draft state, authoring through a staff CMS |
| AI guide | Gemini integration using server-only API key, fallback to catalogue-based guide, sourced tourism responses |
| Itinerary planner | 1–30 days, interest selection, validated daily planning, revisions via conversation; unbooked editorial suggestions for free days |
| Travel budget | Editable EGP budget calculator based on traveller inputs; **not live prices** |
| Traveler accounts | Password-hashed signup/login, revocable sessions, trip create/read/update/delete, server-side trip isolation |
| Saved places | Browser-local favourites |
| Commercial operations | Partner enquiries (disabled by default), staff review, manually approved external offers, privacy-minimal outbound-click counters |
| Administration | Protected editorial CMS and partner-offer dashboard (separate server-side staff token) |
| Portfolio presentation | Project case-study page + docs + CI + Docker/Render deployment recipes |

## Quick start: Windows / VS Code

Install Python 3.11+ and Node.js 20+ (Node 22 recommended).

1. Download/extract this repository; open the **Masr_Guide_AI** root in VS Code.
2. Backend: `cd backend && python -m pip install -r requirements-dev.txt`, then `python -m uvicorn app.main:app --reload --port 8000`.
3. In a **second** terminal: `cd frontend && npm ci && npm run dev`.
4. Open **http://localhost:5173**. This is the main website, **not** `/demo`.
5. Open **http://localhost:8000/docs** to explore FastAPI endpoints.

Or, run `RUN_STARTUP_WINDOWS.bat` from the repository root (opens two windows and performs the normal setup).

### Gemini (optional)

Copy `backend/.env.example` to `backend/.env` and set **your NEW, private** `GEMINI_API_KEY`. `GEMINI_MODEL=gemini-3.1-flash-lite` selects the model verified on the current free project; availability and quotas vary by project. Turn on `GEMINI_SEARCH_GROUNDING=true` only after reviewing its quotas and terms; a live search must be confirmed using returned grounding metadata. Read `GEMINI_SEARCH_GROUNDING_START_HERE_AR.md` for details. Google's free tier may use prompts to improve its products; avoid personal data. **Never commit `.env`, screenshots with secrets, or leaked keys.** Without Gemini, the local catalogue guide and planning engine still work.

### Staff CMS (optional)

Set a random, server-only `ADMIN_API_TOKEN` **at least 24 characters long** before starting the backend. Access the private console at `/#/staff` and enter that token. Staff credentials are **not** traveller accounts. Content drafts and offers stay unpublished until enabled.

For partner interest intake, set `PARTNER_INQUIRIES_ENABLED=true` only once you are ready to collect, protect, and handle emails. It is **false by default**.

## Build and tests

```bash
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q

cd ../frontend
npm ci
npm test
npm run lint
npm run build
```

The GitHub Actions workflow under `.github/workflows/ci.yml` runs these checks on push/PR. **Do not describe frontend CI as passing until you see its green status in your own repository.**

## Run both tiers as a single Docker service

```bash
docker compose -f docker-compose.prod.yml up --build -d
# website and backend: http://localhost:8000
# stop: docker compose -f docker-compose.prod.yml down
```

Docker Compose uses the persistent local named volume `masr_data` for SQLite. For Render hosting, `render.yaml` offers a simple **portfolio preview** service using GitHub + Docker. **Free Render instances use ephemeral storage**; account records, staff edits, trip saves, and referral click counts can disappear on restart/redeploy. Do **not** use the free configuration as a durable production service with real user data. Upgrade to paid persistent disk and backup procedures or migrate to a managed database before onboarding real customers. See `docs/DEPLOY_GITHUB_RENDER_AR.md`.

Visitor star ratings and comments use the tourism SQLite database and now require a signed-in traveler account. One account can revise its vote and comment for a place or coastal destination; the public sees a generated member alias, not the account email. The account export includes reviews, and account deletion removes them. Prior browser-only anonymous submissions are excluded from public listings. Account membership does **not** verify a visit. Comments reject links and email addresses and public submissions have a basic per-peer rate limit. They persist across normal page reloads but can disappear when the free Render instance is recreated or redeployed. New account registration is disabled on that temporary-storage preview; one-click Google OAuth is not configured. Before using reviews as a durable public feature, provide persistent storage, backups, and a moderation workflow, then verify recovery.

## Architecture

```text
Browser (React/Vite, Arabic + English, discovery-first)
   |
   | /api calls (same origin in Docker / Vite proxy in dev)
   v
FastAPI service
   |-- Discovery catalogue + article CMS
   |-- Gemini + RAG + deterministic planner
   |-- Accounts and saved trips
   |-- Partner enquiries, offers and referral redirects
   |-- Staff operation endpoints (token protected)
   |
   +-- SQLite MVP storage (persistent volume required in production)
```

## HR / recruiter quick demo (5 minutes)

Open `/#/project` for the case study. Then demonstrate: Discover Egypt → attractions → ask the AI about Karnak → create a 14-day plan → adjust it → calculate an example budget → register a **test account** and save the trip → show the Journal → open the Staff CMS if privately authorised. Staff CMS and partner referrals are **demonstration infrastructure**, not proof of real travel bookings or earned commissions. See `docs/HR_DEMO_SCRIPT_AR.md`.

## Important limitations / honesty policy

- **No real bookings, prices, hotel inventory, payouts, credit-card processing, live travel availability, or established partner contracts.** Approved external offers can be added after real partner agreements.
- The catalogue is curated but small. Extra days carry clearly identified optional themes, not fabricated attraction reservations. Road/flight times are estimates, not live routing.
- RAG and AI outputs require verification of changing hours/visa/prices. Gemini costs and provider availability are external dependencies.
- No email verification, password reset, robust edge rate-limiting, managed Postgres, full compliance audit, or independent security penetration test. Configure TLS, a protected reverse proxy, logging and database backups before public onboarding.
- React dependency install / production build must pass on your PC and in GitHub CI. The package was assembled with backend tests passing and JSX syntax checked, **but no successful React build/browser proof is claimed for this environment**.
- Confirm licensing of all photos/assets before public commercial marketing.

For global UI design decisions, see `docs/V6_GLOBAL_BENCHMARK_AR.md` and for photography attribution/hosting issues see `docs/EDITORIAL_IMAGE_CREDITS.md`.

For Arabic setup and GitHub/Render steps: **`docs/DEPLOY_GITHUB_RENDER_AR.md`**. For commercialization boundaries and the next stage: **`docs/PRODUCTION_GAPS_AR.md`**.


## Current QA improvement — v7.2 (15 October 2026)

The earlier 3 real stop-day coverage failures are now addressed by spreading unique
curated stops over longer stays, adding 10 ministry/UNESCO-backed Cairo landmarks,
and suggesting a disclosed multi-city route for a long Egypt trip where the user
specified no destinations. Existing explicit destination requirements are not overwritten.

**118/118 backend tests pass.** The 67-case local API probe passes **52/52 of the
corrected acceptance criteria**. The original v7 acceptance script remains verbatim
as `qa_chatbot/legacy_acceptance_v7.py`, where **50/52 pass**; Q49 and Q52 were
logically contradictory to correctly replacing Hurghada with Sharm El Sheikh.
The corrections, score comparison and limitations are documented in
`docs/V7_2_52_OF_52_QA_AR.md`. The CI workflow reruns the corrected suite.

**NOT PRODUCTION READY:** these tests are local/offline only. React production
build, real Gemini answers and real-world travel pricing/transport times have
not been verified. A 60% stop-day coverage threshold is an acceptance heuristic,
not proof that a trip is feasible, priced, bookable or enjoyable.

## Latest tested code patch (v7.1 — 15 October 2026)

The independently tested **v7.1 QA remediation** closes multiple critical local chatbot and itinerary errors. **112 Backend tests pass** and the original independent offline acceptance suite reports **47/52 Pass** (v7 baseline was 22/52). Three true travel-catalog coverage failures remain; two other false negatives are legacy benchmark defects. Frontend production build and live Gemini testing remain unverified.

Read `docs/V7_1_CODE_FIX_QA_AR.md` before deploying.
