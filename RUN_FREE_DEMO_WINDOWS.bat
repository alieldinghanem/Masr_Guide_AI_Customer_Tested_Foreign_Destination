@echo off
setlocal
cd /d "%~dp0"
echo.
echo ========================================================
echo   MASR GUIDE AI - LIGHTWEIGHT AI CONSULTANT PREVIEW
 echo ========================================================
echo [NOTE] This is /demo, not the main React tourism website.
echo.
where py >nul 2>nul
if not errorlevel 1 (
  py -3 scripts\open_quick_demo.py
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo [FAILED] Python is missing. Install Python 3.12 first.
    pause
    exit /b 1
  )
  python scripts\open_quick_demo.py
)
if errorlevel 1 echo [FAILED] Read the message above and the .local-logs folder.
echo.
pause
