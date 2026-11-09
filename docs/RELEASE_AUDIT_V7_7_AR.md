# Masr Guide AI — Independent Release Candidate v7.7

**Base:** previous audited v7.6.1 source; patched and repackaged from a clean working copy on 15 October 2026.

## Added or improved
- Account and staff requests now share the central API wrapper with a bounded 20-second timeout and explicit error handling instead of potentially waiting indefinitely on broken network calls.
- Added a frontend unit regression test for safe explicit staff header forwarding.
- Replaced stale React browser test with checks aligned to the current application: compiled React mount, destinations/landmark search, itinerary creation, local save, offline chat and itinerary, session continuity, desktop/mobile widths, and no runtime JavaScript errors.
- GitHub Actions now includes a **browser job** which builds the real React release, starts FastAPI on the compiled bundle and launches Chromium E2E. Existing Python/backend and JS jobs remain mandatory.
- Added a separate **opt-in** real Gemini smoke script for English and Arabic. It requires a fresh private credential and explicit opt-in; never auto-run in CI.
- Versions of frontend and backend aligned to 7.7.0. No payment/booking functionality invented.

## Actually executed here
| Check | Result |
|--|--|
| pytest Backend | 200/200 PASSED |
| HTTP integration/mock provider | 21/21 PASSED |
| Corrected offline chatbot acceptance | 52/52 PASSED |
| Original legacy chatbot acceptance | 50/52 (2 contradictory expectations, retained for transparency) |
| Planner invariant stress | 18,000 assertions PASSED |
| Tourism retrieval evaluation | hit@3 = 1.00 on 49 answerable cases in bundled benchmark |
| Python compilation, JavaScript API parser, YAML parsing | PASSED |
| Source-tree best-effort secret scanner | PASSED |
| npm ci offline | BLOCKED (`yocto-queue@0.1.0` not in cache) |
| npm ci online | BLOCKED (container cannot resolve `registry.npmjs.org`) |
| React build, Vitest, ESLint | NOT EXECUTED; npm dependency blocker |
| Chromium browser E2E | BLOCKED: environment policy `net::ERR_BLOCKED_BY_ADMINISTRATOR` even on local or data URLs |
| Live Gemini | NOT EXECUTED: no valid unexposed user credential is present in the runtime |
| Live deployment / Docker | NOT EXECUTED |

**Do not call this a production-ready final release.** The above is a distributable source-code release candidate and mandatory CI gates to prove full-stack readiness on GitHub.

## Required before sharing HR demo link
1. Upload this clean source to a new GitHub repository, excluding `.env` and secrets.
2. Confirm all **three** CI jobs green: backend, frontend, browser. If browser fails, read the artifact/job output and fix the UI.
3. Set up an ephemeral portfolio deployment with `APP_ENV=portfolio`, explain that accounts are temporary. **Do not** store real user data on Render's free ephemeral storage.
4. Run real Gemini smoke tests with a newly rotated private key on staging, then exercise multi-turn real itinerary edits and inspect quality manually.
5. Validate public link from an independent device before adding it to a CV.

## Required before commercial launch
- Durable production persistence (managed DB or verified persistent volume), migrations, tested backup and restore, monitored errors and provider cost limits.
- Strong production auth/role permissions, shared rate limits, privacy/retention and external security review.
- SEO/indexable content pages, image rights, official tourism information updates.
- Real partner contracts and independently confirmed bookings/conversions; click analytics are not earned commissions.
