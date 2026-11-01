@echo off
setlocal
cd /d "%~dp0"
echo.
echo ========================================================
echo    MASR GUIDE AI - TOURISM PLATFORM STARTUP

echo ========================================================
echo.
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python is missing from PATH. Install Python 3.10 or newer.
    pause
    exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js/npm is missing. Install Node.js 20 or newer.
    pause
    exit /b 1
)
echo [1/2] Opening FastAPI backend console...
start "Masr Guide AI - Backend" cmd /k ""%~dp0RUN_BACKEND_WINDOWS.bat""
echo [2/2] Opening React frontend console...
start "Masr Guide AI - Frontend" cmd /k ""%~dp0RUN_FRONTEND_WINDOWS.bat""
echo.
echo Wait until both windows show their READY / running messages.
echo Main tourism website: http://localhost:5173
echo Backend API documentation: http://localhost:8000/docs
echo.
echo IMPORTANT: /demo on port 8000 is ONLY the legacy mini demo.
echo To see the REAL tourism website, open http://localhost:5173
pause
