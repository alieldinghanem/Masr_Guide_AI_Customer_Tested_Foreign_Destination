> Historical v1.8 report from a prior environment. For current-session evidence and blockers see [RELEASE_QA_2026-10-14.md](RELEASE_QA_2026-10-14.md).

# Quality report — v1.8.0

This file replaces the older per-version review reports. It lists **what is measured, by which command, and what is NOT verified**. Re-run the commands to reproduce.

## Measured

| Check | Command | Result |
|---|---|---|
| Backend tests | `cd backend && python -m pytest -q` | 60 passed |
| Backend lint | `cd backend && ruff check .` | clean (rules F, E9, B) |
| Frontend lint | `cd frontend && npm run lint` | clean, zero warnings (incl. `react-hooks/exhaustive-deps`) |
| Frontend tests | `cd frontend && npm test` | 43 passed (5 files: API client, i18n, app flows, routing, axe accessibility in EN + AR) |
| Frontend build | `cd frontend && npm run build` | succeeds (~199 kB JS / ~64 kB gzip) |
| HTTP + mock-provider QA | `python scripts/qa_live_http.py` | 21/21 |
| Planner stress | `python scripts/qa_planner_stress.py` | 1,500 seeded plans × 12 invariants pass; mutation-checked (breaking travel deduction or route search makes it fail) |
| Nginx smoke test | real nginx 1.24 + live backend (manual run) | config valid; SPA fallback, `/api` proxy, security headers/CSP, asset caching and the `/api/chat` throttle behave as designed |

### Defects found and fixed by the tests in this round

- **Non-atomic catalogue rebuild**: a concurrent-reader test reproduced readers seeing a missing/partial `places` table (sqlite3 runs DDL outside a transaction). Fixed with one explicit `BEGIN IMMEDIATE` transaction.
- **Accessibility**: axe found heading-order violations on Home and Discover (h1 → h3 jumps); fixed.
- **Hook dependencies**: two `eslint-disable` suppressions were replaced by correct dependencies / a `key`-based remount.
- **Rate limiter behind a proxy**: all clients shared one bucket; the limiter can now key on a trusted `X-Real-IP`.

### Retrieval evaluation (`python -m evaluation.run_eval -v`)

53 hand-written questions: 49 answerable (30 English, 14 Arabic incl. Egyptian dialect, 5 French) and 4 out-of-scope.

| Metric | Value |
|---|---|
| hit@1 (an acceptable place ranked first) | 0.96 |
| hit@3 | 1.00 (EN 1.00 · AR 1.00 · FR 1.00) |
| MRR | 0.98 |
| Out-of-scope questions returning no sources | 4 / 4 |

The two non-top-1 cases are a Siwa question that mentions "Libya" (not in the catalogue text) and a "lake near Cairo" question where a Cairo museum that mentions a lake ranks above Lake Qarun.

**How to read this.** The set was written by the maintainers *before* tuning and kept unchanged, but the same people wrote the catalogue text, so scores are likely optimistic versus real visitors. `tests/test_release_v16.py` fails if hit@3 drops below 0.95, hit@1 below 0.90, or any out-of-scope question returns sources. Treat it as a regression guard, not a benchmark.

## Not verified here

- **Live OpenAI call** (prompt quality, citation accuracy, quota/latency). The provider path is tested only against a mock.
- **Real-browser behaviour**, visual layout and especially the **RTL/Arabic layout**: component tests check text, `dir`/`lang` and behaviour, not pixels. Run `scripts/qa_browser_e2e.py` and review the Arabic UI by eye on desktop and mobile.
- **Docker image build/run.** The Nginx config was exercised with a real nginx (see above) but not inside Docker, and **never with a real browser**, so the effect of the strict CSP on the rendered page (fonts, OpenStreetMap frames) is unconfirmed.
- Currency of catalogue facts and reference URLs; image licences; accessibility audit.
- Inter-city travel times are model estimates; no ground-truth comparison was performed.

## Review checklist before a public launch

1. Run the full commands above on a clean clone, plus `docker compose up --build`.
2. Test the chat with a real key in English, Arabic and French; spot-check answers against the cited pages.
3. Read every place's reference link and update stale facts.
4. Add TLS, a real rate limiter / budget cap and monitoring.
