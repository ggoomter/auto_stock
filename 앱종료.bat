@echo off
chcp 65001 > nul
title 금융 분석 플랫폼 - 종료
color 0C

echo ================================
echo   금융 분석 플랫폼 종료
echo ================================
echo.

echo [작업 1/3] 백엔드 서버 종료 중...
REM FastAPI/Uvicorn 프로세스 종료
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*" > nul 2>&1
taskkill /F /FI "WINDOWTITLE eq *python*" /FI "MEMUSAGE gt 50000" > nul 2>&1

REM 포트 8000번 사용 중인 프로세스 강제 종료
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    taskkill /F /PID %%a > nul 2>&1
    if not errorlevel 1 echo [완료] 백엔드 서버 종료 (PID: %%a)
)

echo.
echo [작업 2/3] 프론트엔드 서버 종료 중...
REM Vite/Node 프로세스 종료
taskkill /F /IM node.exe > nul 2>&1

REM 포트 5173번 사용 중인 프로세스 강제 종료
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5173" ^| find "LISTENING"') do (
    taskkill /F /PID %%a > nul 2>&1
    if not errorlevel 1 echo [완료] 프론트엔드 서버 종료 (PID: %%a)
)

echo.
echo [작업 3/3] 관련 프로세스 정리 중...
REM 남은 관련 프로세스 정리
taskkill /F /IM python.exe /T > nul 2>&1
taskkill /F /IM node.exe /T > nul 2>&1

timeout /t 1 /nobreak > nul

echo.
echo ================================
echo   종료 완료!
echo ================================
echo.
echo 모든 서버가 정상적으로 종료되었습니다.
echo.
pause
