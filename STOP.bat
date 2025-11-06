@echo off

title Stop Services
REM color 0E는 노란색, 0A는 초록색, 07은 기본 흰색
color 0E

echo.
echo ========================================================
echo   Stopping All Services...
echo ========================================================
echo.

echo [1/4] Closing console windows...
REM START.bat로 실행된 창 제목으로 종료
taskkill /FI "WINDOWTITLE eq Backend Server*" /F >nul 2>&1
if %errorlevel% equ 0 (echo   - Backend window closed)
taskkill /FI "WINDOWTITLE eq Frontend Server*" /F >nul 2>&1
if %errorlevel% equ 0 (echo   - Frontend window closed)
taskkill /FI "WINDOWTITLE eq Administrator:  Backend Server*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Administrator:  Frontend Server*" /F >nul 2>&1

echo [2/4] Stopping Backend processes (Python/uvicorn)...
REM Python 및 uvicorn 프로세스 종료
taskkill /F /IM uvicorn.exe >nul 2>&1
taskkill /F /IM python.exe /FI "MEMUSAGE gt 50000" >nul 2>&1
wmic process where "commandline like '%%uvicorn%%app.main:app%%'" delete >nul 2>&1
wmic process where "commandline like '%%uvicorn_start.py%%'" delete >nul 2>&1
wmic process where "commandline like '%%run_backend.bat%%'" delete >nul 2>&1

REM 포트 8650을 사용하는 프로세스 찾아서 종료
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8650') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo   [OK] Backend stopped

echo.
echo [3/4] Stopping Frontend processes (Node/Vite)...
REM Node 및 Vite 프로세스 종료
taskkill /F /IM node.exe /FI "MEMUSAGE gt 50000" >nul 2>&1
wmic process where "commandline like '%%vite%%'" delete >nul 2>&1
wmic process where "commandline like '%%npm%%run%%dev%%'" delete >nul 2>&1
wmic process where "commandline like '%%run_frontend.bat%%'" delete >nul 2>&1

REM 포트 4783을 사용하는 프로세스 찾아서 종료
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :4783') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo   [OK] Frontend stopped

echo.
echo [4/4] Verifying ports are freed...
timeout /t 2 /nobreak >nul

REM 포트 확인
netstat -ano | findstr :8650 >nul 2>&1
if errorlevel 1 (
    echo   [OK] Port 8650 is free
) else (
    echo   [!] Port 8650 may still be in use
    echo   Attempting force kill...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8650') do (
        echo   Killing PID %%a
        taskkill /PID %%a /F
    )
)

netstat -ano | findstr :4783 >nul 2>&1
if errorlevel 1 (
    echo   [OK] Port 4783 is free
) else (
    echo   [!] Port 4783 may still be in use
    echo   Attempting force kill...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :4783') do (
        echo   Killing PID %%a
        taskkill /PID %%a /F
    )
)

echo.
echo ========================================================
echo   All Services Stopped!
echo ========================================================
echo.
echo Logs saved in logs\ folder
echo.
echo Press any key to exit...
pause >nul