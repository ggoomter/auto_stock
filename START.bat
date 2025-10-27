@echo off

title Financial Research Copilot
color 0A

echo.
echo ========================================================
echo   Financial Research Copilot

echo   Starting...
echo ========================================================
echo.

REM --- 환경 점검 ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH!
    pause
    exit /b 1
)

echo [OK] Python found:
python --version
echo.

echo [OK] Node.js found:
node --version
echo.

REM --- 의존성 설치 (필요 시) ---
set BACKEND_INSTALLED=0
set FRONTEND_INSTALLED=0

python -c "import fastapi" >nul 2>&1
if not errorlevel 1 set BACKEND_INSTALLED=1

if exist "%~dp0frontend\node_modules" set FRONTEND_INSTALLED=1

if %BACKEND_INSTALLED%==0 (
    echo Installing backend dependencies...
    pip install -r "%~dp0backend\requirements.txt"
    if errorlevel 1 (
        echo [ERROR] Failed to install backend dependencies.
        pause
        exit /b 1
    )
    echo [OK] Backend dependencies installed
) else (
    echo [OK] Backend dependencies already installed
)
echo.

if %FRONTEND_INSTALLED%==0 (
    echo Installing frontend dependencies...
    cd /d "%~dp0frontend" && call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies.
        pause
        exit /b 1
    )
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies already installed
)
echo.

echo ========================================================
echo   Starting Services...
echo ========================================================
echo.

echo Opening backend console...
start "FR_BACKEND" "%~dp0run_backend.bat"

echo Opening frontend console...
start "FR_FRONTEND" "%~dp0run_frontend.bat"

echo.
echo ========================================================
echo   All Services Running!
echo ========================================================
echo Backend:  http://localhost:8650
echo Frontend: http://localhost:4783
echo API Docs: http://localhost:8650/docs
echo.

start http://localhost:4783

echo.
echo ========================================================
echo   Press any key to stop all services...
echo ========================================================
pause >nul

echo Stopping services...
taskkill /F /FI "WINDOWTITLE eq FR_BACKEND" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq FR_FRONTEND" >nul 2>&1
wmic process where "commandline like '%%uvicorn_start.py%%'" delete >nul 2>&1
wmic process where "commandline like '%%npm%%run%%dev%%'" delete >nul 2>&1

echo Services stopped.
timeout /t 2 /nobreak >nul