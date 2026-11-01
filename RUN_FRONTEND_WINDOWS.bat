@echo off
setlocal
cd /d "%~dp0frontend"

REM npm ci can leave an incomplete node_modules directory when registry access fails.
REM Verify the actual local Vite executable, not merely the directory name.
if not exist "node_modules\.bin\vite.cmd" (
  echo [ERROR] Frontend dependencies are missing or incomplete.
  echo Run SETUP_AND_TEST_LOCAL_WINDOWS.bat with internet access first.
  pause
  exit /b 1
)

echo Starting React/Vite locally at http://127.0.0.1:5173
call npm run dev -- --host 127.0.0.1
if errorlevel 1 echo [ERROR] React/Vite stopped unexpectedly. Check the error above.
pause
