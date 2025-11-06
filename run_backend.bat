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

call venv\Scripts\activate.bat
echo [OK] Virtual environment activated

echo.
echo [2/3] Checking dependencies...
python -c "import fastapi, pandas, apscheduler" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Core dependencies missing
    echo Installing from requirements.txt...
    pip install -q -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
)

python -c "import pandas_ta" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] pandas-ta not found, installing without dependencies...
    pip install --no-deps pandas-ta==0.4.71b0
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

python uvicorn_start.py

if errorlevel 1 (
    echo.
    echo [ERROR] Backend server exited with an error.
    pause
    exit /b 1
)