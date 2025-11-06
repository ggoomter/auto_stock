@echo off
echo ===================================
echo PyKrx 설치 및 테스트
echo ===================================

cd backend

echo.
echo PyKrx 설치 중...
venv\Scripts\pip.exe install pykrx

echo.
echo 삼성전자 데이터 테스트 중...
venv\Scripts\python.exe ..\tests\test_pykrx_samsung.py

pause