# Masr Guide AI — Chatbot Conversational QA (2026-10-28)

## Scope and honesty
- Source baseline: `Masr_Guide_AI_Complete_Local_Release_2026-10-28.zip` (240 entries).
- Actual execution in this run: Python/FastAPI tests, deterministic hotel and itinerary path checks, live **local Uvicorn HTTP** requests over 127.0.0.1:8765.
- Gemini credentials: `GEMINI_API_KEY` and `OPENAI_API_KEY` were **not present** in this runtime. No real model API requests were executed and the outputs below must NOT be called Gemini answers.
- React production build, Chromium browser interaction and user-device launch were NOT EXECUTED in this run. UI source wiring and mode labels were reviewed/edited, but user-facing rendering not validated.

## Actual baseline issues reproduced
1. `رشح لي فندق في القاهرة`: `offline-preview`, no hotel recommendations or credible hotel source.
2. `عايز فندق قريب من الأهرامات`: returned the Grand Egyptian Museum and Sphinx as though those were accommodation suggestions.
3. `الميزانية 100 دولار في الليلة`: ignored accommodation context and had no useful response.
4. `هل فندق Marriott Mena House متاح الليلة وبكام؟`: no targeted hotel answer.
5. `ضيف يومين في الغردقة بدل يومين من القاهرة`: returned `needs-clarification` for an unambiguous day transfer.

## Edits implemented
- `backend/app/hotel_guide.py`: conservative curated Cairo/Giza hotels from direct official operator pages, with links and clear lack of booking/price/availability feeds. Only four reviewed references, not a comprehensive hotel database. Follow-up budget/location questions use prior visitor requests without fabricating pricing. Unsupported cities and unverified restaurants are reported as unsupported.
- `backend/app/guide.py`: route hotel questions to this deterministic editorial guide after the urgent safety/payment handlers and before unrelated attraction retrieval.
- `backend/app/travel_agent.py`: exact, validated day-transfer command for a move from an existing single-city phase into an explicitly identified new city. The total duration and all other existing trip preferences remain unchanged. All other changes still use existing transition guards.
- `frontend/src/components/Guide.jsx` and `frontend/src/messages.js`: add clear non-live hotel response mode labels for Arabic and English.
- `backend/tests/test_hotel_conversation_20261028.py`: nine regression tests for hotel choice, follow-up, booking safety, unsupported destinations and itinerary transfer safety.

## Actual test results
| Check | Outcome |
|---|---|
| Full Python backend suite | **242 passed**, ~10 seconds |
| Added hotel and itinerary regression cases | **9 passed** (included in 242) |
| Actual Uvicorn HTTP socket readiness (`/api/ready`) | HTTP 200 |
| Actual local HTTP hotel conversation | 5/5 POSTs HTTP 200, modes and sources asserted |
| Actual local HTTP itinerary 5d Cairo → 3d Cairo + 2d Hurghada | PASS; `day_allocation` verified |
| Payment card/CVV handling | Warned user not to enter payment credentials; no transaction |
| Real Gemini API | **NOT EXECUTED** (no key in runtime) |
| Browser/UI and React production build | **NOT EXECUTED** in this run |
| Bookings, current hotel rates or vacancy | **NOT IMPLEMENTED** |

## Recorded conversation after fixes (via real localhost HTTP)
1. `رشح لي فندق في القاهرة` → `hotel-editorial`: 4 official hotel examples; clearly disclaims live rates.
2. `عايز فندق قريب من الأهرامات ومناسب لعيلة` → `hotel-editorial`: 2 Giza-area hotels; no unsupported family-room or availability claims.
3. `ميزانيتي 100 دولار في الليلة` → `hotel-editorial`: retains Giza selection; does **not** claim any of them fit the budget, requests actual dates/party size.
4. `هل فندق Marriott Mena House متاح الليلة وبكام؟` → `hotel-editorial`: links specifically to Mena House; explicitly declines to invent rate/availability.
5. `ممكن تحجز لي الفندق وتاخد بيانات الكارت؟` → `local-assistant`: refuses payment credentials; no booking.
6. `عايز أخطط رحلة 5 أيام في القاهرة` → `local-planner`: 5 Cairo days.
7. `ضيف يومين في الغردقة بدل يومين من القاهرة` → `local-planner`: 3 Cairo + 2 Hurghada days, preserving total 5 days.

## Official hotel reference pages (verified for basic location as of Oct 28, 2026)
- Marriott Mena House: https://www.marriott.com/en-us/hotels/caimn-marriott-mena-house-cairo/overview/
- Steigenberger Pyramids Cairo: https://hrewards.com/en/steigenberger-pyramids-cairo
- Steigenberger Hotel El Tahrir Cairo: https://hrewards.com/en/steigenberger-hotel-el-tahrir-cairo
- Sofitel Cairo Nile El Gezirah: https://sofitel.accor.com/en/hotels/5307.html

## Business/product limitations
- The user asked to test chatbot end-to-end; this run validated the actual HTTP server and the offline, deterministic conversational workflows. It **did not** test the real Gemini provider or browser UI, so it is not full end-to-end verification of the public product.
- Hotel candidates are editorial seeds, not real-time inventory or affiliate partners. Do not claim hotel prices, reservations, referrals, commissions, verified family-room inventory or website availability.
- For production-grade accommodation recommendations, integrate a licensed hotel data provider or CMS with review intervals, optional trusted booking deep links, source audits and rate/inventory validation.
- This update is not a production release authorization. Additional React build/browser accessibility tests, provider E2E, deployment smoke and security reviews remain necessary.
