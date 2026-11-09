@echo off
setlocal
cd /d "%~dp0backend"

REM Dependencies are installed and tested once by SETUP_AND_TEST_LOCAL_WINDOWS.bat.
REM Do not run pip install on every launch: offline startup must keep working.
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Backend virtual environment is missing.
  echo Run SETUP_AND_TEST_LOCAL_WINDOWS.bat from the project root first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import fastapi, uvicorn, dotenv"
if errorlevel 1 (
  echo [ERROR] Backend packages are missing or incomplete.
  echo Run SETUP_AND_TEST_LOCAL_WINDOWS.bat again.
  pause
  exit /b 1
)

echo Starting FastAPI on http://127.0.0.1:8000
".venv\Scripts\python.exe" -m uvicorn app.main:app --no-proxy-headers --reload --host 127.0.0.1 --port 8000
if errorlevel 1 echo [ERROR] Backend exited unexpectedly. Check the error above.
pause
