"""
간단한 삼성전자 데이터 테스트
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.korean_stock_data import get_korean_stock_fetcher

def main():
    print("="*50)
    print("삼성전자 데이터 테스트")
    print("="*50)

    fetcher = get_korean_stock_fetcher()

    # 삼성전자 데이터
    symbol = "005930.KS"
    print(f"\n{symbol} 데이터 수집 중...")

    data = fetcher.get_stock_data(symbol)

    if data:
        print(f"\n회사명: {data.get('name')}")
        print(f"현재가: {data.get('current_price'):,.0f}원" if data.get('current_price') else "현재가: N/A")

        metrics = data.get('metrics', {})
        print(f"\n주요 지표:")
        if metrics.get('ROE') is not None:
            print(f"  ROE: {metrics['ROE']:.2f}%" if metrics['ROE'] > 1 else f"  ROE: {metrics['ROE']*100:.2f}%")
        else:
            print(f"  ROE: N/A")

        print(f"  P/E: {metrics.get('PE'):.2f}" if metrics.get('PE') else "  P/E: N/A")
        print(f"  P/B: {metrics.get('PB'):.2f}" if metrics.get('PB') else "  P/B: N/A")
        print(f"  부채비율: {metrics.get('debt_to_equity'):.2f}" if metrics.get('debt_to_equity') else "  부채비율: N/A")

        cashflow = data.get('cashflow', {})
        fcf = cashflow.get('free_cashflow')
        if fcf:
            print(f"  잉여현금흐름: {fcf:,.0f}원")
        else:
            print(f"  잉여현금흐름: N/A")

        # Buffett metrics 테스트
        print(f"\n버핏 지표:")
        buffett_metrics = fetcher.get_buffett_metrics(symbol)
        for key, value in buffett_metrics.items():
            if value is not None:
                if key == 'ROE':
                    print(f"  {key}: {value:.2f}%")
                elif key == 'free_cashflow':
                    print(f"  {key}: {value:,.0f}")
                else:
                    print(f"  {key}: {value:.2f}")
            else:
                print(f"  {key}: N/A")

        print(f"\n버핏 조건 충족 여부:")
        checks = []
        if buffett_metrics.get('ROE'):
            checks.append(f"ROE > 15%: {'✅' if buffett_metrics['ROE'] > 15 else '❌'} ({buffett_metrics['ROE']:.1f}%)")
        if buffett_metrics.get('debt_to_equity') is not None:
            checks.append(f"부채비율 < 0.5: {'✅' if buffett_metrics['debt_to_equity'] < 0.5 else '❌'} ({buffett_metrics['debt_to_equity']:.2f})")
        if buffett_metrics.get('PE'):
            checks.append(f"P/E < 25: {'✅' if buffett_metrics['PE'] < 25 else '❌'} ({buffett_metrics['PE']:.1f})")
        if buffett_metrics.get('PB'):
            checks.append(f"P/B < 3: {'✅' if buffett_metrics['PB'] < 3 else '❌'} ({buffett_metrics['PB']:.2f})")

        for check in checks:
            print(f"  {check}")

    else:
        print("데이터를 가져올 수 없습니다.")

if __name__ == "__main__":
    main()