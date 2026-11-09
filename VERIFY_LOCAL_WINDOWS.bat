@echo off
setlocal
cd /d "%~dp0"
echo Masr Guide AI - independent local QA (no AI charges unless requested separately)
if exist "backend\.venv\Scripts\python.exe" (
    "backend\.venv\Scripts\python.exe" scripts\qa_release_snapshot.py
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 scripts\qa_release_snapshot.py
    ) else (
        python scripts\qa_release_snapshot.py
    )
)
if errorlevel 1 (
    echo [FAILED] Tests failed. See qa_reports\local_release_snapshot.json
) else (
    echo [FINISHED] Review PASS/BLOCKED/NOT EXECUTED in qa_reports\local_release_snapshot.json
)
pause
