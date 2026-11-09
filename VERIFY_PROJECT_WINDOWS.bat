@echo off
setlocal
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto fail
)
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m evaluation.run_eval
if errorlevel 1 goto fail
cd /d "%~dp0frontend"
call npm ci --no-audit --no-fund
if errorlevel 1 goto fail
call npm run lint
if errorlevel 1 goto fail
call npm test
if errorlevel 1 goto fail
call npm run build
if errorlevel 1 goto fail
cd /d "%~dp0"
echo.
echo All automated local checks passed.
echo Next: start backend and frontend, test manual flows and real LLM with your own API key.
pause
exit /b 0
:fail
color 0C
echo.
echo A required test or build failed. Do not mark the project ready for public demo.
pause
exit /b 1
