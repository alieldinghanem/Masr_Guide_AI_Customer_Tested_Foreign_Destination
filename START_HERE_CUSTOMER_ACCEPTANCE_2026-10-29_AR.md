# Masr Guide AI — Customer Experience Engineering (29 October 2026)

**This is a full source-code handoff for local evaluation, NOT a certified public or production release.**

## Start on Windows

1. Unzip into a normal writable directory. Do **not** run BAT scripts inside a compressed ZIP.
2. Install Python 3.11/3.12 and Node.js 22 and make sure `python`, `node` and `npm` are on PATH.
3. Run `SETUP_AND_TEST_LOCAL_WINDOWS.bat` with a working internet connection so `npm ci` can install Vite and React dependencies.
4. Run `OPEN_WEBSITE_WINDOWS.bat` and **wait for `[READY]`**.
5. Open `http://127.0.0.1:5173/` in Chrome/Edge on **the same computer**. This is not a public URL. Do not expect it to open from an unrelated cloud browser.
6. If setup fails, check `.local-logs`; do not call an offline quick demo the real React site.

Gemini is optional for the local deterministic walkthrough. To verify real conversational AI, configure `backend/.env` on your own computer (never send the key in a chat), then run `TEST_GEMINI_CONVERSATION_WINDOWS.bat`. No real Gemini request was executed in this release environment.

## Changes introduced in this engineering pass

- Airport-to-Zamalek transfer questions now match natural English arrivals/reach phrasing and show verified **categories** of safe transfer options, not fabricated fares or journey times.
- Queries about wheelchair accessibility do not misroute into history/attraction retrieval; they explicitly disclose that routes/access are **not verified**.
- A wheelchair/step-free requirement in a planned itinerary is now carried in typed trip state **and** saved itinerary, preserved through trip edits/reallocation and displayed prominently in React.
- Requests to pay by card, including booking a trip, are routed to a safe no-payment response before planner intent matching.
- Night visits to attractions do not claim live access or hours from static catalogue content.
- 'First visit with family for a week — make a plan' creates a 7-day editable itinerary rather than generic advice; historical examples without explicit day constraints remain only suggestions.
- The French planning response is in French, while transparently disclosing that the curated stop names/descriptions remain in English; French localization is not yet complete.
- Fixed duration parsing: `Change the trip: 3 days Cairo and 3 days Aswan` is a 6-day city allocation, not a 3-day total.
- Added adversarial customer regressions and a script that runs a real Uvicorn local HTTP customer journey, saving a detailed result to `qa_reports`.

## Actually executed in this session

| Check | Status |
| --- | --- |
| Full backend regression suite | **292/292 PASS** |
| Browser-independent frontend data/UI mode Node tests | **12/12 PASS** |
| Independent Uvicorn HTTP customer journey | **10/10 PASS** |
| Python code compilation | **PASS** |
| React `npm run build` | **BLOCKED**: `vite` missing from this environment; Node packages cannot be verified here |
| Chromium browser end-to-end | **NOT EXECUTED** for this delivery |
| Real Gemini API multi-turn evaluation | **NOT EXECUTED**: no valid `GEMINI_API_KEY` available in this runtime |
| Public deployment or cloud storage recovery | **NOT EXECUTED** |

Pass counts are only for the tests above; they are not percentages of all traveler needs. Server tests do not prove that an end-user browser can load the full site.

## Product release gate (must happen BEFORE offering travelers full reliance)

1. Clean `npm ci`, real React production build, Vitest, ESLint, Chromium journeys on desktop and mobile; resolve every blocker.
2. Live Gemini evaluation with real API credentials for Arabic, English and French (hotel, safety, routes, follow-ups, multi-day trip edits and explicit tool actions); grade usefulness, factual grounding, consistency and hallucinations.
3. Curated Egypt destination and accessibility datasets, editorial verification dates, official references and refresh jobs; do not pretend static attractions are live operational facts.
4. Verified live supplier data/inventory and consent-based booking integrations (or clearly label offers and links as informational only).
5. Production PostgreSQL or tested durable storage, backup/restore drill, edge rate limits, secrets management, performance and vulnerability testing.
6. Human pilot with travelers and documented acceptance criteria before removing beta disclosure.

This project still cannot honestly promise complete reliance for visas, safety, medical emergencies, wheelchair accessibility, prices, open hours, hotel bookings or transportation schedules without verified providers and live information.
