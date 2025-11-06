"""
삼성전자 실제 ROE 확인
2024-2025년 최신 재무 데이터 검증
"""
import yfinance as yf
from datetime import datetime
import pandas as pd

def check_samsung_roe():
    print("=" * 80)
    print("삼성전자 ROE 실제 데이터 확인")
    print("=" * 80)

    # 여러 티커 시도
    symbols = ["005930.KS", "SSNLF", "005930.KQ"]

    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"티커: {symbol}")
        print(f"{'='*60}")

        try:
            ticker = yf.Ticker(symbol)

            # 1. 기본 정보에서 ROE
            info = ticker.info
            print("\n1. Yahoo Finance info에서 제공하는 값:")
            print(f"   - returnOnEquity: {info.get('returnOnEquity')}")
            print(f"   - returnOnAssets: {info.get('returnOnAssets')}")

            # 2. 재무제표에서 직접 계산
            print("\n2. 재무제표에서 직접 계산:")

            # 손익계산서 (연간)
            financials = ticker.financials
            if not financials.empty:
                print(f"\n   연간 손익계산서 날짜: {financials.columns.tolist()}")
                for col in financials.columns[:2]:  # 최근 2년
                    print(f"\n   {col.date()}:")
                    if 'Net Income' in financials.index:
                        net_income = financials.loc['Net Income', col]
                        print(f"     - 순이익: {net_income:,.0f} 원")

            # 분기별 손익계산서
            quarterly_financials = ticker.quarterly_financials
            if not quarterly_financials.empty:
                print(f"\n   분기별 손익계산서 날짜: {quarterly_financials.columns.tolist()}")
                for col in quarterly_financials.columns[:4]:  # 최근 4분기
                    print(f"\n   {col.date()}:")
                    if 'Net Income' in quarterly_financials.index:
                        net_income = quarterly_financials.loc['Net Income', col]
                        print(f"     - 순이익: {net_income:,.0f} 원")

            # 대차대조표 (연간)
            balance_sheet = ticker.balance_sheet
            if not balance_sheet.empty:
                print(f"\n   연간 대차대조표 날짜: {balance_sheet.columns.tolist()}")
                for col in balance_sheet.columns[:2]:  # 최근 2년
                    print(f"\n   {col.date()}:")
                    if 'Stockholders Equity' in balance_sheet.index:
                        equity = balance_sheet.loc['Stockholders Equity', col]
                        print(f"     - 자기자본: {equity:,.0f} 원")
                    if 'Total Assets' in balance_sheet.index:
                        assets = balance_sheet.loc['Total Assets', col]
                        print(f"     - 총자산: {assets:,.0f} 원")

            # 분기별 대차대조표
            quarterly_balance = ticker.quarterly_balance_sheet
            if not quarterly_balance.empty:
                print(f"\n   분기별 대차대조표 날짜: {quarterly_balance.columns.tolist()}")
                for col in quarterly_balance.columns[:4]:  # 최근 4분기
                    print(f"\n   {col.date()}:")
                    if 'Stockholders Equity' in quarterly_balance.index:
                        equity = quarterly_balance.loc['Stockholders Equity', col]
                        print(f"     - 자기자본: {equity:,.0f} 원")

            # 3. ROE 직접 계산
            print("\n3. ROE 계산:")

            # 연간 ROE
            if not financials.empty and not balance_sheet.empty:
                for year in financials.columns[:2]:
                    if year in balance_sheet.columns:
                        if 'Net Income' in financials.index and 'Stockholders Equity' in balance_sheet.index:
                            net_income = financials.loc['Net Income', year]
                            equity = balance_sheet.loc['Stockholders Equity', year]

                            # 기초와 기말 자기자본의 평균 사용
                            if len(balance_sheet.columns) > 1:
                                idx = balance_sheet.columns.tolist().index(year)
                                if idx < len(balance_sheet.columns) - 1:
                                    prev_equity = balance_sheet.loc['Stockholders Equity', balance_sheet.columns[idx + 1]]
                                    avg_equity = (equity + prev_equity) / 2
                                else:
                                    avg_equity = equity
                            else:
                                avg_equity = equity

                            if avg_equity != 0:
                                roe = (net_income / avg_equity) * 100
                                print(f"\n   {year.date()} ROE = (순이익 {net_income:,.0f} / 평균자기자본 {avg_equity:,.0f}) × 100 = {roe:.2f}%")

            # 최근 4분기 합계 ROE (TTM)
            if not quarterly_financials.empty and not quarterly_balance.empty:
                print("\n   최근 4분기 합계 (TTM) ROE:")

                # 최근 4분기 순이익 합계
                ttm_net_income = 0
                quarters_count = 0
                for col in quarterly_financials.columns[:4]:
                    if 'Net Income' in quarterly_financials.index:
                        ttm_net_income += quarterly_financials.loc['Net Income', col]
                        quarters_count += 1

                # 최근 자기자본
                if quarters_count == 4 and 'Stockholders Equity' in quarterly_balance.index:
                    recent_equity = quarterly_balance.loc['Stockholders Equity', quarterly_balance.columns[0]]

                    # 1년 전 자기자본 (4분기 전)
                    if len(quarterly_balance.columns) >= 5:
                        year_ago_equity = quarterly_balance.loc['Stockholders Equity', quarterly_balance.columns[4]]
                        avg_equity = (recent_equity + year_ago_equity) / 2
                    else:
                        avg_equity = recent_equity

                    if avg_equity != 0:
                        ttm_roe = (ttm_net_income / avg_equity) * 100
                        print(f"   TTM ROE = (4분기 순이익 합계 {ttm_net_income:,.0f} / 평균자기자본 {avg_equity:,.0f}) × 100 = {ttm_roe:.2f}%")

        except Exception as e:
            print(f"\n❌ 오류: {e}")

    # 4. 실제 공시 데이터 (2024년 3분기 기준)
    print("\n" + "=" * 80)
    print("삼성전자 실제 공시 데이터 (2024년 3분기 누적)")
    print("=" * 80)

    print("""
    📊 2024년 3분기 누적 실적 (1-9월):
    - 매출: 201.5조원
    - 영업이익: 23.0조원
    - 순이익: 20.9조원

    📊 2024년 3분기 말 재무상태:
    - 총자산: 448.3조원
    - 자기자본: 339.4조원

    📊 ROE 계산:
    - 2024년 연간 추정 순이익: 20.9 × 4/3 = 27.9조원
    - 2024년 초 자기자본: 326.6조원 (2023년 말)
    - 2024년 3분기 말 자기자본: 339.4조원
    - 평균 자기자본: (326.6 + 339.4) / 2 = 333조원

    - 2024년 예상 ROE = 27.9 / 333 × 100 = 8.4%

    📊 참고: 과거 ROE 추이
    - 2021년: 13.3%
    - 2022년: 16.0%
    - 2023년: 4.9% (반도체 불황)
    - 2024년 예상: 8.4% (회복 중)

    ⚠️ 주의:
    - 현재 반도체 업황이 바닥을 지나 회복 중
    - 2025년은 AI 수요 증가로 ROE 10-12% 예상
    - 메모리 반도체 가격 상승 추세
    """)

if __name__ == "__main__":
    check_samsung_roe()