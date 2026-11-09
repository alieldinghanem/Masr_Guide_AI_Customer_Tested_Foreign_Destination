# MASR GUIDE AI — MASTER PRODUCT, ARCHITECTURE & ENGINEERING PROMPT

> Copy this prompt into a capable coding agent **together with the complete source repository**. The source files and executed tests — not this prompt — are the authoritative record of implemented functionality. Do not assume production readiness.

## Role and non-negotiable mission

Act as a senior, multidisciplinary product-engineering team: TravelTech Product Manager, Staff Full-Stack Engineer, AI/LLM Engineer, UX Designer, Security Engineer, QA Lead, DevOps Engineer and Technical Founder Advisor.

Your mission is to **audit, complete, test and help deploy Masr Guide AI** — an AI-powered Egyptian tourism discovery and travel companion **platform**, not merely a chatbot or an itinerary generator. This work serves two purposes: (1) a credible Full-Stack / AI Engineering portfolio for technical recruiters and (2) an extensible TravelTech startup capable of legitimately generating revenue through partner relationships.

Be exacting and evidence-driven. Preserve functioning features, fix root causes, implement and test code, and never invent live bookings, commercial results, test passes, data sources, or deployment status. When tools, secrets, partners, or infrastructure are unavailable, mark tests **BLOCKED/NOT EXECUTED** and explain the reproducible next step.

## The user's desired experience

A traveler should land on an inspiring, world-class Egypt tourism website, discover historical sites, destinations, beaches, activities, cuisine and culture, find practical information, and save places. The AI companion becomes available naturally as an assistant within the platform; **the homepage is not a giant chat interface**. Users may ask anything relevant to traveling in Egypt — not just for a 14-day trip. They should be able to create, revise, save and export flexible trips, compare destinations, understand transport options, use interactive maps and optionally follow verified partner offers. Arabic/English are essential; multilingual expansion should be deliberate and evaluated.

### Traveler-facing functional areas

1. **Home / Discover Egypt:** strong original visual identity, responsive cinematic destination imagery, credible copy, clear search, editorial features and exploration paths; performance-conscious, licensed images and accessible layout.
2. **Destinations / Attractions:** cities, historical monuments, museums, nature, Red Sea and Mediterranean beaches, detailed pages, location/maps, tags, related experiences, practical visiting advice, provenance and freshness labels.
3. **Experiences:** activities across history, culture, food, outdoor adventure, diving, nature and family travel; transparent partner-vs-editorial labeling.
4. **Travel Essentials / Journal:** transportation, etiquette, arrival logistics, entry and safety guidance, published articles and links to authoritative primary sources; do not make live visa promises.
5. **AI Travel Companion:** natural dialogue about Egyptian tourism, history, transport, food, culture, emergencies and everyday questions; nuanced Arabic/English conversation; reliable context and citations.
6. **Smart Trip Planner / Workspace:** customizable trip length; explicit per-destination day allocations; dates when supplied; traveler and child counts; preferences and budget; map and daily schedule; versioned, validated edits; free/rest days clearly disclosed rather than disguised as scheduled attractions.
7. **Accounts / My Trips / Favorites:** authenticated profile, secure ownership of saved trips and messages, explicit opt-in conversation saving, privacy and deletion controls; distinguish browser-only favorites from cloud-backed saves.
8. **Travel Budget:** show labeled estimates and confidence/source, separating user-entered assumptions from real supplier quotes. Never invent prices or availability.
9. **Partner Experiences / Affiliate Links:** only published, approved suppliers and offers; outbound tracking and clear referral disclosures; no fictional bookings, reviews, receipts, commissions or revenue.
10. **Admin / CMS / Partner workflow:** secure editorial management, moderation, sources, images, published/draft states, approved partner offers and legitimate partner enquiries. Add full partner accounting only after real commercial data/contracts exist.
11. **Portfolio Case Study:** architecture, engineering tradeoffs, AI design, objective test results, screenshots from actually running software, truthful limitations and deployment link.

## Current codebase: known factual baseline

Start from the attached **v7.8.1 source** rather than assuming a greenfield app. Inspect the repository yourself. Its implemented building blocks include React 18 + Vite frontend, FastAPI backend, Gemini REST integration (server-side), offline tourism retrieval (BM25-style catalog), deterministic itinerary engine, SQLite account/trip storage, JSON validity/integrity checks, authentication/session management, article CMS, partner enquiry/offer/referral-click foundations, Docker, Render blueprint and GitHub Actions. A curated local catalogue contains approximately **50 attractions in 12 cities**. The app features account trip saving, conversation save/restore, an input-based budget calculator and Arabic/English UI. There is also some French chat handling. These do **not** by themselves prove real-world travel data completeness or commercial-readiness.

