@echo off

title Frontend - React Dev Server (4783)
color 0B

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

call npm run dev

if errorlevel 1 (
    echo.
    echo [ERROR] Frontend dev server exited with an error.
    pause
    exit /b 1
)