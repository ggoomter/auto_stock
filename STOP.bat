@echo off

title Stop Services
color 0C

echo.
echo ========================================================
echo   Stopping All Services...
echo ========================================================
echo.

echo [1/2] Stopping Backend (port 8650)...
REM 백그라운드 프로세스 종료 (uvicorn)
wmic process where "commandline like '%%uvicorn%%app.main:app%%'" delete >nul 2>&1
wmic process where "commandline like '%%uvicorn_start.py%%'" delete >nul 2>&1
if errorlevel 1 (
    echo   [!] Backend process not found
) else (
    echo   [OK] Backend stopped
)

echo.
echo [2/2] Stopping Frontend (port 4783)...
REM 백그라운드 프로세스 종료 (vite)
wmic process where "commandline like '%%vite%%'" delete >nul 2>&1
if errorlevel 1 (
    echo   [!] Frontend process not found
) else (
    echo   [OK] Frontend stopped
)

echo.
echo ========================================================
echo   All Services Stopped!
echo ========================================================
echo.
echo Logs saved in logs\ folder
echo.

timeout /t 2 /nobreak >nul
