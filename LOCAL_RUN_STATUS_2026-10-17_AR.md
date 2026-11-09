# Masr Guide AI — Local Run Verification (17 October 2026)

This package is a repaired LOCAL START CANDIDATE, not a verified public deployment.

## Changes from the previously delivered one-click ZIP

- Launcher checks that Python, Node, npm and Vite are available.
- `npm ci --include=dev` runs when Vite is absent; install failures have a log.
- Runs an actual `npm run build` BEFORE launching either service.
- Separates frontend-build, npm-install, backend and frontend runtime logs.
- Uses 127.0.0.1 in Vite API proxy to avoid localhost IPv4/IPv6 ambiguity.
- Rejects already-running servers on 5173/8000 to avoid falsely using an old copy.
- Uses exact API readiness JSON and actual React HTML identity, not only HTTP 200.
- Skips system proxy for loopback readiness checks.
- Launches the default local browser only after both endpoints pass readiness.

## Test evidence and limitations

- Python source syntax check: executed.
- Launcher readiness logic self-tests: executed.
- Backend pytest: executed in this session; results should be read from the new log.
- `npm ci`: BLOCKED in the execution environment by missing npm cache entry and registry fetch timeout.
- React production build: NOT EXECUTED successfully here due to unavailable dependencies.
- Chromium live UI: NOT EXECUTED here.
- Gemini live: NOT EXECUTED here (no credentials).
- Windows double-click: NOT EXECUTED here (Linux environment); must be validated on Windows.

The actual public URL does not exist. `http://127.0.0.1:5173/` works only on the same PC **after** a local start reports [READY].

## Executed in the current session

- `cd backend && python -m pytest -q tests` → 233/233 PASS.
- `cd frontend && node --test scripts/validate_trip_contract.test.mjs` → 6/6 PASS.
- FastAPI started on 127.0.0.1:18080 and returned HTTP 200 from `/api/ready`, `/api/health`, and `/api/discover/destinations`.
- Python launcher syntax compiled successfully; nine readiness logic cases passed.
- ZIP integrity verified by ZipFile.testzip(); `.env`, local SQLite files, `node_modules`, `.venv` excluded.
