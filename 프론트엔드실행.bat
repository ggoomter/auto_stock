@echo off
chcp 65001 > nul
title 금융 분석 플랫폼 - 프론트엔드
color 0E

echo ================================
echo   프론트엔드 서버만 실행
echo ================================
echo.

if not exist "frontend" (
    echo [오류] frontend 폴더를 찾을 수 없습니다.
    pause
    exit /b 1
)

cd frontend

echo [단계 1/2] 의존성 확인...
if not exist "node_modules" (
    echo Node.js 패키지 설치 중...
    call npm install
    if errorlevel 1 (
        echo [오류] npm 설치 실패
        echo Node.js가 설치되어 있는지 확인하세요.
        cd ..
        pause
        exit /b 1
    )
    echo [완료] 패키지 설치 완료
) else (
    echo [확인] 패키지 설치 완료
)

echo.
echo [단계 2/2] 서버 시작...
echo ================================
echo   프론트엔드 서버 실행 중
echo ================================
echo.
echo 주소: http://localhost:5173
echo.
echo 백엔드 서버가 실행 중이어야 합니다.
echo 백엔드: http://localhost:8000
echo.
echo 종료하려면 Ctrl+C를 누르세요.
echo.

call npm run dev

cd ..
pause
