@echo off

title Financial Research Copilot

echo.
echo ========================================================
echo   Financial Research Copilot
echo   Starting...
echo ========================================================
echo.

REM --- logs 폴더 생성 ---
if not exist "%~dp0logs" (
    mkdir "%~dp0logs"
)

REM --- 환경 점검 ---
where python
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b 1
)
where node
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

REM --- 포트 충돌 체크 및 이전 인스턴스 종료 ---
echo Checking for port conflicts...
echo.

REM 백엔드 포트 8650 체크
netstat -ano | findstr :8650
if not errorlevel 1 (
    echo [WARNING] Port 8650 is already in use
    echo Attempting to stop previous backend instance...
    wmic process where "commandline like '%%uvicorn%%app.main:app%%'" delete
    wmic process where "commandline like '%%uvicorn_start.py%%'" delete
    timeout /t 2 /nobreak
    echo [OK] Previous backend stopped
    echo.
)

REM 프론트엔드 포트 4783 체크
netstat -ano | findstr :4783
if not errorlevel 1 (
    echo [WARNING] Port 4783 is already in use
    echo Attempting to stop previous frontend instance...
    wmic process where "commandline like '%%vite%%'" delete
    wmic process where "commandline like '%%npm%%run%%dev%%'" delete
    timeout /t 2 /nobreak
    echo [OK] Previous frontend stopped
    echo.
)

REM --- 백엔드 가상환경 확인 ---
if not exist "%~dp0backend\venv" (
    echo [ERROR] Backend virtual environment not found!
    echo.
    echo Please run: backend\SIMPLE_INSTALL.bat
    echo.
    pause
    exit /b 1
)
echo [OK] Backend virtual environment found
echo.

REM --- 프론트엔드 의존성 확인 ---
if not exist "%~dp0frontend\node_modules" (
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
echo   Starting Services (Background Mode)...
echo ========================================================
echo.

REM --- 백엔드 백그라운드 실행 (새 창으로 실행) ---
echo Starting backend on port 8650 (logs/backend.log)...
start "Backend Server" /MIN cmd /c "cd /d "%~dp0" && call run_backend.bat"

echo Waiting for backend to start (5 seconds)...
timeout /t 5 /nobreak

REM --- 프론트엔드 백그라운드 실행 (새 창으로 실행) ---
echo Starting frontend on port 4783 (logs/frontend.log)...
start "Frontend Server" /MIN cmd /c "cd /d "%~dp0" && call run_frontend.bat"

echo.
echo ========================================================
echo   All Services Running! (Background Mode)
echo ========================================================
echo Backend:  http://localhost:8650
echo Frontend: http://localhost:4783
echo API Docs: http://localhost:8650/docs
echo.
echo Logs:
echo   - Backend warnings/errors: logs\app.log.YYYY-MM-DD
echo   - Backend full logs:       logs\backend.log
echo   - Frontend logs:           logs\frontend.log
echo.
echo Note: Backend takes a few seconds to fully start
echo.

timeout /t 3 /nobreak
start http://localhost:4783

echo.
echo ========================================================
echo   Press ANY KEY to stop all services...
echo ========================================================
echo.
choice /C YN /N /M "Press Y to stop services, N to keep running: "
if errorlevel 2 goto :end
if errorlevel 1 goto :stop

:stop
echo.
echo Stopping services...
echo.

REM Backend 프로세스 종료
echo Stopping backend...
taskkill /FI "WINDOWTITLE eq Backend Server*" /F 2>NUL
wmic process where "commandline like '%%uvicorn%%app.main:app%%'" delete 2>NUL

REM Frontend 프로세스 종료
echo Stopping frontend...
taskkill /FI "WINDOWTITLE eq Frontend Server*" /F 2>NUL
wmic process where "commandline like '%%vite%%'" delete 2>NUL

echo.
echo [OK] All services stopped.
echo.
timeout /t 2 /nobreak
goto :end

:end
