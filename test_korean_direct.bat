@echo off
call backend\venv\Scripts\activate
python tests\test_korean_stock_direct.py
pause