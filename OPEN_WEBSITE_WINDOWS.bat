@echo off
setlocal
cd /d "%~dp0"
echo.
echo ===================================================
echo   MASR GUIDE AI - OPEN REAL WEBSITE LOCALLY
 echo ===================================================
echo.
where py >nul 2>nul
if not errorlevel 1 (
    py -3 scripts\open_local_website.py
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python 3.11+ is required. Install it and try again.
        pause
        exit /b 1
    )
    python scripts\open_local_website.py
)
if errorlevel 1 (
    echo.
    echo [FAILED] Check the diagnostic text above and the logs in .local-logs.
)
echo.
pause
