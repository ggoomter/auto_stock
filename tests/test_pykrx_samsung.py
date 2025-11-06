"""
PyKrx를 사용한 삼성전자 실시간 데이터 테스트
하드코딩 없이 실제 데이터만 사용
"""
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

def test_pykrx_samsung():
    print("=" * 80)
    print("PyKrx를 사용한 삼성전자 실시간 데이터 테스트")
    print("=" * 80)

    # PyKrx 설치 확인
    try:
        from pykrx import stock
        print("[OK] PyKrx 정상 설치됨")
    except ImportError:
        print("[ERROR] PyKrx가 설치되지 않았습니다.")
        print("        설치 방법: pip install pykrx")
        return

    # KoreanStockDataFetcher 테스트
    print("\n" + "=" * 60)
    print("KoreanStockDataFetcher 테스트")
    print("=" * 60)

    try:
        from app.services.korean_stock_data import get_korean_stock_fetcher

        fetcher = get_korean_stock_fetcher()

        # 삼성전자 데이터 가져오기
        symbols = ["005930.KS", "005930"]  # 두 가지 형식 테스트

        for symbol in symbols:
            print(f"\n종목: {symbol}")
            print("-" * 40)

            data = fetcher.get_stock_data(symbol)

            if data:
                print(f"회사명: {data.get('name')}")
                print(f"현재가: {data.get('current_price', 0):,.0f}원")
                print(f"시가총액: {data.get('market_cap', 0) / 1e12:.1f}조원")

                metrics = data.get('metrics', {})
                print(f"\n[주요 지표]")
                print(f"  - P/E: {metrics.get('PE', 0):.1f}")
                print(f"  - P/B: {metrics.get('PB', 0):.1f}")
                print(f"  - ROE: {metrics.get('ROE', 0) * 100:.1f}%")
                print(f"  - ROA: {metrics.get('ROA', 0) * 100:.1f}%")
                print(f"  - 부채비율: {metrics.get('debt_to_equity', 0) * 100:.1f}%")
                print(f"  - EPS: {metrics.get('EPS', 0):,.0f}원")
                print(f"  - BPS: {metrics.get('BPS', 0):,.0f}원")
                print(f"  - 배당수익률: {metrics.get('DIV', 0):.2f}%")

                # 버핏 전략 지표
                print(f"\n[워렌 버핏 전략 지표]")
                buffett_metrics = fetcher.get_buffett_metrics(symbol)
                print(f"  - ROE: {buffett_metrics.get('ROE', 0) * 100 if buffett_metrics.get('ROE') else 0:.1f}%")
                print(f"  - 부채비율: {buffett_metrics.get('debt_to_equity', 0):.2f}")
                print(f"  - P/E: {buffett_metrics.get('PE', 0):.1f}")
                print(f"  - P/B: {buffett_metrics.get('PB', 0):.1f}")

                # 워렌 버핏 조건 체크
                print(f"\n[워렌 버핏 조건 체크 (8% 기준)]")
                roe = buffett_metrics.get('ROE', 0)
                if roe:
                    roe_pct = roe * 100 if roe < 1 else roe
                    print(f"  - ROE > 8%: {'PASS' if roe_pct > 8 else 'FAIL'} (현재: {roe_pct:.1f}%)")
                else:
                    print(f"  - ROE > 8%: FAIL (데이터 없음)")

                debt = buffett_metrics.get('debt_to_equity', 999)
                print(f"  - 부채비율 < 0.5: {'PASS' if debt < 0.5 else 'FAIL'} (현재: {debt:.2f})")

                pe = buffett_metrics.get('PE', 999)
                print(f"  - P/E < 25: {'PASS' if 0 < pe < 25 else 'FAIL'} (현재: {pe:.1f})")

                pb = buffett_metrics.get('PB', 999)
                print(f"  - P/B < 3: {'PASS' if pb < 3 else 'FAIL'} (현재: {pb:.1f})")

            else:
                print("[ERROR] 데이터를 가져올 수 없습니다.")

    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()

    # PyKrx 직접 테스트
    print("\n" + "=" * 60)
    print("PyKrx 직접 테스트 (비교용)")
    print("=" * 60)

    try:
        from pykrx import stock
        from datetime import datetime, timedelta

        # 최근 거래일 데이터
        today = datetime.now()
        start_date = (today - timedelta(days=30)).strftime('%Y%m%d')
        end_date = today.strftime('%Y%m%d')

        # 삼성전자 데이터
        ticker = "005930"

        print(f"\n종목: {ticker} (삼성전자)")
        print(f"기간: {start_date} ~ {end_date}")

        # 펀더멘털 데이터
        fundamental = stock.get_market_fundamental(start_date, end_date, ticker)
        if not fundamental.empty:
            latest = fundamental.iloc[-1]
            print(f"\n[PyKrx 펀더멘털 데이터 (최근 거래일)]")
            print(f"  - PER: {latest.get('PER', 0):.1f}")
            print(f"  - PBR: {latest.get('PBR', 0):.1f}")
            print(f"  - EPS: {latest.get('EPS', 0):,.0f}원")
            print(f"  - BPS: {latest.get('BPS', 0):,.0f}원")
            print(f"  - DIV: {latest.get('DIV', 0):.2f}%")

            # ROE 계산
            if latest.get('PBR') and latest.get('PER') and latest.get('PER') > 0:
                roe = latest.get('PBR') / latest.get('PER')
                print(f"  - ROE (계산): {roe * 100:.1f}%")

        # 시가총액 데이터
        cap_data = stock.get_market_cap(start_date, end_date, ticker)
        if not cap_data.empty:
            latest_cap = cap_data.iloc[-1]
            print(f"\n[시가총액 데이터 (최근 거래일)]")
            print(f"  - 시가총액: {latest_cap['시가총액'] / 1e12:.1f}조원")
            print(f"  - 상장주식수: {latest_cap['상장주식수']:,.0f}주")

    except Exception as e:
        print(f"[ERROR] PyKrx 직접 테스트 실패: {e}")

    print("\n" + "=" * 80)
    print("테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    test_pykrx_samsung()