@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo.
echo =====================================================
echo   MASR GUIDE AI - LOCAL FIRST-RUN SETUP AND TESTS
echo =====================================================
echo.
where python >nul 2>nul
if errorlevel 1 goto missing_python
where npm >nul 2>nul
if errorlevel 1 goto missing_node

echo [1/6] Creating isolated Python environment...
if not exist "backend\.venv\Scripts\python.exe" (
  python -m venv "backend\.venv"
  if errorlevel 1 goto fail
)
echo [2/6] Installing backend test and runtime dependencies...
"backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements-dev.txt"
if errorlevel 1 goto fail

echo [3/6] Running Python test suite in backend directory...
pushd backend
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (popd & goto fail)
popd

echo [4/6] Installing locked React dependencies from npm...
pushd frontend
call npm ci --no-audit --no-fund
if errorlevel 1 (popd & goto fail)
echo [5/6] Testing, linting and building the React application...
call npm run test:contract
if errorlevel 1 (popd & goto fail)
call npm test
if errorlevel 1 (popd & goto fail)
call npm run lint
if errorlevel 1 (popd & goto fail)
call npm run build
if errorlevel 1 (popd & goto fail)
popd

echo [6/6] Basic source secret review...
"backend\.venv\Scripts\python.exe" scripts\check_no_secrets_v75.py
if errorlevel 1 goto fail

echo.
echo [PASS] Backend, React build, lint and frontend tests completed.
echo [NEXT] Run RUN_STARTUP_WINDOWS.bat to open http://localhost:5173
echo [NEXT] Browser and live Gemini checks are separate release gates.
echo        For browser: backend\.venv\Scripts\python.exe -m pip install playwright

echo        Then: backend\.venv\Scripts\python.exe -m playwright install chromium

echo        Then: backend\.venv\Scripts\python.exe scripts\verify_release_v78.py --browser
pause
exit /b 0
:missing_python
echo [ERROR] Install Python 3.11+ and add it to PATH.
pause
exit /b 1
:missing_node
echo [ERROR] Install Node.js 20+ with npm and add it to PATH.
pause
exit /b 1
:fail
echo.
echo [FAILED] A required installation or test step failed.
echo Do not proceed as though the frontend or backend has passed.
pause
exit /b 1
