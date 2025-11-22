@echo off
chcp 65001 > nul
title 금융 분석 플랫폼 - 백엔드
color 0B

echo ================================
echo   백엔드 서버만 실행
echo ================================
echo.

if not exist "backend" (
    echo [오류] backend 폴더를 찾을 수 없습니다.
    pause
    exit /b 1
)

cd backend

echo [단계 1/3] 가상환경 활성화...
if not exist "venv\Scripts\activate.bat" (
    echo [오류] 가상환경이 없습니다.
    echo "앱시작.bat"을 먼저 실행해주세요.
    cd ..
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo [완료] 가상환경 활성화 완료

echo.
echo [단계 2/3] 의존성 확인...
pip show fastapi > nul 2>&1
if errorlevel 1 (
    echo 패키지 설치 중...
    pip install -r requirements.txt
    echo [완료] 패키지 설치 완료
) else (
    echo [확인] 패키지 설치 완료
)

echo.
echo [단계 3/3] 서버 시작...
echo ================================
echo   백엔드 서버 실행 중
echo ================================
echo.
echo 주소: http://localhost:8000
echo API 문서: http://localhost:8000/docs
echo.
echo 종료하려면 Ctrl+C를 누르세요.
echo.

venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd ..
pause
