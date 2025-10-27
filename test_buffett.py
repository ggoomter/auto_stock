from backend.app.services.fundamental_analysis import FundamentalAnalyzer
from datetime import datetime

analyzer = FundamentalAnalyzer('AAPL')

# 2024-01-01에 버핏 기준 체크
test_date = datetime(2024, 1, 1)
passes = analyzer.check_buffett_criteria_at_date(test_date)
print(f'2024-01-01 passes Buffett criteria: {passes}')

# 현재 지표
info = analyzer.get_info()
print(f'ROE: {info.get("returnOnEquity", 0):.2%}')
print(f'FCF: ${info.get("freeCashflow", 0):,}')
print(f'PE: {info.get("trailingPE", 0):.2f}')
