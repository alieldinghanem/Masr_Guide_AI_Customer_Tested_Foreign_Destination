MASR GUIDE AI - WINDOWS LOCAL START
==================================

This ZIP is SOURCE CODE for the real app, not a public hosted website.

1) Install Python 3.12 and Node.js 22 LTS (with npm).
2) EXTRACT the complete ZIP to an ordinary folder on your computer.
3) Make sure you have an internet connection for the first launch.
4) Double-click OPEN_WEBSITE_WINDOWS.bat from the extracted Masr_Guide_AI folder.
5) The launcher will install dependencies, attempt `npm run build`, and then
   start FastAPI + React. It will print [READY] only if both respond correctly.
6) After [READY], open http://127.0.0.1:5173/ in NORMAL Chrome/Edge
   ON THE SAME WINDOWS PC. Do not open localhost inside ChatGPT's in-app browser.
7) Do not close the launcher while using the application.

IF SOMETHING FAILS:
- Keep the launcher window open and read the [FAILED] message.
- Look inside .local-logs for npm-install.log, frontend-build.log,
  frontend.log, backend.log and pip-install.log.
- If npm failed, verify your computer can reach registry.npmjs.org.
- If ports 5173/8000 are in use, close old Masr Guide AI/Vite/uvicorn windows.
- Do not share backend/.env or any API keys with anyone.

Offline mode lets you test catalog and deterministic trip planner without an AI key.
Real Gemini chat requires GEMINI_API_KEY in backend/.env.
GitHub and public hosting are intentionally postponed until LOCAL checks pass.
