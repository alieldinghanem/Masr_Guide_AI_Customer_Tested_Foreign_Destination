@echo off
setlocal
cd /d "%~dp0"
echo Checking complete release: Python, React, Browser, Gemini (optional)...
echo First install frontend packages if missing. Make sure Node.js and Python are installed.
python scripts\verify_release_v78.py --install-frontend --browser
if errorlevel 1 (
  echo.
  echo [NOT READY] See failed gates above and release-verification-local.json.
  echo Real Gemini must also be tested before claiming live AI works.
  pause
  exit /b 1
)
echo.
echo [CHECK] Run live AI with your own rotated key only if you authorize real API requests:
echo python scripts\verify_release_v78.py --browser --live-gemini
echo.
pause
