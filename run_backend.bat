@echo off

title Backend - FastAPI Server (8650)

echo.
echo ================================================
echo   Financial Research Copilot - Backend Server
echo ================================================
echo.

cd /d %~dp0backend

echo [1/3] Activating virtual environment...
if not exist venv (
    echo [ERROR] Virtual environment not found!
    echo Please run: backend\SIMPLE_INSTALL.bat
    pause
    exit /b 1
)

REM activate.bat은 venv 생성 당시 경로(G: 드라이브)가 하드코딩돼 있어 무효 —
REM PATH 조작 대신 venv의 python.exe를 직접 지정한다 (전역 python 오염 차단)
set "VENV_PY=%~dp0backend\venv\Scripts\python.exe"
echo [OK] Using venv python: %VENV_PY%

echo.
echo [2/3] Checking dependencies...
"%VENV_PY%" -c "import fastapi, pandas, apscheduler" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Core dependencies missing
    echo Installing from requirements.txt...
    "%VENV_PY%" -m pip install -q -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
)

"%VENV_PY%" -c "import pandas_ta" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] pandas-ta not found, installing without dependencies...
    "%VENV_PY%" -m pip install --no-deps pandas-ta==0.4.71b0
    if errorlevel 1 (
        echo [ERROR] Failed to install pandas-ta!
        pause
        exit /b 1
    )
)

echo [OK] All dependencies ready

echo.
echo [3/3] Starting FastAPI server on http://localhost:8650 (port 8650)
echo Press Ctrl+C to stop the server when finished.
echo.

REM 서버 출력을 logs\backend.log로 기록 — 최소화 창에서 죽어도 원인 추적 가능
if not exist "%~dp0logs" mkdir "%~dp0logs"
echo ===== [%date% %time%] backend start ===== >> "%~dp0logs\backend.log"
"%VENV_PY%" uvicorn_start.py >> "%~dp0logs\backend.log" 2>&1

if errorlevel 1 (
    echo.
    echo [ERROR] Backend server exited with an error.
    pause
    exit /b 1
)