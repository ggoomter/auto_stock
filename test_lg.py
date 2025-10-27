"""
LG전자 실제 데이터 확인
"""
import yfinance as yf

# LG전자 코드
lg_ks = yf.Ticker("066570.KS")
lg_kq = yf.Ticker("066570.KQ")

print("=== LG전자 데이터 확인 ===")
print("\n[066570.KS - 코스피]")
data_ks = lg_ks.history(period="1y")
if not data_ks.empty:
    print(f"데이터 건수: {len(data_ks)}")
    print(f"최근 종가: {data_ks['Close'].iloc[-1]:,.0f}원")
    print(f"1년 최고가: {data_ks['Close'].max():,.0f}원")
    print(f"1년 최저가: {data_ks['Close'].min():,.0f}원")
    print("\n최근 5일 데이터:")
    print(data_ks.tail())
else:
    print("데이터 없음")

print("\n[066570.KQ - 코스닥]")
data_kq = lg_kq.history(period="1y")
if not data_kq.empty:
    print(f"데이터 건수: {len(data_kq)}")
    print(f"최근 종가: {data_kq['Close'].iloc[-1]:,.0f}원")
    print(f"1년 최고가: {data_kq['Close'].max():,.0f}원")
    print(f"1년 최저가: {data_kq['Close'].min():,.0f}원")
    print("\n최근 5일 데이터:")
    print(data_kq.tail())
else:
    print("데이터 없음")