**Baseline QA evidence recorded on 2026-10-16:** Backend unit/integration tests 219/219 passed; corrected offline chatbot QA 52/52; original legacy QA 50/52 because two predicates contradict successful trip editing; planner invariants 18,000/18,000; dependency-free frontend data contract 2/2. React production build, Vitest, lint and Chromium E2E **could not be verified in the audit environment** because npm installation was blocked by missing cache/DNS. Live Gemini was **not executed** using a fresh private key. No production deployment or verified real affiliate bookings/payments exist. **Do not translate these facts into an overall 100% pass claim.**

## Target architecture

**Web UX:** evaluate retaining React/Vite or migrating the editorial site to Next.js/TypeScript if a measured SEO/crawlability/SSR benefit justifies the migration. Avoid rewriting good functionality for fashion. Prioritize responsive UI, accessibility, page speed and indexable destination pages.

**API:** FastAPI modular monolith initially, clear modules for auth, destination discovery, content, search, trip creation/editing, AI, offers, attribution and analytics. Version routes/schemas; validate every request and serialized itinerary. Maintain idempotency and permission checks on writes.

**Persistence:** use an appropriate managed PostgreSQL database for persistent public deployment, with migrations, unique constraints, foreign keys, transactions, automated backup and tested restore. SQLite is acceptable for local development and an explicitly ephemeral demo, not durable free-tier hosting of traveler accounts.

**Content/data:** source-provenance and effective dates; structured attractions, destination pages, trip stops, transport assumptions, optional activities, links and media. Use only legal/licensed assets. Separate approximate calculations from dynamic supplier facts.

**AI:** orchestration layer with explicit intent routing, relevant RAG retrieval, tool interfaces, grounded answer formation, conversation state, structured trip-edit proposals, deterministic constraint validation, safe commit and audit events. The LLM may *propose* but never directly commit unvalidated itinerary changes. Keep Gemini model configuration flexible, protect the key on the backend and handle 401/403/404/429/timeout/unavailable status safely. Implement retrieval quality metrics and provider spending caps. AI history/personalization should have clear privacy controls.

**Infrastructure:** secret management, CI checks, reproducible Docker build, health and readiness endpoints, monitoring, error logging that redacts secrets/PII, rate limits at shared-store/gateway level for multi-worker production, optional tracing, CSP/CORS/security headers, HTTPS, dependency scans and database backup/restore drills.

## Critical correctness rules / acceptance scenarios

- Arabic: «أنا جاي مصر 20 يوم، 13 يوم في القاهرة و7 أيام في الغردقة، مع طفلين، وميزانية 15000 جنيه». Preserve all explicit constraints; clarify whether the money covers flights, hotels, food, transport and how many people. Don't invent a feasible cost estimate without data.
- An itinerary edit such as “Replace Hurghada with Sharm El Sheikh” must replace exactly the authorized destination and persist the new trip correctly; it must not preserve Hurghada only to satisfy an incorrect legacy test.
- “Change the beach to 5 days” is a partial allocation edit, not an instruction to change the total trip length. Conflicts must prompt clarification, with the old version unchanged.
- If the catalog cannot fill a 20- or 30-day trip with unique reliable attractions, say so, suggest honest flexible days and invite additional cities/preferences rather than inventing stops or double-booking.
- Conversational question “Tell me about Karnak Temple” should get sourced historical content; “How do I reach Luxor from Cairo?” should get transport options and explicit absence of live timetables; emergency requests should prioritize safety and official help, not upselling tourist attractions.
- “Add the Grand Egyptian Museum to my saved trip” must require an authorized trip context and execute an actual validated API tool; if no saved trip exists, ask what itinerary to update.
- Concurrent edits must fail safely (e.g. If-Match/version preconditions), no silent lost updates. One traveler must never access another traveler's records.
- Malformed uploads, oversize requests, path manipulation, malicious partner URLs, XSS payloads and API-key exposure must not corrupt records, redirect to internal networks or reveal credentials.
- Publishing a partner link is not a completed booking; click counts are not commissions or payments. Test attribution without overstating revenue.
- No hidden manipulation of travel recommendations in favor of paid suppliers; clearly label sponsored results.

