@echo off
echo ====================================
echo Clean Restart - Kill all processes
echo ====================================

echo.
echo [1/4] Killing Python processes...
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

echo [2/4] Killing Node processes...
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak >nul

echo [3/4] Deleting Python cache...
cd backend
for /d /r %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
del /s /q *.pyc 2>nul
cd ..

echo [4/4] Starting fresh servers...
start /b cmd /c "cd backend && venv\Scripts\activate && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul

start /b cmd /c "cd frontend && npm run dev"

echo.
echo ====================================
echo Server started!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo ====================================