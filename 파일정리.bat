@echo off
chcp 65001 > nul
echo ================================
echo   불필요한 파일 정리 도구
echo ================================
echo.
echo 다음 파일들이 삭제됩니다:
echo.
echo [중복/테스트용 BAT 파일]
echo - START.bat (앱시작.bat으로 대체)
echo - STOP.bat (앱종료.bat으로 대체)
echo - start_auto_stock.bat (앱시작.bat으로 대체)
echo - run_backend.bat (백엔드실행.bat으로 대체)
echo - run_frontend.bat (프론트엔드실행.bat으로 대체)
echo - CLEAN_RESTART.bat
echo - KILL_ALL.bat
echo - STOP_CLEAN.bat
echo - TEST_CONNECTION.bat
echo - check_samsung_roe.bat
echo - run_pykrx_test.bat
echo - test_korean_direct.bat
echo - test_pykrx.bat
echo - backend\SIMPLE_INSTALL.bat
echo.
echo [개발 테스트 Python 파일 - 루트 디렉토리]
echo - test_*.py (26개)
echo.
echo [임시 파일]
echo - backend\verify_upgrade.py
echo.
set /p confirm="정말 삭제하시겠습니까? (Y/N): "
if /i not "%confirm%"=="Y" (
    echo 취소되었습니다.
    pause
    exit /b
)

echo.
echo 삭제 중...
echo.

REM 영문 BAT 파일 삭제 (한글 파일로 대체)
if exist START.bat (del START.bat && echo [완료] START.bat 삭제)
if exist STOP.bat (del STOP.bat && echo [완료] STOP.bat 삭제)
if exist start_auto_stock.bat (del start_auto_stock.bat && echo [완료] start_auto_stock.bat 삭제)
if exist run_backend.bat (del run_backend.bat && echo [완료] run_backend.bat 삭제)
if exist run_frontend.bat (del run_frontend.bat && echo [완료] run_frontend.bat 삭제)

REM 테스트용 BAT 파일 삭제
if exist CLEAN_RESTART.bat (del CLEAN_RESTART.bat && echo [완료] CLEAN_RESTART.bat 삭제)
if exist KILL_ALL.bat (del KILL_ALL.bat && echo [완료] KILL_ALL.bat 삭제)
if exist STOP_CLEAN.bat (del STOP_CLEAN.bat && echo [완료] STOP_CLEAN.bat 삭제)
if exist TEST_CONNECTION.bat (del TEST_CONNECTION.bat && echo [완료] TEST_CONNECTION.bat 삭제)
if exist check_samsung_roe.bat (del check_samsung_roe.bat && echo [완료] check_samsung_roe.bat 삭제)
if exist run_pykrx_test.bat (del run_pykrx_test.bat && echo [완료] run_pykrx_test.bat 삭제)
if exist test_korean_direct.bat (del test_korean_direct.bat && echo [완료] test_korean_direct.bat 삭제)
if exist test_pykrx.bat (del test_pykrx.bat && echo [완료] test_pykrx.bat 삭제)
if exist backend\SIMPLE_INSTALL.bat (del backend\SIMPLE_INSTALL.bat && echo [완료] backend\SIMPLE_INSTALL.bat 삭제)

REM 루트 디렉토리 테스트 Python 파일 삭제
for %%f in (test_*.py) do (
    if exist "%%f" (
        del "%%f"
        echo [완료] %%f 삭제
    )
)

REM 기타 임시 파일
if exist backend\verify_upgrade.py (del backend\verify_upgrade.py && echo [완료] backend\verify_upgrade.py 삭제)

echo.
echo ================================
echo   정리 완료!
echo ================================
echo.
echo 정리된 파일: 약 40개
echo.
echo 남은 주요 파일:
echo - 앱시작.bat (메인 실행)
echo - 앱종료.bat (종료)
echo - 백엔드실행.bat (백엔드만)
echo - 프론트엔드실행.bat (프론트엔드만)
echo - 파일정리.bat (이 파일)
echo - tests\ 폴더 (공식 테스트 유지)
echo.
pause
