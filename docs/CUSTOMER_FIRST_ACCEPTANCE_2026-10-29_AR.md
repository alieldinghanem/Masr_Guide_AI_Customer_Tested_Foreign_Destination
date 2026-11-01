# Masr Guide AI — Readiness decision and product acceptance

## Current release decision: LOCAL BETA; NOT PRODUCTION VERIFIED

This engineering pass targets the most critical observed failures in real tourist questions: safety/payment routing, accessible travel preferences, family plans, multilingual answers, and itinerary day allocation. It deliberately prioritizes a truthful, limited answer over an invented ticket, booking, accessibility claim or cost.

## Demonstrable acceptance journey

A traveler can ask for a first-time family week in Egypt, request an explicitly allocated 6-day Cairo/Luxor trip, edit it to Cairo/Aswan, and save an itinerary in a registered local account. The system must retain the original access requirement, reject payment-card collection, distinguish an unverified nightlife visit from a confirmed ticket, and return transport options without invented live fares. Automated coverage is in `backend/tests/test_customer_safety_accessibility_20261029.py` and `qa_reports/run_customer_http_smoke.py`.

## Known product risks

- No public deployment has been smoke-tested.
- Real Gemini isn't tested in this runtime; offline responses can be generic, especially outside the curated catalog.
- Food, transportation, hotel inventory, accessibility and attraction operational data remain incomplete and cannot form a trustworthy all-in-one booking system yet.
- French itinerary prose is localized only partially; selected attraction descriptions remain in English.
- The React site still requires a successful production build and Chromium-based user acceptance on the operator's machine/CI.
- Local SQLite accounts are **not** a production storage guarantee. A public preview must not imply durable account data without real storage and tested backups.

## Test evidence

- Backend: 292 passed in the actual Python `pytest` invocation.
- Node frontend contracts: 12 passed (`node --test frontend/scripts/*.test.mjs`).
- HTTP smoke: 10 passed (`qa_reports/customer_http_smoke_2026-10-29.json`).
- Gemini live: NOT EXECUTED (key unavailable).
- React production build: BLOCKED (`vite: not found`).

No external booking, payment, commission, revenue, price, availability or official access validation is claimed.
