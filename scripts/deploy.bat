@echo off
title AI Memory OS
echo ========================================
echo   AI Memory OS — Launcher (Windows)
echo ========================================
echo.

echo Checking Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] Docker not found
    echo Install from https://docker.com
    pause
    exit /b 1
)
echo [OK] Docker ready

echo Starting services...
docker compose up -d
if %errorlevel% neq 0 (
    echo [FAIL] Could not start services
    pause
    exit /b 1
)
echo [OK] Services started

echo Waiting for PostgreSQL...
timeout /t 5 /nobreak >nul

echo Setting up Python...
if not exist .venv python -m venv .venv
.venv\Scripts\pip install -q -r backend\requirements.txt
echo [OK] Dependencies ready

echo Starting API server...
set PYTHONPATH=backend
set MEMORY_OS_BM25=1
start http://localhost:8000/admin/ui/
.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
