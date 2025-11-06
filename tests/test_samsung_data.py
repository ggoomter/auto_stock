"""
삼성전자 재무 데이터 테스트
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def test_samsung_data():
    print("=" * 80)
    print("삼성전자 재무 데이터 테스트")
    print("=" * 80)

    # 여러 가지 티커 시도
    tickers = [
        "005930.KS",  # 한국거래소
        "005930.KQ",  # KOSDAQ (잘못된 거 알지만 시도)
        "005930.KRX", # KRX
        "005930",     # 티커만
        "SSNLF",      # 삼성 ADR
    ]

    for ticker_symbol in tickers:
        print(f"\n{'='*60}")
        print(f"테스트 티커: {ticker_symbol}")
        print(f"{'='*60}")

        try:
            ticker = yf.Ticker(ticker_symbol)

            # 1. 기본 정보
            print("\n1. 기본 정보 (info):")
            info = ticker.info
            print(f"   - 회사명: {info.get('longName', 'N/A')}")
            print(f"   - 섹터: {info.get('sector', 'N/A')}")
            print(f"   - 현재가: {info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))}")
            print(f"   - 화폐단위: {info.get('currency', 'N/A')}")

            # 2. 주요 재무 지표
            print("\n2. 주요 재무 지표:")
            print(f"   - P/E (trailingPE): {info.get('trailingPE', 'N/A')}")
            print(f"   - P/E (forwardPE): {info.get('forwardPE', 'N/A')}")
            print(f"   - P/B (priceToBook): {info.get('priceToBook', 'N/A')}")
            print(f"   - ROE (returnOnEquity): {info.get('returnOnEquity', 'N/A')}")
            print(f"   - 부채비율 (debtToEquity): {info.get('debtToEquity', 'N/A')}")
            print(f"   - FCF (freeCashflow): {info.get('freeCashflow', 'N/A')}")
            print(f"   - 영업현금흐름 (operatingCashflow): {info.get('operatingCashflow', 'N/A')}")

            # 3. 재무제표 데이터
            print("\n3. 재무제표 (financials):")
            financials = ticker.financials
            if not financials.empty:
                print("   최근 연도 재무제표:")
                latest_year = financials.columns[0]
                print(f"   날짜: {latest_year}")
                print(f"   - Total Revenue: {financials.loc['Total Revenue', latest_year] if 'Total Revenue' in financials.index else 'N/A'}")
                print(f"   - Net Income: {financials.loc['Net Income', latest_year] if 'Net Income' in financials.index else 'N/A'}")
                print(f"   - Operating Income: {financials.loc['Operating Income', latest_year] if 'Operating Income' in financials.index else 'N/A'}")
            else:
                print("   재무제표 데이터 없음")

            # 4. 대차대조표
            print("\n4. 대차대조표 (balance_sheet):")
            balance = ticker.balance_sheet
            if not balance.empty:
                latest_date = balance.columns[0]
                print(f"   날짜: {latest_date}")
                print(f"   - Total Assets: {balance.loc['Total Assets', latest_date] if 'Total Assets' in balance.index else 'N/A'}")
                print(f"   - Total Liabilities: {balance.loc['Total Liabilities Net Minority Interest', latest_date] if 'Total Liabilities Net Minority Interest' in balance.index else 'N/A'}")
                print(f"   - Stockholders Equity: {balance.loc['Stockholders Equity', latest_date] if 'Stockholders Equity' in balance.index else 'N/A'}")
                print(f"   - Common Stock: {balance.loc['Common Stock', latest_date] if 'Common Stock' in balance.index else 'N/A'}")

                # ROE 수동 계산 시도
                if 'Net Income' in financials.index and 'Stockholders Equity' in balance.index:
                    net_income = financials.loc['Net Income', financials.columns[0]]
                    equity = balance.loc['Stockholders Equity', latest_date]
                    if equity != 0:
                        calculated_roe = (net_income / equity) * 100
                        print(f"\n   *** 계산된 ROE: {calculated_roe:.2f}%")
            else:
                print("   대차대조표 데이터 없음")

            # 5. 현금흐름표
            print("\n5. 현금흐름표 (cashflow):")
            cashflow = ticker.cashflow
            if not cashflow.empty:
                latest_date = cashflow.columns[0]
                print(f"   날짜: {latest_date}")
                print(f"   - Operating Cash Flow: {cashflow.loc['Operating Cash Flow', latest_date] if 'Operating Cash Flow' in cashflow.index else 'N/A'}")
                print(f"   - Free Cash Flow: {cashflow.loc['Free Cash Flow', latest_date] if 'Free Cash Flow' in cashflow.index else 'N/A'}")
                print(f"   - Capital Expenditure: {cashflow.loc['Capital Expenditure', latest_date] if 'Capital Expenditure' in cashflow.index else 'N/A'}")

                # FCF 수동 계산 시도
                if 'Operating Cash Flow' in cashflow.index and 'Capital Expenditure' in cashflow.index:
                    ocf = cashflow.loc['Operating Cash Flow', latest_date]
                    capex = cashflow.loc['Capital Expenditure', latest_date]
                    calculated_fcf = ocf + capex  # capex는 보통 음수로 표시됨
                    print(f"\n   *** 계산된 FCF: {calculated_fcf:,.0f} 원")
            else:
                print("   현금흐름표 데이터 없음")

            # 6. 주가 데이터
            print("\n6. 주가 데이터 (history):")
            hist = ticker.history(period="5d")
            if not hist.empty:
                print(f"   최근 5일 종가:")
                for date, row in hist.tail().iterrows():
                    print(f"   - {date.date()}: {row['Close']:,.0f} 원")
            else:
                print("   주가 데이터 없음")

            # 7. 주당 데이터 계산
            print("\n7. 주당 데이터:")
            shares = info.get('sharesOutstanding', info.get('impliedSharesOutstanding'))
            if shares:
                print(f"   - 발행주식수: {shares:,.0f}")
                if not financials.empty and 'Net Income' in financials.index:
                    net_income = financials.loc['Net Income', financials.columns[0]]
                    eps = net_income / shares
                    print(f"   - 계산된 EPS: {eps:,.2f} 원")

                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        calculated_pe = current_price / eps
                        print(f"   - 계산된 P/E: {calculated_pe:.2f}")
            else:
                print("   발행주식수 데이터 없음")

            print(f"\n✅ {ticker_symbol} 테스트 성공!")

        except Exception as e:
            print(f"\n❌ {ticker_symbol} 오류: {str(e)}")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)

if __name__ == "__main__":
    test_samsung_data()