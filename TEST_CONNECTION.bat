@echo off
title Financial Research Copilot - Connection Test
color 0E

echo.
echo ========================================================
echo   Financial Research Copilot
echo   Testing API Connection
echo ========================================================
echo.

echo [1/2] Testing Backend API...
echo.

REM Test backend
curl -s http://localhost:8000/api/v1/health >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Backend is not responding!
    echo   Make sure the backend is running on http://localhost:8000
    echo.
    echo   To start backend: Double-click run_backend.bat
) else (
    echo   [OK] Backend is running!
    echo   Response from http://localhost:8000/api/v1/health :
    curl -s http://localhost:8000/api/v1/health
)

echo.
echo.

echo [2/2] Testing Frontend...
echo.

REM Test frontend (check if port 5173 is listening)
netstat -an | findstr ":5173" >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Frontend is not running!
    echo   Make sure the frontend is running on http://localhost:5173
    echo.
    echo   To start frontend: Double-click run_frontend.bat
) else (
    echo   [OK] Frontend is running on port 5173!
)

echo.
echo ========================================================
echo   Connection Test Complete
echo ========================================================
echo.
echo If both services are running, open:
echo   http://localhost:5173
echo.
pause
