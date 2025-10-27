"""
현대건설 버그 확인
"""
import yfinance as yf

# 현대건설 데이터 확인
print("=== 현대건설 (000720) 데이터 확인 ===")

hd_ks = yf.Ticker("000720.KS")
data = hd_ks.history(start="2024-01-01", end="2025-10-04")

if not data.empty:
    print(f"\n데이터 건수: {len(data)}")
    print(f"최근 종가: {data['Close'].iloc[-1]:,.0f}원")
    print(f"1년 최고가: {data['Close'].max():,.0f}원")
    print(f"1년 최저가: {data['Close'].min():,.0f}원")

    # 2024-05-27 가격 확인
    print("\n2024-05-27 주변 데이터:")
    may_data = data.loc['2024-05-20':'2024-05-31']
    print(may_data[['Close']])
else:
    print("데이터 없음")
