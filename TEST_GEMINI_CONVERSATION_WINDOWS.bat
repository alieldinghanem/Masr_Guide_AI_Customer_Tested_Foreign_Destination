@echo off
setlocal
cd /d "%~dp0"
echo === Masr Guide AI - REAL Gemini conversation checks ===
echo This uses your own Gemini API key and may consume quota.
if exist "backend\.venv\Scripts\python.exe" (
  "backend\.venv\Scripts\python.exe" scripts\qa_live_gemini_dialogue.py
) else (
  where py >nul 2>nul
  if not errorlevel 1 (py -3 scripts\qa_live_gemini_dialogue.py) else (python scripts\qa_live_gemini_dialogue.py)
)
set RESULT=%ERRORLEVEL%
echo.
if "%RESULT%"=="0" (
 echo [PASS] Real Gemini conversation checks succeeded.
) else (
 echo [INCOMPLETE] Real Gemini checks did not all pass. Examine qa_reports\gemini_live_dialogue_results.json if created.
)
pause
exit /b %RESULT%
