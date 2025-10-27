"""
순수 Livermore 전략 API 테스트

API를 통해 순수 Livermore와 Modern Livermore 전략을 테스트합니다.
"""
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000/api/v1"

print("=" * 80)
print("순수 Livermore vs Modern Livermore API 테스트")
print("=" * 80)
print()

# 1. 전략 목록 확인
print("1️⃣ 전략 목록 확인")
print("-" * 80)
response = requests.get(f"{API_URL}/master-strategies")
if response.status_code == 200:
    strategies = response.json()
    print(f"✅ 총 {len(strategies['strategies'])}개 전략 로드")
    print()
    for strategy in strategies['strategies']:
        print(f"📌 {strategy['name']}")
        print(f"   {strategy['description']}")
        print()
else:
    print(f"❌ 에러: {response.status_code}")
    exit(1)

# 2. 순수 Livermore 테스트
print("=" * 80)
print("2️⃣ 순수 Jesse Livermore 전략 백테스트 (씨젠)")
print("=" * 80)
print()

pure_request = {
    "strategy_name": "livermore",
    "symbols": ["096530.KQ"],
    "date_range": {
        "start": "2024-01-01",
        "end": "2024-12-31"
    },
    "simulate": {
        "bootstrap_runs": 100,  # 빠른 테스트를 위해 100회로 감소
        "transaction_cost_bps": 10,
        "slippage_bps": 5
    },
    "output_detail": "full"
}

print(f"📤 요청:")
print(json.dumps(pure_request, indent=2, ensure_ascii=False))
print()

response = requests.post(f"{API_URL}/master-strategy", json=pure_request)

if response.status_code == 200:
    result = response.json()
    metrics = result['results'][0]['metrics']
    print(f"✅ 백테스트 완료")
    print()
    print(f"📊 성과 지표:")
    print(f"  - CAGR: {metrics['CAGR']:.2%}")
    print(f"  - Sharpe Ratio: {metrics['Sharpe']:.2f}")
    print(f"  - Max Drawdown: {metrics['MaxDD']:.2%}")
    print(f"  - Hit Ratio: {metrics['HitRatio']:.2%}")
    print(f"  - Total Trades: {metrics.get('TotalTrades', 0)}")
    print()

    if 'trades' in result['results'][0]:
        trades = result['results'][0]['trades']
        print(f"📋 거래 내역 ({len(trades)}건):")
        for idx, trade in enumerate(trades, 1):
            print(f"\n  거래 #{idx}:")
            print(f"    진입: {trade['entry_date']} {trade['entry_price']:,.0f}원")
            print(f"    청산: {trade['exit_date']} {trade['exit_price']:,.0f}원")
            print(f"    수량: {trade['shares']}주")
            print(f"    손익: {trade['pnl']:,.0f}원 ({trade['pnl_pct']:+.2%})")
            print(f"    보유: {trade['holding_days']}일")
            print(f"    사유: {trade['exit_reason']}")
        print()
else:
    print(f"❌ 에러: {response.status_code}")
    print(response.text)

# 3. Modern Livermore 테스트
print("=" * 80)
print("3️⃣ Modern Livermore 전략 백테스트 (씨젠)")
print("=" * 80)
print()

modern_request = {
    "strategy_name": "modern_livermore",
    "symbols": ["096530.KQ"],
    "date_range": {
        "start": "2024-01-01",
        "end": "2024-12-31"
    },
    "simulate": {
        "bootstrap_runs": 100,
        "transaction_cost_bps": 10,
        "slippage_bps": 5
    },
    "output_detail": "full"
}

print(f"📤 요청:")
print(json.dumps(modern_request, indent=2, ensure_ascii=False))
print()

response = requests.post(f"{API_URL}/master-strategy", json=modern_request)

if response.status_code == 200:
    result = response.json()
    metrics = result['results'][0]['metrics']
    print(f"✅ 백테스트 완료")
    print()
    print(f"📊 성과 지표:")
    print(f"  - CAGR: {metrics['CAGR']:.2%}")
    print(f"  - Sharpe Ratio: {metrics['Sharpe']:.2f}")
    print(f"  - Max Drawdown: {metrics['MaxDD']:.2%}")
    print(f"  - Hit Ratio: {metrics['HitRatio']:.2%}")
    print(f"  - Total Trades: {metrics.get('TotalTrades', 0)}")
    print()

    if 'trades' in result['results'][0]:
        trades = result['results'][0]['trades']
        print(f"📋 거래 내역 ({len(trades)}건):")
        for idx, trade in enumerate(trades, 1):
            print(f"\n  거래 #{idx}:")
            print(f"    진입: {trade['entry_date']} {trade['entry_price']:,.0f}원")
            print(f"    청산: {trade['exit_date']} {trade['exit_price']:,.0f}원")
            print(f"    수량: {trade['shares']}주")
            print(f"    손익: {trade['pnl']:,.0f}원 ({trade['pnl_pct']:+.2%})")
            print(f"    보유: {trade['holding_days']}일")
            print(f"    사유: {trade['exit_reason']}")
        print()
else:
    print(f"❌ 에러: {response.status_code}")
    print(response.text)

print("=" * 80)
print("✅ 테스트 완료")
print("=" * 80)
