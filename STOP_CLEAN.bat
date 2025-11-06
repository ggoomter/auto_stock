@echo off
REM 깔끔한 서비스 종료 스크립트

title Stop Services
REM 기본 흰색 텍스트 사용
color 07

echo.
echo ========================================================
echo              Stopping All Services
echo ========================================================
echo.

REM 1. 콘솔 창 종료
echo [Step 1/4] Closing console windows...
set "closed_windows=0"

taskkill /FI "WINDOWTITLE eq Backend Server*" /F >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Backend window closed
    set /a closed_windows+=1
)

taskkill /FI "WINDOWTITLE eq Frontend Server*" /F >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Frontend window closed
    set /a closed_windows+=1
)

if %closed_windows% equ 0 (
    echo   [--] No windows to close
)

REM 2. Backend 프로세스 종료
echo.
echo [Step 2/4] Stopping Backend processes...
set "backend_killed=0"

REM uvicorn 종료
taskkill /F /IM uvicorn.exe >nul 2>&1
if %errorlevel% equ 0 (
    set /a backend_killed+=1
)

REM Port 8650 체크 및 종료
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8650 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    if !errorlevel! equ 0 (
        set /a backend_killed+=1
    )
)

if %backend_killed% gtr 0 (
    echo   [OK] Backend stopped
) else (
    echo   [--] Backend was not running
)

REM 3. Frontend 프로세스 종료
echo.
echo [Step 3/4] Stopping Frontend processes...
set "frontend_killed=0"

REM Node 프로세스 중 메모리를 많이 사용하는 것만 종료
taskkill /F /IM node.exe /FI "MEMUSAGE gt 50000" >nul 2>&1
if %errorlevel% equ 0 (
    set /a frontend_killed+=1
)

REM Port 4783 체크 및 종료
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :4783 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
    if !errorlevel! equ 0 (
        set /a frontend_killed+=1
    )
)

if %frontend_killed% gtr 0 (
    echo   [OK] Frontend stopped
) else (
    echo   [--] Frontend was not running
)

REM 4. 포트 확인
echo.
echo [Step 4/4] Verifying ports...
timeout /t 1 /nobreak >nul

set "ports_free=1"

netstat -ano | findstr :8650 >nul 2>&1
if %errorlevel% equ 0 (
    echo   [!] Warning: Port 8650 still in use
    set "ports_free=0"
) else (
    echo   [OK] Port 8650 is free
)

netstat -ano | findstr :4783 >nul 2>&1
if %errorlevel% equ 0 (
    echo   [!] Warning: Port 4783 still in use
    set "ports_free=0"
) else (
    echo   [OK] Port 4783 is free
)

echo.
echo ========================================================
if %ports_free% equ 1 (
    color 0A
    echo              All Services Stopped Successfully!
) else (
    color 0E
    echo              Services Stopped (Some ports may be in use)
    echo              Run KILL_ALL.bat if needed
)
echo ========================================================
echo.
pause