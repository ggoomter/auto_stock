@echo off
chcp 65001 > nul
title 금융 분석 플랫폼 - 시작
color 0A

echo ================================
echo   금융 분석 플랫폼 시작
echo ================================
echo.

REM 백엔드 디렉토리 확인
if not exist "backend" (
    echo [오류] backend 폴더를 찾을 수 없습니다.
    echo 현재 위치: %CD%
    pause
    exit /b 1
)

REM 프론트엔드 디렉토리 확인
if not exist "frontend" (
    echo [오류] frontend 폴더를 찾을 수 없습니다.
    echo 현재 위치: %CD%
    pause
    exit /b 1
)

echo [단계 1/4] 가상환경 설정 확인...
cd backend

REM Python 가상환경 생성 (없을 경우)
if not exist "venv\Scripts\activate.bat" (
    echo 가상환경이 없습니다. 새로 생성합니다...
    python -m venv venv
    if errorlevel 1 (
        echo [오류] 가상환경 생성 실패
        echo Python이 설치되어 있는지 확인하세요.
        cd ..
        pause
        exit /b 1
    )
    echo [완료] 가상환경 생성 완료
)

REM 가상환경 활성화 및 패키지 설치
call venv\Scripts\activate.bat

echo.
echo [단계 2/4] 백엔드 의존성 설치 확인...
pip show fastapi > nul 2>&1
if errorlevel 1 (
    echo 필요한 패키지를 설치합니다...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [오류] 패키지 설치 실패
        cd ..
        pause
        exit /b 1
    )
    echo [완료] 패키지 설치 완료
) else (
    echo [확인] 패키지가 이미 설치되어 있습니다.
)

echo.
echo [단계 3/4] 백엔드 서버 시작...
echo 주소: http://localhost:8000
echo API 문서: http://localhost:8000/docs
start /B cmd /c "venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend_log.txt 2>&1"

REM 백엔드 시작 대기
timeout /t 3 /nobreak > nul

cd ..

echo.
echo [단계 4/4] 프론트엔드 서버 시작...
cd frontend

REM npm 패키지 설치 확인
if not exist "node_modules" (
    echo Node.js 패키지를 설치합니다...
    call npm install
    if errorlevel 1 (
        echo [오류] npm 패키지 설치 실패
        echo Node.js가 설치되어 있는지 확인하세요.
        cd ..
        pause
        exit /b 1
    )
    echo [완료] npm 패키지 설치 완료
) else (
    echo [확인] npm 패키지가 이미 설치되어 있습니다.
)

echo 주소: http://localhost:5173
start /B cmd /c "npm run dev > frontend_log.txt 2>&1"

cd ..

echo.
echo ================================
echo   시작 완료!
echo ================================
echo.
echo 백엔드: http://localhost:8000
echo 프론트엔드: http://localhost:5173
echo API 문서: http://localhost:8000/docs
echo.
echo 로그 파일:
echo - backend\backend_log.txt
echo - frontend\frontend_log.txt
echo.
echo 종료하려면 "앱종료.bat"을 실행하세요.
echo.

REM 5초 후 브라우저 자동 실행
echo 5초 후 브라우저가 자동으로 열립니다...
timeout /t 5 /nobreak > nul
start http://localhost:5173

pause
