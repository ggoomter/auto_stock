@echo off
title Backend Setup - Smart Install
color 0A

echo ========================================================
echo   Backend Installation - Smart Install
echo ========================================================
echo.

cd /d "%~dp0"

REM ============================================================
REM 1. 가상환경 검증
REM ============================================================
echo [1/4] Checking virtual environment...

if exist venv (
    echo Found existing virtual environment
    echo Verifying installation...

    call venv\Scripts\activate.bat

    REM 핵심 패키지들이 모두 설치되어 있는지 확인
    python -c "import fastapi, pandas, numpy, pandas_ta" >nul 2>&1

    if errorlevel 1 (
        echo [WARNING] Virtual environment is incomplete or broken
        echo.
        choice /C YN /M "Recreate virtual environment? (Y=Yes, N=Repair)"
        if errorlevel 2 (
            echo Attempting to repair...
            goto :repair_venv
        )
        echo Removing old virtual environment...
        deactivate 2>nul
        rmdir /s /q venv
        goto :create_venv
    ) else (
        echo [OK] Virtual environment is valid and complete
        echo.
        choice /C YN /M "Skip installation and use existing environment?"
        if not errorlevel 2 (
            echo Using existing environment
            goto :test_imports
        )
        echo Continuing with fresh installation...
        deactivate 2>nul
        rmdir /s /q venv
    )
) else (
    echo No virtual environment found
)

REM ============================================================
REM 2. 가상환경 생성
REM ============================================================
:create_venv
echo.
echo [2/4] Creating new virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment created

call venv\Scripts\activate.bat

echo.
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded

goto :install_packages

REM ============================================================
REM 복구 모드
REM ============================================================
:repair_venv
echo.
echo [REPAIR MODE] Installing missing packages...
goto :install_packages

REM ============================================================
REM 3. 패키지 설치
REM ============================================================
:install_packages
echo.
echo [3/4] Installing packages...
echo.

echo Installing core packages from requirements.txt...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [ERROR] Installation failed!
    echo.
    echo Common issues:
    echo - Python 3.14 compatibility: Some packages may not support it yet
    echo - Network issues: Check your internet connection
    echo.
    echo Recommendation: Use Python 3.13 for best compatibility
    pause
    exit /b 1
)

echo.
echo Installing pandas-ta without dependencies...
pip install --no-deps pandas-ta==0.4.71b0
if errorlevel 1 (
    echo [WARNING] pandas-ta installation failed, but may not be critical
)

echo.
echo [OK] All packages installed successfully

REM ============================================================
REM 4. 검증
REM ============================================================
:test_imports
echo.
echo [4/4] Verifying installation...
echo.

set ERROR_COUNT=0

python -c "import fastapi; print('  [OK] FastAPI')" 2>nul || (
    echo   [FAIL] FastAPI
    set /a ERROR_COUNT+=1
)

python -c "import pandas; print('  [OK] Pandas')" 2>nul || (
    echo   [FAIL] Pandas
    set /a ERROR_COUNT+=1
)

python -c "import numpy; print('  [OK] Numpy')" 2>nul || (
    echo   [FAIL] Numpy
    set /a ERROR_COUNT+=1
)

python -c "import pandas_ta; print('  [OK] pandas-ta')" 2>nul || (
    echo   [FAIL] pandas-ta
    set /a ERROR_COUNT+=1
)

python -c "import yfinance; print('  [OK] yfinance')" 2>nul || (
    echo   [FAIL] yfinance
    set /a ERROR_COUNT+=1
)

echo.
if %ERROR_COUNT% GTR 0 (
    echo [WARNING] %ERROR_COUNT% package(s) failed to import
    echo Please check the errors above
    pause
    exit /b 1
)

echo ========================================================
echo   Installation Complete!
echo ========================================================
echo.
echo Python version:
python --version
echo.
echo Installed packages:
pip list | findstr /i "fastapi pandas numpy uvicorn pandas-ta"
echo.
echo ========================================================
echo   Ready to start!
echo ========================================================
echo.
echo To start the backend server:
echo   1. venv\Scripts\activate
echo   2. python uvicorn_start.py
echo.
echo Or simply run: ..\START.bat
echo.
pause
exit /b 0
