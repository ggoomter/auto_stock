@echo off

title Stop Services
color 0C

echo.
echo ========================================================
echo   Stopping All Services...
echo ========================================================
echo.

echo [1/2] Stopping Backend (port 8650)...
taskkill /F /FI "WINDOWTITLE eq FR_BACKEND" >nul 2>&1
wmic process where "commandline like '%%uvicorn_start.py%%'" delete >nul 2>&1
if errorlevel 1 (
    echo   [!] Backend window not found
) else (
    echo   [OK] Backend stopped
)

echo.
echo [2/2] Stopping Frontend (port 4783)...
taskkill /F /FI "WINDOWTITLE eq FR_FRONTEND" >nul 2>&1
wmic process where "commandline like '%%npm%%run%%dev%%'" delete >nul 2>&1
if errorlevel 1 (
    echo   [!] Frontend window not found
) else (
    echo   [OK] Frontend stopped
)

echo.
echo ========================================================
echo   All Services Stopped!
echo ========================================================
echo.

timeout /t 2 /nobreak >nul