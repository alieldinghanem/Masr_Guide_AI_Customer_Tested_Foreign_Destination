@echo off
setlocal
cd /d "%~dp0"
if exist "backend\.venv\Scripts\python.exe" (
  "backend\.venv\Scripts\python.exe" "backend\scripts\smoke_gemini_grounding.py"
) else (
  python "backend\scripts\smoke_gemini_grounding.py"
)
set "RESULT=%ERRORLEVEL%"
echo.
if "%RESULT%"=="0" echo [PASS] Real Gemini search returned cited web sources.
if "%RESULT%"=="1" echo [NOT VERIFIED] Gemini search did not return confirmed web sources.
if "%RESULT%"=="2" echo [BLOCKED] Missing or disabled key/search setting in backend\.env.
echo.
pause
exit /b %RESULT%
