@echo off
title AutoStock Pro Launcher
echo ==========================================
echo       AutoStock Pro Launcher
echo ==========================================
echo.

echo Starting Backend Server...
:: backend 폴더로 이동하여 venv 활성화 후 uvicorn 실행 (새 창에서)
start "AutoStock Backend" cmd /k "cd /d %~dp0backend && if exist venv\Scripts\activate (call venv\Scripts\activate && python -m uvicorn app.main:app --reload) else (echo Virtual environment not found. Please run backend\SIMPLE_INSTALL.bat first. && pause)"

echo Starting Frontend Server...
:: frontend 폴더로 이동하여 npm run dev 실행 (새 창에서)
start "AutoStock Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ==========================================
echo  Servers are starting...
echo  Backend: http://localhost:8000
echo  Frontend: http://localhost:5173
echo ==========================================
echo.
echo 이 창을 닫으면 실행이 종료될 수 있습니다.
echo 브라우저가 자동으로 열리지 않으면 위 주소로 접속하세요.
pause
