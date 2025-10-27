"""
삼성전자 Jesse Livermore 전략 테스트 (실제 데이터)
"""
import requests
import json
from datetime import datetime, timedelta

# API 엔드포인트
BASE_URL = "http://localhost:8000/api/v1"

# 삼성전자 (005930) Jesse Livermore 전략 테스트
request_data = {
    "strategy_name": "livermore",
    "symbols": ["005930"],  # 삼성전자 코드 (자동으로 005930.KS로 변환됨)
    "date_range": {
        "start": "2024-01-01",
        "end": "2025-10-04"  # 오늘까지
    },
    "simulate": {
        "bootstrap_runs": 1000,
        "transaction_cost_bps": 10,
        "slippage_bps": 5
    }
}

print("=" * 80)
print("삼성전자 (005930) - Jesse Livermore 추세 추종 전략 백테스트")
print("=" * 80)
print(f"\n요청 데이터:")
print(json.dumps(request_data, indent=2, ensure_ascii=False))

# API 호출
response = requests.post(
    f"{BASE_URL}/master-strategy",
    json=request_data,
    timeout=60
)

print(f"\n응답 상태: {response.status_code}")

if response.status_code == 200:
    result = response.json()

    # 디버깅: 전체 응답 확인
    print("\n전체 응답 구조:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n" + "=" * 80)
    print("백테스트 결과")
    print("=" * 80)

    # 전략 정보
    print(f"\n전략: {result['strategy_info']['name']}")
    print(f"설명: {result['strategy_info']['description']}")
    print(f"보유 기간: {result['strategy_info']['holding_period']}")
    print(f"리스크 프로필: {result['strategy_info']['risk_profile']}")

    # 성과 지표
    metrics = result['backtest']['metrics']
    print(f"\n=== 성과 지표 ===")
    print(f"연평균 수익률 (CAGR): {metrics['CAGR']:.2%}")
    print(f"샤프 비율: {metrics['Sharpe']:.2f}")
    print(f"최대 낙폭 (MaxDD): {metrics['MaxDD']:.2%}")
    print(f"승률: {metrics.get('WinRate', metrics.get('HitRatio', 0)):.2%}")
    print(f"평균 수익: {metrics.get('AvgWin', 0):.2%}")
    print(f"평균 손실: {metrics.get('AvgLoss', 0):.2%}")
    print(f"총 거래 횟수: {metrics['TotalTrades']}")
    print(f"수익 거래: {metrics.get('WinTrades', 0)}")
    print(f"손실 거래: {metrics.get('LossTrades', 0)}")

    # 자산 현황
    print(f"\n=== 자산 현황 ===")
    print(f"초기 자본: ${result['initial_capital']:,.2f}")
    print(f"최종 자본: ${result['final_capital']:,.2f}")
    print(f"수익금: ${result['final_capital'] - result['initial_capital']:,.2f}")

    # 거래 내역 (최근 5개)
    if result['trade_history']:
        print(f"\n=== 거래 내역 (최근 5개) ===")
        for trade in result['trade_history'][:5]:
            print(f"\n매수: {trade['entry_date']} @ ${trade['entry_price']:,.2f}")
            print(f"매도: {trade['exit_date']} @ ${trade['exit_price']:,.2f}")
            print(f"보유일: {trade['holding_days']}일")
            print(f"수익률: {trade['pnl_pct']:.2f}%")
            print(f"수익금: ${trade['pnl']:,.2f}")
            print(f"청산 사유: {trade['exit_reason']}")

    # 시그널 예시
    if result['signal_examples']:
        print(f"\n=== 진입 시그널 예시 (최근 5개) ===")
        for signal in result['signal_examples'][:5]:
            print(f"날짜: {signal['date']} - {signal['symbol']}")

else:
    print(f"\n에러 발생:")
    print(response.text)

print("\n" + "=" * 80)
