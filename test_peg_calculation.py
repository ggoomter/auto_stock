"""
PEG Ratio 계산 테스트
한국 주식(삼성전자)과 미국 주식(AAPL)으로 테스트
"""
import sys
sys.path.append('backend')

from app.services.fundamental_analysis import FundamentalAnalyzer

def test_peg_calculation(symbol: str, name: str):
    """PEG 계산 테스트"""
    print(f"\n{'='*60}")
    print(f"종목: {name} ({symbol})")
    print(f"{'='*60}")

    analyzer = FundamentalAnalyzer(symbol)
    metrics = analyzer.get_lynch_metrics()

    print(f"\n[Peter Lynch Metrics]")
    print(f"  - Earnings Growth: {metrics.get('earnings_growth')}% (source: {metrics.get('earnings_growth_source')})")
    print(f"  - Revenue Growth: {metrics.get('revenue_growth')}% (source: {metrics.get('revenue_growth_source')})")

    peg = metrics.get('PEG')
    if peg is not None:
        print(f"  - PEG Ratio: {peg} (source: {metrics.get('PEG_source')})")
        if metrics.get('PEG_calculated'):
            print(f"    [OK] Calculated value")
    else:
        print(f"  - PEG Ratio: None")
        if 'PEG_missing_reason' in metrics:
            print(f"    [FAIL] Reason: {metrics['PEG_missing_reason']}")

    # 기본 정보
    info = analyzer.get_info()
    pe = info.get('trailingPE') or info.get('forwardPE')
    if pe:
        print(f"\n[Basic Metrics]")
        print(f"  - P/E Ratio: {pe:.2f}")

    # 린치 기준 체크
    criteria = analyzer.check_lynch_criteria()
    print(f"\n[Lynch Criteria]")
    print(f"  - PEG < 1.0: {'PASS' if criteria.get('low_PEG') else 'FAIL'}")
    print(f"  - Growth > 20%: {'PASS' if criteria.get('high_growth') else 'FAIL'}")
    print(f"  - Pass Rate: {criteria.get('passed_count', 0)}/{criteria.get('total_count', 2)}")

if __name__ == '__main__':
    # 한국 주식 테스트
    test_peg_calculation('005930.KS', '삼성전자')

    # 미국 주식 테스트
    test_peg_calculation('AAPL', 'Apple')

    print(f"\n{'='*60}")
    print("[NOTE]")
    print("  - Without DART API key: uses yfinance or calculated value")
    print("  - See DART_SETUP.md to configure API key")
    print(f"{'='*60}\n")
