@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Docker Desktop is not installed or not on PATH.
  pause
  exit /b 1
)
echo Building and running Masr Guide AI at http://localhost:8000
set PORT=10000
docker compose -f docker-compose.prod.yml up --build -d
if errorlevel 1 (
  echo [ERROR] Docker startup failed. Run: docker compose -f docker-compose.prod.yml logs
  pause
  exit /b 1
)
echo Site: http://localhost:8000
echo API:  http://localhost:8000/docs
echo Stop: docker compose -f docker-compose.prod.yml down
pause
