@echo off
setlocal
cd /d "%~dp0"
echo Masr Guide AI - REAL Gemini API smoke test
if not exist "backend\.env" (
   echo [BLOCKED] Set up a private key with SETUP_GEMINI_WINDOWS.bat first.
   pause
   exit /b 2
)
if exist "backend\.venv\Scripts\python.exe" (
    "backend\.venv\Scripts\python.exe" scripts\qa_release_snapshot.py --live-gemini
) else (
    where py >nul 2>nul
    if not errorlevel 1 (py -3 scripts\qa_release_snapshot.py --live-gemini) else (python scripts\qa_release_snapshot.py --live-gemini)
)
if errorlevel 1 (echo [FAILED] At least one check failed. Read the report.) else (echo [FINISHED] Read qa_reports\local_release_snapshot.json)
pause
