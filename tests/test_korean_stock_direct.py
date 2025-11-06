"""
한국 주식 데이터 수집 테스트 - 삼성전자를 예시로
yfinance와 pykrx 비교
"""
import yfinance as yf
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# PyKrx 임포트 시도
try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
    print("✅ PyKrx 사용 가능")
except ImportError:
    PYKRX_AVAILABLE = False
    print("❌ PyKrx 사용 불가능")

from datetime import datetime, timedelta

def test_yfinance_samsung():
    """yfinance로 삼성전자 데이터 테스트"""
    print("\n" + "="*50)
    print("1. yfinance로 삼성전자(005930.KS) 데이터 테스트")
    print("="*50)

    ticker = yf.Ticker("005930.KS")
    info = ticker.info

    print(f"회사명: {info.get('longName', 'N/A')}")
    print(f"현재가: {info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))}")
    print(f"시가총액: {info.get('marketCap', 'N/A'):,}" if info.get('marketCap') else "시가총액: N/A")
    print(f"\n주요 지표:")
    print(f"  P/E: {info.get('trailingPE', 'N/A')}")
    print(f"  P/B: {info.get('priceToBook', 'N/A')}")
    print(f"  ROE: {info.get('returnOnEquity', 'N/A')}")
    print(f"  부채비율: {info.get('debtToEquity', 'N/A')}")
    print(f"  잉여현금흐름: {info.get('freeCashflow', 'N/A')}")

    # 분기별 재무제표 확인
    print(f"\n분기별 재무제표:")
    try:
        quarterly_financials = ticker.quarterly_financials
        if not quarterly_financials.empty:
            print(f"  사용 가능한 분기: {len(quarterly_financials.columns)}개")
            print(f"  최신 분기: {quarterly_financials.columns[0]}")

            # Net Income 확인
            if 'Net Income' in quarterly_financials.index:
                latest_income = quarterly_financials.loc['Net Income'].iloc[0]
                print(f"  최신 분기 순이익: {latest_income:,.0f}")
        else:
            print("  분기별 재무제표 없음")
    except Exception as e:
        print(f"  분기별 재무제표 오류: {e}")

    # Balance Sheet 확인
    print(f"\n대차대조표:")
    try:
        balance_sheet = ticker.quarterly_balance_sheet
        if not balance_sheet.empty:
            print(f"  사용 가능한 분기: {len(balance_sheet.columns)}개")

            # 주요 항목 확인
            for item in ['Total Assets', 'Total Liabilities Net Minority Interest',
                        'Stockholders Equity', 'Tangible Book Value', 'Ordinary Shares Number']:
                if item in balance_sheet.index:
                    value = balance_sheet.loc[item].iloc[0]
                    print(f"  {item}: {value:,.0f}")
        else:
            print("  대차대조표 없음")
    except Exception as e:
        print(f"  대차대조표 오류: {e}")