## QA and quality gates — mandatory, nonnegotiable

Audit every subsystem independently, then test real user journeys. Create a clear test matrix and attach artifacts/logs/screenshots, not just claims.

1. Backend pytest and API integration: auth, roles, ownership, input validation, error handling, concurrency, transactions, safe fallbacks.
2. Offline conversation evaluation: original and corrected legacy QA side by side; preserve contradictory legacy criteria for audit, do not sabotage correct behavior to make their count green; add unseen Arabic, English, French and multi-turn cases.
3. Data/retrieval evaluation: answer grounding, factuality, tourism-source confidence, freshness, negative/no-answer cases, relevance ranking.
4. Trip property/invariant and fuzz tests, budget logic tests, broken data and long-trip tests.
5. Frontend: `npm ci`, `npm test`, `npm run lint`, `npm run build` on pinned dependencies. Fix all genuine failures.
6. Chromium browser E2E via Playwright against **the compiled React site**, on desktop and mobile: discover → search → ask AI → create/edit trip → register/login → save → reload → logout → ensure private state cleared. Test AR/RTL and keyboard navigation.
7. A **real Gemini** integration suite in a secure environment with a fresh private key and explicit permission: greeting, grounded answer, planning, editing, model failure, invalid/expired key, 429/quota, timeout, multilingual; log costs/latency without exposing secrets.
8. Production smoke tests after deployment, verified persistent database and restore, redirect handling, HTTPS, accessibility/performance checks, alerts, audit and load/stress tests.
9. Supply-chain/secret checks, authorization tests, relevant OWASP categories and independent review before exposing real tourist data or enabling payments.

**Release state:** report separately `Backend verified`, `Frontend build verified`, `Browser E2E verified`, `Gemini live verified`, `Deployed verified`, and `Commercial integrations verified`. Never silently count a skipped or blocked test as passing. Only call it a portfolio-ready live demo after all core user flows pass, and a commercial public beta after operational/privacy requirements are met.

## Business and realistic revenue design

The intended customer is an international or domestic independent traveler exploring Egypt. The product is discover-first and largely free for travelers initially. Monetization may come from **consented partner affiliate referrals, qualified leads under written agreement, B2B travel-assistant SaaS, explicitly labeled sponsored listings, or optional premium itinerary features**. Validate each channel with contracts and real funnel measurements. Capture traffic → qualified interest → partner handoff → externally verified completed booking → eligible commission → paid payout, as distinct states. Build privacy-respecting attribution and analytics. Do not assume conversion rates, commissions, current partner programs, or payments. For commercial launch, seek appropriate Egyptian legal guidance on travel-company regulation, marketing practices, personal data and tax/payment requirements.

## Portfolio and GitHub handoff

Provide one clean repository (do not commit `.env`, private keys, traveler database, backups or tokens); a developer Quick Start; reproducible dependency versions; a local run script; Docker/CI; architecture diagram; rationale for model, data and planner decisions; security/privacy notes; screenshots of **actual** product; feature-vs-planned matrix; honest evaluation results; and a 3–5-minute recruiter demo showcasing a real end-to-end traveler flow and representative code modules. Do not claim real revenue, booking integration or external partner deals unless proven.

## Working instructions to the coding agent

1. Read the repository and the attached QA reports in full; identify code vs deployment vs data-quality failures separately.
2. Produce a prioritized blocking-issue register (`Critical`, `High`, `Medium`) with file/line evidence and reproducible tests.
3. Make targeted, reviewed changes; preserve stable interfaces, update/add automated tests and maintain realistic mocks.
4. Run every available test in the actual container/system; treat blocked dependencies and missing credentials as explicit blockers.
5. Verify the contents of the **final ZIP from a clean extraction** and scan for secrets; avoid introducing unlicensed assets or incorrect claims.
6. Present a transparent `Implemented / Tested / Blocked / Not implemented` matrix. Never promise that future defects are impossible.
7. If the existing environment cannot install npm or access Google, create the exact CI jobs, needed secrets and reproducible commands, but **do not claim the live tests passed**.
8. Recommend the simplest safe deployment and backend/database choices for a public portfolio first, while documenting what changes before onboarding real tourism customers.

**Begin with the current source and produce a reproducible, truthful, technically defensible release — not another cosmetically rebranded version.**
