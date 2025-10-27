import yfinance as yf

ticker = yf.Ticker('005930.KS')
info = ticker.info

print("=== Samsung Electronics (005930.KS) ===")
print(f"회사명: {info.get('longName', 'N/A')}")
print(f"\n현재 지표:")
print(f"  PEG Ratio: {info.get('pegRatio', 'N/A')}")
print(f"  Earnings Growth: {info.get('earningsGrowth', 'N/A')}")
print(f"  Revenue Growth: {info.get('revenueGrowth', 'N/A')}")
print(f"  ROE: {info.get('returnOnEquity', 'N/A')}")
print(f"  Trailing P/E: {info.get('trailingPE', 'N/A')}")
print(f"  Forward P/E: {info.get('forwardPE', 'N/A')}")

print("\n=== 분기별 순이익 (Net Income) ===")
qf = ticker.quarterly_financials
if 'Net Income' in qf.index:
    ni = qf.loc['Net Income']
    print(ni)

    # 성장률 계산
    quarters = ni.sort_index()
    if len(quarters) >= 4:
        # YoY 성장률 (4분기 전 대비)
        latest = quarters.iloc[0]
        year_ago = quarters.iloc[3]
        yoy_growth = ((latest / year_ago) - 1) * 100
        print(f"\nYoY 성장률 (최근분기 vs 4분기전): {yoy_growth:.1f}%")
        print(f"  최근 분기: {latest:,.0f}")
        print(f"  4분기 전: {year_ago:,.0f}")
else:
    print("Net Income 데이터 없음")

print("\n=== 문제 분석 ===")
print("1. PEG Ratio: yfinance가 한국 주식에 대해 PEG를 제공하지 않음")
print("2. Earnings Growth: yfinance의 earningsGrowth는 최근 실적 기준")
print("3. 삼성전자는 2023년 반도체 불황으로 실제로 실적 감소")
print("4. 2024년 하반기부터 회복세 → 최신 분기 데이터 확인 필요")
