@echo off

title Frontend - React Dev Server (4783)

echo.
echo ================================================
echo   Financial Research Copilot - Frontend UI

echo ================================================

echo.

cd /d %~dp0frontend

echo [1/2] Installing dependencies (if needed)...
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)
echo [OK] Dependencies ready

echo.
echo [2/2] Starting Vite dev server on http://localhost:4783 (port 4783)

echo Press Ctrl+C to stop the server when finished.
echo.

REM 서버 출력을 logs\frontend.log로 기록 — 최소화 창에서 죽어도 원인 추적 가능
if not exist "%~dp0logs" mkdir "%~dp0logs"
echo ===== [%date% %time%] frontend start ===== >> "%~dp0logs\frontend.log"
call npm run dev >> "%~dp0logs\frontend.log" 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] Frontend dev server exited with an error.
    pause
    exit /b 1
)