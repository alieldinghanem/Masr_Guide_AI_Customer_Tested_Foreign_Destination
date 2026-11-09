# Masr Guide AI v7.6.1 — Independent Audit Fixes

**This is a targeted security/configuration maintenance patch, NOT a commercial production release.**

## Confirmed fixes

1. **Account DB configuration (`backend/app/accounts.py`):** removed the eager import-time binding of `MASR_USER_DB`; account DB path now resolves when opening the database, after the application's `.env` has been loaded. Existing tests that inject `_DB` remain supported. Reproduced a previously failing `.env` configuration case and confirmed the configured database is selected.
2. **Shared-device privacy (`frontend/src/components/Account.jsx`, `frontend/src/App.jsx`):** logging out or successfully deleting an account clears saved local trip drafts, AI conversation state/transcript, bookmarks, and local budget calculations. The long-lived React Shell chat state is also reset, so clearing browser storage alone does not leave the prior person's messages visible on navigation.

## Verification after these fixes

- Backend pytest: **200/200 passed**.
- Corrected offline chatbot checks: **52/52 passed**.
- Original offline chatbot checks: **50/52 passed** (unchanged contradictory Q49/Q52).
- Dynamic local `.env` read test: **passed**.
- TS/JSX parser check of both modified React files: **passed**.
- Best-effort secret scan: **passed**.

## Remaining explicit blockers

- `npm ci` could not install frontend dependencies in this environment, so React build/Vitest/ESLint and real browser E2E are **NOT VERIFIED**.
- Gemini live end-to-end behavior with a current private key is **NOT VERIFIED**.
- Render free instance uses ephemeral storage; accounts and trips need managed persistent storage before accepting real customer data.
- Limited client-IP/process rate limiting, SEO restrictions from client-only hash routing, unverified third-party prices, nontransactional affiliate-click metrics, and lack of commercial booking partnerships remain.

**Status:** improved source-code / portfolio candidate. Do not describe as fully deployed, production-safe, or guaranteed error-free.
