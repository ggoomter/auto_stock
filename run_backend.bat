@echo off

title Backend - FastAPI Server (8650)
color 0A

echo.
echo ================================================
echo   Financial Research Copilot - Backend Server

echo ================================================

echo.

cd /d %~dp0backend

echo [1/2] Installing dependencies (if needed)...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)
echo [OK] Dependencies ready

echo.
echo [2/2] Starting FastAPI server on http://localhost:8650

echo Press Ctrl+C to stop the server when finished.
echo.

python uvicorn_start.py

if errorlevel 1 (
    echo.
    echo [ERROR] Backend server exited with an error.
    pause
    exit /b 1
)