def test_pykrx_samsung():
    """PyKrx로 삼성전자 데이터 테스트"""
    if not PYKRX_AVAILABLE:
        print("\n❌ PyKrx가 설치되지 않아 테스트를 건너뜁니다.")
        return

    print("\n" + "="*50)
    print("2. PyKrx로 삼성전자(005930) 데이터 테스트")
    print("="*50)

    ticker_code = "005930"
    today = datetime.now()
    start_date = (today - timedelta(days=30)).strftime('%Y%m%d')
    end_date = today.strftime('%Y%m%d')

    try:
        # 1. 종목명
        stock_name = stock.get_market_ticker_name(ticker_code)
        print(f"회사명: {stock_name}")

        # 2. 현재가 정보 (OHLCV)
        ohlcv = stock.get_market_ohlcv(start_date, end_date, ticker_code)
        if not ohlcv.empty:
            latest = ohlcv.iloc[-1]
            print(f"현재가: {latest['종가']:,.0f}원")
            print(f"거래량: {latest['거래량']:,.0f}")
            print(f"거래대금: {latest['거래대금']:,.0f}원")

        # 3. 시가총액
        cap_data = stock.get_market_cap(start_date, end_date, ticker_code)
        if not cap_data.empty:
            latest_cap = cap_data.iloc[-1]
            print(f"시가총액: {latest_cap['시가총액']:,.0f}원")
            print(f"상장주식수: {latest_cap['상장주식수']:,.0f}")

        # 4. 펀더멘털 데이터
        fundamental = stock.get_market_fundamental(start_date, end_date, ticker_code)
        if not fundamental.empty:
            latest_fund = fundamental.iloc[-1]
            print(f"\n주요 지표:")
            print(f"  PER: {latest_fund.get('PER', 'N/A')}")
            print(f"  PBR: {latest_fund.get('PBR', 'N/A')}")
            print(f"  EPS: {latest_fund.get('EPS', 'N/A')}")
            print(f"  BPS: {latest_fund.get('BPS', 'N/A')}")
            print(f"  DIV(배당수익률): {latest_fund.get('DIV', 'N/A')}%")

            # ROE 계산 (PBR/PER)
            if latest_fund.get('PBR') and latest_fund.get('PER'):
                roe = latest_fund['PBR'] / latest_fund['PER']
                print(f"  ROE(계산): {roe*100:.2f}%")

    except Exception as e:
        print(f"PyKrx 오류: {e}")

def test_korean_stock_data_service():
    """korean_stock_data.py 서비스 테스트"""
    print("\n" + "="*50)
    print("3. korean_stock_data.py 서비스 테스트")
    print("="*50)

    try:
        from app.services.korean_stock_data import get_korean_stock_fetcher

        fetcher = get_korean_stock_fetcher()

        # 삼성전자 데이터 가져오기
        data = fetcher.get_stock_data("005930.KS")

        if data:
            print(f"회사명: {data.get('name')}")
            print(f"현재가: {data.get('current_price')}")
            print(f"통화: {data.get('currency')}")

            metrics = data.get('metrics', {})
            print(f"\n주요 지표:")
            print(f"  ROE: {metrics.get('ROE', 0)*100:.1f}%" if metrics.get('ROE') else "  ROE: N/A")
            print(f"  P/E: {metrics.get('PE')}")
            print(f"  P/B: {metrics.get('PB')}")
            print(f"  부채비율: {metrics.get('debt_to_equity')}")

            # Buffett metrics 테스트
            buffett_metrics = fetcher.get_buffett_metrics("005930.KS")
            print(f"\nBuffett 지표:")
            for key, value in buffett_metrics.items():
                if value is not None:
                    if key == 'ROE':
                        print(f"  {key}: {value*100:.1f}%")
                    else:
                        print(f"  {key}: {value}")
                else:
                    print(f"  {key}: N/A")
        else:
            print("데이터를 가져올 수 없습니다.")

    except Exception as e:
        print(f"서비스 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

def test_fundamental_analysis():
    """fundamental_analysis.py 서비스 테스트"""
    print("\n" + "="*50)
    print("4. fundamental_analysis.py 서비스 테스트")
    print("="*50)

    try:
        from app.services.fundamental_analysis import FundamentalAnalyzer

        analyzer = FundamentalAnalyzer("005930.KS")

        # Buffett metrics 테스트
        buffett = analyzer.get_buffett_metrics()
        print("Buffett 지표:")
        for key, value in buffett.items():
            if 'source' not in key and 'calculated' not in key:
                print(f"  {key}: {value}")

        # 조건 체크
        details = analyzer.get_buffett_condition_details()
        print(f"\nBuffett 조건 체크:")
        for detail in details:
            status = "✅" if detail['passed'] else "❌"
            print(f"  {status} {detail['condition_name']}: {detail['actual_value']} (필요: {detail['required_value']})")

    except Exception as e:
        print(f"fundamental_analysis 테스트 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("한국 주식 데이터 수집 테스트")
    print("테스트 대상: 삼성전자 (005930)")

    test_yfinance_samsung()
    test_pykrx_samsung()
    test_korean_stock_data_service()
    test_fundamental_analysis()

    print("\n" + "="*50)
    print("테스트 완료")
    print("="*50)