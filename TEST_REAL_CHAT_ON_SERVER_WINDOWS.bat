@echo off
setlocal
cd /d "%~dp0"
python backend\scripts\run_customer_live_acceptance.py --base-url http://127.0.0.1:8000 --report qa_reports\live_customer_acceptance.json
set EXITCODE=%ERRORLEVEL%
echo.
echo The test does NOT expose the API key. Read qa_reports\live_customer_acceptance.json.
echo Exit code: %EXITCODE%
pause
exit /b %EXITCODE%
