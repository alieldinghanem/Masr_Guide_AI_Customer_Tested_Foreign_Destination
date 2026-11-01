# Masr Guide AI — v7.1: Code Fixes and Independent Regression Results

**Date:** 2026-10-15

**Release classification:** QA remediation / development candidate. **NOT a production-ready tourist safety, booking or travel-assistance service.**

## Changes actually implemented

- Added risk-aware deterministic responses for medical emergencies, threats to personal safety, unsafe diving/weather questions, and sharing payment-card details. These are limited general safety directions; there is no live emergency hotline or weather verification.
- Prevented a recognized but unsupported destination (e.g. Marsa Matrouh) from silently becoming Cairo.
- Fixed planning intent: Hurghada is classified as a beach destination even when the user did not literally write “beach”. “First week at the beach” is now 7 days, not half the trip.
- Added basic recognition of family travelers with children.
- Allowed **existing** trip state to change total duration, add an explicit EGP budget, and insert an additional supported city (where the schedule has sufficient room). Duration reallocation is proportional, not optimized or budget verified.
- Added French greeting and language switch handling, French transport expressions, one-day trip phrasing, and rejection of 300-day requests beyond the supported range.
- Added local responses to food, Ramadan, visas, phone SIMs, currency, live ticket questions, and transport prices, with caveats about unverified real-time data.
- Added account conversation deletion guidance; messages do not silently delete user data.
- Added 13 test cases covering these corrections, including P0 situations and multi-turn state mutations.

## Executed QA in this release

| Test | Outcome | Limit |
|---|---|---|
| Existing plus new FastAPI tests | **112 / 112 Passed** | Unit + TestClient coverage, not public internet or real visitors |
| Previously established 52 offline QA acceptance checks | **47 / 52 Passed** (v7 baseline: 22 / 52) | Offline fallback / deterministic planning; **not a Gemini accuracy score** |
| Original six P0 failed acceptance criteria | Passed in re-run | Scenarios sampled, no general safety guarantee |
| React production build | **NOT VERIFIED**: `vite: not found` | npm dependencies not available in valid installed state |
| Live Gemini evaluation | **NOT RUN** | No authorized live key used |
| Browser and mobile E2E | **NOT RUN** | Requires working built frontend |
| Real booking, live fares, actual commercial revenue | **NOT IMPLEMENTED / NOT VERIFIED** | Needs licensed providers and contracts |

## Remaining five acceptance failures

**Three genuine, open P1 issues:** the curated attractions database does not fill 60% of stop-days on 14/20/30 day plans. Do **not** invent hotel bookings, prices or unverified attractions to pass these metrics. Expand verified attractions and activity coverage, improve scheduling and validate travel-time feasibility.

**Two scoring artifacts in the original QA benchmark:**
- Q49 erroneously looks for *Hurghada after the test has successfully replaced it with Sharm El Sheikh*. The beach phase is correctly present; inspect `trip_state` and test against the **new** destination.
- Q52 expects the literal failure text "could not identify" on a **successful** edit. A correctly applied edit should *not* claim failure.

Scores are presented unmodified for comparability; do not massage the legacy benchmark to conceal the above.

## Next release gates before public launch

1. Improve verified catalog completeness and address three actual P1 coverage failures.
2. Add tests for varied safety phrasing (without claiming that templates cover all emergencies), language and grounded source quality.
3. Run `npm ci`, `npm test`, `npm run lint`, `npm run build`; inspect desktop/mobile screens and conduct E2E tests.
4. Test Gemini live using a NEW, protected key in a controlled staging environment; evaluate groundedness, injection resistance, token cost and timeouts.
5. Validate database persistence, production authentication/security, edge rate limits, privacy notices and real deployment.
6. Create real affiliate/partner agreements before claiming confirmed bookings or revenue.

## Run locally

From the project root, on Windows:

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest -q
cd ..
python qa_chatbot/blackbox_probe.py
python qa_chatbot/acceptance_evaluation.py
```

The QA script disables Gemini and OpenAI keys **inside its own process**. Never put any real API key into chat, committed files or public bug reports.
