@echo off
REM 강제 종료 스크립트 - 모든 관련 프로세스를 확실하게 종료

title Force Kill All Services
REM 경고 메시지이므로 노란색 사용
color 0E

echo.
echo ========================================================
echo   FORCE KILLING ALL SERVICES
echo ========================================================
echo.

echo [1] Killing all Python processes...
taskkill /F /IM python.exe 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Python processes killed
) else (
    echo   [--] No Python processes found
)
taskkill /F /IM pythonw.exe 2>nul

echo [2] Killing all Node.js processes...
taskkill /F /IM node.exe 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Node processes killed
) else (
    echo   [--] No Node processes found
)

echo [3] Killing specific services...
taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM cmd.exe /FI "WINDOWTITLE eq Backend Server*" 2>nul
taskkill /F /IM cmd.exe /FI "WINDOWTITLE eq Frontend Server*" 2>nul

echo [4] Killing processes by port...
echo.
echo Checking port 8650 (Backend)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8650') do (
    echo   Killing PID %%a
    taskkill /PID %%a /F 2>nul
)

echo.
echo Checking port 4783 (Frontend)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :4783') do (
    echo   Killing PID %%a
    taskkill /PID %%a /F 2>nul
)

echo.
echo ========================================================
echo   All processes terminated!
echo ========================================================
echo.
pause