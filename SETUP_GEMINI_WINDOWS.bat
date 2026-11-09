@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0SETUP_GEMINI_WINDOWS.ps1"
set RESULT=%ERRORLEVEL%
echo.
if "%RESULT%"=="0" (
  echo Gemini setup and live connection check passed.
) else (
  echo Gemini check did not pass. Review the message above.
)
echo.
pause
exit /b %RESULT%
